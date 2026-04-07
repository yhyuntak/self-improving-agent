from __future__ import annotations

import argparse
import json

from minimal_agent_harness.prompt_pipeline import run_critic


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the critic stage on an existing run directory")
    parser.add_argument("run_dir", help="Path to the run directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    review_path = run_critic(args.run_dir)
    print(json.dumps({"review_path": str(review_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
