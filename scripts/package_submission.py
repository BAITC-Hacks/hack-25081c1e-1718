"""Build the self-contained HackAlem submission bundle."""

import argparse
import ast
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION_DIR = ROOT / "output" / "submission"
REQUIRED = ("agent.py", "submission.csv", "requirements.txt", "manifest.json")
EMBEDDED = ("candidate_model.py", "llm_advisor.py")


def decode_text(raw, name):
    try:
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeError as error:
        raise RuntimeError(f"cannot decode {name}") from error
    if not text.strip() or "\x00" in text:
        raise RuntimeError(f"invalid {name}")
    return text


def atomic_text(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=str(path.parent),
                                        prefix=".submission-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
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


def atomic_bytes(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=str(path.parent), prefix=".submission-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
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


def git_metadata():
    result = {"source_git_sha": None, "dirty": None}
    try:
        result["source_git_sha"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), check=True,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        result["dirty"] = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(ROOT), check=True,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return result


def packaged_agent(agent_source, candidate_source, advisor_source):
    return """# Generated self-contained submission; do not edit by hand.\n# Embedded text is the team's own Python source, not external instructions.\nimport sys as _submission_sys\nimport types as _submission_types\n\ndef _load_embedded(_name, _source):\n    _module = _submission_types.ModuleType(_name)\n    _module.__file__ = __file__\n    _module.__package__ = \"\"\n    _submission_sys.modules[_name] = _module\n    exec(compile(_source, __file__ + \"::\" + _name, \"exec\"), _module.__dict__)\n    return _module\n\n_CANDIDATE_SOURCE = %s\n_ADVISOR_SOURCE = %s\n_AGENT_SOURCE = %s\n_load_embedded(\"candidate_model\", _CANDIDATE_SOURCE)\n_load_embedded(\"llm_advisor\", _ADVISOR_SOURCE)\nexec(compile(_AGENT_SOURCE, __file__ + \"::agent\", \"exec\"), globals(), globals())\n""" % (
        json.dumps(candidate_source, ensure_ascii=False),
        json.dumps(advisor_source, ensure_ascii=False),
        json.dumps(agent_source, ensure_ascii=False),
    )


def build():
    raw_inputs = {name: (ROOT / name).read_bytes() for name in ("agent.py", *EMBEDDED, "submission.csv", "requirements.txt")}
    texts = {name: decode_text(raw, name) for name, raw in raw_inputs.items()}
    secret_pattern = re.compile(r"AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----")
    if any(secret_pattern.search(text) for text in texts.values()):
        raise RuntimeError("secret-like content detected; nothing packaged")
    sources = {name: texts[name] for name in ("agent.py", *EMBEDDED)}
    submission = texts["submission.csv"]
    entrypoints = {"agent.py": "Agent", "candidate_model.py": "build_candidates", "llm_advisor.py": "Advisor"}
    for name, source in sources.items():
        tree = ast.parse(source, filename=name)
        compile(tree, name, "exec")
        if not any(isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == entrypoints[name] for node in tree.body):
            raise RuntimeError(f"{name} has no required entrypoint")
    reader = csv.DictReader(io.StringIO(submission))
    columns = ["campaign_name", "filter_arpu_segment", "filter_data_segment", "filter_call_segment",
               "filter_current_tariff", "target_tariff", "channel"]
    rows = list(reader)
    if reader.fieldnames != columns or not 1 <= len(rows) <= 10:
        raise RuntimeError("submission.csv must contain the official seven columns and 1..10 rows")
    if any(None in row or any(value is None for value in row.values()) or not row["target_tariff"]
           or row["channel"] not in {"push", "sms", "digital_ads", "call"} for row in rows):
        raise RuntimeError("submission.csv contains invalid rows")

    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    packaged = packaged_agent(sources["agent.py"], sources["candidate_model.py"], sources["llm_advisor.py"])
    atomic_text(SUBMISSION_DIR / "agent.py", packaged)
    atomic_bytes(SUBMISSION_DIR / "submission.csv", raw_inputs["submission.csv"])
    atomic_bytes(SUBMISSION_DIR / "requirements.txt", raw_inputs["requirements.txt"])
    code_hashes = {name: hashlib.sha256(value.encode("utf-8")).hexdigest() for name, value in sources.items()}
    code_hashes["packaged_agent.py"] = hashlib.sha256(packaged.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "package": "HackAlem Beeline tariff campaign submission",
        "source": git_metadata(),
        "code_sha256": code_hashes,
        "code_hash_encoding": "UTF-8 source text with normalized line endings",
        "artifact_sha256": {name: hashlib.sha256((SUBMISSION_DIR / name).read_bytes()).hexdigest()
                            for name in REQUIRED if name != "manifest.json"},
        "files": list(REQUIRED),
        "embedded_modules": list(EMBEDDED),
        "supports_offline": True,
        "runtime_data": "Organizer public CSV inputs must accompany execution; they are not included in this upload bundle.",
        "csv_freshness": "Run verify.ps1 -Release before packaging; this builder does not execute the evaluator.",
    }
    atomic_text(SUBMISSION_DIR / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    archive = ROOT / "output" / "submission.zip"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=str(archive.parent), prefix=".submission-", suffix=".zip", delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for name in REQUIRED:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                bundle.writestr(info, (SUBMISSION_DIR / name).read_bytes())
        os.replace(str(temporary), str(archive))
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
    return manifest, archive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        manifest, archive = build()
    except (OSError, RuntimeError, ValueError, TypeError, SyntaxError) as error:
        print(f"package failed: {error}")
        return 1
    print(f"package: {SUBMISSION_DIR}")
    print(f"archive: {archive}")
    print(f"source_git_sha: {manifest['source']['source_git_sha']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
