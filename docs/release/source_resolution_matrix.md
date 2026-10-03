# SpectralQ — Source Resolution Matrix

**Generated:** 2026-09-28T23:14:30+05:30  
**Phase:** 4 — Multi-Source Conflict Resolution & Canonical Selection

---

## 1. Executive Summary of Sources

- **Source A (`SIH-main`):** Arpit (Decoder, Demodulation, FEC, Interleaver, Bitstream) + Sinchana (Official Golden `.cf32` captures, `.truth.json`, baseline DSP validation).
- **Source B (`machine-learning-SIH-master`):** Harsh (RF Classifier, Calibration, Reliability) + Archit (Hypothesis Generation, Confidence Fusion Engine, Pydantic Schema Registry).
- **Source C (`sihkaamwala`):** Himanshu (Streamlit GUI, Plotly Observatory, Decimated Visualization Layer, UI Adapters, Guided Demo Tour).

---

## 2. Multi-Source Conflict Resolution Matrix

| File / Package | Source A (`SIH-main`) | Source B (`machine-learning-SIH-master`) | Source C (`sihkaamwala`) | Selected Canonical Version | Why | Adapter Required? | Test Required? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`app.py`** | Rudimentary prototype script | None | Full 7-workspace Streamlit UI | **Source C (`sihkaamwala`)** | Provides complete multi-workspace mission control, observatory, evidence ladder, simulation, and export. | No | `test_production_ui_v2.py`, `test_himanshu_gui.py` |
| **`core/`** (`demodulation`, `fec`, `deinterleave`, `contracts`, `pipeline`) | Complete Arpit decoder & DSP implementation | None | None | **Source A (`SIH-main`)** | Genuine decoder algorithms (Viterbi K=7, Reed-Solomon, block/diagonal deinterleaving). | Yes (`decoder_adapter.py` connecting `core` to `NormalizedDecoder`) | `test_fec.py`, `test_demodulation.py`, `test_pipeline.py` |
| **`python/spectralq/decoder_api.py`, `demod.py`, `fec.py`, `interleave.py`, `bitintel.py`** | Production decoder core library | None | Stub/adapter definitions | **Source A (`SIH-main`)** | Complete implementations of decoder subsystem. | Yes (Adapter between Arpit output and Archit Pydantic schema) | `test_demod_integration.py`, `test_bitstream_intelligence.py` |
| **`python/spectralq/calibration/`** | None | Harsh calibration dataset, calibrator, metrics, plotter | Present (identical) | **Source B / C (Merged)** | Calibrated probability engine for RF classifier. | No | `test_phase7_calibration.py` |
| **`python/spectralq/confidence/`** | Basic rule confidence | Archit multi-stage fusion engine + abstention + weights | Present (identical) | **Source B / C (Merged)** | Strict multi-stage confidence scoring and abstention. | No | `test_phase6_confidence.py` |
| **`python/spectralq/hypothesis/`** | Prototype hypothesis list | Archit candidate registry, engine, debug | Present (identical) | **Source B / C (Merged)** | Production hypothesis evaluation and evidence matching. | No | `test_phase3_hypothesis.py` |
| **`python/spectralq/contracts/`** | Early dataclasses in `core/contracts.py` | Pydantic v2 schemas (`AnalysisContract`, `ResultContract`, etc.) | Present (identical) | **Source B / C (Canonical Pydantic)** | Pydantic v2 validation enforced across pipeline boundaries. | Yes (Bridge `core.contracts.SignalData` and `DemodulationResult`) | `test_contracts.py` |
| **`models/baseline_rf.joblib`** | None | Harsh Random Forest model trained on 8 modulation classes | Present (identical) | **Source B / C (Canonical Model)** | Real scikit-learn model pipeline with calibrated feature extraction. | No | `test_classifier_loading` |
| **`data/official/sinchana/golden/`** | Genuine G1–G7 `.cf32` baseband samples + `.truth.json` | None | None | **Source A (`SIH-main`)** | Crucial genuine IQ baseband data required for zero-fake-data physical visualization. | No | `test_official_validation.py` |
| **`data/handoff/decoder_evidence.json`** | Arpit validated handoff bitstreams (G2-G7) | None | None | **Source A (`SIH-main`)** | Ground-truth decoder telemetry for validation benchmarks. | No | `test_phase3_official_handoff.py` |
| **`data/synthetic/`** | Real synthetic `.iq`, `.wav`, `.json` captures | None | None | **Source A (`SIH-main`)** | Real `.wav` and `.iq` files for live file ingestion testing. | No | `test_io.py`, `test_live_ingest` |
| **`ui/`** (`components`, `charts`, `adapters`, `state`, `styles`) | None | None | Himanshu Streamlit UI | **Source C (`sihkaamwala`)** | Only source containing the production UI layer. | No | Full UI test suite |
| **`python/spectralq/visualization/`** | Basic Matplotlib plots in `core/` | None | Decimated Plotly visualizers + Evidence Bundle zip builder | **Source C (`sihkaamwala`)** | High-performance interactive Plotly charts with zero-fake-data fallbacks. | No | `test_visualization.py` |
| **`pyproject.toml` / `requirements.txt`** | Early dependencies | Core ML dependencies | Production dependencies | **Source C + A Union** | Unified dependency set covering ML, Streamlit, Plotly, SciPy, and CommPy. | No | Package installation test |

---

## 3. Integration Strategy

1. **Import Source A Subsystems:**
   - Copy `_staging/archive_001/SIH-main/core/` into repository root `core/`.
   - Copy `_staging/archive_001/SIH-main/python/spectralq/` decoder modules (`fec.py`, `demod.py`, `interleave.py`, `decoder_api.py`, `bitintel.py`, `bitstream.py`, `encode_chain.py`) into `python/spectralq/`.
   - Copy `_staging/archive_001/SIH-main/data/official/` into `data/official/`.
   - Copy `_staging/archive_001/SIH-main/data/handoff/` into `data/handoff/`.
   - Copy `_staging/archive_001/SIH-main/data/synthetic/` into `data/synthetic/`.
   - Copy Source A's unit and golden tests into `tests/arpit_tests/` or `tests/core/` without conflicting with existing tests.
2. **Canonical Contract Bridge:**
   - Connect Arpit's `core.contracts.DemodulationResult` and `decoder_api` output to Archit's `DecoderOutputContract` and Himanshu's `NormalizedDecoder`.
   - Connect Sinchana's `core.io.load_iq` / `SignalData` and `.cf32` / `.wav` loader to Himanshu's `python.spectralq.visualization.extractor`.
3. **Verify Zero Regressions:**
   - Execute all existing 214 tests + newly integrated decoder and official golden tests.
