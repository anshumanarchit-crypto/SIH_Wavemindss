"""
Generates synthetic and edge-case AnalysisContract and DecoderVerificationContract fixtures
for end-to-end unit and integration testing.
"""

import os
import json
from pathlib import Path


def generate_all_fixtures(output_dir: str = "fixtures") -> None:
    os.makedirs(output_dir, exist_ok=True)

    # 1. BPSK Clean Capture
    bpsk_clean = {
        "capture_id": "CAP_BPSK_001",
        "provenance": "synthetic",
        "is_valid_burst": True,
        "center_freq_hz": 433.92e6,
        "bandwidth_hz": 100e3,
        "baud_rate": 50e3,
        "snr_m2m4_db": 22.5,
        "evm": 0.045,
        "phase_ambiguity_quality": 0.95,
        "envelope_variance": 0.05,
        "phase_entropy": 0.69,
        "cumulants": {
            "C20": 0.98,
            "C21": 1.00,
            "C40": -1.95,
            "C42": -1.96,
            "C60": 0.0,
            "C63": 0.0,
            "C80": 0.0,
        },
        "cluster_metrics": {
            "cluster_count": 2,
            "silhouette_score": 0.92,
            "intra_cluster_dist": 0.08,
            "inter_cluster_dist": 1.95,
            "cluster_count_stability": 0.98,
        },
        "sub_windows": [
            {"window_idx": 0, "estimated_snr_db": 22.8, "estimated_c42": -1.95, "estimated_c20": 0.98, "cluster_count": 2},
            {"window_idx": 1, "estimated_snr_db": 22.3, "estimated_c42": -1.97, "estimated_c20": 0.97, "cluster_count": 2},
            {"window_idx": 2, "estimated_snr_db": 22.4, "estimated_c42": -1.96, "estimated_c20": 0.99, "cluster_count": 2},
        ],
    }

    # 2. QPSK with Sync and CRC Verified
    qpsk_verified = {
        "capture_id": "CAP_QPSK_002",
        "provenance": "synthetic",
        "is_valid_burst": True,
        "center_freq_hz": 868.0e6,
        "bandwidth_hz": 200e3,
        "baud_rate": 100e3,
        "snr_m2m4_db": 18.0,
        "evm": 0.07,
        "phase_ambiguity_quality": 0.92,
        "envelope_variance": 0.06,
        "phase_entropy": 1.38,
        "cumulants": {
            "C20": 0.02,
            "C21": 1.00,
            "C40": 0.96,
            "C42": -0.98,
            "C60": 0.0,
            "C63": 0.0,
            "C80": 0.0,
        },
        "cluster_metrics": {
            "cluster_count": 4,
            "silhouette_score": 0.88,
            "intra_cluster_dist": 0.12,
            "inter_cluster_dist": 1.41,
            "cluster_count_stability": 0.95,
        },
        "sub_windows": [
            {"window_idx": 0, "estimated_snr_db": 18.2, "estimated_c42": -0.98, "estimated_c20": 0.02, "cluster_count": 4},
            {"window_idx": 1, "estimated_snr_db": 17.9, "estimated_c42": -0.97, "estimated_c20": 0.01, "cluster_count": 4},
        ],
    }

    # 3. 2-FSK Capture
    fsk2_capture = {
        "capture_id": "CAP_2FSK_003",
        "provenance": "synthetic",
        "is_valid_burst": True,
        "center_freq_hz": 433.0e6,
        "bandwidth_hz": 50e3,
        "baud_rate": 25e3,
        "snr_m2m4_db": 16.0,
        "evm": 0.12,
        "phase_ambiguity_quality": 0.80,
        "envelope_variance": 0.48,
        "phase_entropy": 2.1,
        "cumulants": {
            "C20": 0.01,
            "C21": 1.00,
            "C40": 0.05,
            "C42": -0.95,
            "C60": 0.0,
            "C63": 0.0,
            "C80": 0.0,
        },
        "cluster_metrics": {
            "cluster_count": 2,
            "silhouette_score": 0.75,
            "intra_cluster_dist": 0.20,
            "inter_cluster_dist": 1.0,
            "cluster_count_stability": 0.90,
        },
        "sub_windows": [
            {"window_idx": 0, "estimated_snr_db": 16.1, "estimated_c42": -0.95, "estimated_c20": 0.01, "cluster_count": 2},
            {"window_idx": 1, "estimated_snr_db": 15.9, "estimated_c42": -0.94, "estimated_c20": 0.02, "cluster_count": 2},
        ],
    }

    # 4. Low SNR Degraded Capture (Triggering UNKNOWN)
    low_snr_unknown = {
        "capture_id": "CAP_LOW_SNR_004",
        "provenance": "synthetic",
        "is_valid_burst": True,
        "center_freq_hz": 433.0e6,
        "bandwidth_hz": 100e3,
        "baud_rate": 50e3,
        "snr_m2m4_db": -0.8,  # Degraded below floor
        "evm": 0.78,
        "phase_ambiguity_quality": 0.15,
        "envelope_variance": 0.40,
        "phase_entropy": 2.8,
        "cumulants": {
            "C20": 0.45,
            "C21": 1.00,
            "C40": -0.30,
            "C42": -0.40,
            "C60": 0.0,
            "C63": 0.0,
            "C80": 0.0,
        },
        "cluster_metrics": {
            "cluster_count": 6,
            "silhouette_score": 0.15,
            "intra_cluster_dist": 0.85,
            "inter_cluster_dist": 0.90,
            "cluster_count_stability": 0.20,
        },
        "sub_windows": [
            {"window_idx": 0, "estimated_snr_db": -0.5, "estimated_c42": -0.2, "estimated_c20": 0.3, "cluster_count": 8},
            {"window_idx": 1, "estimated_snr_db": -1.2, "estimated_c42": -0.6, "estimated_c20": 0.6, "cluster_count": 4},
        ],
    }

    # 5. Invalid Burst (Triggering UNKNOWN at L1)
    no_burst_unknown = {
        "capture_id": "CAP_NO_BURST_005",
        "provenance": "synthetic",
        "is_valid_burst": False,
        "center_freq_hz": None,
        "bandwidth_hz": None,
        "baud_rate": None,
        "snr_m2m4_db": -5.0,
        "evm": 1.2,
        "phase_ambiguity_quality": 0.0,
        "envelope_variance": 0.8,
        "phase_entropy": 3.0,
        "cumulants": {
            "C20": 0.0,
            "C21": 0.0,
            "C40": 0.0,
            "C42": 0.0,
            "C60": 0.0,
            "C63": 0.0,
            "C80": 0.0,
        },
        "cluster_metrics": {
            "cluster_count": 1,
            "silhouette_score": 0.0,
            "intra_cluster_dist": 0.0,
            "inter_cluster_dist": 0.0,
            "cluster_count_stability": 0.0,
        },
        "sub_windows": [],
    }

    for name, data in [
        ("bpsk_clean.json", bpsk_clean),
        ("qpsk_verified.json", qpsk_verified),
        ("fsk2_capture.json", fsk2_capture),
        ("low_snr_unknown.json", low_snr_unknown),
        ("no_burst_unknown.json", no_burst_unknown),
    ]:
        with open(Path(output_dir) / name, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    print(f"Generated 5 test fixtures in {output_dir}/")


if __name__ == "__main__":
    generate_all_fixtures()
