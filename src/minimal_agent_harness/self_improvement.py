from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from minimal_agent_harness.experiments import (
    VariantConfig,
    load_variant_config,
    run_experiment_comparison,
)


ComparisonRunner = Callable[..., dict]


def _write_variant_config(path: str | Path, config: VariantConfig) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "name": config.name,
                "backend_name": config.backend_name,
                "model": config.model,
                "fallback_models": config.fallback_models,
            },
            indent=2,
        )
    )


def run_self_improvement_loop(
    *,
    tasks_dir: str | Path,
    current_best_config_path: str | Path,
    candidate_config_paths: Sequence[str | Path],
    promoted_config_path: str | Path,
    summary_output_path: str | Path,
    log_root: str | Path = "benchmark_runs/self_improvement",
    comparison_runner: ComparisonRunner = run_experiment_comparison,
) -> dict:
    current_best_path = Path(current_best_config_path)
    current_best = load_variant_config(current_best_path)
    decisions: list[dict] = []
    log_root_path = Path(log_root)

    for round_index, candidate_path_raw in enumerate(candidate_config_paths, start=1):
        candidate_path = Path(candidate_path_raw)
        candidate = load_variant_config(candidate_path)
        comparison_output_path = (
            log_root_path / "reports" / f"round-{round_index:02d}-{current_best.name}-vs-{candidate.name}.json"
        )
        try:
            report = comparison_runner(
                tasks_dir=tasks_dir,
                baseline_config_path=current_best_path,
                variant_config_path=candidate_path,
                output_path=comparison_output_path,
                log_root=log_root_path / f"round-{round_index:02d}",
            )
            winner = report["winner"]
            promoted = winner == "variant"
            status = "ok"
            error = None
        except Exception as exc:
            winner = "baseline"
            promoted = False
            status = "crash"
            error = str(exc)
            report = {
                "tasks_dir": str(tasks_dir),
                "baseline_config_path": str(current_best_path),
                "variant_config_path": str(candidate_path),
                "winner": winner,
                "status": status,
                "error": error,
            }
            comparison_output_path.parent.mkdir(parents=True, exist_ok=True)
            comparison_output_path.write_text(json.dumps(report, indent=2))

        decisions.append(
            {
                "round": round_index,
                "baseline": current_best.name,
                "candidate": candidate.name,
                "winner": winner,
                "promoted": promoted,
                "status": status,
                "error": error,
                "report_path": str(comparison_output_path),
            }
        )

        if promoted:
            current_best_path = candidate_path
            current_best = candidate

    _write_variant_config(promoted_config_path, current_best)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tasks_dir": str(tasks_dir),
        "starting_config": str(current_best_config_path),
        "candidate_count": len(candidate_config_paths),
        "decisions": decisions,
        "final_best": {
            "source_path": str(current_best_path),
            "config": {
                "name": current_best.name,
                "backend_name": current_best.backend_name,
                "model": current_best.model,
                "fallback_models": current_best.fallback_models,
            },
        },
        "promoted_config_path": str(promoted_config_path),
    }

    summary_path = Path(summary_output_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a constrained config-only self-improvement loop"
    )
    parser.add_argument("--tasks-dir", default="benchmarks/tasks", help="Benchmark task directory")
    parser.add_argument(
        "--current-best-config",
        required=True,
        help="Path to the current best config JSON",
    )
    parser.add_argument(
        "--candidate-config",
        action="append",
        dest="candidate_configs",
        required=True,
        help="Path to a candidate config JSON. Repeat for multiple candidates.",
    )
    parser.add_argument(
        "--promoted-config-output",
        default="experiments/current-best.json",
        help="Path where the promoted best config should be written",
    )
    parser.add_argument(
        "--summary-output",
        default="benchmark_runs/self_improvement/latest-summary.json",
        help="Path for the self-improvement summary JSON",
    )
    parser.add_argument(
        "--log-root",
        default="benchmark_runs/self_improvement",
        help="Root directory for comparison logs",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    summary = run_self_improvement_loop(
        tasks_dir=args.tasks_dir,
        current_best_config_path=args.current_best_config,
        candidate_config_paths=args.candidate_configs,
        promoted_config_path=args.promoted_config_output,
        summary_output_path=args.summary_output,
        log_root=args.log_root,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
