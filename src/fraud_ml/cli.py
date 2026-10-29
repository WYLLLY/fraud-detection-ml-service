"""Explicit experiment phases; no HTTP or payment execution."""

import argparse
import sys
from pathlib import Path

from fraud_ml.artifact_io import read_json
from fraud_ml.experiment import (
    ExperimentConfig,
    evaluate_experiment,
    generate_experiment,
    train_experiment,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synthetic-risk ML experiment, not real fraud detection"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--config", type=Path, default=Path("configs/experiment.json"))
    generate.add_argument("--data-dir", type=Path, required=True)
    train = commands.add_parser("train")
    train.add_argument("--data-dir", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--data-dir", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate_experiment(args.data_dir, ExperimentConfig(**read_json(args.config)))
        elif args.command == "train":
            train_experiment(args.data_dir, args.output)
        else:
            evaluate_experiment(args.data_dir, args.output, args.report_dir)
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"Experiment failed: {error}", file=sys.stderr)
        return 1
    return 0
