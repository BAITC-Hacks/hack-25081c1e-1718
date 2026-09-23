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
    module._benchmark_source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    try:
        module._benchmark_git_sha = subprocess.run(
            ["git", "rev-parse", "--verify", ref + "^{commit}"], cwd=str(ROOT),
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, "baseline_commit_unresolved"
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


class PublicCaptureAgent:
    """Delegate while retaining only the evaluator's public environment surface."""

    def __init__(self, module):
        self._delegate = module.Agent()
        self.last_report = {}
        self.returned_campaigns = None
        self.before = None
        self.after = None

    @staticmethod
    def _snapshot(env):
        profile = env.customer_profile
        tariffs = env.tariffs
        channels = env.channels
        if hasattr(profile, "copy"):
            profile = profile.copy(deep=True)
        if hasattr(tariffs, "copy"):
            tariffs = tariffs.copy(deep=True)
        elif isinstance(tariffs, list):
            tariffs = list(tariffs)
        if isinstance(channels, dict):
            channels = dict(channels)
        elif isinstance(channels, (list, tuple, set)):
            channels = list(channels)
        return {
            "customer_profile": profile,
            "tariffs": tariffs,
            "channels": channels,
            "remaining_budget": finite(getattr(env, "remaining_budget", None)),
            "remaining_contacts": finite(getattr(env, "remaining_contacts", None)),
            "pilots_left": finite(getattr(env, "pilots_left", None)),
        }

    def act(self, env):
        self.before = self._snapshot(env)
        try:
            self.returned_campaigns = self._delegate.act(env)
            return self.returned_campaigns
        finally:
            self.after = self._snapshot(env)
            report = getattr(self._delegate, "last_report", {})
            self.last_report = report if isinstance(report, dict) else {}


def _channel_names(value):
    if isinstance(value, dict):
        value = value.keys()
    try:
        return {str(item) for item in value}
    except TypeError:
        return set()


def _filter_values(value, allow_union=False):
    if not isinstance(value, str) or not value.strip():
        return None
    if ";" in value and not allow_union:
        return None
    return {item.strip() for item in value.split(";") if item.strip()}


def validate_returned_plan(agent):
    """Validate the actual act() return using only captured public env data."""
    errors = []
    campaigns = agent.returned_campaigns
    before, after = agent.before, agent.after
    if not isinstance(campaigns, list) or not 1 <= len(campaigns) <= 10:
        return {"valid": False, "errors": ["campaign_count"], "campaign_count": 0}
    profile = before["customer_profile"]
    tariffs = {str(item) for item in before["tariffs"]["tariff_plan_code"].tolist()}
    channels = _channel_names(before["channels"])
    allowed = {"campaign_name", "target_tariff", "channel", "filter_arpu_segment",
               "filter_data_segment", "filter_call_segment", "filter_current_tariff"}
    column_map = {"filter_arpu_segment": "arpu_segment", "filter_data_segment": "data_segment",
                  "filter_call_segment": "call_segment", "filter_current_tariff": "current_tariff"}
    names, total_contacts, total_cost = set(), 0, 0.0
    details = []
    for index, campaign in enumerate(campaigns):
        if not isinstance(campaign, dict) or not {"target_tariff", "channel"}.issubset(campaign):
            errors.append(f"campaign_{index}_required_keys")
            continue
        unknown = set(campaign) - allowed
        if unknown:
            errors.append(f"campaign_{index}_unknown_keys")
        target, channel = campaign["target_tariff"], campaign["channel"]
        if not isinstance(target, str) or not target.strip():
            errors.append(f"campaign_{index}_target_type")
        if not isinstance(channel, str) or not channel.strip():
            errors.append(f"campaign_{index}_channel_type")
        target, channel = str(target), str(channel)
        if target not in tariffs:
            errors.append(f"campaign_{index}_target")
        if channel not in channels or channel not in {"push", "sms", "digital_ads", "call"}:
            errors.append(f"campaign_{index}_channel")
        name = str(campaign.get("campaign_name", f"campaign_{index}"))
        if name in names:
            errors.append("duplicate_campaign_name")
        names.add(name)
        mask = None
        for key, column in column_map.items():
            values = _filter_values(campaign.get(key), allow_union=(key == "filter_current_tariff"))
            if campaign.get(key) is not None and values is None:
                errors.append(f"campaign_{index}_filter_type")
            if values:
                if column not in profile.columns:
                    errors.append(f"campaign_{index}_filter_column")
                    continue
                part = profile[column].astype(str).isin(values)
                mask = part if mask is None else mask & part
        count = int(mask.sum()) if mask is not None else len(profile)
        cost = count * {"push": 0.0, "sms": 4.0, "digital_ads": 22.0, "call": 160.0}.get(channel, float("inf"))
        total_contacts += count
        total_cost += cost
        details.append({"index": index, "audience": count, "cost": cost, "target": target, "channel": channel})
        if count < 1 or count > 5000:
            errors.append(f"campaign_{index}_audience")
    budget_available, contacts_available = after["remaining_budget"], after["remaining_contacts"]
    if budget_available is None or contacts_available is None or total_cost > budget_available + 1e-6:
        errors.append("final_budget")
    if contacts_available is None or total_contacts > contacts_available:
        errors.append("final_contacts")
    return {"valid": not errors, "errors": errors, "campaign_count": len(campaigns),
            "total_contacts": total_contacts, "total_cost": total_cost,
            "available_budget": budget_available, "available_contacts": contacts_available,
            "campaigns": details}


def _reported_resource_stage(resources):
    if not isinstance(resources, dict):
        return None
    if all(key in resources for key in ("remaining_budget", "remaining_contacts", "pilots_left")):
        return resources
    for key in ("after_pilots", "afterPILOTS", "remaining"):
        value = resources.get(key)
        if isinstance(value, dict) and all(item in value for item in ("remaining_budget", "remaining_contacts", "pilots_left")):
            return value
    return None


def _resource_match(report, observed):
    stage = _reported_resource_stage(report.get("resources"))
    if stage is None:
        stage = _reported_resource_stage(report)
    if stage is None:
        return False, ["report_resource_stage_missing"]
    errors = []
    for key in ("remaining_budget", "remaining_contacts", "pilots_left"):
        expected, actual = finite(observed.get(key)), finite(stage.get(key))
        if expected is None or actual is None or abs(expected - actual) > 1e-6:
            errors.append(f"report_{key}_mismatch")
        if actual is None or actual < 0:
            errors.append(f"report_{key}_invalid")
    return not errors, errors


def _planned_resource_stage(report):
    if not isinstance(report, dict):
        return None
    for key in ("planned_resources", "planned_resources_after_final"):
        value = report.get(key)
        if isinstance(value, dict):
            return value
    resources = report.get("resources")
    if isinstance(resources, dict):
        for key in ("planned_resources", "planned_resources_after_final", "after_final"):
            value = resources.get(key)
            if isinstance(value, dict):
                return value
    return None


def run_one(module, seed, evaluate):
    started = time.monotonic()
    record = {"seed": seed, "status": "failure"}
    try:
        agent = PublicCaptureAgent(module)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = evaluate(agent, seed=seed, verbose=False)
        if re.search(r"Агент упал|Кампания .*отброшена|Агент не вернул", output.getvalue()):
            record["reason"] = "official_evaluator_rejected_execution_or_campaign"
            return record
        report = agent.last_report
        if result is None or not isinstance(report, dict):
            record["reason"] = "missing_evaluation_or_report"
            return record
        net = finite(result.get("net_arpu_gain")) if isinstance(result, dict) else None
        campaigns = agent.returned_campaigns
        pilots = report.get("pilots", report.get("pilot_records"))
        if net is None or not isinstance(campaigns, list) or not isinstance(pilots, list):
            record["reason"] = "invalid_plan_or_metrics"
            return record
        plan_validation = validate_returned_plan(agent)
        resource_valid, resource_errors = _resource_match(report, agent.after)
        if not plan_validation["valid"] or not resource_valid:
            record["reason"] = "invalid_plan_or_resource_report"
            record["validation"] = {"plan": plan_validation, "resources": resource_errors}
            return record
        completed = 0
        for pilot in pilots:
            if isinstance(pilot, dict) and pilot.get("status", "completed") == "completed":
                completed += 1
        actual_pilots = finite(result.get("n_pilots"))
        if not 1 <= completed <= 20 or len(pilots) > 20 or actual_pilots is None or not 1 <= actual_pilots <= 20:
            record["reason"] = "pilot_limit_exceeded"
            return record
        resources = report.get("resources", {})
        planned_resources = report.get("planned_resources", report.get("planned_resources_after_final", {}))
        if isinstance(resources, dict) and not planned_resources:
            planned_resources = resources.get("planned_resources_after_final", {})
        planned_stage = _planned_resource_stage(report)
        expected_planned = {
            "remaining_budget": plan_validation["available_budget"] - plan_validation["total_cost"],
            "remaining_contacts": plan_validation["available_contacts"] - plan_validation["total_contacts"],
        }
        if planned_stage is None or any(
            finite(planned_stage.get(key)) is None or abs(finite(planned_stage.get(key)) - expected_planned[key]) > 1e-6
            for key in expected_planned
        ):
            record["reason"] = "planned_resource_mismatch"
            record["validation"] = {"plan": plan_validation, "resources": "after_pilots_matched", "planned": {"expected": expected_planned, "reported": planned_stage}}
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
        limits = {"remaining_budget": 100000, "remaining_contacts": 15000, "pilots_left": 20}
        observed_stage = _reported_resource_stage(resources)
        if observed_stage is None or any(finite(observed_stage[key]) > limit for key, limit in limits.items()):
            record["reason"] = "resource_counter_out_of_range"
            return record
        record.update({
            "status": "ok", "evaluation_status": result.get("status"), "net_arpu_gain": net, "pilots_completed": completed,
            "final_campaign_count": len(campaigns), "elapsed_seconds": time.monotonic() - started,
            "resources": resources, "planned_resources": planned_resources,
            "public_before": {key: value for key, value in agent.before.items() if key not in ("customer_profile", "tariffs", "channels")},
            "public_after": {key: value for key, value in agent.after.items() if key not in ("customer_profile", "tariffs", "channels")},
            "validation": {"plan": plan_validation, "resources": "matched_public_after_pilots"},
            "resource_evidence": "Actual returned campaigns and public env counters were independently validated.",
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
        shared_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() if (ROOT / name).is_file() else None
                         for name in ("candidate_model.py", "llm_advisor.py", "customer_profile.csv", "tariff_dictionary.csv",
                                      "data/change_tariff.csv", "data/traffic.csv", "data/arpu_monthly.csv", "data/dict_tariff.csv")}
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
            "shared_input_sha256": shared_hashes,
            "comparison_scope": "Controller comparison; both use current data, optional candidate_model, advisor and public evaluator.",
            "baseline": {"ref": args.baseline_ref,
                         "resolved_sha": getattr(baseline_module, "_benchmark_git_sha", None),
                         "controller_sha256": getattr(baseline_module, "_benchmark_source_sha256", None),
                         "records": baseline_records},
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
