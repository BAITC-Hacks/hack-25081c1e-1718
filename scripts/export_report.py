"""Export a real public evaluator run for the optional web presentation."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    os.chdir(ROOT)
    from agent import Agent
    from local_eval import evaluate_agent

    agent = Agent()
    result = evaluate_agent(agent, seed=args.seed, verbose=False)
    report = dict(agent.last_report)
    report.update({
        'seed': args.seed,
        'synthetic': True,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'evaluation': {'net_arpu_gain': float(result['net_arpu_gain'])} if result else None,
    })
    destination = ROOT / 'output' / 'report.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    main()
