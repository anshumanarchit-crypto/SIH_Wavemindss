"""
Generates reference golden contract JSON files under data/golden/
"""

import json
from pathlib import Path

analysis_sample = {
    "schema_version": "1.0.0",
    "capture_id": "GOLDEN_001_QPSK",
    "source_mode": "synthetic",
    "fs_hz": 20.0e6,
    "fs_source": "header",
    "bursts": [
        {"start_ms": 5.0, "end_ms": 120.0, "power": -12.4}
    ],
    "estimates": {
        "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic_autocorr"},
        "cfo": {"value": 500.0, "ci_lo": 450.0, "ci_hi": 550.0, "method": "fft_peak"},
        "bandwidth": {"value": 1.25e6, "ci_lo": 1.2e6, "ci_hi": 1.3e6, "method": "power_envelope_99"},
        "snr": {"value": 20.0, "ci_lo": 19.0, "ci_hi": 21.0, "method": "M2M4"},
    },
    "features": {
        "cumulants": {
            "C20": 0.01, "C21": 1.0, "C40": 0.97, "C42": -0.99,
            "C60": 0.0, "C63": 0.0, "C80": 0.0,
        },
        "cluster": {
            "count": 4, "silhouette": 0.91, "intra_var": 0.06, "inter_dist": 1.41,
        },
        "evm": 0.035,
        "phase_ambiguity_quality": 0.96,
        "cyclic": None,
    },
}

decoder_sample = {
    "schema_version": "1.0.0",
    "capture_id": "GOLDEN_001_QPSK",
    "status": "ok",
    "interleaver_used": "block",
    "fec_used": "conv_viterbi_k7",
    "decoded_bits": "110010101111000010101100",
    "crc_status": "pass",
    "reencode_ber": 0.0005,
    "failure_reason": None,
}

classifier_sample = {
    "schema_version": "1.0.0",
    "capture_id": "GOLDEN_001_QPSK",
    "window_id": 0,
    "ml_prediction": "QPSK",
    "ml_probabilities": {
        "BPSK": 0.01,
        "QPSK": 0.95,
        "8-PSK": 0.02,
        "16-QAM": 0.01,
        "64-QAM": 0.005,
        "2-FSK": 0.002,
        "4-FSK": 0.003,
    },
    "calibrated_probability": 0.94,
    "model_version": "rf-baseline-1.0.0",
    "feature_vector_used": {
        "C20": 0.01, "C40": 0.97, "C42": -0.99, "snr": 20.0, "evm": 0.035
    },
}

truth_sample = {
    "schema_version": "1.0.0",
    "modulation": "QPSK",
    "sps": 4.0,
    "roll_off": 0.35,
    "snr_db": 20.0,
    "cfo_hz": 500.0,
    "phase": 0.0,
    "interleaver": "block",
    "fec": "conv_viterbi_k7",
    "timing_bits": [1, 1, 0, 0, 1, 0, 1, 0],
    "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}

result_sample = {
    "schema_version": "1.0.0",
    "capture_id": "GOLDEN_001_QPSK",
    "source_mode": "synthetic",
    "ladder_level": "L5",
    "top_hypothesis": {
        "modulation": "QPSK",
        "interleaver": "block",
        "fec": "conv_viterbi_k7",
    },
    "alternate_hypotheses": [
        {
            "modulation": "QPSK",
            "interleaver": "none",
            "fec": "ldpc",
            "prior_score": 0.85,
            "verification_score": 0.0,
            "total_score": 0.0,
            "status": "UNSUPPORTED",
            "rejection_reason": "FEC scheme 'LDPC' is unsupported in current release (never fabricated)",
        }
    ],
    "ml_prediction": "QPSK",
    "ml_probability": 0.95,
    "calibrated_ml_probability": 0.94,
    "rule_prediction": "QPSK",
    "rule_ml_agreement": True,
    "rule_ml_penalty": 0.0,
    "cross_window_agreement": 0.99,
    "evidence": [
        {
            "evidence_id": "EV_001",
            "source": "Sinchana",
            "check_name": "burst_power",
            "status": "PASS",
            "value": -12.4,
            "explanation": "Valid burst energy detected above background noise floor",
        }
    ],
    "final_confidence": 0.975,
    "confidence_version": "n2-logistic-1.0.0",
    "unknown": False,
    "unknown_reason": None,
    "provenance": {
        "input_hash": "b2c3d4e5f6789012",
        "seed": 42,
        "software_version": "1.0.0",
        "generated_at": "2026-09-25T11:30:00Z",
    },
}


def main():
    dest = Path("data/golden")
    dest.mkdir(parents=True, exist_ok=True)
    with open(dest / "analysis.json", "w") as f:
        json.dump(analysis_sample, f, indent=2)
    with open(dest / "decoder_output.json", "w") as f:
        json.dump(decoder_sample, f, indent=2)
    with open(dest / "classifier_output.json", "w") as f:
        json.dump(classifier_sample, f, indent=2)
    with open(dest / "truth.json", "w") as f:
        json.dump(truth_sample, f, indent=2)
    with open(dest / "result.json", "w") as f:
        json.dump(result_sample, f, indent=2)
    print("Golden samples generated successfully.")


if __name__ == "__main__":
    main()
