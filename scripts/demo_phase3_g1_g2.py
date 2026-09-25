"""
Demo script executing and dumping G1 and G2 hypothesis rankings.
"""

from spectralq.contracts.schemas import (
    validate_analysis_dict,
    validate_classifier_output_dict,
    validate_decoder_output_dict,
)
from spectralq.hypothesis import HypothesisEngineV1, format_hypothesis_dump

g1_analysis_raw = {
    "schema_version": "1.0.0",
    "capture_id": "G1_QPSK_BURST_001",
    "source_mode": "synthetic",
    "fs_hz": 20.0e6,
    "fs_source": "header",
    "bursts": [{"start_ms": 10.0, "end_ms": 110.0, "power": -12.0}],
    "estimates": {
        "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic"},
        "cfo": {"value": 100.0, "ci_lo": 50.0, "ci_hi": 150.0, "method": "fft"},
        "bandwidth": {"value": 1.3e6, "ci_lo": 1.25e6, "ci_hi": 1.35e6, "method": "obw"},
        "snr": {"value": 20.0, "ci_lo": 19.0, "ci_hi": 21.0, "method": "m2m4"},
    },
    "features": {
        "cumulants": {
            "C20": 0.01, "C21": 1.0, "C40": 0.98, "C42": -0.99,
            "C60": 0.0, "C63": 0.0, "C80": 0.0,
        },
        "cluster": {"count": 4, "silhouette": 0.90, "intra_var": 0.05, "inter_dist": 1.41},
        "evm": 0.035,
        "phase_ambiguity_quality": 0.95,
        "cyclic": None,
    },
}

g1_classifier_raw = {
    "schema_version": "1.0.0",
    "capture_id": "G1_QPSK_BURST_001",
    "window_id": 0,
    "ml_prediction": "QPSK",
    "ml_probabilities": {
        "BPSK": 0.01, "QPSK": 0.94, "8-PSK": 0.02, "16-QAM": 0.01,
        "64-QAM": 0.005, "2-FSK": 0.005, "4-FSK": 0.01,
    },
    "calibrated_probability": 0.92,
    "model_version": "rf-baseline-1.0.0",
    "feature_vector_used": {"C20": 0.01, "C40": 0.98, "C42": -0.99, "snr": 20.0},
}

g1_decoder_raw = {
    "schema_version": "1.0.0",
    "capture_id": "G1_QPSK_BURST_001",
    "status": "ok",
    "interleaver_used": "block",
    "fec_used": "conv_viterbi_k7",
    "decoded_bits": "110010101111000010101100" * 4,
    "crc_status": "pass",
    "reencode_ber": 0.001,
    "failure_reason": None,
}

g2_analysis_raw = {
    "schema_version": "1.0.0",
    "capture_id": "G2_2FSK_BURST_002",
    "source_mode": "synthetic",
    "fs_hz": 10.0e6,
    "fs_source": "header",
    "bursts": [{"start_ms": 5.0, "end_ms": 95.0, "power": -15.0}],
    "estimates": {
        "baud": {"value": 50.0e3, "ci_lo": 49.5e3, "ci_hi": 50.5e3, "method": "cyclic"},
        "cfo": {"value": 0.0, "ci_lo": -50.0, "ci_hi": 50.0, "method": "fft"},
        "bandwidth": {"value": 120.0e3, "ci_lo": 115.0e3, "ci_hi": 125.0e3, "method": "obw"},
        "snr": {"value": 16.0, "ci_lo": 15.0, "ci_hi": 17.0, "method": "m2m4"},
    },
    "features": {
        "cumulants": {
            "C20": 0.01, "C21": 1.0, "C40": 0.05, "C42": -0.95,
            "C60": 0.0, "C63": 0.0, "C80": 0.0,
        },
        "cluster": {"count": 2, "silhouette": 0.85, "intra_var": 0.10, "inter_dist": 1.0},
        "evm": 0.08,
        "phase_ambiguity_quality": 0.88,
        "cyclic": None,
    },
}

g2_classifier_raw = {
    "schema_version": "1.0.0",
    "capture_id": "G2_2FSK_BURST_002",
    "window_id": 0,
    "ml_prediction": "2-FSK",
    "ml_probabilities": {
        "BPSK": 0.02, "QPSK": 0.01, "8-PSK": 0.01, "16-QAM": 0.005,
        "64-QAM": 0.001, "2-FSK": 0.91, "4-FSK": 0.044,
    },
    "calibrated_probability": 0.89,
    "model_version": "rf-baseline-1.0.0",
    "feature_vector_used": {"C20": 0.01, "C40": 0.05, "C42": -0.95, "snr": 16.0},
}

g2_decoder_raw = {
    "schema_version": "1.0.0",
    "capture_id": "G2_2FSK_BURST_002",
    "status": "ok",
    "interleaver_used": "none",
    "fec_used": "none",
    "decoded_bits": "101010101100110011110000",
    "crc_status": "pass",
    "reencode_ber": 0.0,
    "failure_reason": None,
}


def run_demos():
    engine = HypothesisEngineV1()

    # Case G1
    a1 = validate_analysis_dict(g1_analysis_raw)
    c1 = validate_classifier_output_dict(g1_classifier_raw)
    d1 = validate_decoder_output_dict(g1_decoder_raw)
    ranked_g1 = engine.run(a1, c1, d1)
    dump_g1 = format_hypothesis_dump(ranked_g1, top_n=6, title="Case G1: Standard Verified QPSK Signal")
    print(dump_g1)

    print("\n" + "#" * 84 + "\n")

    # Case G2
    a2 = validate_analysis_dict(g2_analysis_raw)
    c2 = validate_classifier_output_dict(g2_classifier_raw)
    d2 = validate_decoder_output_dict(g2_decoder_raw)
    ranked_g2 = engine.run(a2, c2, d2)
    dump_g2 = format_hypothesis_dump(ranked_g2, top_n=6, title="Case G2: Unencoded 2-FSK Telemetry Signal")
    print(dump_g2)


if __name__ == "__main__":
    run_demos()
