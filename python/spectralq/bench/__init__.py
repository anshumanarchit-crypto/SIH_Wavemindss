"""
Phase 10: Golden Test Bench & Integration Validation Package for SpectralQ.
"""

from spectralq.bench.golden_cases import (
    GoldenCaseDefinition,
    get_all_golden_cases,
    build_case_inputs,
)
from spectralq.bench.runner import (
    GoldenBenchRunner,
    GoldenCaseResult,
    run_golden_bench,
)
from spectralq.bench.evaluator import (
    ClassifierEvaluator,
    evaluate_classifier_and_confidence,
)
from spectralq.bench.report_generator import (
    generate_bench_report,
)

__all__ = [
    "GoldenCaseDefinition",
    "get_all_golden_cases",
    "build_case_inputs",
    "GoldenBenchRunner",
    "GoldenCaseResult",
    "run_golden_bench",
    "ClassifierEvaluator",
    "evaluate_classifier_and_confidence",
    "generate_bench_report",
]
