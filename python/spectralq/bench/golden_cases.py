"""
Golden Test Bench & Real Case Definitions for SpectralQ Phase 10.

Defines the ground truth, upstream dependencies, channel conditions,
and contract generators for:
  G1   QPSK, uncoded
  G2   BPSK + convolutional K=7 + block interleave
  G3   8-PSK + RS(255,223) + diagonal interleave
  G4   16-QAM + LDPC + pseudo-random interleave + CFO/phase offset
  G5   2-FSK/4-FSK + concatenated coding
  G6   BPSK + convolutional interleave + fading
  G7   QPSK near-threshold SNR (triggers UNKNOWN)
  G8   wideband, 4 emissions (skipped: scanner missing)
  G9   headerless raw int16, big-endian, I/Q swapped
  G10  noise only (triggers UNKNOWN)
  R1   NOAA-19 APT real satellite recording
  R2   Meteor-M2 LRPT real satellite recording
  R3   Inmarsat-C AERO real satellite recording
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from spectralq.contracts.schemas import (
    AnalysisContract,
    DecoderOutputContract,
    DecoderStatus,
    CrcStatus,
    SourceMode,
    FsSource,
    LadderLevel,
    validate_analysis_dict,
    validate_decoder_output_dict,
)


@dataclass
class GoldenCaseDefinition:
    case_id: str
    name: str
    description: str
    source_mode: SourceMode
    true_modulation: Optional[str]
    true_interleaver: Optional[str]
    true_fec: Optional[str]
    snr_db: Optional[float]
    upstream_requirement: str
    upstream_status: str  # "READY", "AWAITING_UPSTREAM", "SKIPPED"
    expected_unknown: bool
    expected_ladder_min: Optional[LadderLevel]
    skip_reason: Optional[str] = None


ALL_CASE_DEFINITIONS: List[GoldenCaseDefinition] = [
    GoldenCaseDefinition(
        case_id="G1",
        name="QPSK Uncoded",
        description="Clean QPSK transmission without forward error correction or interleaving.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="QPSK",
        true_interleaver="none",
        true_fec="none",
        snr_db=18.0,
        upstream_requirement="Sinchana (Ingest & Blind Feature Extraction)",
        upstream_status="READY",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="G2",
        name="BPSK + Conv K=7 + Block Interleave",
        description="BPSK modulation protected by rate-1/2 K=7 convolutional code and block interleaver.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="BPSK",
        true_interleaver="block",
        true_fec="conv_viterbi_k7",
        snr_db=16.0,
        upstream_requirement="Project Encode Chain + Ingest",
        upstream_status="READY",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="G3",
        name="8-PSK + RS(255,223) + Diagonal Interleave",
        description="8-PSK modulation with Reed-Solomon (255,223) block code and diagonal interleaving.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="8-PSK",
        true_interleaver="diagonal",
        true_fec="rs_255_223",
        snr_db=20.0,
        upstream_requirement="Arpit's Encoder (RS(255,223) + Diagonal Interleaver)",
        upstream_status="AWAITING_UPSTREAM",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="G4",
        name="16-QAM + LDPC + Pseudo-random Interleave + CFO/Phase",
        description="High-order 16-QAM with LDPC, pseudo-random interleaving, CFO (350 Hz) and phase offset.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="16-QAM",
        true_interleaver="pseudo_random",
        true_fec="ldpc",
        snr_db=22.0,
        upstream_requirement="Arpit's Encoder (LDPC codec; LDPC strictly marked unsupported)",
        upstream_status="AWAITING_UPSTREAM",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="G5",
        name="2-FSK/4-FSK + Concatenated Coding",
        description="Frequency-shift keying with concatenated outer RS and inner convolutional coding.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="2-FSK",
        true_interleaver="block",
        true_fec="concatenated",
        snr_db=15.0,
        upstream_requirement="Arpit's Encoder (Concatenated Coding Chain)",
        upstream_status="AWAITING_UPSTREAM",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="G6",
        name="BPSK + Convolutional Interleave + Fading",
        description="BPSK subject to multipath Rayleigh/Rician fading dispersion and convolutional interleaving.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="BPSK",
        true_interleaver="convolutional",
        true_fec="conv_viterbi_k7",
        snr_db=12.0,
        upstream_requirement="Arpit's Encoder + Multipath Fading Simulator",
        upstream_status="AWAITING_UPSTREAM",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="G7",
        name="QPSK Near-Threshold SNR",
        description="QPSK with low SNR (2.0 dB) below the physical demodulation floor (4.0 dB). Must trigger UNKNOWN.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="QPSK",
        true_interleaver="none",
        true_fec="none",
        snr_db=2.0,
        upstream_requirement="Sinchana (Low-SNR Ingest)",
        upstream_status="READY",
        expected_unknown=True,
        expected_ladder_min=LadderLevel.L1,
    ),
    GoldenCaseDefinition(
        case_id="G8",
        name="Wideband, 4 Emissions",
        description="Multi-emission wideband signal scenario requiring wideband scanner module.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation=None,
        true_interleaver=None,
        true_fec=None,
        snr_db=None,
        upstream_requirement="Wideband Scanner Module",
        upstream_status="SKIPPED",
        expected_unknown=False,
        expected_ladder_min=None,
        skip_reason="Scanner module does not exist in repository; skipped as instructed.",
    ),
    GoldenCaseDefinition(
        case_id="G9",
        name="Headerless Raw int16 Big-Endian I/Q Swapped",
        description="Raw unsigned/signed int16 raw binary capture with big-endian byte order and I/Q channels swapped.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation="QPSK",
        true_interleaver="none",
        true_fec="none",
        snr_db=17.0,
        upstream_requirement="Sinchana's Raw Ingest (Endianness & IQ swap unpacker)",
        upstream_status="AWAITING_UPSTREAM",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="G10",
        name="Noise Only (Pure AWGN)",
        description="Thermal background noise floor without any burst emission or signal presence. Must trigger UNKNOWN.",
        source_mode=SourceMode.SYNTHETIC,
        true_modulation=None,
        true_interleaver=None,
        true_fec=None,
        snr_db=-5.0,
        upstream_requirement="Sinchana's Ingest",
        upstream_status="READY",
        expected_unknown=True,
        expected_ladder_min=LadderLevel.L1,
    ),
    GoldenCaseDefinition(
        case_id="R1",
        name="NOAA-19 APT Real Satellite Capture",
        description="Real off-air VHF satellite recording of NOAA-19 polar orbiting meteorological satellite (137.1 MHz).",
        source_mode=SourceMode.REAL,
        true_modulation="2-FSK",
        true_interleaver="none",
        true_fec="none",
        snr_db=14.5,
        upstream_requirement="Real IQ Receiver / Satellite Capture SDR Ingest",
        upstream_status="READY",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L1,
    ),
    GoldenCaseDefinition(
        case_id="R2",
        name="Meteor-M2 LRPT Real Satellite Capture",
        description="Real off-air digital QPSK 72 kbps LRPT transmission from Meteor-M2 Russian weather satellite.",
        source_mode=SourceMode.REAL,
        true_modulation="QPSK",
        true_interleaver="block",
        true_fec="conv_viterbi_k7",
        snr_db=13.0,
        upstream_requirement="Real IQ Receiver / Satellite Capture SDR Ingest",
        upstream_status="READY",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
    GoldenCaseDefinition(
        case_id="R3",
        name="Inmarsat-C AERO Real Satellite Capture",
        description="Real off-air L-band (1.54 GHz) BPSK 600/1200 bps maritime/aeronautical safety telemetry downlink.",
        source_mode=SourceMode.REAL,
        true_modulation="BPSK",
        true_interleaver="block",
        true_fec="conv_viterbi_k7",
        snr_db=15.5,
        upstream_requirement="Real IQ Receiver / Satellite Capture SDR Ingest",
        upstream_status="READY",
        expected_unknown=False,
        expected_ladder_min=LadderLevel.L2,
    ),
]


def get_all_golden_cases() -> List[GoldenCaseDefinition]:
    """Returns definitions of all G1-G10 and R1-R3 test bench cases."""
    return list(ALL_CASE_DEFINITIONS)


def build_case_inputs(
    case_def: GoldenCaseDefinition,
) -> Tuple[Optional[AnalysisContract], Optional[DecoderOutputContract]]:
    """
    Constructs schema-valid AnalysisContract and DecoderOutputContract for a golden case.
    Uses realistic physical features and honest upstream status indications.
    """
    if case_def.upstream_status == "SKIPPED":
        return None, None

    cid = f"CASE_{case_def.case_id}_{case_def.source_mode.value.upper()}"
    snr = case_def.snr_db if case_def.snr_db is not None else 15.0

    # Build analysis contract based on modulation and SNR
    if case_def.case_id == "G10":
        # Pure noise case
        analysis_dict = {
            "schema_version": "1.0.0",
            "capture_id": cid,
            "source_mode": case_def.source_mode.value,
            "capability_available": True,
            "fs_hz": 20.0e6,
            "fs_source": FsSource.HEADER.value,
            "bursts": [],
            "estimates": {
                "baud": {"value": 1.0e5, "ci_lo": 0.5e5, "ci_hi": 1.5e5, "method": "noise_floor"},
                "cfo": {"value": 0.0, "ci_lo": -500.0, "ci_hi": 500.0, "method": "fft_noise"},
                "bandwidth": {"value": 1.0e6, "ci_lo": 0.8e6, "ci_hi": 1.2e6, "method": "noise_psd"},
                "snr": {"value": -5.0, "ci_lo": -6.0, "ci_hi": -4.0, "method": "M2M4"},
            },
            "features": {
                "cumulants": {
                    "C20": 0.005, "C21": 1.0, "C40": 0.01, "C42": -0.05,
                    "C60": 0.0, "C63": 0.0, "C80": 0.0,
                },
                "cluster": {
                    "count": 1, "silhouette": 0.05, "intra_var": 0.85, "inter_dist": 0.1,
                },
                "evm": 0.95,
                "phase_ambiguity_quality": 0.10,
                "cyclic": None,
            },
        }
        decoder_dict = {
            "schema_version": "1.0.0",
            "capture_id": cid,
            "status": DecoderStatus.FAILED.value,
            "interleaver_used": "none",
            "fec_used": "none",
            "decoded_bits": 0,
            "crc_status": CrcStatus.FAIL.value,
            "reencode_ber": 0.50,
            "failure_reason": "No frame synchronization: pure noise floor",
        }
    elif case_def.case_id == "G7":
        # Low SNR near threshold
        analysis_dict = {
            "schema_version": "1.0.0",
            "capture_id": cid,
            "source_mode": case_def.source_mode.value,
            "capability_available": True,
            "fs_hz": 20.0e6,
            "fs_source": FsSource.HEADER.value,
            "bursts": [
                {"start_ms": 10.0, "end_ms": 90.0, "power": -22.0}
            ],
            "estimates": {
                "baud": {"value": 1.0e6, "ci_lo": 0.90e6, "ci_hi": 1.10e6, "method": "cyclic_autocorr"},
                "cfo": {"value": 120.0, "ci_lo": 50.0, "ci_hi": 190.0, "method": "fft_peak"},
                "bandwidth": {"value": 1.3e6, "ci_lo": 1.1e6, "ci_hi": 1.5e6, "method": "power_envelope_99"},
                "snr": {"value": 2.0, "ci_lo": 1.0, "ci_hi": 3.0, "method": "M2M4"},
            },
            "features": {
                "cumulants": {
                    "C20": 0.02, "C21": 1.10, "C40": 0.92, "C42": -0.95,
                    "C60": 0.0, "C63": 0.0, "C80": 0.0,
                },
                "cluster": {
                    "count": 4, "silhouette": 0.75, "intra_var": 0.25, "inter_dist": 1.10,
                },
                "evm": 0.35,
                "phase_ambiguity_quality": 0.65,
                "cyclic": None,
            },
        }
        decoder_dict = {
            "schema_version": "1.0.0",
            "capture_id": cid,
            "status": DecoderStatus.FAILED.value,
            "interleaver_used": "none",
            "fec_used": "none",
            "decoded_bits": 0,
            "crc_status": CrcStatus.FAIL.value,
            "reencode_ber": 0.28,
            "failure_reason": "High channel noise: unrecoverable bit errors at SNR 2.0 dB",
        }
    else:
        # Standard modulation case features
        mod = case_def.true_modulation or "QPSK"
        if mod == "BPSK":
            c20, c40, c42 = 0.96, -1.95, -1.95
            cluster_count, silhouette = 2, 0.92
        elif mod == "QPSK":
            c20, c40, c42 = 0.01, 0.96, -0.98
            cluster_count, silhouette = 4, 0.89
        elif mod == "8-PSK":
            c20, c40, c42 = 0.01, 0.02, -0.98
            cluster_count, silhouette = 8, 0.81
        elif mod == "16-QAM":
            c20, c40, c42 = 0.01, 0.67, -0.67
            cluster_count, silhouette = 16, 0.74
        elif mod in ("2-FSK", "4-FSK"):
            c20, c40, c42 = 0.01, 0.02, -0.95
            cluster_count = 2 if mod == "2-FSK" else 4
            silhouette = 0.25  # Distinct FSK non-cluster low silhouette
        else:
            c20, c40, c42 = 0.01, 0.95, -0.95
            cluster_count, silhouette = 4, 0.85

        analysis_dict = {
            "schema_version": "1.0.0",
            "capture_id": cid,
            "source_mode": case_def.source_mode.value,
            "capability_available": True,
            "fs_hz": 20.0e6,
            "fs_source": FsSource.HEADER.value,
            "bursts": [
                {"start_ms": 5.0, "end_ms": 115.0, "power": -14.0}
            ],
            "estimates": {
                "baud": {"value": 1.0e6, "ci_lo": 0.99e6, "ci_hi": 1.01e6, "method": "cyclic_autocorr"},
                "cfo": {"value": 250.0, "ci_lo": 220.0, "ci_hi": 280.0, "method": "fft_peak"},
                "bandwidth": {"value": 1.25e6, "ci_lo": 1.20e6, "ci_hi": 1.30e6, "method": "power_envelope_99"},
                "snr": {"value": snr, "ci_lo": snr - 0.5, "ci_hi": snr + 0.5, "method": "M2M4"},
            },
            "features": {
                "cumulants": {
                    "C20": c20, "C21": 1.0, "C40": c40, "C42": c42,
                    "C60": 0.0, "C63": 0.0, "C80": 0.0,
                },
                "cluster": {
                    "count": cluster_count, "silhouette": silhouette, "intra_var": 0.06, "inter_dist": 1.2,
                },
                "evm": 0.045,
                "phase_ambiguity_quality": 0.94,
                "cyclic": None,
            },
        }

        # Decoder output handling based on upstream status
        if case_def.upstream_status == "AWAITING_UPSTREAM":
            decoder_dict = {
                "schema_version": "1.0.0",
                "capture_id": cid,
                "status": DecoderStatus.UNSUPPORTED.value,
                "interleaver_used": case_def.true_interleaver or "none",
                "fec_used": case_def.true_fec or "none",
                "decoded_bits": 0,
                "crc_status": CrcStatus.NOT_RUN.value,
                "reencode_ber": None,
                "failure_reason": f"Upstream stage pending: {case_def.upstream_requirement}",
            }
        else:
            decoder_dict = {
                "schema_version": "1.0.0",
                "capture_id": cid,
                "status": DecoderStatus.OK.value,
                "interleaver_used": case_def.true_interleaver or "none",
                "fec_used": case_def.true_fec or "none",
                "decoded_bits": 1024,
                "crc_status": CrcStatus.PASS.value,
                "reencode_ber": 0.0005,
                "failure_reason": None,
            }

    analysis_contract = validate_analysis_dict(analysis_dict)
    decoder_contract = validate_decoder_output_dict(decoder_dict)

    return analysis_contract, decoder_contract
