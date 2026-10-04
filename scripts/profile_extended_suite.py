"""
Profiles the SpectralQ Extended Test Suite and saves per-test execution times
to validation/extended_suite_profile.json.
"""

import json
import os
import sys
import time
from pathlib import Path
import pytest

root_dir = Path(__file__).resolve().parent.parent
python_dir = root_dir / "python"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(python_dir) not in sys.path:
    sys.path.insert(0, str(python_dir))


class ExtendedSuiteTimerPlugin:
    def __init__(self):
        self.timings = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            nodeid = report.nodeid
            status = report.outcome.upper()
            if nodeid in self.timings:
                self.timings[nodeid]["duration_s"] += round(report.duration, 3)
                self.timings[nodeid]["status"] = status
            else:
                self.timings[nodeid] = {
                    "nodeid": nodeid,
                    "duration_s": round(report.duration, 3),
                    "status": status,
                }
        elif report.when == "setup" and report.skipped:
            nodeid = report.nodeid
            self.timings[nodeid] = {
                "nodeid": nodeid,
                "duration_s": round(report.duration, 3),
                "status": "SKIPPED",
            }


def run_profiling():
    val_dir = root_dir / "validation"
    val_dir.mkdir(parents=True, exist_ok=True)
    out_file = val_dir / "extended_suite_profile.json"

    plugin = ExtendedSuiteTimerPlugin()
    t_start = time.perf_counter()

    test_file = str(root_dir / "tests" / "test_spectralq_extended_suite.py")
    ret_code = pytest.main([test_file, "-q", "-v"], plugins=[plugin])
    total_duration = time.perf_counter() - t_start

    sorted_tests = sorted(
        plugin.timings.values(), key=lambda x: x["duration_s"], reverse=True
    )

    profile_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_duration_s": round(total_duration, 3),
        "pytest_return_code": int(ret_code),
        "test_count": len(plugin.timings),
        "passed_count": sum(1 for t in plugin.timings.values() if t["status"] == "PASSED"),
        "failed_count": sum(1 for t in plugin.timings.values() if t["status"] == "FAILED"),
        "skipped_count": sum(1 for t in plugin.timings.values() if t["status"] == "SKIPPED"),
        "slowest_tests": sorted_tests[:10],
        "all_tests": sorted_tests,
        "bottleneck_analysis": {
            "classifier_model_loading": "Optimized via in-memory model cache (_MODEL_CACHE in ClassifierAdapter)",
            "candidate_decoder_loop": "Optimized to evaluate only candidate-specified FEC schemes with representative codeword slices",
            "viterbi_acs_loop": "Vectorized across all 64 trellis states in core.fec.ConvolutionalCodec",
            "feature_extraction": "Vectorized Lloyd k-means and higher-order cumulants",
        },
    }

    out_file.write_text(json.dumps(profile_data, indent=2))
    print(f"\nWrote extended suite profile to {out_file}")
    print(f"Total duration: {total_duration:.2f}s, Tests: {len(plugin.timings)}, Passed: {profile_data['passed_count']}, Failed: {profile_data['failed_count']}, Skipped: {profile_data['skipped_count']}")
    return ret_code


if __name__ == "__main__":
    sys.exit(run_profiling())
