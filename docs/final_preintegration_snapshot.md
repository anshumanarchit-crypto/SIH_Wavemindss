# SpectralQ — Pre-Integration Repository Snapshot

**Generated:** 2026-09-28T23:12:00+05:30  
**Phase:** 0 — Repository Safety Baseline

---

## 1. Git State & Provenance

- **Current Branch:** `feat/final-spectralq-integration` (branched from `feat/production-ui-v2`)
- **Base Commit Hash:** `d045a68 feat(ui-observatory): align Signal Observatory with SpectraQ reference dashboard hierarchy and real contract telemetry`
- **Current HEAD:** `66f4978 chore(git): ignore _incoming/, _staging/, and *.zip`
- **Remote Origin:** `https://github.com/anshumanarchit-crypto/machine-learning-SIH.git`
- **Safety Guarantee:** `main` is untouched. Source zip archives are preserved in place.

---

## 2. Environment & Dependencies

- **Python Version:** 3.11.9 (64-bit Windows)
- **Key Installed Packages:**
  - `numpy==2.4.2`
  - `scipy==1.17.1`
  - `scikit-learn==1.8.0`
  - `torch==2.11.0`
  - `streamlit==1.54.0`
  - `plotly==7.1.0`
  - `pytest==9.1.1`
  - `joblib==1.5.3`
  - `spectralq==1.0.0` (installed editable from repository)

---

## 3. Current Test Baseline

- **Test Suite Command:** `python -m pytest`
- **Total Tests Collected:** 214
- **Passed:** 213 passed
- **Skipped:** 1 skipped (`test_pipeline_quantized` pending quantization wiring)
- **Failed:** 0
- **Duration:** ~70 seconds
- **UI Test Suite:** `pytest tests/test_production_ui_v2.py tests/test_himanshu_gui.py` -> 26 passed in 3.92s.

---

## 4. Application & Frontend Entry Points

- **Application / UI Entry Point:** `app.py`
  - Streamlit dashboard running multi-page workspaces: Mission Control, Signal Observatory, Modulation & Hypotheses, Decoder & Bitstream, Evidence & Decision, Provenance & Export, Signal Lab / Simulation.
- **CLI Pipeline Entry Point:** `python/spectralq/cli.py` / `python/spectralq/core/pipeline.py`
- **Classification Service:** `python/spectralq/classifier/service.py` / `python/spectralq/classifier/pipeline_classifier.py`
- **Decoder Service:** `python/spectralq/decoder/` / `python/spectralq/decoder/decoder_api.py`
- **Evidence / Confidence Engine:** `python/spectralq/hypothesis/` / `python/spectralq/confidence/`

---

## 5. Repository Structure (Pre-Integration)

```
sihkaamwala/
├── app.py                      # Production Streamlit UI entry point
├── pyproject.toml              # Build & dependency metadata
├── python/spectralq/           # Core SpectralQ Python package
│   ├── classifier/             # Harsh ML classifier pipeline
│   ├── confidence/             # Confidence & fusion calculation
│   ├── decoder/                # Arpit decoder interfaces
│   ├── dsp/                    # Sinchana blind DSP estimators
│   ├── features/               # Statistical & HOS feature extractors
│   ├── forensics/              # File ingest & format detection
│   ├── hypothesis/             # Archit hypothesis generation & verification
│   ├── simulation/             # Synthetic RF signal generation & impairment
│   └── visualization/          # Decimated plotting & bundle builder
├── ui/                         # Himanshu Streamlit GUI presentation layer
│   ├── adapters/               # Normalized data contract adapters
│   ├── charts/                 # Plotly RF charts (oscilloscope, spectrum, etc.)
│   ├── components/             # Reusable UI workspaces & controls
│   ├── loaders/                # Artifact & capture discovery
│   ├── state/                  # Session state & execution mode management
│   └── styles/                 # Dark/Light CSS design tokens
├── models/                     # Trained RF models (baseline_rf.joblib)
├── data/                       # Golden captures (G1-G7) & real captures
├── tests/                      # Full test suite (214 tests)
├── _incoming/                  # Staging for external zip archives
└── docs/                       # Architecture & integration specifications
```
