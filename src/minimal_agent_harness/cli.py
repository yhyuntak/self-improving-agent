from __future__ import annotations

import argparse
import os

from minimal_agent_harness.engine import build_default_runner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the minimal agent harness")
    parser.add_argument("instruction", help="Task instruction for the agent")
    parser.add_argument(
        "--backend",
        default=os.getenv("MINIMAL_AGENT_BACKEND", "scripted"),
        choices=["scripted", "openrouter"],
        help="Backend used to choose the next action",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_MODEL"),
        help="Model name for the OpenRouter backend",
    )
    parser.add_argument(
        "--log-file",
        default="run_logs/latest.json",
        help="Path to the structured run log file",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    runner = build_default_runner(backend_name=args.backend, model=args.model)
    response = runner.run(instruction=args.instruction, log_file=args.log_file)
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
