"""Bounded checks for the optional exploration and uncertainty policies.

These tests use public-contract-shaped data only. They never inspect the
organizer environment or call a paid provider.
"""

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from agent import Agent


def candidate(index, *, prior=0.0, current="tariff_1", target="tariff_2", size=20):
    return {
        "candidate_id": f"c_{index:02d}",
        "filters": {"filter_current_tariff": current, "filter_arpu_segment": "high"},
        "target_tariff": target,
        "audience_size": size,
        "arpu_sum": float(size * (100 + index)),
        "prior_lift_ratio": prior,
        "prior_n": 10 if prior else 0,
        "rationale": "test",
        "members": frozenset(range(index * 100, index * 100 + size)),
        "segment_key": f"segment-{index}",
    }


class FakeEnv:
    channels = ["sms"]

    def __init__(self, *, ratio=0.12, contacts=15000):
        self.customer_profile = pd.DataFrame({
            "ID_NUMBER": list(range(20)), "current_tariff": ["tariff_1"] * 20,
            "arpu_segment": ["high"] * 20, "data_segment": ["medium"] * 20,
            "call_segment": ["medium"] * 20, "predicted_arpu": [100.0] * 20,
        })
        self.tariffs = pd.DataFrame({"tariff_plan_code": ["tariff_1", "tariff_2"]})
        self.remaining_budget, self.remaining_contacts, self.pilots_left = 100000.0, contacts, 20
        self.ratio = ratio
        self.calls = []

    def run_pilot(self, *, target_tariff, channel, n_customers, **filters):
        self.calls.append((target_tariff, channel, n_customers, filters.get("filter_data_segment")))
        self.remaining_budget -= n_customers * 4
        self.remaining_contacts -= n_customers
        self.pilots_left -= 1
        return {"observed_lift_ratio": self.ratio, "observed_lift_total": self.ratio * n_customers,
                "n_customers": n_customers}


class QualityPolicyTests(unittest.TestCase):
    def setUp(self):
        offline = patch.dict("os.environ", {"ARPU_OFFLINE": "1"})
        offline.start()
        self.addCleanup(offline.stop)

    def test_transition_seats_are_distinct_and_equal_values_use_stable_ids(self):
        pool = [candidate(i, prior=.1, current=f"tariff_{i % 6}") for i in range(40)]
        for item in pool:
            item["arpu_sum"] = 10000
        agent = Agent(exploration_policy="balanced")
        first = agent._balanced_shortlist(pool)
        second = agent._balanced_shortlist(list(reversed(pool)))
        self.assertEqual([r["candidate_id"] for r in first], [r["candidate_id"] for r in second])
        self.assertEqual(len({r["filters"]["filter_current_tariff"] for r in first[3:6]}), 3)

    def test_only_one_slot_left_does_not_open_another_hypothesis(self):
        agent = Agent(exploration_policy="balanced")
        pool = [candidate(i) for i in range(14)]
        agent._candidates = lambda *_: (pool, "test")
        env = FakeEnv()
        env.pilots_left = 9
        agent.act(env)
        self.assertEqual(len({r["candidate_id"] for r in agent.last_report["pilots"]}), 8)

    def test_constructor_defaults_and_modes(self):
        self.assertEqual((Agent().exploration_policy, Agent().uncertainty_mode), ("baseline", "template"))
        self.assertEqual(Agent(exploration_policy="balanced", uncertainty_mode="empirical").uncertainty_mode,
                         "empirical")
        with self.assertRaises(ValueError):
            Agent(exploration_policy="invalid")
        with self.assertRaises(ValueError):
            Agent(uncertainty_mode="invalid")

    def test_advisor_exception_retains_autonomous_shortlist(self):
        agent = Agent(exploration_policy="balanced")
        pool = agent._balanced_shortlist([candidate(i, prior=.02, current=f"tariff_{i % 5}") for i in range(30)])
        class FailingAdvisor:
            def recommend(self, *_):
                raise TimeoutError("fixture")
        events = []
        result = agent._advice(FailingAdvisor(), pool, [], FakeEnv(), "initial", "sms", events)
        self.assertEqual({r["candidate_id"] for r in result}, {r["candidate_id"] for r in pool})
        self.assertEqual(events[-1]["status"], "fallback")

    def test_negative_pilots_outweigh_positive_historical_prior(self):
        item = candidate(1, prior=.025)
        rows = [{"candidate_id": item["candidate_id"], "channel": "sms", "status": "completed",
                 "n_customers": 150, "observed_lift_ratio": -.1} for _ in range(2)]
        estimate = Agent._estimate(item, rows, "sms", "empirical")
        self.assertLess(estimate["posterior_mean"], 0)
        self.assertLess(estimate["conservative_net"], 0)

    def test_balanced_shortlist_has_stable_ids_and_quotas(self):
        agent = Agent(exploration_policy="balanced")
        candidates = [candidate(i, prior=0.1 if i % 3 == 0 else 0.0,
                                current=f"tariff_{i % 3}", target=f"tariff_{(i + 1) % 3}")
                      for i in range(40)]
        first = agent._balanced_shortlist(candidates)
        second = agent._balanced_shortlist(candidates)
        self.assertEqual([item["candidate_id"] for item in first], [item["candidate_id"] for item in second])
        self.assertLessEqual(len(first), 24)
        self.assertEqual(len({item["candidate_id"] for item in first}), len(first))
        categories = [agent._exploration_categories[item["candidate_id"]] for item in first[:8]]
        self.assertGreaterEqual(categories.count("revenue"), 3)
        self.assertGreaterEqual(categories.count("transition"), 3)
        self.assertGreaterEqual(categories.count("history"), 2)

    def test_empirical_uncertainty_uses_weighted_repeat_variance(self):
        item = candidate(1)
        observations = [
            {"candidate_id": "c_01", "channel": "sms", "status": "completed",
             "n_customers": 100, "observed_lift_ratio": 0.10},
            {"candidate_id": "c_01", "channel": "sms", "status": "completed",
             "n_customers": 100, "observed_lift_ratio": 0.30},
        ]
        estimate = Agent._estimate(item, observations, "sms", "empirical")
        self.assertEqual(estimate["uncertainty_method"], "max_template_empirical")
        self.assertAlmostEqual(estimate["sample_std"], 0.1414213562, places=5)
        self.assertGreaterEqual(estimate["uncertainty"], estimate["template_uncertainty"])

    def test_single_observation_keeps_template_floor(self):
        item = candidate(1)
        estimate = Agent._estimate(item, [{"candidate_id": "c_01", "channel": "sms",
                                           "status": "completed", "n_customers": 100,
                                           "observed_lift_ratio": 0.10}], "sms", "empirical")
        self.assertIsNone(estimate["sample_std"])
        self.assertIsNone(estimate["empirical_se"])
        self.assertEqual(estimate["uncertainty_method"], "template_floor")

    def test_contradictory_repeat_can_skip_conservative_selection(self):
        item = candidate(1)
        rows = [{"candidate_id": "c_01", "channel": "sms", "status": "completed",
                 "n_customers": 100, "observed_lift_ratio": 1.0},
                {"candidate_id": "c_01", "channel": "sms", "status": "completed",
                 "n_customers": 100, "observed_lift_ratio": -1.0}]
        estimate = Agent._estimate(item, rows, "sms", "empirical")
        self.assertLessEqual(estimate["conservative_net"], 0)

    def test_selection_diagnostics_have_bounded_refs_and_reasons(self):
        agent = Agent()
        item = candidate(1)
        observations = [{"candidate_id": "c_01", "channel": "sms", "status": "completed",
                         "n_customers": 20, "observed_lift_ratio": 0.2}]
        diagnostics = agent._selection_diagnostics([item], observations, [], [], [], 1000, 1000)
        self.assertEqual(diagnostics["tested_candidates"], 1)
        self.assertEqual(diagnostics["tested_variants"], 1)
        self.assertEqual(diagnostics["confirmed_variants"], 0)
        self.assertEqual(diagnostics["variants"][0]["pilot_refs"], ["pilots.0"])
        self.assertEqual(diagnostics["variants"][0]["reason"], "insufficient_pilots")
        self.assertNotIn("members", diagnostics["variants"][0])

    def test_balanced_run_keeps_limits_and_explores_after_eight(self):
        agent = Agent(exploration_policy="balanced", uncertainty_mode="empirical")
        pool = [candidate(i, prior=0.1 if i % 2 else 0.0,
                          current=f"tariff_{i % 4}", target=f"tariff_{(i + 1) % 4}")
                for i in range(30)]
        for index, item in enumerate(pool):
            item["filters"]["filter_data_segment"] = f"segment-{index}"
        agent._candidates = lambda profile, tariffs, warnings: (pool, "test")
        env = FakeEnv()
        campaigns = agent.act(env)
        self.assertTrue(campaigns)
        self.assertLessEqual(len(env.calls), 20)
        self.assertLessEqual(sum(row[2] for row in env.calls), 15000)
        opening = [agent._exploration_categories[f"c_{int(row[3].split('-')[-1]):02d}"]
                   for row in env.calls[:8]]
        self.assertGreaterEqual(opening.count("revenue"), 3)
        self.assertGreaterEqual(opening.count("transition"), 3)
        self.assertGreaterEqual(opening.count("history"), 2)
        self.assertIn("selection_diagnostics", agent.last_report)
        self.assertEqual(agent.last_report["strategy_config"]["exploration_policy"], "balanced")
        actions = [event["action"] for event in agent.last_report["events"] if event.get("role") == "experimenter"]
        self.assertEqual(actions[8:12], ["explore", "confirm", "explore", "confirm"])
        rows = agent.last_report["pilots"]
        self.assertEqual(rows[8]["candidate_id"], rows[9]["candidate_id"])
        self.assertEqual(rows[10]["candidate_id"], rows[11]["candidate_id"])
        self.assertNotEqual(rows[8]["candidate_id"], rows[10]["candidate_id"])
        self.assertEqual(len({row["candidate_id"] for row in rows}), 10)

    def test_negative_upper_bound_releases_reserved_pair(self):
        agent = Agent(exploration_policy="balanced")
        pool = [candidate(i) for i in range(12)]
        agent._candidates = lambda profile, tariffs, warnings: (pool, "test")
        env = FakeEnv(ratio=-0.5)
        agent.act(env)
        actions = [event["action"] for event in agent.last_report["events"] if event.get("role") == "experimenter"]
        self.assertNotIn("confirm", actions)

    def test_low_resources_fall_back_without_unconfirmable_pair(self):
        agent = Agent(exploration_policy="balanced")
        pool = [candidate(i, size=20) for i in range(12)]
        agent._candidates = lambda profile, tariffs, warnings: (pool, "test")
        env = FakeEnv(contacts=200)
        agent.act(env)
        self.assertEqual(len({r["candidate_id"] for r in agent.last_report["pilots"]}), 8)
        self.assertEqual(len(env.calls), 9)

    def test_no_positive_variant_still_returns_mandatory_fallback(self):
        agent = Agent()
        pool = [candidate(i) for i in range(4)]
        agent._candidates = lambda profile, tariffs, warnings: (pool, "test")
        env = FakeEnv(ratio=-0.5)
        campaigns = agent.act(env)
        self.assertEqual(len(campaigns), 1)
        self.assertIn("no_positive_conservative_plan_fallback", agent.last_report["warnings"])


if __name__ == "__main__":
    unittest.main()
