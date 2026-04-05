from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minimal_agent_harness.benchmark import run_benchmark_with_config


@dataclass
class VariantConfig:
    name: str
    backend_name: str = "scripted"
    model: str | None = None
    fallback_models: list[str] = field(default_factory=list)


def load_variant_config(path: str | Path) -> VariantConfig:
    payload = json.loads(Path(path).read_text())
    return VariantConfig(
        name=payload["name"],
        backend_name=payload.get("backend_name", "scripted"),
        model=payload.get("model"),
        fallback_models=payload.get("fallback_models", []),
    )


def compare_summaries(baseline: dict[str, Any], variant: dict[str, Any]) -> str:
    baseline_key = (baseline["passed"], baseline["avg_score"])
    variant_key = (variant["passed"], variant["avg_score"])
    if variant_key > baseline_key:
        return "variant"
    if variant_key < baseline_key:
        return "baseline"
    return "tie"


def run_experiment_comparison(
    *,
    tasks_dir: str | Path,
    baseline_config_path: str | Path,
    variant_config_path: str | Path,
    output_path: str | Path,
    log_root: str | Path = "benchmark_runs/experiments",
) -> dict[str, Any]:
    baseline_config = load_variant_config(baseline_config_path)
    variant_config = load_variant_config(variant_config_path)
    log_root_path = Path(log_root)

    baseline_summary = run_benchmark_with_config(
        tasks_dir=tasks_dir,
        log_root=log_root_path / baseline_config.name,
        backend_name=baseline_config.backend_name,
        model=baseline_config.model,
        fallback_models=baseline_config.fallback_models,
    )
    variant_summary = run_benchmark_with_config(
        tasks_dir=tasks_dir,
        log_root=log_root_path / variant_config.name,
        backend_name=variant_config.backend_name,
        model=variant_config.model,
        fallback_models=variant_config.fallback_models,
    )

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tasks_dir": str(tasks_dir),
        "baseline": {
            "config": asdict(baseline_config),
            "summary": baseline_summary,
        },
        "variant": {
            "config": asdict(variant_config),
            "summary": variant_summary,
        },
        "winner": compare_summaries(baseline_summary, variant_summary),
    }

    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare baseline and variant configs against the same benchmark suite"
    )
    parser.add_argument("--tasks-dir", default="benchmarks/tasks", help="Benchmark task directory")
    parser.add_argument("--baseline-config", required=True, help="JSON config path for baseline")
    parser.add_argument("--variant-config", required=True, help="JSON config path for variant")
    parser.add_argument(
        "--output",
        default="benchmark_runs/experiments/latest-report.json",
        help="Path for the experiment comparison report",
    )
    parser.add_argument(
        "--log-root",
        default="benchmark_runs/experiments",
        help="Root directory for per-variant benchmark logs",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    report = run_experiment_comparison(
        tasks_dir=args.tasks_dir,
        baseline_config_path=args.baseline_config,
        variant_config_path=args.variant_config,
        output_path=args.output,
        log_root=args.log_root,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
