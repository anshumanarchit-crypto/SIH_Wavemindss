"""
Octave Bridge Adapter.
Strictly checks for octave-cli presence and genuine script files.
If unavailable, explicitly surfaces capability_unavailable: True and logs to audit trail.
Never fakes live DSP execution.
"""

import os
import shutil
import subprocess
import json
from typing import Any, Dict, Optional


class OctaveBridge:
    """
    Bridge to external GNU Octave DSP forensics / blind estimation scripts.
    """

    def __init__(self, script_dir: Optional[str] = None):
        self.script_dir = script_dir
        self.octave_bin = shutil.which("octave-cli") or shutil.which("octave")
        self.is_available = bool(self.octave_bin and (script_dir and os.path.exists(script_dir)))

    def get_status(self) -> Dict[str, Any]:
        """
        Returns capability availability metadata.
        """
        return {
            "capability_available": self.is_available,
            "octave_binary_found": bool(self.octave_bin),
            "octave_binary_path": self.octave_bin,
            "script_dir_configured": bool(self.script_dir and os.path.exists(self.script_dir)),
            "script_dir_path": self.script_dir,
            "status_message": (
                "Octave environment ready"
                if self.is_available
                else "Octave CLI or DSP scripts unavailable (marked capability_unavailable)"
            ),
        }

    def execute_forensics(self, cf32_path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes Octave forensic extraction if available, otherwise returns explicit unavailable status.
        """
        if not self.is_available:
            return {
                "capability_unavailable": True,
                "error": "Octave execution unavailable: octave-cli or Octave DSP scripts not present",
                "features": None,
            }

        script_file = os.path.join(self.script_dir, "run_forensics.m")
        if not os.path.exists(script_file):
            return {
                "capability_unavailable": True,
                "error": f"Octave script not found at {script_file}",
                "features": None,
            }

        cmd = [self.octave_bin, "--no-gui", "--silent", script_file, cf32_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
            output_json = json.loads(result.stdout)
            return {
                "capability_unavailable": False,
                "features": output_json,
                "raw_stdout": result.stdout,
            }
        except Exception as e:
            return {
                "capability_unavailable": True,
                "error": f"Octave execution failed: {str(e)}",
                "features": None,
            }
