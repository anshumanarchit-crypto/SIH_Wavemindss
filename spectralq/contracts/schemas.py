"""
Data contracts and frozen schema definitions for SpectralQ pipeline.
Enforces strict boundaries between Sinchana (DSP), Harsh (ML), Arpit (Demod/Decoder),
Archit (Integration & Decision Layer), and Himanshu (GUI).
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class ProvenanceType(str, Enum):
    REAL = "real"
    REPLAYED = "replayed"
    SYNTHETIC = "synthetic"


class LadderLevel(str, Enum):
    L1 = "L1"  # Signal Detected
    L2 = "L2"  # Signal Characterised (Blind estimation & features extracted)
    L3 = "L3"  # Demodulated, Internally Consistent (Constellation / timing resolved)
    L4 = "L4"  # Structure Verified (Sync pattern + CRC or known frame decoded)
    L5 = "L5"  # Independently Cross-Checked (Window stability + N5 agreement + FEC verified)


class Cumulants(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    C20: float = Field(..., description="Second-order cumulant C20 = E[y^2]")
    C21: float = Field(..., description="Second-order cumulant C21 = E[|y|^2]")
    C40: float = Field(..., description="Fourth-order cumulant C40")
    C42: float = Field(..., description="Fourth-order cumulant C42")
    C60: float = Field(..., description="Sixth-order cumulant C60")
    C63: float = Field(..., description="Sixth-order cumulant C63")
    C80: float = Field(..., description="Eighth-order cumulant C80")


class ClusterMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    cluster_count: int = Field(..., ge=1, le=256, description="Estimated constellation cluster count")
    silhouette_score: float = Field(..., ge=-1.0, le=1.0, description="Silhouette score of constellation clusters")
    intra_cluster_dist: float = Field(..., ge=0.0, description="Mean intra-cluster distance / spread")
    inter_cluster_dist: float = Field(..., ge=0.0, description="Mean inter-cluster separation")
    cluster_count_stability: float = Field(..., ge=0.0, le=1.0, description="Cluster count stability across sub-windows")


class SubWindowMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    window_idx: int = Field(..., ge=0)
    estimated_snr_db: float
    estimated_c42: float
    estimated_c20: float
    cluster_count: int


class CyclicFeatures(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    spectral_correlation_peaks: Optional[List[float]] = None
    alpha_profile: Optional[List[float]] = None
    cyclic_frequency_hz: Optional[float] = None


class AnalysisContract(BaseModel):
    """
    Contract received from Sinchana (Stages 1-4).
    Contains blind estimation, cumulants, SNR, EVM, and cluster metrics.
    """
    model_config = ConfigDict(extra="forbid")

    capture_id: str = Field(..., description="Unique capture identifier")
    provenance: ProvenanceType = Field(..., description="Capture provenance: real, replayed, or synthetic")
    is_valid_burst: bool = Field(..., description="Whether a valid signal burst was detected")
    center_freq_hz: Optional[float] = Field(None, description="Estimated center frequency in Hz")
    bandwidth_hz: Optional[float] = Field(None, description="Estimated occupied bandwidth in Hz")
    baud_rate: Optional[float] = Field(None, description="Estimated baud/symbol rate in symbols/sec")
    snr_m2m4_db: float = Field(..., description="M2M4 estimated SNR in dB")
    evm: float = Field(..., ge=0.0, description="Error Vector Magnitude (fraction or dB)")
    phase_ambiguity_quality: float = Field(..., ge=0.0, le=1.0, description="Phase ambiguity resolution score")
    envelope_variance: float = Field(..., ge=0.0, description="Normalized envelope variance")
    phase_entropy: float = Field(..., ge=0.0, description="Constellation phase angle entropy")
    cumulants: Cumulants
    cluster_metrics: ClusterMetrics
    sub_windows: List[SubWindowMetrics] = Field(default_factory=list)
    cyclic_features: Optional[CyclicFeatures] = None
    raw_capture_file: Optional[str] = None


class ClassifierOutputContract(BaseModel):
    """
    Contract received from Harsh (Stage 5 Classifier).
    """
    model_config = ConfigDict(extra="forbid")

    predicted_class: str
    class_probabilities: Dict[str, float]
    feature_vector: Dict[str, float]
    model_name: str = "RandomForest_Baseline"
    model_version: str = "1.0.0"
    is_synthetic_model: bool = False


class DecoderStatus(str, Enum):
    SUCCESS = "SUCCESS"
    SYNC_FOUND_CRC_FAILED = "SYNC_FOUND_CRC_FAILED"
    DECODE_FAILED = "DECODE_FAILED"
    UNSUPPORTED_FEC = "UNSUPPORTED_FEC"
    UNAVAILABLE = "UNAVAILABLE"


class DecoderVerificationContract(BaseModel):
    """
    Contract received from Arpit (Stages 6 & 9: Demodulation & FEC Decoding).
    """
    model_config = ConfigDict(extra="forbid")

    sync_detected: bool = Field(..., description="Whether frame sync pattern / preamble was detected")
    sync_confidence: float = Field(..., ge=0.0, le=1.0, description="Frame sync correlator peak-to-sidelobe score")
    crc_valid: Optional[bool] = Field(None, description="CRC check passed (None if no CRC present/tested)")
    reencode_ber: Optional[float] = Field(None, ge=0.0, le=1.0, description="Re-encode residual Bit Error Rate")
    interleaver_detected: Optional[str] = Field(None, description="Detected interleaver mode")
    fec_detected: Optional[str] = Field(None, description="Detected FEC scheme")
    status: DecoderStatus = Field(..., description="Decoder status flag")
    decoded_bits_count: int = Field(default=0, ge=0)
    details: Dict[str, Any] = Field(default_factory=dict)


class CandidateStatus(str, Enum):
    EVALUATED = "EVALUATED"
    PRUNED = "PRUNED"
    UNSUPPORTED = "UNSUPPORTED"


class HypothesisCandidate(BaseModel):
    """
    A single candidate hypothesis evaluated by the Hypothesis Engine.
    """
    model_config = ConfigDict(extra="forbid")

    modulation: str
    interleaver: str
    fec: str
    prior_score: float = Field(..., ge=0.0, le=1.0)
    verification_score: float = Field(..., ge=0.0, le=1.0)
    total_score: float = Field(..., ge=0.0, le=1.0)
    status: CandidateStatus
    rejection_reason: Optional[str] = None


class EvidenceLedgerEntry(BaseModel):
    """
    Audit trail item recording evidence derivation and weighting.
    """
    model_config = ConfigDict(extra="forbid")

    stage: str
    source: str
    timestamp_utc: str
    metric_name: str
    metric_value: Any
    interpretation: str
    weight: float


class ResultContract(BaseModel):
    """
    Final output contract (result.json) produced by Archit's decision layer
    and consumed strictly as read-only by Himanshu's Streamlit GUI.
    """
    model_config = ConfigDict(extra="forbid")

    capture_id: str
    provenance: ProvenanceType
    ladder_level: LadderLevel = Field(..., description="Deterministic evidence ladder level L1-L5")
    decision_label: str = Field(..., description="Top modulation label or UNKNOWN")
    final_confidence: float = Field(..., ge=0.0, le=1.0, description="Computed, bounded, calibrated confidence")
    is_calibrated: bool = Field(..., description="Whether confidence went through validated calibration")
    unknown_reason: Optional[str] = Field(None, description="Explicit reason if decision_label is UNKNOWN")
    
    # N5 Hybrid Modulation Details
    rule_prediction: Optional[str] = None
    rule_score: Optional[float] = None
    ml_prediction: Optional[str] = None
    ml_calibrated_prob: Optional[float] = None
    n5_agreement: bool
    n5_agreement_score: float = Field(..., ge=0.0, le=1.0)
    
    # Cross-window and Verification Scores
    cross_window_agreement_score: float = Field(..., ge=0.0, le=1.0)
    verification_evidence_score: float = Field(..., ge=0.0, le=1.0)
    
    # Full Evidence & Candidates
    top_hypothesis: Optional[HypothesisCandidate] = None
    candidates: List[HypothesisCandidate] = Field(default_factory=list)
    evidence_ledger: List[EvidenceLedgerEntry] = Field(default_factory=list)
    
    # Diagnostics & Timing
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
