"""Export one public evaluator run for the optional web presentation."""

import argparse
import contextlib
from collections import Counter
import hashlib
import importlib
import io
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def _finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def forecast_summary(report):
    """Forecast only the final plan; never subtract this from the all-campaign score."""
    rows = report.get("allocation")
    campaigns = report.get("campaigns")
    if not isinstance(rows, list) or not isinstance(campaigns, list) or not rows or len(rows) != len(campaigns):
        return None
    fields = ("estimated_net", "conservative_net", "communication_cost")
    if any(not isinstance(row, dict) or any(_finite(row.get(field)) is None for field in fields) for row in rows):
        return None
    return {"scope": "final_campaigns_only", "campaign_count": len(rows),
            **{field: math.fsum(float(row[field]) for row in rows) for field in fields},
            "comparison_to_evaluation": "not_comparable"}


def validate_selection_diagnostics(report):
    """Check optional counts and source references independently of display code."""
    data = report.get("selection_diagnostics")
    if data is None:
        return {"checked": False, "valid": True}
    if not isinstance(data, dict):
        return {"checked": True, "valid": False, "errors": ["diagnostics_type"]}
    groups = {}
    for index, row in enumerate(report.get("pilots", [])):
        if isinstance(row, dict) and row.get("status") == "completed":
            key = (row.get("candidate_id"), row.get("channel"))
            groups.setdefault(key, []).append(f"pilots.{index}")
    generated = report.get("candidate_count")
    expected = {"generated_candidates": generated,
                "tested_candidates": len({key[0] for key in groups}), "tested_variants": len(groups),
                "confirmed_variants": sum(len(refs) >= 2 for refs in groups.values()),
                "selected_variants": len(report.get("campaigns", []))}
    if isinstance(generated, int) and not isinstance(generated, bool):
        expected["unexplored_candidates"] = generated - expected["tested_candidates"]
    errors = [key for key, value in expected.items() if not isinstance(data.get(key), int)
              or isinstance(data.get(key), bool) or data[key] < 0 or data[key] != value]
    variants = data.get("variants")
    allowed = {"selected", "mandatory_fallback", "insufficient_pilots", "nonpositive_estimate",
               "overlap", "budget", "contacts", "not_selected"}
    selected = {(str(campaign.get("campaign_name", "")).removeprefix("compass_").removeprefix("fallback_"),
                 campaign.get("channel")) for campaign in report.get("campaigns", [])}
    seen, reasons = set(), Counter()
    if not isinstance(variants, list) or len(variants) > 20:
        errors.append("variants_type_or_size")
    else:
        for row in variants:
            if not isinstance(row, dict):
                errors.append("variant_type")
                continue
            key = (row.get("candidate_id"), row.get("channel"))
            if key not in groups or key in seen:
                errors.append("variant_identity")
            seen.add(key)
            if (row.get("pilot_refs") != groups.get(key) or row.get("repeats") != len(groups.get(key, []))
                    or not isinstance(row.get("selected"), bool) or row["selected"] != (key in selected)
                    or _finite(row.get("conservative_net")) is None or row.get("reason") not in allowed):
                errors.append("variant_evidence")
            reasons[str(row.get("reason"))] += 1
        if seen != set(groups):
            errors.append("variant_coverage")
        if dict(reasons) != data.get("reason_counts"):
            errors.append("reason_counts")
    return {"checked": True, "valid": not errors, "errors": sorted(set(errors)),
            "source": "completed_report_records_and_returned_plan"}


def _provenance():
    metadata = {"source_git_sha": None, "dirty": None, "seed": None,
                "requested_mode": "offline" if os.environ.get("ARPU_OFFLINE") == "1" or not os.environ.get("OPENAI_API_KEY") else "openai_with_fallback"}
    try:
        metadata["source_git_sha"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), check=True,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        metadata["dirty"] = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(ROOT), check=True,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    for key, filename in (("controller_sha256", "agent.py"), ("candidate_sha256", "candidate_model.py"),
                          ("advisor_sha256", "llm_advisor.py")):
        path = ROOT / filename
        if path.is_file():
            try:
                metadata[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                metadata[key] = None
        else:
            metadata[key] = None
    return metadata


def _atomic_write(path, payload):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(path.parent), prefix=".report-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-id", help="Server-owned output identity; exactly 32 lowercase hex characters")
    args = parser.parse_args(argv)
    if not 0 <= args.seed < 2 ** 32:
        parser.error("--seed must be between 0 and 4294967295")
    if args.run_id is not None and not re.fullmatch(r"[0-9a-f]{32}", args.run_id):
        parser.error("--run-id must be 32 lowercase hex characters")
    os.chdir(ROOT)
    destination = ROOT / "output" / "runs" / (args.run_id + ".json") if args.run_id else ROOT / "output" / "report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    provenance = _provenance()
    provenance["seed"] = args.seed
    if args.run_id:
        provenance["run_id"] = args.run_id
    try:
        from benchmark import PublicCaptureAgent, validate_returned_plan, validate_portfolio_evidence, _resource_match
        from local_eval import evaluate_agent
        wrapper = PublicCaptureAgent(importlib.import_module("agent"))
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = evaluate_agent(wrapper, seed=args.seed, verbose=False)
        report = wrapper.last_report
        net = _finite(result.get("net_arpu_gain")) if isinstance(result, dict) else None
        if result is None or not isinstance(report, dict) or net is None:
            print("export failed: invalid_evaluation", file=sys.stderr)
            return 1
        validation = validate_returned_plan(wrapper)
        portfolio_evidence = validate_portfolio_evidence(wrapper, validation)
        validation["portfolio"] = portfolio_evidence
        diagnostics_valid = validate_selection_diagnostics(report)
        validation["selection_diagnostics"] = diagnostics_valid
        resources_valid, _ = _resource_match(report, wrapper.after)
        rejected = bool(re.search(r"Агент упал|Кампания .*отброшена|Агент не вернул", captured.getvalue()))
        planned = report.get("planned_resources", {})
        expected = {"remaining_budget": validation["available_budget"] - validation["total_cost"],
                    "remaining_contacts": validation["available_contacts"] - validation["total_contacts"]} if validation.get("valid") else {}
        planned_valid = bool(expected) and isinstance(planned, dict) and all(
            _finite(planned.get(key)) is not None and abs(_finite(planned[key]) - value) < 1e-6 for key, value in expected.items())
        pilots = report.get("pilots")
        if (not validation.get("valid") or not portfolio_evidence["valid"] or not diagnostics_valid["valid"] or not resources_valid or not planned_valid or rejected
                or report.get("campaigns") != wrapper.returned_campaigns or report.get("schema_version") != "1.0"
                or not isinstance(pilots, list) or not 1 <= len(pilots) <= 20
                or not 1 <= int(result.get("n_pilots", 0)) <= 20):
            print("export failed: invalid_report_or_plan", file=sys.stderr)
            return 1
        actual_pilots = int(result["n_pilots"])
        completed = sum(isinstance(row, dict) and row.get("status") == "completed" for row in pilots)
        consumed = wrapper.before["pilots_left"] - wrapper.after["pilots_left"]
        # Failed calls may consume no slot. Their records remain explicitly
        # reported attempts, while the evaluator supplies the actual count.
        if (not completed <= actual_pilots <= len(pilots) or actual_pilots != consumed
                or int(result.get("n_campaigns", 0)) != actual_pilots + len(wrapper.returned_campaigns)):
            print("export failed: pilot_or_campaign_count_mismatch", file=sys.stderr)
            return 1
        validation["pilot_evidence"] = {"reported_attempts": len(pilots), "reported_completed": completed,
                                        "public_pilots": actual_pilots, "record_source": "agent_report"}
        provenance["mode"] = report.get("engine", "unknown")
        output = dict(report)
        output.update({
            "seed": args.seed, "synthetic": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provenance": provenance, "validation": validation,
            "evaluation": {
                "net_arpu_gain": net, "status": str(result.get("status", "unknown")),
                "scope": "pilots_and_final_deduplicated",
                "n_pilots": int(result.get("n_pilots", 0)),
                "n_campaigns_including_pilots": int(result.get("n_campaigns", 0)),
            },
        })
        forecast = forecast_summary(report)
        if forecast is not None:
            output["forecast_summary"] = forecast
        _atomic_write(destination, output)
        print(destination)
        print("Engine:", output.get("engine", "unknown"))
        for event in output.get("advisor", []):
            print("OpenAI:", event.get("phase"), event.get("status"), event.get("reason", ""), event.get("status_code", ""))
        return 0
    except Exception:
        print("export failed: execution_error", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
