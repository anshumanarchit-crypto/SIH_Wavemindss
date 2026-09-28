"""
Capture Sample Extractor & Normalizer for SpectralQ Visualization.
Strictly reads genuine RF capture files (.cf32, .iq, .wav, .npy).
Never fabricates or substitutes missing capture data.
"""

import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """Computes SHA-256 hash of a capture file."""
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_capture_samples(
    capture_path: Union[str, Path],
    max_samples: Optional[int] = None,
    offset: int = 0,
    dtype_override: Optional[str] = None,
) -> Tuple[Optional[np.ndarray], Dict[str, Union[str, int, float, bool]]]:
    """
    Loads raw RF samples from disk.
    Supports complex64 (.cf32), raw int16/complex (.iq), WAV audio/SDR (.wav), and NumPy (.npy).
    Returns (samples, metadata_dict). If file does not exist or cannot be read, returns (None, metadata).
    """
    p = Path(capture_path)
    meta: Dict[str, Union[str, int, float, bool]] = {
        "file_exists": False,
        "format": "UNKNOWN",
        "sample_count": 0,
        "sha256": "",
        "size_bytes": 0,
    }

    if not p.exists() or not p.is_file():
        return None, meta

    meta["file_exists"] = True
    meta["size_bytes"] = p.stat().st_size
    meta["sha256"] = compute_file_sha256(p)
    ext = p.suffix.lower()

    try:
        if ext == ".cf32":
            meta["format"] = "complex64_cf32"
            raw = np.fromfile(p, dtype=np.complex64, count=max_samples if max_samples else -1, offset=offset * 8)
            samples = raw.astype(np.complex64)
        elif ext == ".npy":
            meta["format"] = "numpy_binary"
            arr = np.load(p)
            if np.iscomplexobj(arr):
                samples = arr.astype(np.complex64)
            elif arr.ndim == 2 and arr.shape[1] == 2:
                samples = (arr[:, 0] + 1j * arr[:, 1]).astype(np.complex64)
            else:
                samples = arr.astype(np.float32).astype(np.complex64)
            if max_samples and len(samples) > max_samples:
                samples = samples[:max_samples]
        elif ext == ".wav":
            from scipy.io import wavfile
            meta["format"] = "wav_audio_sdr"
            fs, data = wavfile.read(p)
            if data.ndim == 2 and data.shape[1] >= 2:
                # Stereo WAV treated as I/Q
                norm = data.astype(np.float32) / (np.max(np.abs(data)) or 1.0)
                samples = (norm[:, 0] + 1j * norm[:, 1]).astype(np.complex64)
            else:
                # Mono treated as real baseband
                norm = data.astype(np.float32) / (np.max(np.abs(data)) or 1.0)
                samples = norm.astype(np.complex64)
            if max_samples and len(samples) > max_samples:
                samples = samples[:max_samples]
        elif ext == ".iq" or dtype_override == "int16":
            meta["format"] = "int16_iq_interleaved"
            raw = np.fromfile(p, dtype=np.int16, count=(max_samples * 2) if max_samples else -1, offset=offset * 4)
            if len(raw) % 2 != 0:
                raw = raw[:-1]
            i_ch = raw[0::2].astype(np.float32) / 32768.0
            q_ch = raw[1::2].astype(np.float32) / 32768.0
            samples = (i_ch + 1j * q_ch).astype(np.complex64)
        else:
            # Fallback: attempt to read as complex64
            meta["format"] = "raw_binary_complex64"
            samples = np.fromfile(p, dtype=np.complex64, count=max_samples if max_samples else -1, offset=offset * 8)

        meta["sample_count"] = int(len(samples))
        return samples, meta
    except Exception as exc:
        meta["load_error"] = str(exc)
        return None, meta
