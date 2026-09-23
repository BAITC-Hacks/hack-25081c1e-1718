"""Public-data transition hypotheses, deliberately weak until tested by pilots.

No environment access, channel selection, customer-ID joins, or output writes.
Historical before/after association is not a causal campaign effect.
"""

import hashlib
import json
import math
from pathlib import Path

import pandas as pd


SEGMENTS = {
    "arpu_segment": {"LOW", "MID", "HIGH"},
    "data_segment": {"NON_USER", "LITE", "HEAVY"},
    "call_segment": {"LOW", "MEDIUM", "HIGH"},
}
HISTORY_COLUMNS = ["tariff_plan_code_from", "tariff_plan_code_to",
                   "AVG_ARPU_PREV_3M", "AVG_ARPU_NEXT_3M"]
MAX_CANDIDATES = 320
OFFER_FIELDS = ("price_tariff", "Data_in_PKG", "Min_another_operator_in_PKG",
                "Min_another_operator_and_city_in_PKG")


def _number(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _median(frame, name):
    if name not in frame:
        return 0.0
    values = pd.to_numeric(frame[name], errors="coerce")
    values = values.where(values.map(lambda x: math.isfinite(x) if pd.notna(x) else False))
    return max(0.0, _number(values.median())) if values.notna().any() else 0.0


def _history(data_dir):
    """Read one explicitly allowed CSV; never infer target labels from IDs."""
    try:
        frame = pd.read_csv(Path(data_dir) / "change_tariff.csv")
    except (OSError, ValueError, TypeError, pd.errors.ParserError, UnicodeError):
        return {}
    if not set(HISTORY_COLUMNS).issubset(frame.columns):
        return {}
    # Remove exact duplicated records, not unrelated equal-valued observations.
    frame = frame.drop_duplicates().copy()
    before = pd.to_numeric(frame["AVG_ARPU_PREV_3M"], errors="coerce")
    after = pd.to_numeric(frame["AVG_ARPU_NEXT_3M"], errors="coerce")
    finite = before.map(math.isfinite) & after.map(math.isfinite)
    good = finite & before.gt(0) & after.ge(0)
    good &= frame["tariff_plan_code_from"].notna() & frame["tariff_plan_code_to"].notna()
    good &= frame["tariff_plan_code_from"].ne(frame["tariff_plan_code_to"])
    frame = frame.loc[good].copy()
    before, after = before.loc[good], after.loc[good]
    # Public segment thresholds; do not pool LOW-denominator effects into HIGH.
    frame["band"] = "MID"
    frame.loc[before.lt(1000), "band"] = "LOW"
    frame.loc[before.gt(5000), "band"] = "HIGH"
    frame["ratio"] = ((after - before) / before).clip(-1.0, 1.0)
    stats = frame.groupby(["tariff_plan_code_from", "tariff_plan_code_to", "band"], observed=True)["ratio"].agg(["median", "count", "mean"])
    return {tuple(map(str, key)): (_number(row["median"]), int(row["count"]), _number(row["mean"]))
            for key, row in stats.iterrows()}


def _prior(history, current, target, band):
    median, count, mean = history.get((current, target, band), (0.0, 0, 0.0))
    # A regularized association, not an estimated treatment effect: 90% transfer
    # discount, 50-observation zero prior, and bounded robust magnitude.
    prior = 0.1 * count / (count + 50) * max(-0.25, min(0.25, median))
    if band == "LOW" or count < 10 or median * mean <= 0:
        prior = 0.0
    return prior, count, median


def _fit(plan, demand_data, demand_voice, reference):
    data = max(0.0, _number(plan.get("Data_in_PKG")))
    voice = max(0.0, _number(plan.get("Min_another_operator_in_PKG")))
    voice += max(0.0, _number(plan.get("Min_another_operator_and_city_in_PKG")))
    shortages, waste = [], []
    for supplied, needed in ((data, demand_data), (voice, demand_voice)):
        if needed > 0:
            shortages.append(max(0.0, needed - supplied) / needed)
            waste.append(max(0.0, supplied - needed) / max(supplied, needed))
    shortfall = sum(shortages) / max(1, len(shortages))
    unused = sum(waste) / max(1, len(waste))
    price = max(0.0, _number(plan.get("price_tariff")))
    stretch = max(0.0, price / reference - 1.0)
    # Ranking heuristics only. None of these package/price terms become a lift.
    return shortfall + 0.15 * unused + stretch


def _same_offer(left, right):
    # Missing catalog attributes do not establish offer equivalence.
    return all(name in left and name in right and pd.notna(left[name]) and pd.notna(right[name])
               and _number(left[name], None) is not None
               and _number(left[name], None) == _number(right[name], None) for name in OFFER_FIELDS)


def build_candidates(profile, tariffs, data_dir) -> list[dict]:
    """Return <=320 deterministic filter-expressible candidates, using 3 inputs.

    priors are fractional pre-channel ARPU associations, max absolute 2.5%.
    prior_n is the number of valid deduplicated historical observations, never
    a pseudo sample size or a count of matching target subscribers.
    """
    if not isinstance(profile, pd.DataFrame) or not isinstance(tariffs, pd.DataFrame):
        return []
    if profile.empty or tariffs.empty or not {"current_tariff", "predicted_arpu"}.issubset(profile.columns):
        return []
    if "tariff_plan_code" not in tariffs:
        return []
    catalog = {}
    for _, row in tariffs.iterrows():
        code = row["tariff_plan_code"]
        if isinstance(code, str) and code.strip() and ";" not in code:
            catalog[code] = row.to_dict()
    if len(catalog) < 2:
        return []
    history = _history(data_dir)
    group_columns = ["current_tariff"] + [name for name in SEGMENTS if name in profile]
    cells = []
    for keys, group in profile.groupby(group_columns, observed=True, sort=True, dropna=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        values = dict(zip(group_columns, keys))
        current = values["current_tariff"]
        if current not in catalog or not 10 <= len(group) <= 5000:
            continue
        if any(value not in SEGMENTS[name] for name, value in values.items() if name in SEGMENTS):
            continue
        revenue = pd.to_numeric(group["predicted_arpu"], errors="coerce").replace([float("inf"), -float("inf")], 0).fillna(0).clip(lower=0)
        arpu_sum = _number(revenue.sum())
        if arpu_sum <= 0:
            continue
        price = max(0.0, _number(catalog[current].get("price_tariff")))
        reference = max(price, _median(group, "predicted_arpu"), 1.0)
        demand_data = _median(group, "DATA_VOLUME")
        demand_voice = _median(group, "OUT_LOC_OFFNET_MIN") + _median(group, "OUT_LOC_LAND_MIN")
        band = str(values.get("arpu_segment", ""))
        choices = []
        for target in sorted(catalog):
            if target == current:
                continue
            target_price = max(0.0, _number(catalog[target].get("price_tariff")))
            prior, count, median = _prior(history, current, target, band)
            if prior <= 0 and _same_offer(catalog[current], catalog[target]):
                continue
            fit = _fit(catalog[target], demand_data, demand_voice, reference)
            choices.append({"target": target, "price": target_price, "prior": prior,
                            "count": count, "median": median, "fit": fit})
        if not choices:
            continue
        # Prefer bounded fee changes. Price is a hypothesis, never predicted ARPU.
        affordable = [item for item in choices if item["price"] <= 1.5 * reference]
        pool = affordable or choices
        upgrades = [item for item in pool if item["price"] > price]
        nondecreasing = [item for item in pool if item["price"] >= price]
        primary = min(upgrades or nondecreasing or pool,
                      key=lambda item: (max(0, item["price"] - price) / reference + item["fit"], item["target"]))
        chosen = [(primary, "Умеренный переход по цене/пакету")]
        alternatives = [item for item in pool if item["target"] != primary["target"]
                        and (item["prior"] > 0 or not _same_offer(catalog[item["target"]], catalog[primary["target"]]))]
        # Positive same-band observations may justify testing a lower-fee offer,
        # but never establish a causal benefit. Sparse pairs do not outrank fit.
        supported = [item for item in alternatives if item["prior"] > 0 and item["fit"] <= 0.75]
        if supported:
            alternative = max(supported, key=lambda item: (item["prior"] - 0.01 * item["fit"], -item["price"], item["target"]))
            chosen.append((alternative, "Историческая гипотеза по ARPU-группе"))
        else:
            alternatives = [item for item in alternatives if item["price"] >= price]
            if alternatives:
                alternative = min(alternatives, key=lambda item: (item["fit"], abs(item["price"] - price), item["target"]))
                chosen.append((alternative, "Альтернатива по потреблению/пакету"))
        filters = {"filter_" + name: str(value) for name, value in values.items()}
        entries = []
        for item, hypothesis in chosen:
            signature = json.dumps([filters, item["target"]], sort_keys=True)
            if not item["count"]:
                prior_text = "Нет истории той же ARPU-группы; приор 0."
            elif not item["prior"]:
                reason = "малый ARPU до" if band == "LOW" else "мало/смешанная история"
                prior_text = f"История иной выборки: n={item['count']}; приор 0 ({reason})."
            else:
                prior_text = f"История иной выборки: n={item['count']}, огранич. медиана={item['median']:+.1%}; приор={item['prior']:+.2%}."
            risk = " Возможен downsell." if item["price"] < price else ""
            entries.append({"candidate_id": "c_" + hashlib.sha256(signature.encode()).hexdigest()[:14],
                            "filters": dict(filters), "target_tariff": item["target"],
                            "audience_size": int(len(group)), "arpu_sum": arpu_sum,
                            "prior_lift_ratio": float(item["prior"]), "prior_n": item["count"],
                            "rationale": f"{prior_text} {hypothesis}.{risk} Нужен пилот."})
        cells.append((arpu_sum, json.dumps(filters, sort_keys=True), entries))
    cells.sort(key=lambda cell: (-cell[0], cell[1]))
    # Preserve segment breadth before adding a second target, within core's cap.
    return [entries[tier] for tier in range(2) for _, _, entries in cells if len(entries) > tier][:MAX_CANDIDATES]
