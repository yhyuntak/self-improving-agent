from __future__ import annotations

import argparse
import json

from minimal_agent_harness.prompt_pipeline import run_evaluator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the evaluator stage on an existing run directory")
    parser.add_argument("run_dir", help="Path to the run directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    diagnosis_path = run_evaluator(args.run_dir)
    print(json.dumps({"diagnosis_path": str(diagnosis_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
