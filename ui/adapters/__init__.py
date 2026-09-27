"""
UI Adapters package.
Contains contract-compliant adapters converting backend JSON contracts
into clean view models for the Streamlit GUI.
"""

from ui.adapters.result_adapter import (
    NormalizedResult,
    NormalizedHypothesis,
    NormalizedEvidence,
    ContractValidationError,
    adapt_result,
)
from ui.adapters.analysis_adapter import (
    NormalizedAnalysis,
    NormalizedEstimate,
    NormalizedBurst,
    NormalizedFeatures,
    AnalysisValidationError,
    adapt_analysis,
)
from ui.adapters.decoder_adapter import (
    NormalizedDecoder,
    DecoderValidationError,
    adapt_decoder,
)
from ui.adapters.evidence_adapter import (
    EvidenceSummary,
    summarize_evidence,
    categorize_evidence_item,
)

__all__ = [
    "NormalizedResult",
    "NormalizedHypothesis",
    "NormalizedEvidence",
    "ContractValidationError",
    "adapt_result",
    "NormalizedAnalysis",
    "NormalizedEstimate",
    "NormalizedBurst",
    "NormalizedFeatures",
    "AnalysisValidationError",
    "adapt_analysis",
    "NormalizedDecoder",
    "DecoderValidationError",
    "adapt_decoder",
    "EvidenceSummary",
    "summarize_evidence",
    "categorize_evidence_item",
]
