"""Compare agent controllers on identical local mock seeds (not a judge score)."""

import argparse
import contextlib
import importlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import types


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAX_SEEDS = 50


def parse_seeds(value):
    result = []
    for token in str(value).split(","):
        token = token.strip()
        if not token:
            continue
        try:
            seed = int(token)
        except ValueError as error:
            raise ValueError("seeds must be comma-separated integers") from error
        if not 0 <= seed < 2 ** 32 or seed in result:
            raise ValueError("seeds must be unique integers from 0 through 4294967295")
        result.append(seed)
    if not result or len(result) > MAX_SEEDS:
        raise ValueError("seed count must be between 1 and 50")
    return result


def load_ref(ref):
    if not ref or ref.startswith("-") or ":" in ref:
        return None, "invalid_git_ref"
    try:
        completed = subprocess.run(
            ["git", "show", ref + ":agent.py"], cwd=str(ROOT), check=True,
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        source = completed.stdout
    except (OSError, subprocess.SubprocessError):
        return None, "git_ref_unavailable"
    module = types.ModuleType("benchmark_baseline_agent")
    module.__file__ = str(ROOT / "agent.py")
    try:
        exec(compile(source, str(ROOT / "agent.py"), "exec"), module.__dict__)
        if not callable(getattr(module, "Agent", None)):
            return None, "baseline_agent_missing"
    except Exception:
        return None, "baseline_agent_invalid"
    return module, None


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def load_current():
    sys.path.insert(0, str(ROOT))
    return importlib.import_module("agent")


def run_one(module, seed, evaluate):
    started = time.monotonic()
    record = {"seed": seed, "status": "failure"}
    try:
        agent = module.Agent()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = evaluate(agent, seed=seed, verbose=False)
        if re.search(r"Агент упал|Кампания .*отброшена|Агент не вернул", output.getvalue()):
            record["reason"] = "official_evaluator_rejected_execution_or_campaign"
            return record
        report = getattr(agent, "last_report", None)
        if result is None or not isinstance(report, dict):
            record["reason"] = "missing_evaluation_or_report"
            return record
        net = finite(result.get("net_arpu_gain")) if isinstance(result, dict) else None
        campaigns = report.get("campaigns")
        pilots = report.get("pilots", report.get("pilot_records"))
        if net is None or not isinstance(campaigns, list) or not isinstance(pilots, list):
            record["reason"] = "invalid_plan_or_metrics"
            return record
        if len(campaigns) < 1 or len(campaigns) > 10:
            record["reason"] = "invalid_final_campaign_count"
            return record
        completed = 0
        for pilot in pilots:
            if isinstance(pilot, dict) and pilot.get("status", "completed") == "completed":
                completed += 1
        if completed > 20:
            record["reason"] = "pilot_limit_exceeded"
            return record
        resources = report.get("resources", {})
        planned_resources = report.get("planned_resources", {})
        if not isinstance(resources, dict) or not all(key in resources for key in ("remaining_budget", "remaining_contacts", "pilots_left")):
            record["reason"] = "missing_resource_counters"
            return record
        resource_values = []
        if isinstance(resources, dict):
            for value in resources.values():
                if isinstance(value, dict):
                    resource_values.extend(value.values())
                else:
                    resource_values.append(value)
        if isinstance(planned_resources, dict):
            resource_values.extend(planned_resources.values())
        if any(finite(value) is None or finite(value) < 0 for value in resource_values):
            record["reason"] = "invalid_resources"
            return record
        record.update({
            "status": "ok", "evaluation_status": result.get("status"), "net_arpu_gain": net, "pilots_completed": completed,
            "final_campaign_count": len(campaigns), "elapsed_seconds": time.monotonic() - started,
            "resources": resources, "planned_resources": planned_resources,
            "warnings": report.get("warnings", []),
        })
    except Exception:
        record["reason"] = "execution_failure"
    finally:
        record.setdefault("elapsed_seconds", time.monotonic() - started)
    return record


def summary(records):
    values = [item["net_arpu_gain"] for item in records if item.get("status") == "ok"]
    if not values:
        return {"successful_runs": 0, "positive_count": 0, "negative_count": 0}
    values.sort()
    return {
        "successful_runs": len(values), "median": values[len(values) // 2] if len(values) % 2 else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2,
        "min": min(values), "max": max(values),
        "positive_count": sum(value > 0 for value in values),
        "negative_count": sum(value < 0 for value in values),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9")
    parser.add_argument("--baseline-ref")
    parser.add_argument("--label", default="comparison")
    args = parser.parse_args(argv)
    try:
        seeds = parse_seeds(args.seeds)
    except ValueError as error:
        parser.error(str(error))
    label = re.sub(r"[^A-Za-z0-9_.-]+", "_", args.label)[:64] or "comparison"
    previous = os.environ.get("ARPU_OFFLINE")
    os.environ["ARPU_OFFLINE"] = "1"
    try:
        os.chdir(ROOT)
        controller_hash = hashlib.sha256((ROOT / "agent.py").read_bytes()).hexdigest()
        local_eval = importlib.import_module("local_eval")
        evaluate = getattr(local_eval, "evaluate_agent", None)
        current_module = load_current()
        baseline_module, baseline_error = load_ref(args.baseline_ref) if args.baseline_ref else (None, None)
        current_records, baseline_records = [], []
        for seed in seeds:
            current = run_one(current_module, seed, evaluate) if callable(evaluate) else {"seed": seed, "status": "failure", "reason": "evaluate_agent_missing"}
            baseline = run_one(baseline_module, seed, evaluate) if baseline_module and callable(evaluate) else {"seed": seed, "status": "not_requested" if not args.baseline_ref else "failure", "reason": baseline_error if args.baseline_ref else None}
            current_records.append(current); baseline_records.append(baseline)
            left = current.get("net_arpu_gain", "FAIL"); right = baseline.get("net_arpu_gain", "FAIL")
            print(f"seed {seed}: current={left} baseline={right}", flush=True)
        payload = {
            "schema_version": "1.0", "note": "not judge score", "git_sha": None,
            "dirty": None, "seeds": seeds, "current": current_records,
            "controller_sha256": controller_hash,
            "comparison_scope": "Controller comparison; both use current data, optional candidate_model, advisor and public evaluator.",
            "baseline": {"ref": args.baseline_ref, "records": baseline_records},
            "summary": {"current": summary(current_records), "baseline": summary(baseline_records)},
        }
        try:
            payload["git_sha"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), check=True, capture_output=True, text=True, timeout=10).stdout.strip()
            payload["dirty"] = bool(subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT), check=True, capture_output=True, text=True, timeout=10).stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
        output_dir = ROOT / "output"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"benchmark-{label}.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(f"summary: {output_path}")
        print(json.dumps(payload["summary"], ensure_ascii=False))
        current_ok = all(item.get("status") == "ok" for item in current_records)
        baseline_ok = not args.baseline_ref or all(item.get("status") == "ok" for item in baseline_records)
        return 0 if current_ok and baseline_ok else 1
    finally:
        if previous is None:
            os.environ.pop("ARPU_OFFLINE", None)
        else:
            os.environ["ARPU_OFFLINE"] = previous


if __name__ == "__main__":
    raise SystemExit(main())
