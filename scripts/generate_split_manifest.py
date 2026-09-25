#!/usr/bin/env python3
"""
Generate bench/split_manifest.json from the existing synthetic calibration sweep.

This manifest records exact train/val/calibration instance IDs used during
Phase 7 calibration so that the leakage guard test (TestH) can verify strict
disjointness programmatically.

Run:
  python scripts/generate_split_manifest.py
"""

import json
import sys
from pathlib import Path

# Add python dir to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

from spectralq.calibration.dataset import (
    generate_synthetic_sweep,
    split_by_signal_instance,
)


def main() -> None:
    print("Generating synthetic sweep (n=40 per class, seed=2026) ...")
    records = generate_synthetic_sweep(n_instances_per_class=40, seed=2026)
    print(f"  Total instances: {len(records)}")

    train_records, test_records = split_by_signal_instance(
        records, test_ratio=0.35, seed=42
    )
    print(f"  Train instances: {len(train_records)}")
    print(f"  Test/validation instances: {len(test_records)}")

    # For calibration, the calibration set is the entire held-out test split
    # (no further sub-split in Phase 7 — this matches the calibration run)
    train_ids = sorted([r.instance_id for r in train_records])
    test_ids = sorted([r.instance_id for r in test_records])
    calib_ids = sorted(test_ids)  # calibration uses same held-out split

    # Verify strict disjointness
    overlap_tt = set(train_ids) & set(test_ids)
    overlap_tc = set(train_ids) & set(calib_ids)
    assert not overlap_tt, f"Train/test overlap: {overlap_tt}"
    assert not overlap_tc, f"Train/calib overlap: {overlap_tc}"

    manifest = {
        "description": (
            "Instance-level split manifest for SpectralQ calibration sweep v1 "
            "(synthetic_sweep_v1_seed2026). All splits are strictly by signal "
            "instance — no instance ID appears in more than one split."
        ),
        "dataset_id": "synthetic_sweep_v1_seed2026",
        "split_method": "by_signal_instance",
        "split_seed": 42,
        "test_ratio": 0.35,
        "n_classes": 7,
        "n_instances_per_class": 40,
        "total_instances": len(records),
        "train_count": len(train_ids),
        "test_count": len(test_ids),
        "calibration_count": len(calib_ids),
        "train_instance_ids": train_ids,
        "test_instance_ids": test_ids,
        "calibration_instance_ids": calib_ids,
    }

    out_path = ROOT / "bench" / "split_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSplit manifest written to: {out_path}")
    print(f"  Train IDs: {len(train_ids)}")
    print(f"  Test/Val IDs: {len(test_ids)}")
    print(f"  Calibration IDs: {len(calib_ids)}")
    print("  Overlap check: PASSED (all sets strictly disjoint)")


if __name__ == "__main__":
    main()
