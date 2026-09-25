"""
Golden Test Bench Execution Runner for SpectralQ Phase 10.

Runs each golden case (G1-G10) and real case (R1-R3) through the SpectralQ decision engine,
recording detailed metrics, provenance, evidence ledgers, and pass/fail against ground truth.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from spectralq.bench.golden_cases import (
    GoldenCaseDefinition,
    get_all_golden_cases,
    build_case_inputs,
)
from spectralq.pipeline.runner import run, PipelineResult
from spectralq.contracts.schemas import LadderLevel


@dataclass
class GoldenCaseResult:
    case_id: str
    name: str
    source_mode: str
    true_modulation: Optional[str]
    predicted_modulation: str
    final_confidence: float
    unknown_state: bool
    unknown_reason: Optional[str]
    ladder_level: str
    hypothesis_rank: Optional[int]
    full_evidence: List[Dict[str, Any]]
    rule_prediction: str
    ml_prediction: str
    rule_ml_agreement: bool
    pass_fail: str  # "PASS", "FAIL", "SKIPPED"
    runtime_sec: float
    upstream_status: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "source_mode": self.source_mode,
            "true_modulation": self.true_modulation,
            "predicted_modulation": self.predicted_modulation,
            "final_confidence": round(self.final_confidence, 4),
            "unknown_state": self.unknown_state,
            "unknown_reason": self.unknown_reason,
            "ladder_level": self.ladder_level,
            "hypothesis_rank": self.hypothesis_rank,
            "full_evidence": self.full_evidence,
            "rule_prediction": self.rule_prediction,
            "ml_prediction": self.ml_prediction,
            "rule_ml_agreement": self.rule_ml_agreement,
            "pass_fail": self.pass_fail,
            "runtime_sec": round(self.runtime_sec, 4),
            "upstream_status": self.upstream_status,
            "notes": self.notes,
        }


class GoldenBenchRunner:
    """
    Executes all golden and real test cases against the SpectralQ engine.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def run_all(self) -> List[GoldenCaseResult]:
        cases = get_all_golden_cases()
        results: List[GoldenCaseResult] = []

        for c in cases:
            res = self.run_single_case(c)
            results.append(res)

        return results

    def run_single_case(self, case_def: GoldenCaseDefinition) -> GoldenCaseResult:
        if case_def.upstream_status == "SKIPPED":
            return GoldenCaseResult(
                case_id=case_def.case_id,
                name=case_def.name,
                source_mode=case_def.source_mode.value,
                true_modulation=case_def.true_modulation,
                predicted_modulation="N/A",
                final_confidence=0.0,
                unknown_state=False,
                unknown_reason=None,
                ladder_level="N/A",
                hypothesis_rank=None,
                full_evidence=[],
                rule_prediction="N/A",
                ml_prediction="N/A",
                rule_ml_agreement=False,
                pass_fail="SKIPPED",
                runtime_sec=0.0,
                upstream_status=case_def.upstream_status,
                notes=case_def.skip_reason or "Case skipped.",
            )

        analysis, decoder_output = build_case_inputs(case_def)
        capture_virtual_path = f"bench/{case_def.case_id}_{case_def.source_mode.value}.cf32"

        t_start = time.perf_counter()
        pipeline_res = run(
            capture_path=capture_virtual_path,
            seed=self.seed,
            mode="stub" if case_def.source_mode.value == "stub" else "auto",
            analysis_override=analysis,
            decoder_override=decoder_output,
        )
        t_elapsed = time.perf_counter() - t_start

        res_contract = pipeline_res.result

        # Determine true hypothesis rank
        hypo_rank: Optional[int] = None
        if case_def.true_modulation:
            if res_contract.top_hypothesis.modulation == case_def.true_modulation:
                hypo_rank = 1
            else:
                for idx, alt in enumerate(res_contract.alternate_hypotheses, start=2):
                    if alt.modulation == case_def.true_modulation:
                        hypo_rank = idx
                        break

        # Pass / Fail criteria against ground truth
        if case_def.case_id in ("G7", "G10"):
            # UNKNOWN behavior validation: G7 and G10 MUST return UNKNOWN
            if res_contract.unknown:
                pass_fail = "PASS"
            else:
                pass_fail = "FAIL"
        else:
            # Positive identification validation
            if (
                res_contract.top_hypothesis.modulation == case_def.true_modulation
                and not res_contract.unknown
            ):
                pass_fail = "PASS"
            else:
                pass_fail = "FAIL"

        evidence_dicts = [ev.model_dump() for ev in res_contract.evidence]

        return GoldenCaseResult(
            case_id=case_def.case_id,
            name=case_def.name,
            source_mode=case_def.source_mode.value,
            true_modulation=case_def.true_modulation,
            predicted_modulation=res_contract.top_hypothesis.modulation,
            final_confidence=res_contract.final_confidence,
            unknown_state=res_contract.unknown,
            unknown_reason=res_contract.unknown_reason,
            ladder_level=res_contract.ladder_level.value,
            hypothesis_rank=hypo_rank,
            full_evidence=evidence_dicts,
            rule_prediction=res_contract.rule_prediction,
            ml_prediction=res_contract.ml_prediction,
            rule_ml_agreement=res_contract.rule_ml_agreement,
            pass_fail=pass_fail,
            runtime_sec=t_elapsed,
            upstream_status=case_def.upstream_status,
            notes=case_def.description,
        )


def run_golden_bench(seed: int = 42) -> List[GoldenCaseResult]:
    """Convenience helper to run golden bench."""
    runner = GoldenBenchRunner(seed=seed)
    return runner.run_all()
