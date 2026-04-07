from __future__ import annotations

import argparse
import json

from minimal_agent_harness.prompt_pipeline import run_generator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the single-prompt generator stage")
    parser.add_argument("topic", help="Topic or product prompt")
    parser.add_argument("--run-id", default=None, help="Optional run identifier")
    parser.add_argument("--base-dir", default="artifacts/runs", help="Run root directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_paths = run_generator(args.topic, base_dir=args.base_dir, run_id=args.run_id)
    print(json.dumps({"run_id": run_paths.run_id, "run_dir": str(run_paths.root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
