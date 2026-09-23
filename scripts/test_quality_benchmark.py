import tempfile
import unittest
from pathlib import Path

try:
    from . import quality_benchmark as qb
except ImportError:  # Direct execution from the scripts directory.
    import quality_benchmark as qb


class QualityBenchmarkTests(unittest.TestCase):
    def test_frozen_inputs_detect_added_removed_and_analysis_changes(self):
        original = {"candidate_model.py": "a", "customer_profile.csv": "b", "analysis/history.py": "c"}
        self.assertTrue(qb.frozen_hashes_equal(original, dict(original)))
        self.assertFalse(qb.frozen_hashes_equal(original, {"candidate_model.py": "a"}))
        self.assertFalse(qb.frozen_hashes_equal(original, {**original, "data/new.csv": "d"}))
        self.assertFalse(qb.frozen_hashes_equal(original, {**original, "analysis/history.py": "d"}))

    def test_parse_seeds_rejects_duplicates_and_limits(self):
        self.assertEqual(qb.parse_seeds("0, 2,4"), [0, 2, 4])
        with self.assertRaises(ValueError):
            qb.parse_seeds("1,1")
        with self.assertRaises(ValueError):
            qb.parse_seeds(",".join(str(i) for i in range(51)))

    def test_parse_variants_and_invalid_ref(self):
        self.assertEqual(qb.parse_variants("balanced, empirical,combined"),
                         ["balanced", "empirical", "combined"])
        with self.assertRaises(ValueError):
            qb.parse_variants("balanced,balanced")
        self.assertFalse(qb._safe_ref("HEAD:agent.py"))
        self.assertFalse(qb._safe_ref("-bad"))

    def test_gate_requires_all_quality_conditions(self):
        baseline = {"median": 100.0, "p10": 50.0, "failure_count": 0, "negative_count": 0,
                    "max_runtime_seconds": 2.0, "successful_runs": 1}
        current = {"median": 111.0, "p10": 50.0, "failure_count": 0, "negative_count": 0,
                   "max_runtime_seconds": 3.0, "successful_runs": 1}
        paired = {"valid": True, "count": 1, "median_delta": 1.0}
        self.assertTrue(qb.adoption_gate(current, baseline, paired,
                                         evidence_comparable=True, inputs_unchanged=True,
                                         frozen_hashes_equal=True, expected_count=1)["passed"])
        current["median"] = 109.99
        self.assertFalse(qb.adoption_gate(current, baseline, paired,
                                          evidence_comparable=True, inputs_unchanged=True,
                                          frozen_hashes_equal=True, expected_count=1)["passed"])
        empty = qb.summarize([])
        self.assertFalse(qb.adoption_gate(empty, empty, {"valid": False, "count": 0}, expected_count=0)["passed"])

    def test_summary_keeps_failures_and_pairs_by_seed(self):
        records = [{"seed": 1, "status": "ok", "net_arpu_gain": 4.0, "elapsed_seconds": 2.0},
                   {"seed": 2, "status": "failure", "reason": "timeout", "elapsed_seconds": 301.0}]
        summary = qb.summarize(records)
        self.assertEqual(summary["successful_runs"], 1)
        self.assertEqual(summary["failure_count"], 1)
        mismatch = qb.paired_summary(records, [{"seed": 1, "status": "ok", "net_arpu_gain": 2.0},
                                                {"seed": 2, "status": "ok", "net_arpu_gain": 9.0}])
        self.assertFalse(mismatch["valid"])
        paired = qb.paired_summary([{"seed": 1, "status": "ok", "net_arpu_gain": 4.0}],
                                   [{"seed": 1, "status": "ok", "net_arpu_gain": 2.0}])
        self.assertEqual(paired["count"], 1)
        self.assertEqual(paired["median_delta"], 2.0)

    def test_snapshot_fingerprint_skips_forbidden_organizer_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "agent.py").write_text("agent", encoding="utf-8")
            (root / "mock_environment.py").write_text("hidden", encoding="utf-8")
            result = qb.fingerprint_snapshot(root, ["agent.py", "mock_environment.py"])
            self.assertEqual(list(result), ["agent.py"])
            self.assertEqual(qb.comparison_paths(["agent.py", "README.md", "data/example.csv"]),
                             ["agent.py", "data/example.csv"])

    def test_child_source_imports_snapshot_first(self):
        source = qb._child_source()
        self.assertIn("sys.path.insert(0, str(root))", source)
        self.assertIn('module = importlib.import_module("agent")', source)
        self.assertIn("QUALITY_RESULT=", source)

    def test_child_loads_fake_snapshot_modules_without_worktree_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "snapshot"
            scripts = snapshot / "scripts"
            scripts.mkdir(parents=True)
            (snapshot / "agent.py").write_text(
                "class Agent:\n"
                "    def __init__(self, exploration_policy=None, uncertainty_mode=None):\n"
                "        self.last_report = {}; self.exploration_policy = exploration_policy; self.uncertainty_mode = uncertainty_mode\n",
                encoding="utf-8",
            )
            (snapshot / "local_eval.py").write_text(
                "def evaluate_agent(agent, seed=None, verbose=False): return {}\n", encoding="utf-8")
            (scripts / "benchmark.py").write_text(
                "def run_one(module, seed, evaluate):\n"
                "    module.Agent()\n"
                "    return {'seed': seed, 'status': 'ok', 'net_arpu_gain': 3.0, 'elapsed_seconds': 0.1}\n",
                encoding="utf-8",
            )
            record = qb.run_child(snapshot, 7, "balanced", timeout=10)
            self.assertEqual(record["status"], "ok")
            self.assertEqual(record["variant"], "balanced")
            self.assertEqual(record["net_arpu_gain"], 3.0)
            self.assertTrue(record["strategy_config"]["honored"])


if __name__ == "__main__":
    unittest.main()
