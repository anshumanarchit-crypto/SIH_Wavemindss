# Baseline Snapshot Before Final Repair & Validation

**Captured At:** 2026-10-03T11:03:00+05:30  
**Git Branch at Snapshot:** `feat/final-spectralq-release`  
**Git Commit at Snapshot:** `51ea87b remove(guided_demo): completely delete demo mode - remove toggle, banner, all imports and session state logic`  
**Remotes:**
- `origin`: `https://github.com/anshumanarchit-crypto/machine-learning-SIH.git`
- `waveminds`: `https://github.com/anshumanarchit-crypto/SIH_Wavemindss.git`

---

## 1. Environment & Runtime Versions
- **Operating System:** Windows (win32)
- **Python Version:** 3.13.7 (tags/v3.13.7:bcee1c3, Aug 14 2025, 14:15:11) [MSC v.1944 64 bit (AMD64)]
- **Streamlit Version:** 1.55.0
- **NumPy Version:** 2.2.6
- **SciPy Version:** 1.17.1
- **Scikit-Learn Version:** 1.8.0
- **Octave Status:** Not installed / not in system PATH
- **Native LDPC C-extension / pyldpc:** Module `ldpc` not installed
- **Trained Model Artifact:** `models/baseline_rf.joblib` present (11,768,236 bytes)

---

## 2. Test Execution Baseline

### Full Suite (`pytest -q`)
- **Total Tests Collected:** 240
- **Passed:** 239
- **Failed:** 0
- **Skipped:** 1 (`tests/test_spectralq_extended_suite.py::TestQuantizationConsistency::test_float_vs_quantized_agreement_rate` due to `run_pipeline_quantized()` not wired)
- **Warnings:** 10 RuntimeWarnings in `test_adversarial_suite.py::TestFMalformedInput` (invalid value encountered in subtract, reduce, power during inf/single-value edge case inputs)

### Frontend Tests (`test_himanshu_gui.py` & `test_production_ui_v2.py`)
- **Total Tests Collected:** 26
- **Passed:** 26
- **Failed:** 0
- **Duration:** 14.81s

### Test File Breakdown
| Test File | Count | Baseline Status |
| :--- | :--- | :--- |
| `tests/test_adversarial_suite.py` | 58 | 58 Passed |
| `tests/test_contracts.py` | 25 | 25 Passed |
| `tests/test_golden_modulation_regression.py` | 4 | 4 Passed |
| `tests/test_himanshu_gui.py` | 15 | 15 Passed |
| `tests/test_phase10_bench.py` | 6 | 6 Passed |
| `tests/test_phase11_real_integration.py` | 10 | 10 Passed |
| `tests/test_phase2_pipeline.py` | 9 | 9 Passed |
| `tests/test_phase3_hypothesis.py` | 7 | 7 Passed |
| `tests/test_phase4_evidence.py` | 11 | 11 Passed |
| `tests/test_phase5_ml_n5.py` | 8 | 8 Passed |
| `tests/test_phase6_confidence.py` | 8 | 8 Passed |
| `tests/test_phase7_calibration.py` | 5 | 5 Passed |
| `tests/test_phase8_unknown.py` | 5 | 5 Passed |
| `tests/test_phase9_replay.py` | 7 | 7 Passed |
| `tests/test_production_ui_v2.py` | 11 | 11 Passed |
| `tests/test_sample_captures_decoder_regression.py` | 22 | 22 Passed |
| `tests/test_spectralq_extended_suite.py` | 29 | 28 Passed, 1 Skipped |
| **Total** | **240** | **239 Passed, 1 Skipped** |

---

## 3. Pre-Repair Real Defects & Fragilities Identified
Even though 239 tests pass, audit of the codebase reveals major systemic weaknesses identified in the problem statement:

1. **Extended Suite uses Stub Mode**: `test_spectralq_extended_suite.py` calls `_pipeline_run(..., mode="stub")` in its adapter rather than real production execution.
2. **CLI Test uses Stub Mode**: `TestRealCLIInvocation.CLI_CMD` explicitly specifies `--mode stub`.
3. **Golden Schemes / Truth Shortcuts**: Checking where `golden_schemes`, `truth.json`, and expected modulation shortcuts might exist in production and decoder paths.
4. **CRC and Re-Encode Semantics**: Ensuring Barker/sync detection does not imply CRC success without genuine CRC-16 calculation, and re-encode BER is computed from actual re-encoding and bit alignment.
5. **LDPC Truthful Resolution**: Discrepancies where LDPC is unsupported yet may have claimed CRC PASS or BER 0 in legacy handoffs.
6. **Cross-Layer Disagreements**: Handling and surfacing ML vs Rule vs Decoder conflicts honestly rather than silently hiding them.
7. **File Ingest & Provenance**: Ensuring .WAV, .IQ, .CF32 properly determine sample rate without hardcoded hidden defaults.
8. **Real Visualizations**: Ensuring all charts in production use actual IQ samples, FFT PSD, real waterfalls, eye diagrams, and burst envelopes.
