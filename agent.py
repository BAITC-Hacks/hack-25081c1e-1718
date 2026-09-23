"""ARPU Compass: propose, pilot, revise, and allocate using only public data."""

import hashlib
import importlib
import json
import math
from pathlib import Path
import time

import pandas as pd

try:
    from llm_advisor import Advisor
except ModuleNotFoundError as error:
    if error.name != "llm_advisor":
        raise

    class Advisor:
        """Allow a minimal agent.py-only upload to remain autonomous."""

        def __init__(self):
            self.events = []

        def recommend(self, candidates, observations, resources, phase):
            self.events.append({"phase": phase, "status": "skipped", "reason": "advisor_module_unavailable"})
            return {"candidate_ids": [], "summary": ""}

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
    def __init__(self, *, exploration_policy="baseline", uncertainty_mode="template", pilot_sizing="fixed"):
        if exploration_policy not in {"baseline", "balanced", "confirmation_first"}:
            raise ValueError("exploration_policy must be baseline, balanced or confirmation_first")
        if uncertainty_mode not in {"template", "empirical"}:
            raise ValueError("uncertainty_mode must be template or empirical")
        if pilot_sizing not in {"fixed", "adaptive"}:
            raise ValueError("pilot_sizing must be fixed or adaptive")
        self.pilot_sizing = pilot_sizing
        self.exploration_policy = exploration_policy
        self.uncertainty_mode = uncertainty_mode
        self._exploration_categories = {}
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
        # Standalone fallback when the specialist module is unavailable.
        # Narrow cells limit exposure to an unreliable historical prior.
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
    def _estimate(candidate, observations, channel, uncertainty_mode="template"):
        rows = [row for row in observations if row["candidate_id"] == candidate["candidate_id"]
                and row["status"] == "completed" and row["channel"] == channel]
        # The target population differs: history ranks exploration, but contributes
        # only a weak bounded prior once we have actual pilot feedback.
        weight = min(5, candidate["prior_n"])
        total = sum(row["n_customers"] for row in rows)
        prior = max(-0.15, min(0.15, candidate["prior_lift_ratio"]))
        numerator = prior * CHANNEL_EFFECT[channel] * weight
        # The response's channel semantics are not fully specified. A measured
        # SMS arm is not evidence for an untested advertising/call arm.
        numerator += sum(row["observed_lift_ratio"] * row["n_customers"] for row in rows)
        mean = numerator / max(1, weight + total)
        template_uncertainty = 0.07 * math.sqrt(150 / max(1, total))
        sample_std = None
        empirical_se = None
        if len(rows) >= 2:
            weights = [max(1, int(finite(row.get("n_customers"), 0))) for row in rows]
            observed = [finite(row.get("observed_lift_ratio"), 0.0) for row in rows]
            weight_sum = sum(weights)
            weight_squared = sum(weight * weight for weight in weights)
            observed_mean = sum(weight * value for weight, value in zip(weights, observed)) / max(1, weight_sum)
            denominator = weight_sum - weight_squared / max(1, weight_sum)
            if denominator > 0:
                variance = sum(weight * (value - observed_mean) ** 2
                               for weight, value in zip(weights, observed)) / denominator
                sample_std = math.sqrt(max(0.0, variance))
                effective_n = weight_sum * weight_sum / max(1, weight_squared)
                empirical_se = sample_std / math.sqrt(max(1.0, effective_n))
        if uncertainty_mode == "empirical" and empirical_se is not None:
            uncertainty = max(template_uncertainty, empirical_se)
            uncertainty_method = "max_template_empirical"
        else:
            uncertainty = template_uncertainty
            uncertainty_method = "template_floor"
        lower = mean - 0.8 * uncertainty
        return {"posterior_mean": mean, "uncertainty": uncertainty, "template_uncertainty": template_uncertainty,
                "sample_std": sample_std, "empirical_se": empirical_se,
                "uncertainty_method": uncertainty_method, "n_customers": total,
                "estimated_net": mean * candidate["arpu_sum"] - CHANNEL_COSTS[channel] * candidate["audience_size"],
                "conservative_net": lower * candidate["arpu_sum"] - CHANNEL_COSTS[channel] * candidate["audience_size"],
                "repeats": len(rows)}

    def _pilot_sample(self, candidate, observations, channel, *, first_sample):
        """Heuristic repeat size from own-channel distance to break-even.

        Keep first observations unchanged. This inverts the existing planning
        margin, not a calibrated confidence interval or a per-customer variance.
        A repeat always samples at least 50 (or the entire smaller audience).
        Budget/contact reservations are checked by the caller.
        """
        estimate = self._estimate(candidate, observations, channel, self.uncertainty_mode)
        if not estimate["repeats"]:
            return min(candidate["audience_size"], first_sample)
        if self.pilot_sizing == "fixed":
            return min(candidate["audience_size"], 200)
        average_arpu = candidate["arpu_sum"] / max(1, candidate["audience_size"])
        if average_arpu <= 0:
            return min(candidate["audience_size"], 200)
        distance = abs(estimate["posterior_mean"] - CHANNEL_COSTS[channel] / average_arpu)
        # Clamp before squaring: only <=200 additional samples can be used.
        if not math.isfinite(distance) or distance <= 1e-9:
            requested = 200
        else:
            target_total = 150 * (0.8 * 0.07 / distance) ** 2
            requested = 200 if target_total >= estimate["n_customers"] + 200 else max(
                50, math.ceil(target_total - estimate["n_customers"]))
        return min(candidate["audience_size"], requested)

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

    def _balanced_shortlist(self, candidates):
        """Choose 3/3/2 first, then round-robin the baskets up to 24 IDs."""
        ordered = list(candidates)
        revenue = sorted(ordered, key=lambda item: (-item["arpu_sum"], item["candidate_id"]))
        positive = sorted((item for item in ordered if item["prior_lift_ratio"] > 0),
                          key=lambda item: (-item["prior_lift_ratio"], -item["prior_n"], item["candidate_id"]))
        selected, seen, transitions = [], set(), set()
        self._exploration_categories = {}

        def add(category):
            pool = positive if category == "history" else revenue if category != "ranking" else ordered
            for item in pool:
                cid = item["candidate_id"]
                transition = (str(item.get("filters", {}).get("filter_current_tariff", "")),
                              str(item.get("target_tariff", "")))
                if cid in seen or (category == "transition" and transition in transitions):
                    continue
                selected.append(item)
                seen.add(cid)
                self._exploration_categories[cid] = category
                if category == "transition":
                    transitions.add(transition)
                return True
            return False

        for category, quota in (("revenue", 3), ("transition", 3), ("history", 2)):
            for _ in range(quota):
                if not add(category):
                    break
        while len(selected) < 8 and add("ranking"):
            pass
        while len(selected) < 24:
            added = False
            for category in ("revenue", "transition", "history"):
                if len(selected) < 24:
                    added = add(category) or added
            if not added and not add("ranking"):
                break
        return selected

    def _respect_initial_quota(self, ordered, candidates):
        """Keep advisor ordering while retaining the balanced 3/3/2 opening."""
        if self.exploration_policy not in {"balanced", "confirmation_first"}:
            return ordered
        quota = {"revenue": 3, "transition": 3, "history": 2}
        selected = []
        used = set()
        for category, count in quota.items():
            for item in ordered:
                cid = item["candidate_id"]
                if cid in used or self._exploration_categories.get(cid) != category:
                    continue
                selected.append(item)
                used.add(cid)
                if sum(1 for item2 in selected if self._exploration_categories.get(item2["candidate_id"]) == category) >= count:
                    break
        for item in ordered:
            if item["candidate_id"] not in used:
                selected.append(item)
        return selected

    def _advice(self, advisor, candidates, observations, env, phase, channel, events):
        payload = [{key: value for key, value in item.items() if key not in {"members", "segment_key"}} |
                   self._estimate(item, observations, channel, self.uncertainty_mode) | {"channel": channel}
                   for item in candidates[:24]]
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
                advised = sorted(candidates, key=lambda item: order.get(item["candidate_id"], len(selected)))
                return self._respect_initial_quota(advised, candidates)
        except Exception:
            events.append({"role": "advisor", "phase": phase, "status": "fallback"})
        return self._respect_initial_quota(candidates, candidates)

    def _run_pilot(self, env, candidate, channel, sample, observations, events, warnings, action):
        before = self._resources(env)
        cid = candidate["candidate_id"]
        completed = False
        try:
            result = env.run_pilot(target_tariff=candidate["target_tariff"], channel=channel,
                                   n_customers=sample, **candidate["filters"])
            ratio = finite(result.get("observed_lift_ratio"), None)
            actual_n = int(finite(result.get("n_customers"), sample))
            if ratio is None or not 10 <= actual_n <= sample:
                raise ValueError("invalid_pilot_response")
            after = self._resources(env)
            observations.append({"candidate_id": cid, "target_tariff": candidate["target_tariff"],
                                 "filters": candidate["filters"], "channel": channel,
                                 "requested_n": sample, "n_customers": actual_n,
                                 "cost": before["remaining_budget"] - after["remaining_budget"],
                                 "observed_lift_ratio": ratio,
                                 "observed_lift_total": finite(result.get("observed_lift_total"), None),
                                 "remaining_budget": after["remaining_budget"],
                                 "remaining_contacts": after["remaining_contacts"], "status": "completed"})
            completed = True
        except Exception:
            observations.append({"candidate_id": cid, "target_tariff": candidate["target_tariff"],
                                 "channel": channel, "n_customers": sample, "status": "failed"})
            warnings.append("pilot_failed_" + cid + "_" + channel)
        events.append({"role": "experimenter", "step": len(observations), "candidate_id": cid,
                       "channel": channel, "action": action, "status": observations[-1]["status"]})
        return completed

    def _promote_channels(self, env, candidates, channels, scout, observations, events, warnings, started):
        # Public channel multipliers rank hypotheses only. A promoted channel
        # still needs two real observations before entering the main allocation.
        initial = self._resources(env)
        spend_limit = 0.20 * initial["remaining_budget"]
        considered, promoted_members = set(), set()
        while len(observations) <= 18 and time.monotonic() - started < 220:
            resources = self._resources(env)
            if resources["pilots_left"] < 2:
                break
            spent = max(0, initial["remaining_budget"] - resources["remaining_budget"])
            proposals = []
            for item in candidates:
                base = self._estimate(item, observations, scout, self.uncertainty_mode)
                if base["repeats"] < 2 or base["conservative_net"] <= 0 or item["members"] & promoted_members:
                    continue
                sample = min(200, item["audience_size"])
                for channel in channels:
                    key = (item["candidate_id"], channel)
                    if channel == scout or key in considered or CHANNEL_COSTS[channel] <= CHANNEL_COSTS[scout]:
                        continue
                    pilot_cost = 2 * sample * CHANNEL_COSTS[channel]
                    final_cost = item["audience_size"] * CHANNEL_COSTS[channel]
                    if spent + pilot_cost > spend_limit or pilot_cost + final_cost > resources["remaining_budget"]:
                        continue
                    if 2 * sample + item["audience_size"] > resources["remaining_contacts"]:
                        continue
                    projected_mean = base["posterior_mean"] * CHANNEL_EFFECT[channel] / CHANNEL_EFFECT[scout]
                    incremental = projected_mean * item["arpu_sum"] - final_cost - base["estimated_net"] - pilot_cost
                    if incremental > 0:
                        proposals.append((incremental, item, channel, sample))
            if not proposals:
                break
            _, item, channel, sample = max(proposals, key=lambda proposal: proposal[0])
            considered.add((item["candidate_id"], channel))
            for _ in range(2):
                sample = self._pilot_sample(item, observations, channel, first_sample=200)
                resources = self._resources(env)
                if time.monotonic() - started >= 220 or len(observations) >= 20 or resources["pilots_left"] < 1:
                    break
                if (sample + item["audience_size"] > resources["remaining_contacts"]
                        or (sample + item["audience_size"]) * CHANNEL_COSTS[channel] > resources["remaining_budget"]):
                    break
                if not self._run_pilot(env, item, channel, sample, observations, events, warnings, "channel_check"):
                    break
            promoted_members.update(item["members"])

    @staticmethod
    def _select_portfolio(options, budget, contacts):
        """Choose a disjoint portfolio; exact search is bounded to small eligible sets."""
        eligible = []
        for option in options:
            score, item, channel, estimate = option
            score = finite(score, None)
            audience = int(finite(item.get("audience_size"), 0))
            repeats = int(finite(estimate.get("repeats"), 0))
            if (score is None or score <= 0 or repeats < 2 or audience < 1 or audience > 5000
                    or channel not in CHANNEL_COSTS):
                continue
            cost = CHANNEL_COSTS[channel] * audience
            if cost <= budget and audience <= contacts:
                eligible.append((score, item, channel, estimate, cost, audience))

        def greedy_pick(pool):
            used, left_budget, left_contacts, selected = set(), budget, contacts, []
            for score, item, channel, estimate, cost, audience in pool:
                members = item.get("members", frozenset())
                if members & used or cost > left_budget or audience > left_contacts or len(selected) >= 10:
                    continue
                selected.append((score, item, channel, estimate, cost, audience))
                used.update(members)
                left_budget -= cost
                left_contacts -= audience
            return selected

        greedy = greedy_pick(eligible)
        greedy_score = sum(item[0] for item in greedy)
        best = list(greedy)
        if len(eligible) <= 10:
            best_score = greedy_score
            suffix = [0.0] * (len(eligible) + 1)
            for index in range(len(eligible) - 1, -1, -1):
                suffix[index] = suffix[index + 1] + eligible[index][0]

            def search(index, used, left_budget, left_contacts, selected, total):
                nonlocal best, best_score
                if len(selected) >= 10 or index >= len(eligible):
                    if total > best_score + 1e-9:
                        best, best_score = list(selected), total
                    return
                if total + suffix[index] <= best_score + 1e-9:
                    return
                option = eligible[index]
                score, item, channel, estimate, cost, audience = option
                members = item.get("members", frozenset())
                if not members & used and cost <= left_budget and audience <= left_contacts:
                    search(index + 1, used | set(members), left_budget - cost,
                           left_contacts - audience, selected + [option], total + score)
                search(index + 1, used, left_budget, left_contacts, selected, total)

            search(0, set(), budget, contacts, [], 0.0)
        selected_score = sum(item[0] for item in best)
        return best, {
            "mode": "exact" if len(eligible) <= 10 else "greedy",
            "eligible_count": len(eligible),
            "baseline_conservative_net": greedy_score,
            "selected_conservative_net": selected_score,
            "improved": selected_score > greedy_score + 1e-9,
        }

    def _selection_diagnostics(self, candidates, observations, selected_options, campaigns,
                               allocation, budget, contacts):
        completed = [row for row in observations if row.get("status") == "completed"]
        groups = {}
        for index, row in enumerate(observations):
            if row.get("status") != "completed":
                continue
            key = (row.get("candidate_id"), row.get("channel"))
            groups.setdefault(key, []).append((index, row))
        selected_keys = {(item[1]["candidate_id"], item[2]) for item in selected_options}
        fallback_keys = set()
        for allocation_row, campaign in zip(allocation, campaigns):
            if campaign.get("campaign_name", "").startswith("fallback_"):
                fallback_keys.add((allocation_row.get("candidate_id"), allocation_row.get("channel")))
        variants = []
        reason_counts = {reason: 0 for reason in (
            "selected", "mandatory_fallback", "insufficient_pilots", "nonpositive_estimate",
            "overlap", "budget", "contacts", "not_selected")}
        candidate_by_id = {item["candidate_id"]: item for item in candidates}
        used_members = set()
        selected_ids = set()
        for score, item, channel, estimate, _, _ in selected_options:
            selected_ids.add(item["candidate_id"])
            used_members.update(item.get("members", frozenset()))
        for key, rows in groups.items():
            cid, channel = key
            item = candidate_by_id.get(cid)
            if item is None:
                continue
            estimate = self._estimate(item, observations, channel, self.uncertainty_mode)
            is_selected = key in selected_keys
            if is_selected:
                reason = "selected"
            elif key in fallback_keys:
                reason = "mandatory_fallback"
            elif len(rows) < 2:
                reason = "insufficient_pilots"
            elif estimate["conservative_net"] <= 0:
                reason = "nonpositive_estimate"
            elif item.get("members", frozenset()) & used_members:
                reason = "overlap"
            elif CHANNEL_COSTS[channel] * item["audience_size"] > budget:
                reason = "budget"
            elif item["audience_size"] > contacts:
                reason = "contacts"
            else:
                reason = "not_selected"
            reason_counts[reason] += 1
            variants.append({
                "candidate_id": cid, "channel": channel, "repeats": len(rows),
                "conservative_net": finite(estimate["conservative_net"]),
                "selected": is_selected or key in fallback_keys, "reason": reason,
                "pilot_refs": [f"pilots.{index}" for index, _ in rows],
            })
        variants.sort(key=lambda row: (row["pilot_refs"][0] if row["pilot_refs"] else "", row["candidate_id"], row["channel"]))
        tested_ids = {row["candidate_id"] for row in completed}
        tested_variants = {(row["candidate_id"], row["channel"]) for row in completed}
        confirmed = {key for key, rows in groups.items() if len(rows) >= 2}
        return {
            "generated_candidates": len(candidates),
            "tested_candidates": len(tested_ids),
            "tested_variants": len(tested_variants),
            "confirmed_variants": len(confirmed),
            "selected_variants": len(selected_keys | fallback_keys),
            "unexplored_candidates": max(0, len(candidates) - len(tested_ids)),
            "reason_counts": {key: value for key, value in reason_counts.items() if value},
            "variants": variants[:20],
            "strategy_config": {"exploration_policy": self.exploration_policy,
                                "uncertainty_mode": self.uncertainty_mode, "pilot_sizing": self.pilot_sizing},
        }

    def act(self, env):
        started = time.monotonic()
        warnings, observations, events = [], [], []
        advisor = Advisor()
        profile, tariffs = env.customer_profile, env.tariffs
        channels = [str(channel) for channel in env.channels if str(channel) in CHANNEL_COSTS]
        if not channels:
            self.last_report = {"schema_version": "1.0", "engine": "adaptive-offline", "campaigns": [],
                                "pilots": [], "resources": self._resources(env),
                                "portfolio_selection": {"mode": "greedy", "eligible_count": 0,
                                "baseline_conservative_net": 0.0, "selected_conservative_net": 0.0,
                                "improved": False}, "warnings": ["no_supported_channels"]}
            return []
        # Limit the worst-case scout spend before choosing its documented signal
        # strength. This permits inexpensive SMS where affordable while keeping
        # advertising/calls for measured promotion rather than blind exploration.
        scout_limit = 16 if len(channels) > 1 or self.exploration_policy in {"balanced", "confirmation_first"} else 20
        scout_slots = max(1, min(scout_limit, int(env.pilots_left)))
        scout_budget = 0.15 * self._resources(env)["remaining_budget"]
        affordable = [channel for channel in channels
                      if scout_slots * 200 * CHANNEL_COSTS[channel] <= scout_budget]
        scout = (max(affordable, key=lambda channel: CHANNEL_EFFECT[channel]) if affordable
                 else min(channels, key=lambda channel: CHANNEL_COSTS[channel]))
        candidates, source = self._candidates(profile, tariffs, warnings)
        candidates = self._diverse(candidates)
        events.append({"role": "analyst", "status": "completed", "source": source, "candidate_count": len(candidates)})
        shortlist = (self._balanced_shortlist(candidates)
                     if self.exploration_policy in {"balanced", "confirmation_first"} else candidates)
        initial_advice = self._advice(advisor, shortlist, observations, env, "initial", scout, events)
        initial = (initial_advice if self.exploration_policy in {"balanced", "confirmation_first"}
                   else self._diverse(initial_advice))
        attempts, failed, feedback_order = {}, set(), {}
        new_scouted = set()
        balanced_reservations = {}
        # Reserve at most four pilot slots for checking profitable paid channels.
        for step in range(min(scout_limit, int(env.pilots_left))):
            if time.monotonic() - started > 220 or int(env.pilots_left) <= 0:
                break
            if step == 8:
                feedback_pool = (self._balanced_shortlist(candidates)
                                 if self.exploration_policy in {"balanced", "confirmation_first"} else candidates)
                pool = sorted(feedback_pool,
                              key=lambda item: self._estimate(item, observations, scout, self.uncertainty_mode)["estimated_net"],
                              reverse=True)
                revised = self._advice(advisor, pool, observations, env, "feedback", scout, events)
                feedback_order = {item["candidate_id"]: index for index, item in enumerate(revised)}
            available = [item for item in initial if attempts.get(item["candidate_id"], 0) < 3 and item["candidate_id"] not in failed]
            if step < 8:
                available = [item for item in available if not attempts.get(item["candidate_id"])]
            else:
                def pilot_priority(item):
                    estimate = self._estimate(item, observations, scout, self.uncertainty_mode)
                    optimism = estimate["posterior_mean"] + 0.25 * estimate["uncertainty"]
                    value = optimism * item["arpu_sum"] - CHANNEL_COSTS[scout] * item["audience_size"]
                    if not estimate["repeats"]:
                        value = (max(0, item["prior_lift_ratio"]) * CHANNEL_EFFECT[scout] + 0.01) * item["arpu_sum"]
                    preference = 1.0 + 0.10 / (1 + feedback_order.get(item["candidate_id"], 24))
                    return value * preference / math.sqrt(1 + estimate["repeats"])
                available.sort(key=pilot_priority, reverse=True)
                if self.exploration_policy in {"balanced", "confirmation_first"}:
                    # Finish the reserved new arm before opening another. The
                    # reservation includes a second pilot slot as well as money
                    # and contacts; negative first observations release it.
                    pending = []
                    for item in available:
                        cid = item["candidate_id"]
                        if cid not in balanced_reservations:
                            continue
                        estimate = self._estimate(item, observations, scout, self.uncertainty_mode)
                        upper_net = ((estimate["posterior_mean"] + estimate["uncertainty"]) * item["arpu_sum"]
                                     - CHANNEL_COSTS[scout] * item["audience_size"])
                        if estimate["repeats"] == 1 and upper_net > 0:
                            pending.append(item)
                        else:
                            balanced_reservations.pop(cid, None)
                    confirmations = [item for item in available
                                     if self._estimate(item, observations, scout, self.uncertainty_mode)["repeats"]
                                     and pilot_priority(item) > 0]
                    new_pairs = []
                    if (not pending and len(new_scouted) < 2 and scout_limit - step >= 2
                            and int(env.pilots_left) >= 2 and time.monotonic() - started < 190):
                        resources_now = self._resources(env)
                        minimum_final = min((item["audience_size"] for item in candidates), default=0)
                        final_cost = minimum_final * min(CHANNEL_COSTS[channel] for channel in channels)
                        for item in available:
                            if attempts.get(item["candidate_id"]):
                                continue
                            pair_size = min(item["audience_size"], 150) + min(item["audience_size"], 200)
                            if (pair_size + minimum_final <= resources_now["remaining_contacts"]
                                    and pair_size * CHANNEL_COSTS[scout] + final_cost <= resources_now["remaining_budget"]):
                                new_pairs.append(item)
                    available = (pending or confirmations or new_pairs
                                 if self.exploration_policy == "confirmation_first"
                                 else pending or new_pairs or confirmations)
                else:
                    # Preserve the baseline confirmation ordering exactly.
                    confirmation = [item for item in available
                                    if self._estimate(item, observations, scout, self.uncertainty_mode)["repeats"]
                                    and pilot_priority(item) > 0]
                    if confirmation:
                        available = confirmation
                    elif any(self._estimate(item, observations, scout, self.uncertainty_mode)["repeats"] >= 2
                             and self._estimate(item, observations, scout, self.uncertainty_mode)["conservative_net"] > 0 for item in candidates):
                        break
                    else:
                        available = [item for item in available if not attempts.get(item["candidate_id"])]
            chosen = None
            resources = self._resources(env)
            reserve_contacts = min((item["audience_size"] for item in candidates), default=0)
            reserve_cost = reserve_contacts * min(CHANNEL_COSTS[channel] for channel in channels)
            for item in available:
                previous = attempts.get(item["candidate_id"], 0)
                sample = self._pilot_sample(item, observations, scout, first_sample=150)
                if sample < 10 or sample + reserve_contacts > resources["remaining_contacts"]:
                    continue
                other_reserved_contacts = sum(value[0] for key, value in balanced_reservations.items()
                                              if key != item["candidate_id"])
                other_reserved_budget = sum(value[1] for key, value in balanced_reservations.items()
                                            if key != item["candidate_id"])
                required_sample = sample
                required_cost = sample * CHANNEL_COSTS[scout]
                if (self.exploration_policy in {"balanced", "confirmation_first"} and step >= 8 and previous == 0
                        and len(new_scouted) < 2):
                    second_sample = min(item["audience_size"], 200)
                    required_sample += second_sample
                    required_cost += second_sample * CHANNEL_COSTS[scout]
                if (required_sample + reserve_contacts + other_reserved_contacts
                        > resources["remaining_contacts"]):
                    continue
                if (required_cost + reserve_cost + other_reserved_budget
                        > resources["remaining_budget"]):
                    continue
                if (self.exploration_policy in {"balanced", "confirmation_first"} and previous == 1
                        and item["candidate_id"] in balanced_reservations):
                    estimate = self._estimate(item, observations, scout, self.uncertainty_mode)
                    upper_net = ((estimate["posterior_mean"] + estimate["uncertainty"]) * item["arpu_sum"]
                                 - CHANNEL_COSTS[scout] * item["audience_size"])
                    if upper_net <= 0:
                        balanced_reservations.pop(item["candidate_id"], None)
                        continue
                chosen = item
                break
            if chosen is None:
                break
            cid = chosen["candidate_id"]
            if self.exploration_policy in {"balanced", "confirmation_first"} and step >= 8 and attempts.get(cid, 0) == 0:
                new_scouted.add(cid)
            attempts[cid] = attempts.get(cid, 0) + 1
            if self.exploration_policy in {"balanced", "confirmation_first"} and attempts[cid] == 1 and step >= 8:
                second_sample = min(chosen["audience_size"], 200)
                balanced_reservations[cid] = (second_sample, second_sample * CHANNEL_COSTS[scout])
            elif self.exploration_policy in {"balanced", "confirmation_first"} and attempts[cid] > 1:
                balanced_reservations.pop(cid, None)
            if not self._run_pilot(env, chosen, scout, sample, observations, events, warnings,
                                   "confirm" if attempts[cid] > 1 else "explore"):
                failed.add(cid)
                balanced_reservations.pop(cid, None)

        self._promote_channels(env, candidates, channels, scout, observations, events, warnings, started)

        resources = self._resources(env)
        budget, contacts = resources["remaining_budget"], resources["remaining_contacts"]
        options = []
        for item in candidates:
            for channel in channels:
                estimate = self._estimate(item, observations, channel, self.uncertainty_mode)
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

        selected_options, portfolio_selection = self._select_portfolio(options, budget, contacts)
        for score, item, channel, estimate, cost, audience in selected_options:
            budget -= add_campaign(item, channel, estimate)
            contacts -= audience
            members.update(item["members"])
        if not campaigns:
            # Prefer an actually observed arm for the mandatory minimum campaign.
            observed_options = sorted(options, key=lambda option: option[0], reverse=True)
            for _, item, channel, estimate in observed_options:
                cost = CHANNEL_COSTS[channel] * item["audience_size"]
                if item["audience_size"] <= contacts and cost <= budget:
                    budget -= add_campaign(item, channel, estimate, fallback=True)
                    contacts -= item["audience_size"]
                    warnings.append("no_positive_conservative_plan_fallback")
                    break
        if not campaigns:
            cheapest = min(channels, key=lambda channel: CHANNEL_COSTS[channel])
            # Minimum one campaign is mandatory; report this explicitly as fallback.
            for pool in (candidates,):
                ranked = sorted(pool, key=lambda item: self._estimate(item, observations, cheapest, self.uncertainty_mode)["conservative_net"], reverse=True)
                for item in ranked:
                    cost = CHANNEL_COSTS[cheapest] * item["audience_size"]
                    if item["audience_size"] <= contacts and cost <= budget:
                        budget -= add_campaign(item, cheapest, self._estimate(item, observations, cheapest, self.uncertainty_mode), fallback=True)
                        contacts -= item["audience_size"]
                        warnings.append("unobserved_fallback")
                        break
                if campaigns:
                    break
        events.append({"role": "allocator", "status": "completed", "campaign_count": len(campaigns)})
        self.last_report = {
            "schema_version": "1.0", "engine": "adaptive-openai" if any(event["status"] == "completed" for event in advisor.events) else "adaptive-offline",
            "strategy_config": {"exploration_policy": self.exploration_policy,
                                "uncertainty_mode": self.uncertainty_mode, "pilot_sizing": self.pilot_sizing},
            "candidate_source": source, "candidate_count": len(candidates), "scout_channel": scout,
            "resource_stage": "after_pilots_before_final_campaigns", "resources": resources,
            "planned_resources": {"remaining_budget": budget, "remaining_contacts": contacts},
            "campaigns": campaigns, "allocation": allocation, "pilots": observations,
            "portfolio_selection": portfolio_selection,
            "events": events, "advisor": advisor.events, "warnings": sorted(set(warnings)),
            "uncertainty_note": ("Heuristic margin uses the template floor and empirical repeat variation; "
                                 "not a calibrated confidence interval."
                                 if self.uncertainty_mode == "empirical" else
                                 "Approximate planning margin from public template; not a calibrated confidence interval."),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        self.last_report["selection_diagnostics"] = self._selection_diagnostics(
            candidates, observations, selected_options, campaigns, allocation, budget, contacts)
        return campaigns
