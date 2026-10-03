"""
Tests for Phase 4: Truth Isolation Runtime Verification.
Ensures that:
1. No production modules import, load, or reference truth files (e.g. truth.json).
2. No production code uses capture ID or filename pattern matching (e.g. 'G1', 'G2', etc.)
   to make decisions or short-circuit decoding/classification.
3. Renaming capture files does not alter pipeline classification or decoder output.
"""

import os
import re
import shutil
import tempfile
from pathlib import Path
import pytest
import numpy as np

import spectralq
import core


def test_no_truth_references_in_production():
    """Verify no production source code references truth.json or ground_truth loading."""
    root = Path(__file__).resolve().parent.parent
    prod_dirs = [
        root / "python" / "spectralq" / "pipeline",
        root / "python" / "spectralq" / "decoder",
        root / "python" / "spectralq" / "features",
        root / "python" / "spectralq" / "evidence",
        root / "python" / "spectralq" / "confidence",
        root / "python" / "spectralq" / "integration",
        root / "core",
    ]
    
    forbidden_patterns = [
        re.compile(r'truth\.json', re.IGNORECASE),
        re.compile(r'truth_mapping\.json', re.IGNORECASE),
        re.compile(r'golden_schemes\s*=', re.IGNORECASE),
    ]

    violations = []
    for p_dir in prod_dirs:
        if not p_dir.exists():
            continue
        for py_file in p_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                match = pattern.search(text)
                if match:
                    violations.append(f"{py_file}: matched forbidden pattern '{match.group(0)}'")

    assert not violations, f"Truth isolation violations found in production code:\n" + "\n".join(violations)


def test_no_golden_case_id_hardcoding_in_production():
    """Verify production modules do not branch on G1-G10 case IDs."""
    root = Path(__file__).resolve().parent.parent
    prod_dirs = [
        root / "python" / "spectralq" / "pipeline",
        root / "python" / "spectralq" / "decoder",
        root / "python" / "spectralq" / "features",
        root / "python" / "spectralq" / "evidence",
        root / "python" / "spectralq" / "confidence",
        root / "python" / "spectralq" / "integration",
        root / "core",
    ]
    
    case_patterns = [
        re.compile(r'["\']G[1-9]["\']\s*(?:in|==)', re.IGNORECASE),
        re.compile(r'(?:in|==)\s*["\']G[1-9]["\']', re.IGNORECASE),
        re.compile(r'["\']G10["\']\s*(?:in|==)', re.IGNORECASE),
        re.compile(r'(?:in|==)\s*["\']G10["\']', re.IGNORECASE),
    ]

    violations = []
    for p_dir in prod_dirs:
        if not p_dir.exists():
            continue
        for py_file in p_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in case_patterns:
                match = pattern.search(text)
                if match:
                    violations.append(f"{py_file}: hardcoded case ID branch '{match.group(0)}'")

    assert not violations, f"Hardcoded case ID branching found in production code:\n" + "\n".join(violations)


def test_filename_invariance_runtime():
    """Verify that renaming a capture produces identical results across the entire pipeline."""
    from spectralq.pipeline.runner import run
    
    golden_file = Path("data/official/sinchana/golden/G1_QPSK_uncoded.cf32")
    companion_json = golden_file.with_suffix(".json")
    if not golden_file.exists() or not companion_json.exists():
        pytest.skip("Golden capture or companion JSON not present")
        
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_iq = Path(tmp_dir) / "arbitrary_unseen_signal_99999.cf32"
        tmp_meta = Path(tmp_dir) / "arbitrary_unseen_signal_99999.json"
        shutil.copy2(golden_file, tmp_iq)
        shutil.copy2(companion_json, tmp_meta)
        
        orig_res = run(str(golden_file), mode="live")
        renamed_res = run(str(tmp_iq), mode="live")
        
        # Classification & rules must match exactly
        assert orig_res.result.top_hypothesis.modulation == renamed_res.result.top_hypothesis.modulation
        assert orig_res.result.rule_prediction == renamed_res.result.rule_prediction
        assert orig_res.result.ml_prediction == renamed_res.result.ml_prediction
        assert abs(orig_res.result.final_confidence - renamed_res.result.final_confidence) < 1e-4
        
        # Decoder outputs must match exactly
        assert orig_res.decoder.status == renamed_res.decoder.status
        assert orig_res.decoder.crc_status == renamed_res.decoder.crc_status
        assert orig_res.decoder.fec_used == renamed_res.decoder.fec_used
        assert orig_res.decoder.interleaver_used == renamed_res.decoder.interleaver_used
        assert orig_res.decoder.decoded_bits == renamed_res.decoder.decoded_bits
