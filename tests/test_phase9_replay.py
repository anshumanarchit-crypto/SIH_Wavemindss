"""
Phase 9 Tests: Replay Mode, Deterministic Cache Integrity & Loud Corruption Failure.

Covers:
1. Cache write/read round-trip with schema validation.
2. Cache invalidation (removal and subsequent CacheNotFoundError).
3. Wrong-capture cache mismatch caught via content hashing (CacheMismatchError).
4. Corrupted cache fails loudly with CacheCorruptedError (never silently stale).
5. Missing-Octave triggers correct fallback path (auto-detects and surfaces state).
6. Replay result is schema-equivalent to live/stub result modulo the source_mode field.
"""

import json
from pathlib import Path
import pytest

from spectralq.contracts.schemas import (
    AnalysisContract,
    ResultContract,
    SourceMode,
    validate_analysis_dict,
)
from spectralq.replay import (
    ReplayCache,
    ReplayCacheError,
    CacheNotFoundError,
    CacheCorruptedError,
    CacheMismatchError,
    compute_file_sha256,
)
from spectralq.pipeline.runner import run


@pytest.fixture
def sample_analysis_dict():
    return {
        "schema_version": "1.0.0",
        "capture_id": "REPLAY_TEST_CAPTURE_01",
        "source_mode": "synthetic",
        "fs_hz": 20.0e6,
        "fs_source": "header",
        "bursts": [
            {"start_ms": 10.0, "end_ms": 90.0, "power": -14.0}
        ],
        "estimates": {
            "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic"},
            "cfo": {"value": 50.0, "ci_lo": 40.0, "ci_hi": 60.0, "method": "fft"},
            "bandwidth": {"value": 1.25e6, "ci_lo": 1.20e6, "ci_hi": 1.30e6, "method": "obw"},
            "snr": {"value": 20.0, "ci_lo": 19.5, "ci_hi": 20.5, "method": "m2m4"},
        },
        "features": {
            "cumulants": {
                "C20": 0.01, "C21": 1.0, "C40": 0.98, "C42": -0.99,
                "C60": 0.0, "C63": 0.0, "C80": 0.0,
            },
            "cluster": {
                "count": 4, "silhouette": 0.88, "intra_var": 0.08, "inter_dist": 1.41,
            },
            "evm": 0.045,
            "phase_ambiguity_quality": 0.92,
            "cyclic": None,
        },
    }


# -----------------------------------------------------------------------------
# 1. Cache Write / Read Round-Trip
# -----------------------------------------------------------------------------
def test_replay_cache_write_read_roundtrip(tmp_path, sample_analysis_dict):
    cache = ReplayCache(cache_dir=tmp_path / "cache")
    capture_file = tmp_path / "signal_A.cf32"
    capture_file.write_bytes(b"\x00\x01\x02\x03" * 256)

    analysis = validate_analysis_dict(sample_analysis_dict)
    saved_path = cache.save_analysis(capture_file, analysis, generation_parameters={"snr_db": 20.0})

    assert saved_path.exists()
    assert cache.has_cache(capture_file) is True

    # Read back
    loaded_analysis, metadata = cache.load_analysis(capture_file)
    assert isinstance(loaded_analysis, AnalysisContract)
    assert loaded_analysis.capture_id == "REPLAY_TEST_CAPTURE_01"
    # Invariant: source_mode must be strictly REPLAY
    assert loaded_analysis.source_mode == SourceMode.REPLAY
    assert metadata["input_hash"] == compute_file_sha256(capture_file)
    assert metadata["generation_parameters"]["snr_db"] == 20.0


# -----------------------------------------------------------------------------
# 2. Cache Invalidation
# -----------------------------------------------------------------------------
def test_replay_cache_invalidation(tmp_path, sample_analysis_dict):
    cache = ReplayCache(cache_dir=tmp_path / "cache")
    capture_file = tmp_path / "signal_inval.cf32"
    capture_file.write_bytes(b"\xAA\xBB\xCC\xDD" * 128)

    analysis = validate_analysis_dict(sample_analysis_dict)
    cache.save_analysis(capture_file, analysis)
    assert cache.has_cache(capture_file) is True

    # Invalidate
    deleted = cache.invalidate_cache(capture_file)
    assert deleted is True
    assert cache.has_cache(capture_file) is False

    with pytest.raises(CacheNotFoundError, match="No replay cache found"):
        cache.load_analysis(capture_file)


# -----------------------------------------------------------------------------
# 3. Wrong-Capture Cache Mismatch Caught
# -----------------------------------------------------------------------------
def test_wrong_capture_cache_mismatch_caught(tmp_path, sample_analysis_dict):
    """
    Keyed by file content hash: If a different capture tries to point to a cache file
    whose inner hash doesn't match the capture bytes, it must raise CacheMismatchError.
    """
    cache = ReplayCache(cache_dir=tmp_path / "cache")
    file_original = tmp_path / "file_original.cf32"
    file_original.write_bytes(b"ORIGINAL_BYTES_12345")

    analysis = validate_analysis_dict(sample_analysis_dict)
    cache_path = cache.save_analysis(file_original, analysis)

    # Different capture with different bytes
    file_different = tmp_path / "file_different.cf32"
    file_different.write_bytes(b"DIFFERENT_BYTES_67890")

    # Trying to load file_different directly raises CacheNotFoundError because hash differs
    with pytest.raises(CacheNotFoundError):
        cache.load_analysis(file_different)

    # If an attacker renames the cache file to match file_different's hash:
    diff_hash = compute_file_sha256(file_different)
    spoofed_cache_path = tmp_path / "cache" / f"{diff_hash}.replay.json"
    spoofed_cache_path.write_text(cache_path.read_text(encoding="utf-8"), encoding="utf-8")

    # Mismatch between filename hash and inner envelope input_hash must fail loudly
    with pytest.raises(CacheMismatchError, match="Cache input hash mismatch"):
        cache.load_analysis(file_different)


# -----------------------------------------------------------------------------
# 4. Corrupted Cache Fails Loudly (Never Stale or Garbage)
# -----------------------------------------------------------------------------
def test_corrupted_cache_fails_loudly_truncated_json(tmp_path, sample_analysis_dict):
    cache = ReplayCache(cache_dir=tmp_path / "cache")
    capture_file = tmp_path / "corrupt_test.cf32"
    capture_file.write_bytes(b"CORRUPT_TEST_BYTES")

    analysis = validate_analysis_dict(sample_analysis_dict)
    cache_path = cache.save_analysis(capture_file, analysis)

    # Corrupt the JSON file by truncating it
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write('{"schema_version": "1.0.0", "input_hash": "truncated...')

    with pytest.raises(CacheCorruptedError, match="corrupted JSON"):
        cache.load_analysis(capture_file)


def test_corrupted_cache_fails_loudly_checksum_tampering(tmp_path, sample_analysis_dict):
    cache = ReplayCache(cache_dir=tmp_path / "cache")
    capture_file = tmp_path / "tamper_test.cf32"
    capture_file.write_bytes(b"TAMPER_TEST_BYTES")

    analysis = validate_analysis_dict(sample_analysis_dict)
    cache_path = cache.save_analysis(capture_file, analysis)

    # Tamper with the analysis payload without updating the payload_checksum
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["analysis"]["estimates"]["snr"]["value"] = 999.0  # Tampered SNR
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(CacheCorruptedError, match="checksum corruption detected"):
        cache.load_analysis(capture_file)


# -----------------------------------------------------------------------------
# 5. Missing-Octave Auto-Fallback Surfaces State
# -----------------------------------------------------------------------------
def test_missing_octave_fallback_path(tmp_path, sample_analysis_dict):
    cache = ReplayCache(cache_dir=tmp_path / "cache")
    capture_file = tmp_path / "fallback_signal.cf32"
    capture_file.write_bytes(b"FALLBACK_PAYLOAD_DATA" * 64)

    # Pre-populate cache so replay fallback is available
    analysis = validate_analysis_dict(sample_analysis_dict)
    cache.save_analysis(capture_file, analysis)

    # Run in auto mode: Octave is missing, so auto-falls back to REPLAY
    pipeline_res = run(str(capture_file), mode="auto", replay_cache=cache)

    assert pipeline_res.stage_status["Ingest & Forensics"] == "REPLAY"
    assert pipeline_res.stage_status["Feature Extraction"] == "REPLAY"
    assert pipeline_res.stage_status["Auto Fallback"] == "LIVE_UNAVAILABLE_FALLBACK_TO_REPLAY"
    assert pipeline_res.result.source_mode == SourceMode.REPLAY


# -----------------------------------------------------------------------------
# 6. Replay Result is Schema-Equivalent to Live/Stub Result Modulo source_mode
# -----------------------------------------------------------------------------
def test_replay_result_schema_equivalent(tmp_path, sample_analysis_dict):
    cache = ReplayCache(cache_dir=tmp_path / "cache")
    capture_file = tmp_path / "schema_equiv.cf32"
    capture_file.write_bytes(b"SCHEMA_EQUIV_BYTES" * 32)

    # Save cache
    analysis = validate_analysis_dict(sample_analysis_dict)
    cache.save_analysis(capture_file, analysis)

    # Run in stub mode
    stub_res = run(str(capture_file), mode="stub", replay_cache=cache).result
    # Run in replay mode
    replay_res = run(str(capture_file), mode="replay", replay_cache=cache).result

    # Both must be valid ResultContract instances
    assert isinstance(stub_res, ResultContract)
    assert isinstance(replay_res, ResultContract)

    # Source modes differ as required
    assert stub_res.source_mode == SourceMode.STUB
    assert replay_res.source_mode == SourceMode.REPLAY

    # Schema version and fields match identically
    assert stub_res.schema_version == replay_res.schema_version == "1.0.0"
    assert stub_res.top_hypothesis.modulation == replay_res.top_hypothesis.modulation
    assert stub_res.provenance.input_hash == replay_res.provenance.input_hash
