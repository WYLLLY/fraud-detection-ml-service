"""Explicit experiment phases and an HTTP-only read-only payment demonstration."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID


def _demo(args: argparse.Namespace) -> int:
    from fraud_ml.payment_demo import NOTICE, DemoError, score_payment

    try:
        result = asyncio.run(
            score_payment(
                args.payment_id,
                args.payment_api_url,
                args.fraud_api_url,
                os.environ.get("PAYMENT_API_TOKEN", ""),
            )
        )
    except DemoError as error:
        print(f"Score unavailable: {error.code}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "payment_id": str(result.payment_id),
                **result.prediction.model_dump(),
                "notice": NOTICE,
            },
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


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
    demo = commands.add_parser("demo", help="Advisory read-only local Payment HTTP demonstration")
    demo.add_argument("--payment-id", type=UUID, required=True)
    demo.add_argument("--payment-api-url", default="http://127.0.0.1:8000")
    demo.add_argument("--fraud-api-url", default="http://127.0.0.1:8002")
    args = parser.parse_args()
    if args.command == "demo":
        return _demo(args)

    # Model/data modules are needed only for explicit offline experiment phases.
    from fraud_ml.artifact_io import read_json
    from fraud_ml.experiment import (
        ExperimentConfig,
        evaluate_experiment,
        generate_experiment,
        train_experiment,
    )

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
