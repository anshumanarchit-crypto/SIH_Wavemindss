# SpectralQ — Source Archive Inventory

**Generated:** 2026-09-28T23:13:00+05:30  
**Phase:** 1 — Discovery & Phase 2 — Classification

---

## 1. Discovered Source Archives

| Attribute | Archive 001 (`SIH-main (3).zip`) | Archive 002 (`machine-learning-SIH-master.zip`) | Archive 003 (`sihkaamwala.zip`) |
| :--- | :--- | :--- | :--- |
| **Path** | `SIH-main (3).zip` | `machine-learning-SIH-master.zip` | `_incoming/sihkaamwala.zip` |
| **Filename** | `SIH-main (3).zip` | `machine-learning-SIH-master.zip` | `sihkaamwala.zip` |
| **Size** | 2,048,316 bytes (1.95 MB) | 1,257,963 bytes (1.20 MB) | 3,305,357 bytes (3.15 MB) |
| **SHA-256** | `9041c23aa75d3332ab000ffcb0e7a52a0f82a8a24e6a01b161c44f677c95b5ef` | `6e6062366a1d9e6d35d32c43330393f2a14a7abf194692141b5457f0147679d2` | `93d63158a77b16ecb0e818b652c43084aa26eab7e835ae64ff6ef8c3d7d5307b` |
| **Total Files** | 197 files | 153 files | 455 files |
| **Top-Level Dir** | `SIH-main/` | `machine-learning-SIH-master/` | `sihkaamwala/` |
| **Presence of `.git`** | Yes (contained git metadata) | Yes (contained git metadata) | Yes (contained git metadata) |
| **`app.py`** | Yes (rudimentary pilot script) | No | Yes (full production GUI entry point) |
| **`ui/`** | No | No | Yes (`components`, `adapters`, `charts`, `styles`, `state`) |
| **`core/`** | Yes (`demodulation`, `fec`, `deinterleave`, `pipeline`, `contracts`) | No | No |
| **`python/spectralq/`**| Yes (`demod.py`, `fec.py`, `decoder_api.py`) | Yes (`calibration`, `confidence`, `hypothesis`, `integration`) | Yes (`features`, `dsp`, `visualization`, `simulation`) |
| **`models/`** | No | Yes (`models/baseline_rf.joblib`) | Yes (`models/baseline_rf.joblib`) |
| **`octave/`** | Yes | Yes | Yes |
| **`data/golden/`** | Yes | Yes | Yes |
| **`data/official/`** | Yes (`data/official/sinchana/golden/` G1-G7 `.cf32`) | No | No |
| **`data/handoff/`** | Yes (`decoder_evidence.json`, reference bits G2-G7) | No | No |
| **`calibration/`** | No | Yes (`calibrator.py`, `metrics.py`, `calibration_object.pkl`) | Yes |
| **Classifier Artifacts**| No | Yes (`baseline_rf.joblib`, `classifier_output.json`) | Yes |
| **Decoder Artifacts** | Yes (`core/fec.py`, `core/demodulation.py`, `core/deinterleave.py`) | Yes (interfaces in hypothesis engine) | Yes (decoder adapter & normalized classes) |
| **Visualization** | Yes (basic `core/visualization.py`) | No | Yes (`python/spectralq/visualization/`, `ui/charts/`) |
| **Frontend Tests** | No | No | Yes (`tests/test_himanshu_gui.py`, `tests/test_production_ui_v2.py`)|

---

## 2. Classification by Content (Structural Fingerprints)

### Archive 001: Source Type A — DSP / Decoder Contribution
- **Identified Contributors:** Sinchana (Official DSP Golden Captures & Validation) + Arpit (Decoder, Demodulation, FEC, De-interleaver)
- **Primary Artifacts:**
  - `core/demodulation.py`, `core/fec.py`, `core/deinterleave.py`, `core/pipeline.py`
  - Real baseband samples: `data/official/sinchana/golden/G1` through `G7` (`.cf32` format)
  - Validation benchmarks: `data/official/sinchana/official_validation_results.json`
  - Decoder evidence: `data/handoff/decoder_evidence.json`
  - Synthetic test capture: `data/synthetic/bpsk_fec_viterbi.iq`, `.wav`, `.json`
  - Decoder APIs: `python/spectralq/decoder_api.py`, `demod.py`, `fec.py`

### Archive 002: Source Type B — Machine Learning / Classifier Contribution
- **Identified Contributors:** Harsh (RF Classifier, Calibration, Reliability) + Archit (Hypothesis Generation, Confidence Fusion Engine)
- **Primary Artifacts:**
  - Trained model: `models/baseline_rf.joblib`
  - Calibration matrix: `bench/calibration_object.pkl`, `bench/calibration_metrics.json`
  - Calibration modules: `python/spectralq/calibration/`
  - Confidence calculation: `python/spectralq/confidence/` (`abstention.py`, `engine.py`, `weights_config.json`)
  - Hypothesis generation: `python/spectralq/hypothesis/` (`candidate.py`, `engine.py`, `registry.py`)
  - Calibration evaluation report: `reports/calibration_reliability_diagram.png`

### Archive 003: Source Type C — Frontend / UI Contribution
- **Identified Contributor:** Himanshu (Streamlit GUI, Visualization Layer, Presentation Contracts)
- **Primary Artifacts:**
  - Streamlit entry point: `app.py`
  - UI subsystem: `ui/components/`, `ui/adapters/`, `ui/charts/`, `ui/state/`, `ui/styles/`
  - Visualization engine: `python/spectralq/visualization/`
  - UI regression test suite: `tests/test_himanshu_gui.py`, `tests/test_production_ui_v2.py`
