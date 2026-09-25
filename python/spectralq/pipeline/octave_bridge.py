"""
Octave Bridge & Deterministic Stub Adapter.

Supports:
1. Detecting octave-cli presence non-interactively.
2. Detecting available Octave function signatures dynamically in script_dir.
3. Timeout handling, stdout/stderr capture, non-zero return code handling.
4. JSON parsing with clear parse-failure diagnostics.
5. Deterministic fallback stub adapter returning schema-valid analysis.json
   marked source_mode="stub" and capability_available=false.
"""

import os
import re
import json
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from spectralq.contracts.schemas import (
    AnalysisContract,
    BurstRecord,
    EstimatesBlock,
    ParameterEstimate,
    FeaturesBlock,
    CumulantsBlock,
    ClusterBlock,
    SourceMode,
    FsSource,
    validate_analysis_dict,
)


class OctaveBridgeError(Exception):
    """Base exception for Octave bridge errors."""
    pass


class OctaveNotFoundError(OctaveBridgeError):
    """Raised when octave-cli binary is missing."""
    pass


class OctaveTimeoutError(OctaveBridgeError):
    """Raised when Octave process execution exceeds timeout threshold."""
    pass


class OctaveExecutionError(OctaveBridgeError):
    """Raised when Octave process exits with a non-zero return code."""
    pass


class OctaveParseError(OctaveBridgeError):
    """Raised when Octave output cannot be parsed as valid JSON."""
    pass


class OctaveBridge:
    """
    Manages non-interactive execution of GNU Octave DSP scripts with dynamic
    function signature discovery and deterministic fallback.
    """

    def __init__(
        self,
        script_dir: Optional[str] = "octave",
        timeout_sec: float = 30.0,
        octave_executable: Optional[str] = None,
    ):
        self.script_dir = Path(script_dir) if script_dir else Path("octave")
        self.timeout_sec = float(timeout_sec)
        self.octave_bin = octave_executable or shutil.which("octave-cli") or shutil.which("octave")
        self.is_octave_installed = bool(self.octave_bin)

    def detect_available_function(self) -> Optional[Tuple[str, Path]]:
        """
        Inspects script_dir for .m files and extracts the top function name.
        Does NOT hardcode 'analyse_capture' — dynamically parses function signature.
        Returns:
            (function_name, script_path) or None if no scripts found.
        """
        if not self.script_dir.exists():
            return None

        m_files = sorted(self.script_dir.glob("*.m"))
        for m_file in m_files:
            try:
                content = m_file.read_text(encoding="utf-8", errors="ignore")
                # Match octave function signature: function [out] = func_name(args)
                match = re.search(
                    r"^\s*function\s+(?:\[?[^\]=]+\]?\s*=\s*)?([a-zA-Z0-9_]+)\s*\(([^)]*)\)",
                    content,
                    re.MULTILINE,
                )
                if match:
                    func_name = match.group(1)
                    return func_name, m_file
            except Exception:
                continue

        return None

    def is_live_capable(self) -> bool:
        """
        Checks if both octave-cli binary AND an Octave script exist.
        """
        return self.is_octave_installed and (self.detect_available_function() is not None)

    def run_live(self, capture_path: str) -> Dict[str, Any]:
        """
        Executes real Octave function via octave-cli.
        Raises specific exceptions on missing binary, timeout, failure, or parse error.
        """
        if not self.octave_bin:
            raise OctaveNotFoundError("GNU Octave binary ('octave-cli' or 'octave') was not found on PATH.")

        func_info = self.detect_available_function()
        if not func_info:
            raise OctaveBridgeError(f"No valid Octave function (.m) found in '{self.script_dir}'.")

        func_name, script_path = func_info
        cap_path_abs = Path(capture_path).resolve().as_posix()
        script_dir_abs = self.script_dir.resolve().as_posix()

        # Build non-interactive Octave command
        eval_cmd = (
            f"addpath('{script_dir_abs}'); "
            f"out = {func_name}('{cap_path_abs}'); "
            f"if isstruct(out) || iscell(out), disp(jsonencode(out)); else disp(out); end; exit;"
        )

        cmd = [self.octave_bin, "--no-gui", "--silent", "--eval", eval_cmd]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise OctaveTimeoutError(
                f"Octave execution timed out after {self.timeout_sec}s for '{capture_path}'"
            ) from exc

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Exit code {proc.returncode}"
            raise OctaveExecutionError(
                f"Octave process exited with non-zero code {proc.returncode}: {err_msg}"
            )

        # Parse JSON output from stdout
        raw_output = proc.stdout.strip()
        try:
            data = json.loads(raw_output)
            if not isinstance(data, dict):
                raise ValueError("Parsed JSON is not an object/dictionary")
            return data
        except Exception as exc:
            raise OctaveParseError(
                f"Failed to parse Octave JSON output. Raw stdout: '{raw_output}'"
            ) from exc

    def run(self, capture_path: str) -> AnalysisContract:
        """
        Orchestrates ingest: runs live if capable, else falls back to deterministic stub.
        Never marks stub output as live.
        """
        if self.is_live_capable():
            raw_dict = self.run_live(capture_path)
            raw_dict["source_mode"] = SourceMode.REAL.value
            raw_dict["capability_available"] = True
            return validate_analysis_dict(raw_dict)
        else:
            return self.generate_deterministic_stub(capture_path)

    def generate_deterministic_stub(self, capture_path: str) -> AnalysisContract:
        """
        Generates a deterministic, schema-valid AnalysisContract for stub execution.
        Marked source_mode='stub' and capability_available=false.
        """
        path_obj = Path(capture_path)
        cap_id = path_obj.stem or "STUB_CAPTURE"

        # Compute deterministic seed from capture path name
        h = hashlib.sha256(capture_path.encode("utf-8")).hexdigest()
        seed_int = int(h[:8], 16)
        
        # Deterministic parameters
        snr_val = 15.0 + (seed_int % 100) / 10.0  # 15.0 to 25.0 dB
        baud_val = 1.0e6
        evm_val = 0.05 + ((seed_int >> 4) % 50) / 1000.0

        stub_data = {
            "schema_version": "1.0.0",
            "capture_id": cap_id,
            "source_mode": SourceMode.STUB.value,
            "capability_available": False,
            "fs_hz": 20.0e6,
            "fs_source": FsSource.INFERRED.value,
            "bursts": [
                {"start_ms": 0.0, "end_ms": 100.0, "power": -15.0}
            ],
            "estimates": {
                "baud": {
                    "value": baud_val,
                    "ci_lo": baud_val * 0.98,
                    "ci_hi": baud_val * 1.02,
                    "method": "stub_blind_estimation",
                },
                "cfo": {
                    "value": 0.0,
                    "ci_lo": -100.0,
                    "ci_hi": 100.0,
                    "method": "stub_cfo_estimation",
                },
                "bandwidth": {
                    "value": baud_val * 1.25,
                    "ci_lo": baud_val * 1.2,
                    "ci_hi": baud_val * 1.3,
                    "method": "stub_bandwidth_99",
                },
                "snr": {
                    "value": snr_val,
                    "ci_lo": snr_val - 1.0,
                    "ci_hi": snr_val + 1.0,
                    "method": "stub_m2m4",
                },
            },
            "features": {
                "cumulants": {
                    "C20": 0.01,
                    "C21": 1.0,
                    "C40": 0.98,
                    "C42": -0.99,
                    "C60": 0.0,
                    "C63": 0.0,
                    "C80": 0.0,
                },
                "cluster": {
                    "count": 4,
                    "silhouette": 0.85,
                    "intra_var": 0.08,
                    "inter_dist": 1.41,
                },
                "evm": evm_val,
                "phase_ambiguity_quality": 0.90,
                "cyclic": None,
            },
        }

        return validate_analysis_dict(stub_data)

    def run_stub(self, capture_path: str) -> AnalysisContract:
        """Alias for generate_deterministic_stub."""
        return self.generate_deterministic_stub(capture_path)
