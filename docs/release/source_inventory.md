# SpectralQ SIH26147 — Source Material Inventory

**Generated:** 2026-10-03T11:15:00+05:30  
**Phase:** 1 — Inventory Actual Source Material  
**Branch:** `fix/final-release-integrity`

---

## 1. Discovered Source Archives & Checksums

| Archive Filename | Canonical Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `SIH-main (3).zip` | `SIH-main (3).zip` | 2,048,316 | `9041c23aa75d3332ab000ffcb0e7a52a0f82a8a24e6a01b161c44f677c95b5ef` |
| `machine-learning-SIH-master.zip` | `machine-learning-SIH-master.zip` | 1,257,963 | `6e6062366a1d9e6d35d32c43330393f2a14a7abf194692141b5457f0147679d2` |
| `sample_captures.zip` | `sample_captures.zip` | 1,218,272 | `f862c072d6b76b95ca2025c532b7d94b98ac1d099b78dc4f7115f0a5801147e9` |
| `sihkaamwala.zip` | `_incoming/sihkaamwala.zip` | 3,305,357 | `93d63158a77b16ecb0e818b652c43084aa26eab7e835ae64ff6ef8c3d7d5307b` |

---

## 2. Source Classification by Subsystem

### A. DSP & Decoder Subsystem (Sinchana & Arpit)
- **Primary Source Archive:** `SIH-main (3).zip` (staged in `_staging/archive_001`)
- **Key Modules:**
  - `core/demodulation.py`: Constellation demapping, soft slicing, synchronization.
  - `core/fec.py`: Viterbi convolutional decoder (K=7, polynomials 171/133), Reed-Solomon (255,223/239), LDPC interfaces.
  - `core/deinterleave.py`: Matrix block, convolutional, helical, diagonal, and pseudo-random deinterleavers.
  - `core/pipeline.py`: Low-level decoder execution pipeline.
  - `core/contracts.py`: Structured typing for DSP & decoder handoffs.
  - `python/spectralq/demod.py`, `python/spectralq/fec.py`, `python/spectralq/decoder_api.py`.
- **Golden & Reference Captures:**
  - `data/official/sinchana/golden/`: G1 through G10 `.cf32` captures with companion metadata (`.truth.json`).
  - `data/handoff/`: Reference payload bits `bitsG2.txt` through `bitsG7.txt`, plus `decoder_evidence.json`.

### B. Machine Learning, Feature Extraction & Confidence Fusion (Harsh & Archit)
- **Primary Source Archive:** `machine-learning-SIH-master.zip` (staged in `_staging/archive_002`)
- **Key Modules:**
  - `models/baseline_rf.joblib`: 11.7 MB Random Forest classifier trained on HOS (higher-order cumulants $C_{40}, C_{42}, C_{60}, C_{63}, C_{80}$), spectral features, and cyclic moments across BPSK, QPSK, 8PSK, 16QAM, 64QAM, 2FSK, 4FSK.
  - `python/spectralq/features/`: `iq_extractor.py`, `cumulants.py`, `spectral.py`.
  - `python/spectralq/calibration/`: Expected Calibration Error (ECE) measurement, temperature scaling, reliability diagrams.
  - `python/spectralq/confidence/`: Multi-factor confidence fusion engine combining ML posterior, rule AMC, SNR penalty, and cross-window agreement.
  - `python/spectralq/hypothesis/`: Hypothesis generator ranking modulations, interleavers, and FEC schemes based on physics + ML evidence.

### C. Frontend, GUI & Visualization Subsystem (Himanshu)
- **Primary Source Archive:** `_incoming/sihkaamwala.zip` (staged in `_staging/archive_003`)
- **Key Modules:**
  - `app.py`: Streamlit multi-tab application orchestrator.
  - `ui/components/`: Mission Control, Signal Observatory, Modulation Workspace, Decoder Workspace, Evidence Workspace, Provenance, Run Trace, Signal Lab, Wideband Scanner, Validation Center.
  - `ui/adapters/`: Pydantic/contract normalization layer converting raw backend outputs into UI consumable structures.
  - `ui/charts/`: High-performance Plotly charts (IQ constellation, eye diagram, time-domain waveform, PSD, spectrogram waterfall, burst timeline).
  - `ui/state/`: Centralized Streamlit session management.
  - `ui/styles/`: Dual-theme CSS engine (Engineering Dark & Scientific Light).

### D. Captured Benchmark & Demonstration Datasets
- **Source Archive:** `sample_captures.zip`
- **Contents:**
  - 19 standard operational test captures in `.wav`, `.iq` (int16), and `.cf32` (complex64).
  - Impairment profiles: Carrier Frequency Offset (CFO), low SNR (5 dB), convolutional Viterbi coding, Reed-Solomon coding, near-threshold decoding, and CRC corruption.

---

## 3. Duplication & Staging Audit
- `sihkaamwala/` untracked directory in repository root is a direct unpacked mirror of `_incoming/sihkaamwala.zip` created during prior workspace setup.
- Active development root is the top-level repository directory (`c:\Users\arpit\Desktop\sihkaamwala`).
- All code edits and validations must occur strictly in canonical package locations:
  - `python/spectralq/`
  - `core/`
  - `ui/`
  - `tests/`
