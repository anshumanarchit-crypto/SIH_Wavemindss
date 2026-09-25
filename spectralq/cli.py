"""
SpectralQ Command Line Interface (CLI).
Provides commands for running pipeline evaluation, deterministic replay,
and generating calibration reports.
"""

import argparse
import json
import sys
from pathlib import Path

from spectralq.contracts.schemas import AnalysisContract
from spectralq.pipeline.orchestrator import SpectralQOrchestrator
from spectralq.pipeline.replay import ReplayController


def cmd_run(args: argparse.Namespace) -> int:
    """
    Executes SpectralQ orchestrator on an analysis.json file.
    """
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    analysis = AnalysisContract.model_validate(data)
    orchestrator = SpectralQOrchestrator(
        classifier_model_path=args.model,
        confidence_threshold=args.threshold,
        seed=args.seed,
    )

    result = orchestrator.process(analysis=analysis)

    output_json = result.model_dump_json(indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Result successfully saved to: {args.output}")
    else:
        print(output_json)

    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """
    Executes deterministic replay on historical capture.
    """
    replay = ReplayController(seed=args.seed)
    analysis = replay.load_replay_analysis(args.input)

    orchestrator = SpectralQOrchestrator(
        classifier_model_path=args.model,
        confidence_threshold=args.threshold,
        seed=args.seed,
    )

    result = orchestrator.process(analysis=analysis)
    output_json = result.model_dump_json(indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Replay result saved to: {args.output}")
    else:
        print(output_json)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="spectralq",
        description="SpectralQ Evidence-First Decision and Integration Layer CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    p_run = subparsers.add_parser("run", help="Run SpectralQ decision pipeline on analysis.json")
    p_run.add_argument("--input", "-i", required=True, help="Path to input analysis.json file")
    p_run.add_argument("--output", "-o", help="Path to output result.json file")
    p_run.add_argument("--model", "-m", help="Path to trained classifier model (.joblib)")
    p_run.add_argument("--threshold", "-t", type=float, default=0.60, help="Confidence threshold for UNKNOWN")
    p_run.add_argument("--seed", "-s", type=int, default=42, help="RNG Seed")
    p_run.set_defaults(func=cmd_run)

    # replay command
    p_rep = subparsers.add_parser("replay", help="Replay a historical capture file with fixed seed")
    p_rep.add_argument("--input", "-i", required=True, help="Path to replay analysis.json file")
    p_rep.add_argument("--output", "-o", help="Path to output result.json file")
    p_rep.add_argument("--model", "-m", help="Path to trained classifier model")
    p_rep.add_argument("--threshold", "-t", type=float, default=0.60, help="Confidence threshold")
    p_rep.add_argument("--seed", "-s", type=int, default=42, help="RNG Seed")
    p_rep.set_defaults(func=cmd_replay)

    parsed_args = parser.parse_args()
    sys.exit(parsed_args.func(parsed_args))


if __name__ == "__main__":
    main()
