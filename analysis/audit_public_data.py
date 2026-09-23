"""Print reproducible aggregate evidence from the explicitly allowed CSVs.

Run from repository root: python -X utf8 analysis/audit_public_data.py.
No joins to the target population, model fitting, environment imports or writes.
"""

import json
from pathlib import Path

import pandas as pd


def audit():
    root = Path(__file__).resolve().parents[1]
    profile = pd.read_csv(root / "customer_profile.csv")
    history_raw = pd.read_csv(root / "data" / "change_tariff.csv")
    history = history_raw.drop_duplicates().copy()
    catalog = pd.read_csv(root / "data" / "dict_tariff.csv")
    traffic = pd.read_csv(root / "data" / "traffic.csv")
    monthly = pd.read_csv(root / "data" / "arpu_monthly.csv")
    before = pd.to_numeric(history.AVG_ARPU_PREV_3M, errors="coerce")
    after = pd.to_numeric(history.AVG_ARPU_NEXT_3M, errors="coerce")
    history = history.loc[before.gt(0) & after.ge(0)].copy()
    history["ratio"] = (after - before) / before
    history["band"] = pd.cut(before, [-float("inf"), 999.999999, 5000, float("inf")], labels=["LOW", "MID", "HIGH"])
    by_band = history.groupby("band", observed=True).ratio.agg(["size", "median", "mean"])
    counts = history.groupby(["tariff_plan_code_from", "tariff_plan_code_to", "band"], observed=True).size()
    target_ids = set(profile.ID_NUMBER)
    return {
        "rows": {"profile": len(profile), "history": len(history_raw), "history_deduplicated": len(history_raw.drop_duplicates()),
                 "history_valid_before_after": len(history), "traffic": len(traffic), "monthly": len(monthly), "tariffs": len(catalog)},
        "id_overlap_counts_only_no_join": {"history": len(target_ids & set(history_raw.ID_NUMBER)),
            "traffic": len(target_ids & set(traffic.ID_NUMBER)), "monthly": len(target_ids & set(monthly.ID_NUMBER))},
        "arpu_medians": {"target_3m": float(profile.ARPU_3m_avg.median()), "target_predicted": float(profile.predicted_arpu.median()),
                         "history_pre_all": float(before.median())},
        "valid_lift_raw": {"median": float(history.ratio.median()), "mean": float(history.ratio.mean())},
        "history_by_pre_arpu_band": by_band.to_dict(orient="index"),
        "pair_band_support": {"groups": len(counts), "median_n": float(counts.median()), "at_least_20": int(counts.ge(20).sum())},
        "historical_destination_count": int(history.tariff_plan_code_to.nunique()),
        "target_lte_exceeds_total_fraction": float(profile.LTE_DATA_VOLUME.gt(profile.DATA_VOLUME).mean()),
        "monthly_duplicate_id_month_rows": int(monthly.duplicated(["ID_NUMBER", "TIME_KEY"], keep=False).sum()),
        "target_missing_filters": profile[["current_tariff", "arpu_segment", "data_segment", "call_segment"]].isna().sum().to_dict(),
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2, allow_nan=False))
