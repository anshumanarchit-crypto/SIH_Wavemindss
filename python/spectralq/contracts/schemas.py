"""
Versioned, field-level JSON schemas and strict validation contracts for SpectralQ.
Every schema strictly includes 'schema_version' and forbids silent coercion or extra fields.

Field states that must never be confused:
  known | estimated | hypothesized | unsupported | unavailable | replayed | synthetic | real
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

CURRENT_SCHEMA_VERSION = "1.0.0"


# -----------------------------------------------------------------------------
# Explicit State Enums (Never confused across boundaries)
# -----------------------------------------------------------------------------
class SourceMode(str, Enum):
    REAL = "real"
    SYNTHETIC = "synthetic"
    REPLAY = "replay"
    STUB = "stub"


class FsSource(str, Enum):
    HEADER = "header"
    USER = "user"
    INFERRED = "inferred"


class DecoderStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class CrcStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_RUN = "not_run"


class LadderLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"


class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICT = "CONFLICT"


class EpistemicState(str, Enum):
    """
    Epistemic boundary tracker to ensure estimation, ground-truth knowledge,
    hypotheses, and unsupported/unavailable states are never conflated.
    """
    KNOWN = "known"
    ESTIMATED = "estimated"
    HYPOTHESIZED = "hypothesized"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    REPLAYED = "replayed"
    SYNTHETIC = "synthetic"
    REAL = "real"


# -----------------------------------------------------------------------------
# 1. analysis.json (from Sinchana)
# -----------------------------------------------------------------------------
class BurstRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_ms: float = Field(..., ge=0.0, description="Burst start time in milliseconds")
    end_ms: float = Field(..., ge=0.0, description="Burst end time in milliseconds")
    power: float = Field(..., description="Estimated burst power")

    @model_validator(mode="after")
    def validate_burst_interval(self) -> "BurstRecord":
        if self.end_ms < self.start_ms:
            raise ValueError(f"end_ms ({self.end_ms}) cannot be less than start_ms ({self.start_ms})")
        return self


class ParameterEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float = Field(..., description="Central point estimate")
    ci_lo: float = Field(..., description="Confidence interval lower bound (95%)")
    ci_hi: float = Field(..., description="Confidence interval upper bound (95%)")
    method: str = Field(..., min_length=1, description="Estimation algorithm used")

    @model_validator(mode="after")
    def validate_ci_ordering(self) -> "ParameterEstimate":
        if self.ci_lo > self.ci_hi:
            raise ValueError(f"Confidence interval lower bound ci_lo ({self.ci_lo}) cannot exceed ci_hi ({self.ci_hi})")
        return self


class EstimatesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baud: ParameterEstimate
    cfo: ParameterEstimate
    bandwidth: ParameterEstimate
    snr: ParameterEstimate


class CumulantsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    C20: float
    C21: float
    C40: float
    C42: float
    C60: float
    C63: float
    C80: float


class ClusterBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(..., ge=1, le=256, description="Estimated constellation cluster count")
    silhouette: float = Field(..., ge=-1.0, le=1.0, description="Silhouette metric")
    intra_var: float = Field(..., ge=0.0, description="Intra-cluster variance")
    inter_dist: float = Field(..., ge=0.0, description="Inter-cluster separation distance")


class FeaturesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cumulants: CumulantsBlock
    cluster: ClusterBlock
    evm: float = Field(..., ge=0.0, description="Error Vector Magnitude (linear or ratio)")
    phase_ambiguity_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Phase ambiguity resolution score")
    cyclic: Optional[Dict[str, Any]] = None


class AnalysisContract(BaseModel):
    """
    Contract for analysis.json (Sinchana: Ingest, Forensics, Blind Estimation, Features).
    """
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., description="Semantic contract version")
    capture_id: str = Field(..., min_length=1, description="Unique capture identifier")
    source_mode: SourceMode = Field(..., description="Source mode: real, synthetic, or replay")
    fs_hz: float = Field(..., gt=0.0, description="Sample rate in Hz")
    fs_source: FsSource = Field(..., description="Source of sampling rate specification")
    bursts: List[BurstRecord] = Field(..., description="Detected signal bursts")
    estimates: EstimatesBlock = Field(..., description="Blind parameter estimates")
    features: FeaturesBlock = Field(..., description="Extracted physical & statistical features")
    sub_windows: Optional[List[Dict[str, Any]]] = Field(None, description="Optional temporal sub-window forensic metrics")
    notes: Optional[str] = Field(None, description="Ingest and provenance notes")
    capability_available: Optional[bool] = Field(None, description="Whether live DSP capability was available")

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v != CURRENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: expected '{CURRENT_SCHEMA_VERSION}', got '{v}'")
        return v


# -----------------------------------------------------------------------------
# 2. decoder_output.json (from Arpit)
# -----------------------------------------------------------------------------
class DecoderOutputContract(BaseModel):
    """
    Contract for decoder_output.json (Arpit: Timing/Carrier Recovery, Demod, Deinterleaving, FEC).
    """
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., description="Semantic contract version")
    capture_id: str = Field(..., min_length=1, description="Unique capture identifier")
    status: DecoderStatus = Field(..., description="Decoder status: ok, failed, or unsupported")
    interleaver_used: str = Field(..., min_length=1, description="Interleaver scheme evaluated")
    fec_used: str = Field(..., min_length=1, description="FEC scheme evaluated (e.g. conv_viterbi_k7, rs_255_223, ldpc)")
    decoded_bits: Union[str, List[int], int] = Field(..., description="Decoded bitstream or bit count")
    crc_status: CrcStatus = Field(..., description="CRC check result: pass, fail, or not_run")
    reencode_ber: Optional[float] = Field(None, ge=0.0, le=1.0, description="Re-encode residual Bit Error Rate")
    failure_reason: Optional[str] = Field(None, description="Explicit failure/unsupported reason")
    evm_percent: Optional[float] = Field(None, ge=0.0, description="Constellation EVM percentage")
    sync_word: Optional[str] = Field(None, description="Detected sync word preamble (hex or identifier)")

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v != CURRENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: expected '{CURRENT_SCHEMA_VERSION}', got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_consistency(self) -> "DecoderOutputContract":
        if self.status == DecoderStatus.FAILED and not self.failure_reason:
            raise ValueError("failure_reason must be provided when status is 'failed'")
        if self.status == DecoderStatus.UNSUPPORTED and not self.failure_reason:
            raise ValueError("failure_reason must be provided when status is 'unsupported'")
        if self.status == DecoderStatus.OK and self.crc_status == CrcStatus.FAIL:
            raise ValueError("Decoder status cannot be 'ok' when crc_status is 'fail'")
        return self


# -----------------------------------------------------------------------------
# 3. classifier_output.json (from Harsh, via adapter)
# -----------------------------------------------------------------------------
class ClassifierOutputContract(BaseModel):
    """
    Contract for classifier_output.json (Harsh: Baseline RF/ML Classifier).
    """
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., description="Semantic contract version")
    capture_id: str = Field(..., min_length=1)
    window_id: Union[str, int] = Field(..., description="Window index or identifier")
    ml_prediction: str = Field(..., min_length=1, description="Top predicted modulation class")
    ml_probabilities: Dict[str, float] = Field(..., description="Probability vector over candidate classes")
    calibrated_probability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Calibrated probability of top class")
    model_version: str = Field(..., min_length=1, description="Model release version tag")
    feature_vector_used: Dict[str, float] = Field(..., description="Feature dictionary fed into model")

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v != CURRENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: expected '{CURRENT_SCHEMA_VERSION}', got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_prediction_presence(self) -> "ClassifierOutputContract":
        if self.ml_prediction not in self.ml_probabilities:
            raise ValueError(f"ml_prediction '{self.ml_prediction}' must be present in ml_probabilities dictionary")
        return self


# -----------------------------------------------------------------------------
# 4. truth.json (synthetic / golden captures only)
# -----------------------------------------------------------------------------
class TruthContract(BaseModel):
    """
    Contract for truth.json (Ground truth metadata for synthetic and golden benchmarks).
    """
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., description="Semantic contract version")
    modulation: str = Field(..., min_length=1, description="True modulation label")
    sps: float = Field(..., gt=0.0, description="Samples per symbol")
    roll_off: float = Field(..., ge=0.0, le=1.0, description="Pulse-shaping filter roll-off factor")
    snr_db: float = Field(..., description="True simulated SNR in dB")
    cfo_hz: float = Field(..., description="Carrier Frequency Offset injected in Hz")
    phase: float = Field(..., description="Initial carrier phase in radians")
    interleaver: str = Field(..., description="Ground truth interleaver scheme")
    fec: str = Field(..., description="Ground truth FEC scheme")
    timing_bits: Union[str, List[int], int] = Field(..., description="Ground truth transmitted bits or length")
    source_hash: str = Field(..., min_length=1, description="SHA256 checksum of ground truth generator")

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v != CURRENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: expected '{CURRENT_SCHEMA_VERSION}', got '{v}'")
        return v


# -----------------------------------------------------------------------------
# 5. result.json (final Archit output)
# -----------------------------------------------------------------------------
class HypothesisItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modulation: str
    interleaver: str
    fec: str


class AlternateHypothesisItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modulation: str
    interleaver: str
    fec: str
    prior_score: float = Field(..., ge=0.0, le=1.0)
    verification_score: float = Field(..., ge=0.0, le=1.0)
    total_score: float = Field(..., ge=0.0, le=1.0)
    status: str = Field(..., description="EVALUATED, PRUNED, or UNSUPPORTED")
    rejection_reason: Optional[str] = None


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., min_length=1)
    hypothesis_id: Optional[str] = None
    source: str = Field(..., min_length=1)
    check_name: str = Field(..., min_length=1)
    status: EvidenceStatus
    value: Any = None
    numeric_value: Optional[float] = None
    normalized_value: Optional[float] = None
    threshold: Optional[float] = None
    provenance: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    explanation: str = Field(..., min_length=1)
    failure_reason: Optional[str] = None


class ProvenanceBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_hash: str = Field(..., min_length=1, description="Checksum of input capture or analysis file")
    seed: int = Field(..., description="Deterministic RNG seed")
    software_version: str = Field(..., min_length=1, description="SpectralQ software release tag")
    generated_at: str = Field(..., min_length=1, description="ISO-8601 UTC timestamp")


class ResultContract(BaseModel):
    """
    Final output contract (result.json) produced by Archit's decision layer.
    """
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(..., description="Semantic contract version")
    capture_id: str = Field(..., min_length=1)
    source_mode: SourceMode
    ladder_level: LadderLevel
    top_hypothesis: HypothesisItem
    alternate_hypotheses: List[AlternateHypothesisItem] = Field(default_factory=list)
    ml_prediction: str = Field(..., min_length=1)
    ml_probability: float = Field(..., ge=0.0, le=1.0)
    calibrated_ml_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    rule_prediction: str = Field(..., min_length=1)
    rule_ml_agreement: bool
    rule_ml_penalty: float = Field(..., ge=0.0, le=1.0)
    cross_window_agreement: float = Field(..., ge=0.0, le=1.0)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    failed_checks: List[str] = Field(default_factory=list)
    unavailable_checks: List[str] = Field(default_factory=list)
    final_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_version: str = Field(..., min_length=1)
    unknown: bool
    unknown_reason: Optional[str] = None
    provenance: ProvenanceBlock
    capability_available: Optional[bool] = Field(None, description="Whether live DSP capability was available")

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v != CURRENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: expected '{CURRENT_SCHEMA_VERSION}', got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_unknown_consistency(self) -> "ResultContract":
        if self.unknown and not self.unknown_reason:
            raise ValueError("unknown_reason must be provided when unknown is True")
        return self


# -----------------------------------------------------------------------------
# Explicit Non-Coercive Validation Helpers
# -----------------------------------------------------------------------------
def validate_analysis_dict(data: Dict[str, Any]) -> AnalysisContract:
    return AnalysisContract.model_validate(data)


def validate_decoder_output_dict(data: Dict[str, Any]) -> DecoderOutputContract:
    return DecoderOutputContract.model_validate(data)


def validate_classifier_output_dict(data: Dict[str, Any]) -> ClassifierOutputContract:
    return ClassifierOutputContract.model_validate(data)


def validate_truth_dict(data: Dict[str, Any]) -> TruthContract:
    return TruthContract.model_validate(data)


def validate_result_dict(data: Dict[str, Any]) -> ResultContract:
    return ResultContract.model_validate(data)
