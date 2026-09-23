"""ARPU Compass: propose, pilot, revise, and allocate using only public data."""

import hashlib
import importlib
import json
import math
from pathlib import Path
import time

import pandas as pd

from llm_advisor import Advisor

ROOT = Path(__file__).resolve().parent
CHANNEL_COSTS = {"push": 0.0, "sms": 4.0, "digital_ads": 22.0, "call": 160.0}
CHANNEL_EFFECT = {"push": 0.50, "sms": 0.65, "digital_ads": 0.85, "call": 1.20}
FILTERS = {
    "filter_current_tariff": "current_tariff", "filter_arpu_segment": "arpu_segment",
    "filter_data_segment": "data_segment", "filter_call_segment": "call_segment",
}


def finite(value, default=0.0):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (ValueError, TypeError, OverflowError):
        return default


class Agent:
    def __init__(self):
        self.last_report = {}

    @staticmethod
    def _resources(env):
        return {"remaining_budget": finite(env.remaining_budget),
                "remaining_contacts": int(finite(env.remaining_contacts)),
                "pilots_left": int(finite(env.pilots_left))}

    @staticmethod
    def _history():
        """Provisional historical prior, never a measured target-population effect."""
        frame = pd.read_csv(ROOT / "data" / "change_tariff.csv")
        before = pd.to_numeric(frame["AVG_ARPU_PREV_3M"], errors="coerce")
        after = pd.to_numeric(frame["AVG_ARPU_NEXT_3M"], errors="coerce")
        frame = frame.loc[(before > 0) & after.notna()].copy()
        # Small denominators create extreme ratios; keep a bounded robust median.
        frame["ratio"] = ((after - before) / before).clip(-0.5, 1.0)
        pairs = frame.groupby(["tariff_plan_code_from", "tariff_plan_code_to"])["ratio"].agg(["median", "count"])
        return {tuple(map(str, pair)): (finite(row["median"]), int(row["count"]))
                for pair, row in pairs.iterrows()}

    def _fallback_candidates(self, profile, tariffs, warnings):
        try:
            history = self._history()
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            history = {}
            warnings.append("historical_prior_unavailable")
        prices = {}
        if "price_tariff" in tariffs:
            prices = {str(row["tariff_plan_code"]): finite(row["price_tariff"])
                      for _, row in tariffs.iterrows()}
        valid = sorted(str(item) for item in tariffs["tariff_plan_code"])
        raw, groups = [], []
        # A conservative standalone shortlist while the specialist data module is
        # pending. Narrow cells limit exposure to an unreliable historical prior.
        names = ["current_tariff", "arpu_segment", "data_segment", "call_segment"]
        for keys, group in profile.groupby(names, observed=True):
            filters = {"filter_" + name: str(value) for name, value in zip(names, keys)}
            groups.append((filters, group))
        for filters, group in groups:
            if not 10 <= len(group) <= 5000:
                continue
            current = filters["filter_current_tariff"]
            available = [target for target in valid if target != current]
            higher = sorted((target for target in available if prices.get(target, 0) > prices.get(current, 0)),
                            key=lambda target: prices.get(target, 0))
            targets = list(dict.fromkeys(higher[:1] + higher[-1:])) if higher else available[:2]
            for target in targets:
                ratio, count = history.get((current, target), (0.0, 0))
                raw.append({"filters": filters, "target_tariff": target,
                            "prior_lift_ratio": 0.0, "prior_n": 0,
                            "rationale": "Ценовая гипотеза; история другой выборки (median={:.3f}, n={}) не принята за эффект.".format(ratio, count)})
        return raw

    def _candidates(self, profile, tariffs, warnings):
        raw, source = [], "builtin_price_hypotheses"
        try:
            module = importlib.import_module("candidate_model")
            raw = module.build_candidates(profile.copy(deep=True), tariffs.copy(deep=True), ROOT / "data")
            source = "candidate_model"
        except ModuleNotFoundError as error:
            if error.name != "candidate_model":
                warnings.append("candidate_model_dependency_missing")
        except Exception:
            warnings.append("candidate_model_failed")
        if not isinstance(raw, list) or not raw:
            raw = self._fallback_candidates(profile, tariffs, warnings)
            source = "builtin_price_hypotheses"
        normalized = self._normalize(raw, profile, tariffs)
        if not normalized and source == "candidate_model":
            warnings.append("candidate_model_no_valid_candidates")
            normalized = self._normalize(self._fallback_candidates(profile, tariffs, warnings), profile, tariffs)
            source = "builtin_price_hypotheses"
        return normalized, source

    @staticmethod
    def _normalize(raw, profile, tariffs):
        valid_tariffs = set(tariffs["tariff_plan_code"].astype(str))
        columns = {key: profile[column].astype("string") for key, column in FILTERS.items()}
        revenue = pd.to_numeric(profile["predicted_arpu"], errors="coerce").replace([float("inf"), -float("inf")], 0).fillna(0).clip(lower=0)
        normalized, seen = [], set()
        for proposal in raw[:400]:
            if not isinstance(proposal, dict) or not isinstance(proposal.get("target_tariff"), str):
                continue
            if proposal["target_tariff"] not in valid_tariffs:
                continue
            filters = proposal.get("filters", {})
            if not isinstance(filters, dict) or not filters or any(key not in FILTERS for key in filters):
                continue
            if any(not isinstance(value, str) or not value.strip() for value in filters.values()):
                continue
            mask = pd.Series(True, index=profile.index)
            for key, value in filters.items():
                values = [part.strip() for part in value.split(";")] if key == "filter_current_tariff" else [value]
                mask &= columns[key].isin(values).fillna(False)
            size = int(mask.sum())
            if not 10 <= size <= 5000:
                continue
            # Every selected subscriber must be offered a different tariff.
            # Reject mixed unions too; silently removing rows would change coverage.
            if bool((columns["filter_current_tariff"].loc[mask] == proposal["target_tariff"]).any()):
                continue
            signature = json.dumps([filters, proposal["target_tariff"]], sort_keys=True)
            cid = "c_" + hashlib.sha256(signature.encode()).hexdigest()[:14]
            if cid in seen:
                continue
            seen.add(cid)
            normalized.append({
                "candidate_id": cid, "filters": dict(filters), "target_tariff": proposal["target_tariff"],
                "audience_size": size, "arpu_sum": finite(revenue.loc[mask].sum()),
                "prior_lift_ratio": max(-0.5, min(1.0, finite(proposal.get("prior_lift_ratio")))),
                "prior_n": max(0, int(finite(proposal.get("prior_n")))),
                "rationale": str(proposal.get("rationale", ""))[:180],
                "members": frozenset(profile.loc[mask, "ID_NUMBER"].tolist()),
                "segment_key": json.dumps(filters, sort_keys=True),
            })
        return sorted(normalized, key=lambda item: item["arpu_sum"] * (max(0, item["prior_lift_ratio"]) + 0.01), reverse=True)

    @staticmethod
    def _estimate(candidate, observations, channel):
        rows = [row for row in observations if row["candidate_id"] == candidate["candidate_id"] and row["status"] == "completed"]
        # The target population differs: history ranks exploration, but contributes
        # only a weak bounded prior once we have actual pilot feedback.
        weight = min(5, candidate["prior_n"])
        total = sum(row["n_customers"] for row in rows)
        prior = max(-0.15, min(0.15, candidate["prior_lift_ratio"]))
        numerator = prior * CHANNEL_EFFECT[channel] * weight
        numerator += sum(row["observed_lift_ratio"] * CHANNEL_EFFECT[channel] / CHANNEL_EFFECT[row["channel"]] * row["n_customers"] for row in rows)
        mean = numerator / max(1, weight + total)
        uncertainty = 0.07 * math.sqrt(150 / max(1, weight + total))
        if rows:
            uncertainty *= max(CHANNEL_EFFECT[channel] / CHANNEL_EFFECT[row["channel"]] for row in rows)
        lower = mean - 0.8 * uncertainty
        return {"posterior_mean": mean, "uncertainty": uncertainty, "n_customers": total,
                "estimated_net": mean * candidate["arpu_sum"] - CHANNEL_COSTS[channel] * candidate["audience_size"],
                "conservative_net": lower * candidate["arpu_sum"] - CHANNEL_COSTS[channel] * candidate["audience_size"],
                "repeats": len(rows)}

    @staticmethod
    def _diverse(candidates):
        first, rest, seen = [], [], set()
        for candidate in candidates:
            if candidate["segment_key"] in seen:
                rest.append(candidate)
            else:
                first.append(candidate)
                seen.add(candidate["segment_key"])
        return first + rest

    def _advice(self, advisor, candidates, observations, env, phase, channel, events):
        payload = [{key: value for key, value in item.items() if key not in {"members", "segment_key"}} |
                   self._estimate(item, observations, channel) | {"channel": channel} for item in candidates[:24]]
        try:
            result = advisor.recommend(payload, observations, self._resources(env), phase)
            selected = result["candidate_ids"]
            valid = {item["candidate_id"] for item in candidates[:24]}
            if not isinstance(selected, list) or any(not isinstance(cid, str) or cid not in valid for cid in selected):
                raise ValueError("invalid_advice")
            if selected:
                order = {cid: index for index, cid in enumerate(selected)}
                events.append({"role": "advisor", "phase": phase, "status": "completed", "candidate_ids": selected,
                               "summary": str(result.get("summary", ""))[:500]})
                return sorted(candidates, key=lambda item: order.get(item["candidate_id"], len(selected)))
        except Exception:
            events.append({"role": "advisor", "phase": phase, "status": "fallback"})
        return candidates

    def act(self, env):
        started = time.monotonic()
        warnings, observations, events = [], [], []
        advisor = Advisor()
        profile, tariffs = env.customer_profile, env.tariffs
        channels = [str(channel) for channel in env.channels if str(channel) in CHANNEL_COSTS]
        if not channels:
            self.last_report = {"schema_version": "1.0", "engine": "adaptive-offline", "campaigns": [],
                                "pilots": [], "resources": self._resources(env), "warnings": ["no_supported_channels"]}
            return []
        scout = "sms" if "sms" in channels else min(channels, key=lambda channel: CHANNEL_COSTS[channel])
        candidates, source = self._candidates(profile, tariffs, warnings)
        candidates = self._diverse(candidates)
        events.append({"role": "analyst", "status": "completed", "source": source, "candidate_count": len(candidates)})
        initial = self._diverse(self._advice(advisor, candidates, observations, env, "initial", scout, events))
        attempts, failed, feedback_order = {}, set(), {}
        for step in range(min(20, int(env.pilots_left))):
            if time.monotonic() - started > 220 or int(env.pilots_left) <= 0:
                break
            if step == 8:
                pool = sorted(candidates, key=lambda item: self._estimate(item, observations, scout)["estimated_net"], reverse=True)
                revised = self._advice(advisor, pool, observations, env, "feedback", scout, events)
                feedback_order = {item["candidate_id"]: index for index, item in enumerate(revised)}
            available = [item for item in initial if attempts.get(item["candidate_id"], 0) < 3 and item["candidate_id"] not in failed]
            if step < 8:
                available = [item for item in available if not attempts.get(item["candidate_id"])]
            else:
                def pilot_priority(item):
                    estimate = self._estimate(item, observations, scout)
                    optimism = estimate["posterior_mean"] + 0.25 * estimate["uncertainty"]
                    value = optimism * item["arpu_sum"] - CHANNEL_COSTS[scout] * item["audience_size"]
                    if not estimate["repeats"]:
                        value = (max(0, item["prior_lift_ratio"]) * CHANNEL_EFFECT[scout] + 0.01) * item["arpu_sum"]
                    preference = 1.0 + 0.10 / (1 + feedback_order.get(item["candidate_id"], 24))
                    return value * preference / math.sqrt(1 + estimate["repeats"])
                available.sort(key=pilot_priority, reverse=True)
                # Prioritize confirmation before more history-driven exploration.
                # Otherwise optimistic historical pairs crowd out real feedback.
                confirmation = [item for item in available
                                if self._estimate(item, observations, scout)["repeats"]
                                and pilot_priority(item) > 0]
                if confirmation:
                    available = confirmation
                elif any(self._estimate(item, observations, scout)["repeats"] >= 2
                         and self._estimate(item, observations, scout)["conservative_net"] > 0 for item in candidates):
                    break
                else:
                    available = [item for item in available if not attempts.get(item["candidate_id"])]
            chosen = None
            resources = self._resources(env)
            reserve_contacts = min((item["audience_size"] for item in candidates), default=0)
            reserve_cost = reserve_contacts * min(CHANNEL_COSTS[channel] for channel in channels)
            for item in available:
                previous = attempts.get(item["candidate_id"], 0)
                sample = min(item["audience_size"], 150 if previous == 0 else 200)
                if sample < 10 or sample + reserve_contacts > resources["remaining_contacts"]:
                    continue
                if sample * CHANNEL_COSTS[scout] + reserve_cost > resources["remaining_budget"]:
                    continue
                chosen = item
                break
            if chosen is None:
                break
            cid = chosen["candidate_id"]
            attempts[cid] = attempts.get(cid, 0) + 1
            try:
                result = env.run_pilot(target_tariff=chosen["target_tariff"], channel=scout,
                                       n_customers=sample, **chosen["filters"])
                ratio = finite(result.get("observed_lift_ratio"), None)
                if ratio is None:
                    raise ValueError("nonfinite_pilot")
                observations.append({"candidate_id": cid, "target_tariff": chosen["target_tariff"],
                                     "filters": chosen["filters"], "channel": scout, "n_customers": sample,
                                     "observed_lift_ratio": ratio, "status": "completed"})
            except Exception:
                failed.add(cid)
                observations.append({"candidate_id": cid, "target_tariff": chosen["target_tariff"],
                                     "channel": scout, "n_customers": sample, "status": "failed"})
                warnings.append("pilot_failed_" + cid)
            events.append({"role": "experimenter", "step": step + 1, "candidate_id": cid,
                           "action": "confirm" if attempts[cid] > 1 else "explore", "status": observations[-1]["status"]})

        resources = self._resources(env)
        budget, contacts = resources["remaining_budget"], resources["remaining_contacts"]
        options = []
        for item in candidates:
            for channel in channels:
                estimate = self._estimate(item, observations, channel)
                if estimate["repeats"]:
                    options.append((estimate["conservative_net"], item, channel, estimate))
        options.sort(key=lambda option: option[0], reverse=True)
        campaigns, allocation, members = [], [], set()

        def add_campaign(item, channel, estimate, fallback=False):
            cost = CHANNEL_COSTS[channel] * item["audience_size"]
            campaigns.append({"campaign_name": ("fallback_" if fallback else "compass_") + item["candidate_id"],
                              **item["filters"], "target_tariff": item["target_tariff"], "channel": channel})
            allocation.append({"candidate_id": item["candidate_id"], "channel": channel,
                               "audience_size": item["audience_size"], "communication_cost": cost, **estimate})
            return cost

        for score, item, channel, estimate in options:
            cost = CHANNEL_COSTS[channel] * item["audience_size"]
            if score <= 0 or estimate["repeats"] < 2 or item["members"] & members or cost > budget or item["audience_size"] > contacts:
                continue
            budget -= add_campaign(item, channel, estimate)
            contacts -= item["audience_size"]
            members.update(item["members"])
            if len(campaigns) >= 10:
                break
        if not campaigns:
            cheapest = min(channels, key=lambda channel: CHANNEL_COSTS[channel])
            observed = [item for item in candidates if self._estimate(item, observations, cheapest)["repeats"]]
            # Minimum one campaign is mandatory; report this explicitly as fallback.
            for pool in (observed, candidates):
                ranked = sorted(pool, key=lambda item: self._estimate(item, observations, cheapest)["conservative_net"], reverse=True)
                for item in ranked:
                    cost = CHANNEL_COSTS[cheapest] * item["audience_size"]
                    if item["audience_size"] <= contacts and cost <= budget:
                        budget -= add_campaign(item, cheapest, self._estimate(item, observations, cheapest), fallback=True)
                        contacts -= item["audience_size"]
                        warnings.append("no_positive_conservative_plan_fallback" if observed else "unobserved_fallback")
                        break
                if campaigns:
                    break
        events.append({"role": "allocator", "status": "completed", "campaign_count": len(campaigns)})
        self.last_report = {
            "schema_version": "1.0", "engine": "adaptive-openai" if any(event["status"] == "completed" for event in advisor.events) else "adaptive-offline",
            "candidate_source": source, "candidate_count": len(candidates),
            "resource_stage": "after_pilots_before_final_campaigns", "resources": resources,
            "planned_resources": {"remaining_budget": budget, "remaining_contacts": contacts},
            "campaigns": campaigns, "allocation": allocation, "pilots": observations,
            "events": events, "advisor": advisor.events, "warnings": sorted(set(warnings)),
            "uncertainty_note": "Approximate planning margin from public template; not a calibrated confidence interval.",
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        return campaigns
