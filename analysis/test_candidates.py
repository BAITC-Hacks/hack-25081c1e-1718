"""Contract and leakage checks: python -m unittest discover -s analysis -v."""

import inspect
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from candidate_model import build_candidates


ROOT = Path(__file__).resolve().parents[1]


class CandidateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = pd.read_csv(ROOT / "customer_profile.csv")
        cls.tariffs = pd.read_csv(ROOT / "tariff_dictionary.csv")

    def test_real_candidates_match_exact_filters_and_do_not_mutate_inputs(self):
        profile, tariffs = self.profile.copy(deep=True), self.tariffs.copy(deep=True)
        result = build_candidates(profile, tariffs, ROOT / "data")
        self.assertEqual(len(inspect.signature(build_candidates).parameters), 3)
        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), 320)
        self.assertEqual(len({item["candidate_id"] for item in result}), len(result))
        json.dumps(result, allow_nan=False)
        for item in result:
            mask = pd.Series(True, index=profile.index)
            for key, value in item["filters"].items():
                self.assertIn(key, {"filter_current_tariff", "filter_arpu_segment", "filter_data_segment", "filter_call_segment"})
                mask &= profile[key.removeprefix("filter_")].eq(value).fillna(False)
            audience = profile.loc[mask]
            self.assertEqual(len(audience), item["audience_size"])
            self.assertTrue(10 <= len(audience) <= 5000)
            self.assertFalse(audience.current_tariff.eq(item["target_tariff"]).any())
            self.assertIn(item["target_tariff"], set(tariffs.tariff_plan_code))
            self.assertAlmostEqual(audience.predicted_arpu.clip(lower=0).sum(), item["arpu_sum"], places=6)
            self.assertLessEqual(abs(item["prior_lift_ratio"]), 0.025)
            self.assertIsInstance(item["prior_n"], int)
            if item["filters"].get("filter_arpu_segment") == "LOW":
                self.assertEqual(item["prior_lift_ratio"], 0)
        pd.testing.assert_frame_equal(profile, self.profile)
        pd.testing.assert_frame_equal(tariffs, self.tariffs)

    def test_target_ids_cannot_change_candidates_or_history(self):
        altered = self.profile.copy(deep=True)
        altered["ID_NUMBER"] = range(900000, 900000 + len(altered))
        self.assertEqual(build_candidates(self.profile, self.tariffs, ROOT / "data"),
                         build_candidates(altered, self.tariffs, ROOT / "data"))

    def test_order_does_not_change_segment_target_ids(self):
        a = build_candidates(self.profile, self.tariffs, ROOT / "data")
        b = build_candidates(self.profile.sample(frac=1, random_state=2), self.tariffs.sample(frac=1, random_state=3), ROOT / "data")
        self.assertEqual([x["candidate_id"] for x in a], [x["candidate_id"] for x in b])

    def test_missing_or_malformed_history_produces_neutral_hypotheses(self):
        with tempfile.TemporaryDirectory() as folder:
            for contents in (None, "bad,column\na,b\n", "\xff\xfe"):
                if contents is not None:
                    (Path(folder) / "change_tariff.csv").write_bytes(contents.encode("latin1"))
                result = build_candidates(self.profile, self.tariffs, folder)
                self.assertTrue(result)
                self.assertTrue(all(x["prior_lift_ratio"] == 0 and x["prior_n"] == 0 for x in result))

    def test_empty_unknown_and_unexpressibly_large_cells(self):
        self.assertEqual(build_candidates(pd.DataFrame(), self.tariffs, ROOT / "data"), [])
        self.assertEqual(build_candidates(self.profile, pd.DataFrame(), ROOT / "data"), [])
        profile = pd.concat([self.profile.iloc[[0]]] * 5001, ignore_index=True)
        self.assertEqual(build_candidates(profile, self.tariffs, ROOT / "data"), [])
        profile = profile.iloc[:20].copy()
        profile["current_tariff"] = None
        self.assertEqual(build_candidates(profile, self.tariffs, ROOT / "data"), [])
        profile["current_tariff"] = "tariff_11"
        profile["arpu_segment"] = "nan"
        self.assertEqual(build_candidates(profile, self.tariffs, ROOT / "data"), [])

    def test_sparse_history_and_duplicate_rows_do_not_manufacture_support(self):
        profile = pd.concat([self.profile.iloc[[0]]] * 20, ignore_index=True)
        profile["current_tariff"] = "tariff_11"
        profile["arpu_segment"] = "HIGH"
        row = {"ID_NUMBER": 99, "tariff_plan_code_from": "tariff_11", "tariff_plan_code_to": "tariff_12",
               "AVG_ARPU_PREV_3M": 10000, "AVG_ARPU_NEXT_3M": 20000}
        with tempfile.TemporaryDirectory() as folder:
            pd.DataFrame([row] * 100).to_csv(Path(folder) / "change_tariff.csv", index=False)
            result = build_candidates(profile, self.tariffs, folder)
            pair = next(x for x in result if x["target_tariff"] == "tariff_12")
            self.assertEqual(pair["prior_n"], 1)
            self.assertEqual(pair["prior_lift_ratio"], 0)

    def test_identical_offers_need_positive_history_to_justify_switch(self):
        profile = pd.concat([self.profile.iloc[[0]]] * 20, ignore_index=True)
        profile["current_tariff"] = "tariff_5"
        tariffs = self.tariffs[self.tariffs.tariff_plan_code.isin(["tariff_5", "tariff_6"])].copy()
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(build_candidates(profile, tariffs, folder), [])


if __name__ == "__main__":
    unittest.main()
