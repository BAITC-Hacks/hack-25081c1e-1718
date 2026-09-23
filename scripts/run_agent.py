"""Launch an official workflow with an optional memory-only API key prompt."""

import argparse
import getpass
import os
from pathlib import Path
import runpy
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Tariflow local runner")
    parser.add_argument("--mode", choices=("report", "evaluate", "submission"), default="report")
    parser.add_argument("--seed", type=int, default=42, help="Used by report mode")
    parser.add_argument("--run-id", help="Server-owned report identity; used only by report mode")
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--ask-key", action="store_true", help="Prompt without echo; key exists only during this process")
    options.add_argument("--offline", action="store_true", help="Disable all model calls")
    args = parser.parse_args()
    if args.run_id and args.mode != "report":
        parser.error("--run-id is only supported in report mode")
    previous_key = os.environ.get("OPENAI_API_KEY")
    previous_offline = os.environ.get("ARPU_OFFLINE")
    try:
        if args.ask_key:
            # Never put a secret on a command line, in a URL, or into a repo file.
            if not sys.stdin.isatty():
                parser.error("--ask-key requires an interactive terminal")
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    secret = getpass.getpass("OpenAI API key (hidden, memory only): ").strip()
            except getpass.GetPassWarning:
                parser.error("This terminal cannot hide input; use an interactive local terminal")
            if not secret:
                parser.error("Empty key; use --offline to continue without OpenAI")
            os.environ["OPENAI_API_KEY"] = secret
            secret = None
            os.environ.pop("ARPU_OFFLINE", None)
        elif args.offline:
            os.environ["ARPU_OFFLINE"] = "1"
        os.chdir(ROOT)
        sys.path.insert(0, str(ROOT))
        scripts = {"report": "scripts/export_report.py", "evaluate": "local_eval.py", "submission": "make_submission.py"}
        target = ROOT / scripts[args.mode]
        sys.argv = [str(target)] + (["--seed", str(args.seed)] if args.mode == "report" else [])
        if args.run_id:
            sys.argv.extend(["--run-id", args.run_id])
        runpy.run_path(str(target), run_name="__main__")
    finally:
        for name, previous in (("OPENAI_API_KEY", previous_key), ("ARPU_OFFLINE", previous_offline)):
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous


if __name__ == "__main__":
    main()
