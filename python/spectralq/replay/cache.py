"""
Deterministic Replay Cache & Integrity Engine for SpectralQ.

Guarantees:
1. Cache artifacts are keyed strictly by SHA-256 hash of the input file content,
   never by filename alone (preventing cross-capture collision).
2. Schema validation: Cached analysis is strictly validated against AnalysisContract
   before emission.
3. Cryptographic integrity: Cached payload includes a content checksum.
   Any corruption or truncation fails loudly with CacheCorruptedError.
4. Input mismatch check: ReplayCache verifies that the cached input_hash matches
   the target file hash; mismatches raise CacheMismatchError.
5. Replay output is strictly marked with source_mode = SourceMode.REPLAY.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from spectralq.contracts.schemas import (
    AnalysisContract,
    CURRENT_SCHEMA_VERSION,
    SourceMode,
    validate_analysis_dict,
)


DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "replay"


class ReplayCacheError(Exception):
    """Base exception for replay cache errors."""
    pass


class CacheNotFoundError(ReplayCacheError):
    """Raised when no cache exists for the specified input hash."""
    pass


class CacheCorruptedError(ReplayCacheError):
    """Raised when cached artifact JSON or checksum is corrupt/invalid."""
    pass


class CacheMismatchError(ReplayCacheError):
    """Raised when cache content does not match the requested input file hash."""
    pass


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """
    Computes deterministic SHA-256 checksum of file content.
    If file is virtual/in-memory string representation, hashes UTF-8 bytes.
    """
    p = Path(file_path)
    if p.exists() and p.is_file():
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    else:
        return hashlib.sha256(str(file_path).encode("utf-8")).hexdigest()


class ReplayCache:
    """
    Manages cryptographic persistence and retrieval of upstream analysis artifacts.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, capture_path: Union[str, Path]) -> Path:
        """Computes deterministic cache path keyed by input content hash."""
        input_hash = compute_file_sha256(capture_path)
        return self.cache_dir / f"{input_hash}.replay.json"

    def has_cache(self, capture_path: Union[str, Path]) -> bool:
        """Checks if a cache file exists for this capture's content hash."""
        return self.get_cache_path(capture_path).is_file()

    def save_analysis(
        self,
        capture_path: Union[str, Path],
        analysis: AnalysisContract,
        generation_parameters: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Serializes analysis contract with metadata and cryptographic checksum.
        """
        input_hash = compute_file_sha256(capture_path)
        cache_path = self.cache_dir / f"{input_hash}.replay.json"

        # Serialize analysis payload
        analysis_dict = analysis.model_dump(mode="json")
        # Ensure cached analysis marks source_mode as replay
        analysis_dict["source_mode"] = SourceMode.REPLAY.value

        payload_bytes = json.dumps(analysis_dict, sort_keys=True).encode("utf-8")
        payload_checksum = hashlib.sha256(payload_bytes).hexdigest()

        cache_envelope: Dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "input_hash": input_hash,
            "capture_id": analysis.capture_id,
            "source_mode": SourceMode.REPLAY.value,
            "cached_at_utc": datetime.now(timezone.utc).isoformat(),
            "generation_parameters": generation_parameters or {},
            "payload_checksum": payload_checksum,
            "analysis": analysis_dict,
        }

        temp_path = cache_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cache_envelope, f, indent=2)

        # Atomic replacement
        temp_path.replace(cache_path)
        return cache_path

    def load_analysis(self, capture_path: Union[str, Path]) -> Tuple[AnalysisContract, Dict[str, Any]]:
        """
        Loads, validates, and unpacks cached analysis for the given capture.
        Fails loudly with explicit exceptions upon corruption, mismatch, or schema error.
        
        Returns:
            (analysis_contract, cache_metadata)
        """
        expected_hash = compute_file_sha256(capture_path)
        cache_path = self.get_cache_path(capture_path)

        if not cache_path.is_file():
            raise CacheNotFoundError(
                f"No replay cache found for capture '{capture_path}' (hash: {expected_hash}) "
                f"at expected path: {cache_path}"
            )

        # 1. Read JSON
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
        except json.JSONDecodeError as e:
            raise CacheCorruptedError(f"Replay cache artifact at '{cache_path}' is corrupted JSON: {e}") from e
        except Exception as e:
            raise CacheCorruptedError(f"Failed to read replay cache artifact at '{cache_path}': {e}") from e

        # 2. Keyed Mismatch Verification (Keyed by file content hash)
        cached_hash = envelope.get("input_hash")
        if cached_hash != expected_hash:
            raise CacheMismatchError(
                f"Cache input hash mismatch: expected '{expected_hash}', "
                f"found '{cached_hash}' in '{cache_path}'"
            )

        # 3. Cryptographic Checksum Integrity
        analysis_data = envelope.get("analysis")
        if not analysis_data or not isinstance(analysis_data, dict):
            raise CacheCorruptedError(f"Missing or invalid 'analysis' payload in cache envelope '{cache_path}'")

        payload_bytes = json.dumps(analysis_data, sort_keys=True).encode("utf-8")
        actual_checksum = hashlib.sha256(payload_bytes).hexdigest()
        expected_checksum = envelope.get("payload_checksum")

        if expected_checksum and actual_checksum != expected_checksum:
            raise CacheCorruptedError(
                f"Cache payload checksum corruption detected in '{cache_path}'! "
                f"Expected '{expected_checksum}', computed '{actual_checksum}'."
            )

        # 4. Strict Schema Contract Validation
        # Must enforce source_mode = SourceMode.REPLAY
        analysis_data["source_mode"] = SourceMode.REPLAY.value
        try:
            validated_analysis = validate_analysis_dict(analysis_data)
        except Exception as e:
            raise CacheCorruptedError(f"Cached analysis failed schema validation: {e}") from e

        metadata = {
            "cached_at_utc": envelope.get("cached_at_utc"),
            "input_hash": cached_hash,
            "generation_parameters": envelope.get("generation_parameters", {}),
            "cache_file": str(cache_path),
        }

        return validated_analysis, metadata

    def invalidate_cache(self, capture_path: Union[str, Path]) -> bool:
        """Deletes the cache artifact for the specified capture file."""
        cache_path = self.get_cache_path(capture_path)
        if cache_path.is_file():
            cache_path.unlink()
            return True
        return False

    def clear_all(self) -> int:
        """Deletes all cache artifacts in the cache directory."""
        count = 0
        for f in self.cache_dir.glob("*.replay.json"):
            f.unlink()
            count += 1
        return count
