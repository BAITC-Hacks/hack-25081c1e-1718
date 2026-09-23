"""Initial pilot-based baseline; historical priors are the next integration."""

from pathlib import Path
import csv
import math
import time


CHANNEL_COSTS = {"push": 0.0, "sms": 4.0, "digital_ads": 22.0, "call": 160.0}


class Agent:
    def __init__(self):
        self.last_report = {}
        self._prices = self._load_tariff_prices()

    @staticmethod
    def _load_tariff_prices():
        prices = {}
        try:
            with Path(__file__).with_name("tariff_dictionary.csv").open(
                newline="", encoding="utf-8"
            ) as fh:
                for row in csv.DictReader(fh):
                    prices[row["tariff_plan_code"]] = float(row["price_tariff"])
        except (OSError, KeyError, ValueError):
            pass
        return prices

    @staticmethod
    def _json_value(value):
        return value.item() if hasattr(value, "item") else value

    @staticmethod
    def _channels(value):
        if isinstance(value, dict):
            return [str(key) for key in value]
        return [str(channel) for channel in value]

    def _targets(self, current, tariffs):
        price = self._prices.get(current)
        if price is None:
            return [tariff for tariff in tariffs if tariff != current][:2]
        higher = sorted(
            (tariff for tariff in tariffs
             if tariff != current and self._prices.get(tariff, -1) > price),
            key=lambda tariff: self._prices.get(tariff, 0),
        )
        if not higher:
            return [tariff for tariff in tariffs if tariff != current][:2]
        return list(dict.fromkeys(higher[:1] + higher[-1:]))[:2]

    @staticmethod
    def _cell_filters(row):
        return {
            "filter_arpu_segment": str(row["arpu_segment"]),
            "filter_data_segment": str(row["data_segment"]),
            "filter_call_segment": str(row["call_segment"]),
            "filter_current_tariff": str(row["current_tariff"]),
        }

    def _campaign(self, row, target, channel, name):
        campaign = {"campaign_name": name}
        campaign.update(self._cell_filters(row))
        campaign.update({"target_tariff": target, "channel": channel})
        return campaign

    def act(self, env):
        started = time.monotonic()
        profile = env.customer_profile
        tariffs = [str(value) for value in env.tariffs["tariff_plan_code"].tolist()]
        valid_tariffs = set(tariffs)
        channels = [channel for channel in self._channels(env.channels)
                    if channel in CHANNEL_COSTS]
        if not channels:
            channels = ["push"]

        group_cols = ["current_tariff", "arpu_segment", "data_segment", "call_segment"]
        cells = (profile.groupby(group_cols, observed=True)
                 .agg(n=("ID_NUMBER", "size"), arpu=("predicted_arpu", "mean"),
                      total_arpu=("predicted_arpu", "sum"))
                 .reset_index())
        cells = cells[(cells["n"] >= 20) & (cells["n"] <= 5000)].copy()
        cells["priority"] = cells["total_arpu"]
        cells = cells.sort_values("priority", ascending=False)

        # Baseline explores a fixed shortlist and uses observations for the final
        # plan. Adaptive pilot scheduling is a separate, subsequent improvement.
        candidates = []
        for _, cell in cells.head(10).iterrows():
            for target in self._targets(str(cell["current_tariff"]), tariffs):
                for channel in channels[:2]:
                    candidates.append((cell, target, channel))
                    if len(candidates) >= 12:
                        break
                if len(candidates) >= 12:
                    break
            if len(candidates) >= 12:
                break

        remaining_budget = float(getattr(env, "remaining_budget", 0))
        remaining_contacts = int(getattr(env, "remaining_contacts", 0))
        observations = []
        for cell, target, channel in candidates:
            if int(getattr(env, "pilots_left", 0)) <= 0 or time.monotonic() - started > 240:
                break
            remaining_budget = float(env.remaining_budget)
            remaining_contacts = int(env.remaining_contacts)
            n_customers = min(120, int(cell["n"]))
            cost = CHANNEL_COSTS[channel] * n_customers
            if n_customers < 10 or n_customers > remaining_contacts or cost > remaining_budget:
                continue
            try:
                result = env.run_pilot(
                    target_tariff=target,
                    channel=channel,
                    n_customers=n_customers,
                    **self._cell_filters(cell),
                )
                ratio = float(result["observed_lift_ratio"])
                if not math.isfinite(ratio):
                    continue
            except (KeyError, RuntimeError, TypeError, ValueError):
                continue
            observations.append({
                "current_tariff": str(cell["current_tariff"]),
                "arpu_segment": str(cell["arpu_segment"]),
                "data_segment": str(cell["data_segment"]),
                "call_segment": str(cell["call_segment"]),
                "target_tariff": target,
                "channel": channel,
                "n_customers": n_customers,
                "observed_lift_ratio": ratio,
                "estimated_net": ratio * float(cell["total_arpu"]) - CHANNEL_COSTS[channel] * int(cell["n"]),
            })

        # The environment is authoritative, including failed/partial pilot calls.
        remaining_budget = float(env.remaining_budget)
        remaining_contacts = int(env.remaining_contacts)
        ranked = sorted(observations, key=lambda row: row["estimated_net"], reverse=True)
        campaigns = []
        used_cells = set()
        for row in ranked:
            cell_key = tuple(row[key] for key in (
                "current_tariff", "arpu_segment", "data_segment", "call_segment"))
            cell = profile[
                (profile["current_tariff"].astype(str) == row["current_tariff"]) &
                (profile["arpu_segment"].astype(str) == row["arpu_segment"]) &
                (profile["data_segment"].astype(str) == row["data_segment"]) &
                (profile["call_segment"].astype(str) == row["call_segment"])
            ]
            n_customers = len(cell)
            campaign_cost = CHANNEL_COSTS.get(row["channel"], 0) * n_customers
            if (row["target_tariff"] not in valid_tariffs or cell_key in used_cells or
                    n_customers < 1 or n_customers > 5000 or
                    n_customers > remaining_contacts or campaign_cost > remaining_budget):
                continue
            if row["estimated_net"] <= 0:
                continue
            used_cells.add(cell_key)
            campaigns.append(self._campaign(
                row, row["target_tariff"], row["channel"],
                "baseline_{}_{}".format(row["current_tariff"], row["target_tariff"])))
            remaining_contacts -= n_customers
            remaining_budget -= campaign_cost
            if len(campaigns) >= 10:
                break

        # If no positive observation survived, retain one feasible observed idea.
        if not campaigns:
            for row in ranked:
                cell_key = tuple(row[key] for key in (
                    "current_tariff", "arpu_segment", "data_segment", "call_segment"))
                cell = profile[
                    (profile["current_tariff"].astype(str) == row["current_tariff"]) &
                    (profile["arpu_segment"].astype(str) == row["arpu_segment"]) &
                    (profile["data_segment"].astype(str) == row["data_segment"]) &
                    (profile["call_segment"].astype(str) == row["call_segment"])
                ]
                n_customers = len(cell)
                cost = CHANNEL_COSTS.get(row["channel"], 0) * n_customers
                if (row["target_tariff"] in valid_tariffs and cell_key not in used_cells and
                        1 <= n_customers <= 5000 and n_customers <= remaining_contacts and
                        cost <= remaining_budget):
                    campaigns.append(self._campaign(
                        row, row["target_tariff"], row["channel"],
                        "fallback_{}_{}".format(row["current_tariff"], row["target_tariff"])))
                    break

        if not campaigns:
            # Degraded path if all pilot responses were unusable; prefer a small
            # expressible segment and a known cheap channel, without claiming gain.
            for _, cell in cells.sort_values("n").iterrows():
                targets = self._targets(str(cell["current_tariff"]), tariffs)
                cheap_channel = min(channels, key=lambda channel: CHANNEL_COSTS[channel])
                size = int(cell["n"])
                if targets and size <= remaining_contacts and size * CHANNEL_COSTS[cheap_channel] <= remaining_budget:
                    campaigns.append(self._campaign(cell, targets[0], cheap_channel, "unobserved_fallback"))
                    break

        self.last_report = {
            "schema_version": "1.0",
            "engine": "baseline",
            "resource_stage": "after_pilots_before_final_campaigns",
            "campaigns": campaigns,
            "pilots": observations,
            "resources": {
                "remaining_budget": self._json_value(getattr(env, "remaining_budget", None)),
                "remaining_contacts": self._json_value(getattr(env, "remaining_contacts", None)),
                "pilots_left": self._json_value(getattr(env, "pilots_left", None)),
            },
        }
        return campaigns
