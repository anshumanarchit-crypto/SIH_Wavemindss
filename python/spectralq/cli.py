"""
SpectralQ Command Line Interface (CLI).
Provides 'spectralq analyze <file>' printing per-stage execution status (LIVE/STUB/REPLAY).
"""

import argparse
import json
import sys
from pathlib import Path

from spectralq.pipeline.runner import run


from spectralq.replay import (
    ReplayCacheError,
    CacheNotFoundError,
    CacheCorruptedError,
    CacheMismatchError,
)


def cmd_analyze(args: argparse.Namespace) -> int:
    capture_path = args.file
    p = Path(capture_path)
    if not p.exists():
        print(f"Error: Capture file not found: {capture_path}", file=sys.stderr)
        return 1

    try:
        pipeline_res = run(capture_path=capture_path, seed=args.seed, mode=args.mode)
        res = pipeline_res.result
        stage_status = pipeline_res.stage_status
    except ReplayCacheError as e:
        print("=" * 60, file=sys.stderr)
        print("SPECTRALQ PIPELINE STAGE EXECUTION STATUS", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"  {'Ingest & Forensics':<28} : [ERROR]", file=sys.stderr)
        print(f"  {'Replay Cache Integrity':<28} : [ERROR: {type(e).__name__}]", file=sys.stderr)
        print("-" * 60, file=sys.stderr)
        print(f"Fatal Replay Error: {e}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        return 1
    except Exception as e:
        print("=" * 60, file=sys.stderr)
        print("SPECTRALQ PIPELINE STAGE EXECUTION STATUS", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"  {'Ingest & Forensics':<28} : [ERROR]", file=sys.stderr)
        print("-" * 60, file=sys.stderr)
        print(f"Fatal Pipeline Error: {e}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        return 1

    print("=" * 60)
    print("SPECTRALQ PIPELINE STAGE EXECUTION STATUS")
    print("=" * 60)
    for stage, status in stage_status.items():
        print(f"  {stage:<28} : [{status}]")
    print("-" * 60)
    print(f"Overall Source Mode        : {res.source_mode.value.upper()}")
    print(f"Evidence Ladder Level      : {res.ladder_level.value}")
    print(f"Top Modulation Hypothesis  : {res.top_hypothesis.modulation}")
    print(f"Final Decision Confidence  : {res.final_confidence:.4f}")
    print(f"Unknown Flag               : {res.unknown}")
    if res.unknown_reason:
        print(f"Unknown Reason             : {res.unknown_reason}")
    print(f"Live Octave Available      : {res.capability_available}")
    print(f"Input Hash                 : {res.provenance.input_hash[:16]}...")
    print("=" * 60)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(res.model_dump_json(indent=2))
        print(f"Result successfully saved to: {args.output}")

    if args.json:
        print("\nFull result.json:")
        print(res.model_dump_json(indent=2))

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="spectralq",
        description="SpectralQ Signal Intelligence Pipeline CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze command
    p_analyze = subparsers.add_parser("analyze", help="Analyze signal capture through SpectralQ pipeline")
    p_analyze.add_argument("file", help="Path to capture file (.cf32, .wav, or test json)")
    p_analyze.add_argument(
        "--mode", "-m",
        choices=["auto", "live", "replay", "stub"],
        default="auto",
        help="Pipeline execution mode: auto (default), live, replay, or stub"
    )
    p_analyze.add_argument("--output", "-o", help="Optional output path for result.json")
    p_analyze.add_argument("--seed", "-s", type=int, default=42, help="Deterministic RNG seed")
    p_analyze.add_argument("--json", action="store_true", help="Print full result.json to stdout")
    p_analyze.set_defaults(func=cmd_analyze)

    parsed = parser.parse_args()
    sys.exit(parsed.func(parsed))


if __name__ == "__main__":
    main()
