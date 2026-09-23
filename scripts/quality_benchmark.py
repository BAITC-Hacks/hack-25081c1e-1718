"""Compare complete Git revisions under identical offline local-evaluator runs.

This is a development-quality comparison, not an organizer score.  Each row is
executed in a fresh subprocess whose import root is a unique ``git archive``
snapshot.  The parent process never imports controller code from a snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import textwrap
import uuid


ROOT = Path(__file__).resolve().parents[1]
MAX_SEEDS = 50
MAX_RUNTIME_SECONDS = 300.0
FORBIDDEN_NAMES = {"environment.py", "mock_environment.py", "scoring_core.py"}
VARIANT_NAMES = ("balanced", "empirical", "combined")
REQUIRED_COMPARISON_PATHS = {"agent.py", "candidate_model.py", "llm_advisor.py",
                             "local_eval.py", "scripts/benchmark.py"}


def parse_seeds(value: str) -> list[int]:
    result: list[int] = []
    for token in str(value).split(","):
        token = token.strip()
        if not token:
            continue
        try:
            seed = int(token)
        except ValueError as error:
            raise ValueError("seeds must be comma-separated integers") from error
        if not 0 <= seed < 2**32 or seed in result:
            raise ValueError("seeds must be unique integers from 0 through 4294967295")
        result.append(seed)
    if not result or len(result) > MAX_SEEDS:
        raise ValueError("seed count must be between 1 and 50")
    return result


def parse_variants(value: str) -> list[str]:
    names = []
    for token in str(value).split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token not in VARIANT_NAMES or token in names:
            raise ValueError(f"variants must be unique values from: {', '.join(VARIANT_NAMES)}")
        names.append(token)
    if not names:
        raise ValueError("at least one variant is required")
    return names


def _safe_ref(ref: str) -> bool:
    return bool(ref) and not ref.startswith("-") and ":" not in ref


def resolve_ref(ref: str) -> str:
    if not _safe_ref(ref):
        raise ValueError("invalid_git_ref")
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", ref + "^{commit}"],
            cwd=ROOT, check=True, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("git_ref_unavailable") from error
    sha = completed.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("git_ref_unresolved")
    return sha


def _tracked_paths(ref: str) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref], cwd=ROOT,
        check=True, capture_output=True, text=True, timeout=20,
    )
    return [line for line in completed.stdout.splitlines() if line]


def _allowed_for_fingerprint(path: str) -> bool:
    # The organizer implementation is deliberately not inspected here.  It is
    # still included in the archive for the official local evaluator child.
    return Path(path).name not in FORBIDDEN_NAMES


def comparison_paths(paths: list[str]) -> list[str]:
    """Return tracked executable code and public input data for the manifest."""
    result = []
    for path in paths:
        if not _allowed_for_fingerprint(path):
            continue
        suffix = Path(path).suffix.lower()
        if suffix in {".py", ".ps1", ".csv", ".json"}:
            result.append(path)
    return result


def _frozen_path(path: str) -> bool:
    return (path == "candidate_model.py" or path.startswith(("data/", "analysis/")) or
            (Path(path).suffix.lower() == ".csv" and path != "submission.csv"))


def frozen_hashes_equal(baseline: dict[str, str], current: dict[str, str]) -> bool:
    """Check candidate and public CSV/data inputs stayed frozen across revisions."""
    frozen = [path for path in set(baseline) | set(current) if _frozen_path(path)]
    return bool(frozen) and all(path in baseline and path in current and baseline[path] == current[path]
                                for path in frozen)


def fingerprint_snapshot(snapshot: Path, paths: list[str]) -> dict[str, str]:
    result = {}
    for relative in paths:
        if not _allowed_for_fingerprint(relative):
            continue
        path = snapshot / relative
        if path.is_file():
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def create_snapshot(ref: str, resolved_sha: str, parent: Path) -> tuple[Path, list[str]]:
    """Extract one immutable, unique Git snapshot without unsafe tar paths."""
    snapshot = parent / f"{resolved_sha[:12]}-{uuid.uuid4().hex}"
    snapshot.mkdir(parents=True)
    archive = snapshot.with_suffix(".tar")
    try:
        with archive.open("wb") as stream:
            subprocess.run(["git", "archive", "--format=tar", resolved_sha], cwd=ROOT,
                           check=True, stdout=stream, stderr=subprocess.PIPE, timeout=60)
        paths = _tracked_paths(resolved_sha)
        with tarfile.open(archive, "r") as tar:
            root = snapshot.resolve()
            members = []
            for member in tar.getmembers():
                if member.issym() or member.islnk() or member.isdev() or not (member.isdir() or member.isfile()):
                    raise ValueError("unsafe_git_archive_member")
                target = (snapshot / member.name).resolve()
                if target != root and root not in target.parents:
                    raise ValueError("unsafe_git_archive_path")
                members.append(member)
            tar.extractall(snapshot, members=members)
        return snapshot, paths
    except Exception:
        # Keep the unique partial snapshot for post-mortem inspection.  Never
        # recursively remove a path after an untrusted archive error.
        raise
    finally:
        archive.unlink(missing_ok=True)


def _child_source() -> str:
    return textwrap.dedent(r'''
        import contextlib
        import hashlib
        import importlib
        import inspect
        import io
        import json
        import os
        from pathlib import Path
        import sys

        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root))
        sys.path.insert(0, str(root / "scripts"))
        variant = sys.argv[1]
        seed = int(sys.argv[2])

        import benchmark
        import local_eval
        module = importlib.import_module("agent")
        original = module.Agent
        holder = {}
        options = {
            "balanced": {"exploration_policy": "balanced", "uncertainty_mode": "template"},
            "empirical": {"exploration_policy": "baseline", "uncertainty_mode": "empirical"},
            "combined": {"exploration_policy": "balanced", "uncertainty_mode": "empirical"},
        }.get(variant, {})

        class UnsupportedStrategyConfig(Exception):
            pass

        class VariantAgent:
            def __new__(cls):
                if variant == "baseline":
                    instance = original()
                else:
                    try:
                        parameters = inspect.signature(original).parameters
                    except (TypeError, ValueError) as error:
                        holder["config_error"] = "constructor_signature_unavailable"
                        raise UnsupportedStrategyConfig("constructor_signature_unavailable") from error
                    accepts_kwargs = any(p.kind == p.VAR_KEYWORD for p in parameters.values())
                    if not accepts_kwargs and any(key not in parameters for key in options):
                        holder["config_error"] = "requested_strategy_modes_not_supported"
                        raise UnsupportedStrategyConfig("requested_strategy_modes_not_supported")
                    try:
                        instance = original(**options)
                    except Exception as error:
                        holder["config_error"] = "requested_strategy_modes_rejected"
                        raise UnsupportedStrategyConfig("requested_strategy_modes_rejected") from error
                    for key, value in options.items():
                        if hasattr(instance, key) and getattr(instance, key) != value:
                            holder["config_error"] = "requested_strategy_mode_not_honored"
                            raise UnsupportedStrategyConfig("requested_strategy_mode_not_honored")
                holder["instance"] = instance
                return instance

        module.Agent = VariantAgent
        try:
            record = benchmark.run_one(module, seed, local_eval.evaluate_agent)
        except UnsupportedStrategyConfig as error:
            record = {"seed": seed, "status": "failure", "reason": str(error),
                      "elapsed_seconds": 0.0}
        if holder.get("config_error"):
            record["status"] = "failure"
            record["reason"] = holder["config_error"]
        delegate = holder.get("instance")
        report = getattr(delegate, "last_report", {}) if delegate is not None else {}
        if isinstance(report, dict):
            selection = report.get("selection_diagnostics", report.get("portfolio_selection"))
            allocations = report.get("allocation", [])
            forecasts = []
            if isinstance(allocations, list):
                forecasts = [row.get("conservative_net") for row in allocations
                             if isinstance(row, dict) and isinstance(row.get("conservative_net"), (int, float))]
            record["report_metrics"] = {
                "candidate_count": report.get("candidate_count"),
                "tested_candidate_count": report.get("tested_candidate_count",
                    report.get("tested_count", report.get("pilot_candidate_count"))),
                "selection_diagnostics": selection,
                "forecast_sum_conservative_net": sum(forecasts) if forecasts else None,
                "allocation_count": len(allocations) if isinstance(allocations, list) else None,
            }
        record["variant"] = variant
        record["strategy_config"] = {"requested": options, "applied": variant == "baseline" or record.get("status") == "ok",
                                      "honored": variant == "baseline" or record.get("reason") not in {
                                          "requested_strategy_modes_not_supported", "requested_strategy_modes_rejected",
                                          "requested_strategy_mode_not_honored", "constructor_signature_unavailable"}}
        print("QUALITY_RESULT=" + json.dumps(record, ensure_ascii=False, allow_nan=False), flush=True)
    ''')


def run_child(snapshot: Path, seed: int, variant: str, timeout: float = MAX_RUNTIME_SECONDS) -> dict:
    timeout = min(float(timeout), MAX_RUNTIME_SECONDS)
    runner = snapshot / "scripts" / f".quality_child_{uuid.uuid4().hex}.py"
    runner.write_text(_child_source(), encoding="utf-8")
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env["ARPU_OFFLINE"] = "1"
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONHASHSEED"] = "0"
    started = __import__("time").monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", str(runner), variant, str(seed)], cwd=snapshot, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        elapsed = __import__("time").monotonic() - started
    except subprocess.TimeoutExpired:
        return {"seed": seed, "variant": variant, "status": "failure",
                "reason": "timeout", "elapsed_seconds": timeout}
    finally:
        runner.unlink(missing_ok=True)
    marker = next((line[len("QUALITY_RESULT="):] for line in completed.stdout.splitlines()
                   if line.startswith("QUALITY_RESULT=")), None)
    if marker is None:
        return {"seed": seed, "variant": variant, "status": "failure",
                "reason": "child_no_result", "elapsed_seconds": elapsed}
    try:
        record = json.loads(marker)
    except json.JSONDecodeError:
        return {"seed": seed, "variant": variant, "status": "failure",
                "reason": "child_invalid_result", "elapsed_seconds": elapsed}
    record["elapsed_seconds"] = elapsed
    if completed.returncode != 0 and record.get("status") == "ok":
        record["status"] = "failure"
        record["reason"] = "child_nonzero_exit"
    return record


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * fraction
    left, right = int(index), min(int(index) + 1, len(values) - 1)
    return values[left] + (values[right] - values[left]) * (index - int(index))


def summarize(records: list[dict]) -> dict:
    values = [float(row["net_arpu_gain"]) for row in records
              if row.get("status") == "ok" and isinstance(row.get("net_arpu_gain"), (int, float))
              and math.isfinite(float(row["net_arpu_gain"]))]
    runtimes = [float(row["elapsed_seconds"]) for row in records if isinstance(row.get("elapsed_seconds"), (int, float))]
    ordered = sorted(values)
    median = None if not ordered else (ordered[len(ordered)//2] if len(ordered) % 2 else
                                       (ordered[len(ordered)//2-1] + ordered[len(ordered)//2]) / 2)
    return {
        "successful_runs": len(values), "failure_count": len(records) - len(values),
        "positive_count": sum(value > 0 for value in values),
        "negative_count": sum(value < 0 for value in values),
        "median": median, "p10": _percentile(values, 0.10),
        "min": min(values) if values else None, "max": max(values) if values else None,
        "max_runtime_seconds": max(runtimes) if runtimes else None,
    }


def paired_summary(current: list[dict], baseline: list[dict]) -> dict:
    current_by_seed = {row.get("seed"): row for row in current}
    baseline_by_seed = {row.get("seed"): row for row in baseline}
    if (len(current_by_seed) != len(current) or len(baseline_by_seed) != len(baseline)
            or set(current_by_seed) != set(baseline_by_seed)):
        return {"valid": False, "reason": "seed_pair_mismatch", "count": 0,
                "median_delta": None, "better": 0, "worse": 0, "equal": 0, "seeds": []}
    pairs = []
    for seed in sorted(current_by_seed):
        left, right = current_by_seed[seed], baseline_by_seed[seed]
        if left.get("status") != right.get("status") or left.get("status") != "ok":
            return {"valid": False, "reason": "non_successful_seed_pair", "count": 0,
                    "median_delta": None, "better": 0, "worse": 0, "equal": 0, "seeds": []}
        if not all(isinstance(row.get("net_arpu_gain"), (int, float)) and
                   math.isfinite(float(row["net_arpu_gain"])) for row in (left, right)):
            return {"valid": False, "reason": "nonfinite_seed_pair", "count": 0,
                    "median_delta": None, "better": 0, "worse": 0, "equal": 0, "seeds": []}
        pairs.append((float(left["net_arpu_gain"]) - float(right["net_arpu_gain"]), seed))
    deltas = [item[0] for item in pairs]
    return {"valid": True, "count": len(deltas), "median_delta": _percentile(deltas, 0.5),
            "better": sum(item > 1e-6 for item in deltas),
            "worse": sum(item < -1e-6 for item in deltas),
            "equal": sum(abs(item) <= 1e-6 for item in deltas),
            "seeds": [seed for _, seed in pairs]}


def adoption_gate(current_summary: dict, baseline_summary: dict, paired: dict, *,
                  evidence_comparable: bool = False, inputs_unchanged: bool = False,
                  frozen_hashes_equal: bool = False, expected_count: int | None = None) -> dict:
    baseline_median = baseline_summary.get("median")
    current_median = current_summary.get("median")
    current_runtime = current_summary.get("max_runtime_seconds")
    baseline_runtime = baseline_summary.get("max_runtime_seconds")
    current_p10, baseline_p10 = current_summary.get("p10"), baseline_summary.get("p10")
    delta = paired.get("median_delta")
    passed = all((current_summary.get("failure_count") == 0,
                  isinstance(current_runtime, (int, float)) and math.isfinite(float(current_runtime)) and
                  current_runtime <= MAX_RUNTIME_SECONDS,
                  baseline_summary.get("failure_count") == 0,
                  isinstance(baseline_runtime, (int, float)) and math.isfinite(float(baseline_runtime)) and
                  baseline_runtime <= MAX_RUNTIME_SECONDS,
                  expected_count is not None and current_summary.get("successful_runs") == expected_count and
                  baseline_summary.get("successful_runs") == expected_count and paired.get("count") == expected_count and
                  paired.get("valid") is True,
                  evidence_comparable, inputs_unchanged, frozen_hashes_equal,
                  isinstance(current_median, (int, float)) and isinstance(baseline_median, (int, float)) and
                  math.isfinite(float(current_median)) and math.isfinite(float(baseline_median)) and
                  current_median >= baseline_median * 1.10,
                  isinstance(delta, (int, float)) and math.isfinite(float(delta)) and delta > 0,
                  isinstance(current_p10, (int, float)) and isinstance(baseline_p10, (int, float)) and
                  math.isfinite(float(current_p10)) and math.isfinite(float(baseline_p10)) and
                  current_p10 >= baseline_p10,
                  isinstance(current_summary.get("negative_count"), int) and
                  isinstance(baseline_summary.get("negative_count"), int) and
                  current_summary["negative_count"] <= baseline_summary["negative_count"]))
    return {"passed": passed, "target_median_ratio": 1.10,
            "informational": "A passing development gate is evidence for a holdout run, not a judge-score guarantee."}


def _atomic_write(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temporary, path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="4473540")
    parser.add_argument("--current-ref", default="HEAD")
    parser.add_argument("--variants", default="balanced,empirical,combined")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9")
    parser.add_argument("--label", default="development")
    args = parser.parse_args(argv)
    try:
        seeds = parse_seeds(args.seeds)
        variants = parse_variants(args.variants)
        baseline_sha, current_sha = resolve_ref(args.baseline_ref), resolve_ref(args.current_ref)
    except ValueError as error:
        parser.error(str(error))
    label = re.sub(r"[^A-Za-z0-9_.-]+", "_", args.label)[:64] or "development"
    snapshot_root = ROOT / "output" / "quality-snapshots"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    try:
        baseline_snapshot, baseline_paths = create_snapshot(args.baseline_ref, baseline_sha, snapshot_root)
        current_snapshot, current_paths = create_snapshot(args.current_ref, current_sha, snapshot_root)
        baseline_hashes = fingerprint_snapshot(baseline_snapshot, comparison_paths(baseline_paths))
        current_hashes = fingerprint_snapshot(current_snapshot, comparison_paths(current_paths))
        baseline_records = []
        for seed in seeds:
            row = run_child(baseline_snapshot, seed, "baseline")
            baseline_records.append(row)
            print(f"baseline seed {seed}: {row.get('status')} {row.get('net_arpu_gain', row.get('reason', ''))}", flush=True)
        current_records = {}
        for variant in variants:
            current_records[variant] = []
            for seed in seeds:
                row = run_child(current_snapshot, seed, variant)
                current_records[variant].append(row)
                print(f"{variant} seed {seed}: {row.get('status')} {row.get('net_arpu_gain', row.get('reason', ''))}", flush=True)
        baseline_after = fingerprint_snapshot(baseline_snapshot, comparison_paths(baseline_paths))
        current_after = fingerprint_snapshot(current_snapshot, comparison_paths(current_paths))
        baseline_summary, current_summaries = summarize(baseline_records), {}
        inputs_unchanged = baseline_hashes == baseline_after and current_hashes == current_after
        comparable = REQUIRED_COMPARISON_PATHS.issubset(baseline_hashes) and REQUIRED_COMPARISON_PATHS.issubset(current_hashes)
        frozen_equal = frozen_hashes_equal(baseline_hashes, current_hashes)
        variants_output = {}
        for variant, records in current_records.items():
            current_summaries[variant] = summarize(records)
            paired = paired_summary(records, baseline_records)
            variants_output[variant] = {"records": records, "summary": current_summaries[variant],
                                        "paired_comparison": paired,
                                        "adoption_gate": adoption_gate(
                                            current_summaries[variant], baseline_summary, paired,
                                            evidence_comparable=comparable,
                                            inputs_unchanged=inputs_unchanged,
                                            frozen_hashes_equal=frozen_equal,
                                            expected_count=len(seeds))}
        payload = {
            "schema_version": "1.0", "kind": "full_revision_quality_comparison",
            "note": "Development evidence only; not an organizer score.",
            "baseline": {"ref": args.baseline_ref, "resolved_sha": baseline_sha,
                         "records": baseline_records, "summary": baseline_summary},
            "current": {"ref": args.current_ref, "resolved_sha": current_sha,
                        "variants": variants_output},
            "seeds": seeds, "variant_names": variants,
            "full_revision_hashes": {"baseline": baseline_hashes, "current": current_hashes},
            "fingerprinted_inputs_unchanged": inputs_unchanged,
            "evidence_comparable": comparable,
            "frozen_candidate_and_public_data_equal": frozen_equal,
            "frozen_hashes": {
                "baseline": {path: digest for path, digest in baseline_hashes.items()
                              if _frozen_path(path)},
                "current": {path: digest for path, digest in current_hashes.items()
                             if _frozen_path(path)},
            },
            "snapshot_dirs": {"baseline": str(baseline_snapshot), "current": str(current_snapshot)},
        }
        output = ROOT / "output" / f"quality-{label}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(output, payload)
        print(output)
        for variant in variants:
            gate = variants_output[variant]["adoption_gate"]
            print(f"{variant}: median={current_summaries[variant]['median']} gate={'PASS' if gate['passed'] else 'HOLD'}")
        return 0 if payload["fingerprinted_inputs_unchanged"] and payload["evidence_comparable"] else 1
    finally:
        # Snapshots intentionally remain for auditability and are unique per run.
        pass


if __name__ == "__main__":
    raise SystemExit(main())
