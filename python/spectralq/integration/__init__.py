"""
SpectralQ External Component Integration & N5 Consensus Module.
"""

from spectralq.integration.classifier_adapter import (
    ClassifierAdapter,
    CANONICAL_FEATURE_NAMES,
    extract_features_from_analysis,
)
from spectralq.integration.rule_config import (
    RuleThresholdConfig,
    DEFAULT_RULE_CONFIG,
)
from spectralq.integration.rule_classifier import (
    RuleBasedClassifier,
    RuleClassificationResult,
)
from spectralq.integration.n5_fusion import (
    N5FusionResult,
    evaluate_n5_consensus,
    DISAGREEMENT_PENALTY_WEIGHT,
)
from spectralq.integration.cross_window import (
    CrossWindowReport,
    WindowClassification,
    evaluate_cross_window,
)
from spectralq.integration.team_adapters import (
    IntegrationError,
    FeatureCompatibilityError,
    SinchanaContractError,
    ArpitContractError,
    consume_sinchana_analysis,
    consume_arpit_decoder_output,
    consume_harsh_classifier_output,
    validate_harsh_feature_compatibility,
    run_real_team_pipeline,
)

__all__ = [
    "ClassifierAdapter",
    "CANONICAL_FEATURE_NAMES",
    "extract_features_from_analysis",
    "RuleThresholdConfig",
    "DEFAULT_RULE_CONFIG",
    "RuleBasedClassifier",
    "RuleClassificationResult",
    "N5FusionResult",
    "evaluate_n5_consensus",
    "DISAGREEMENT_PENALTY_WEIGHT",
    "CrossWindowReport",
    "WindowClassification",
    "evaluate_cross_window",
    "IntegrationError",
    "FeatureCompatibilityError",
    "SinchanaContractError",
    "ArpitContractError",
    "consume_sinchana_analysis",
    "consume_arpit_decoder_output",
    "consume_harsh_classifier_output",
    "validate_harsh_feature_compatibility",
    "run_real_team_pipeline",
]
