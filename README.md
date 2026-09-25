# SpectralQ: Evidence-First Decision & Integration Layer

**SIH 2026 — Problem Statement SIH26147 (NTRO)**  
**Owner / Author:** Archit (Integration, Contracts, Pipeline Orchestration, Hypothesis Engine, Evidence Ledger, N5 Hybrid ID, N2 Confidence, UNKNOWN Fallback, Replay Engine)

---

## 1. System Architecture & Team Boundaries

SpectralQ implements an offline, evidence-first, deterministic decision layer for blind signal intelligence and modulation characterisation.

```
RAW .IQ / .wav
    -> 1. Ingest + Forensics        (Sinchana)
    -> 2. Burst Detection            (Sinchana)
    -> 3. Blind Estimation           (Sinchana)
    -> 4. Feature Extraction         (Sinchana)
    -> capture.cf32 + analysis.json
    -> 5. Classifier                 (Harsh, integrated by Archit)
    -> 6. Demodulation               (Arpit)
    -> 7. Hypothesis Engine          (Archit)
    -> 8. Evidence Ledger + N2 Conf  (Archit)
    -> 9. Bitstream Intelligence     (Arpit)
    -> 10. Streamlit GUI             (Himanshu, strictly consumes result.json)
```

### Team Interface Contracts
- **Sinchana (Stages 1–4):** Produces `AnalysisContract` containing blind estimation parameters, normalized cumulants ($C_{20} \dots C_{80}$), $M_2M_4$ SNR, EVM, and sub-window cluster metrics.
- **Harsh (Stage 5):** Trains baseline `RandomForestClassifier` on scalar statistical features; integrated via `ClassifierAdapter`.
- **Arpit (Stages 6 & 9):** Performs timing recovery, demodulation, and FEC decoding; outputs `DecoderVerificationContract`.
- **Archit (Stages 7 & 8):** Orchestrates pipeline, evaluates N5 rule-vs-ML consensus, searches modulation/FEC hypotheses, calculates deterministic ladder levels (`L1`–`L5`), fuses multi-evidence confidence, and enforces `UNKNOWN` fallback.
- **Himanshu (Stage 10):** Streamlit GUI consumes `result.json` as read-only. Zero decision or confidence logic resides in the GUI.

---

## 2. ML & Decision Engine Architecture

### Signal-Derived Features ONLY
SpectralQ uses strictly physical, statistical signal-derived features (never raw pixels, CNNs, or deep learning models):
- **Higher-Order Cumulants:** $C_{20}, C_{21}, C_{40}, C_{42}, C_{60}, C_{63}, C_{80}$
- **Noise & Quality:** $M_2M_4$ estimated SNR (dB), Error Vector Magnitude (EVM), Phase Ambiguity Resolution Quality
- **Constellation Clustering:** Cluster count, silhouette score, intra/inter-cluster distance, sub-window cluster stability
- **Envelope & Phase:** Normalized envelope variance (FSK discrimination), phase angle entropy

### N5 Hybrid Modulation Identification
Both the analytic rule path and ML probability path run independently and are preserved in full:
$$\text{Consensus Check} = (\text{Rule Prediction} \stackrel{?}{=} \text{ML Prediction})$$
Disagreement is treated as active evidence of ambiguity and strictly penalizes confidence down to $[0.05, 0.40]$.

### N2 Computed Confidence Fusion
Confidence is computed via a multi-evidence logistic regression mapping:
$$z = w_0 + w_{\text{ML}} P_{\text{ML, cal}} + w_{\text{N5}} S_{\text{N5}} + w_{\text{win}} S_{\text{window}} + w_{\text{verif}} S_{\text{verif}} - w_{\text{EVM}} \text{EVM}_{\text{norm}} + w_{\text{SNR}} \text{SNR}_{\text{norm}}$$
$$\text{Confidence} = \frac{1}{1 + e^{-z}} \in [0.0, 1.0]$$

*Hardcoded constants (e.g. 95%) or uncalibrated pass-through probabilities are strictly forbidden. Note: Synthetic calibration is validated via held-out instance sweeps (ECE 0.0908), while full operational calibration is strictly held pending over-the-air field RF data.*

### Deterministic Evidence Ladder (`ladder_level`)
Computed purely from genuine, verified stage data availability:
- **`L1` (Detected):** Ingest and signal energy burst detected.
- **`L2` (Characterised):** Blind estimation parameters, SNR, and cumulants valid.
- **`L3` (Demodulated, Internally Consistent):** Carrier/timing locked, EVM bounded, symbols generated.
- **`L4` (Structure Verified):** Frame sync detected AND (CRC valid OR low re-encode BER residual).
- **`L5` (Independently Cross-Checked):** `L4` verified + high cross-window consistency ($\ge 0.80$) + N5 Rule/ML agreement.

### Operational Gatekeeping (`UNKNOWN` Fallback)
If confidence falls below operational threshold ($T = 0.60$), SNR $< 1.0$ dB, cross-window drift is severe, or N5 conflict is unresolved, SpectralQ asserts `UNKNOWN` with a structured reason code (e.g. `CONFIDENCE_BELOW_THRESHOLD`, `N5_CONFLICT_UNRESOLVED`, `CROSS_WINDOW_INSTABILITY`).

---

## 3. Installation & Quickstart

### Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- NumPy, SciPy, scikit-learn, Pydantic v2, Matplotlib, pytest

### Setup & Clone
```bash
# Clone the repository
git clone https://github.com/anshumanarchit-crypto/machine-learning-SIH.git
cd machine-learning-SIH

# Install SpectralQ package in editable mode
pip install -e .
```

### Running SpectralQ Pipeline
```bash
# Process a capture analysis file in auto mode
python -m spectralq.cli analyze fixtures/qpsk_verified.json --mode auto --output result.json

# Process in explicit stub mode
python -m spectralq.cli analyze fixtures/qpsk_verified.json --mode stub --output result.json

# Replay Mode with deterministic cache and fixed RNG seed
python -m spectralq.cli analyze fixtures/qpsk_verified.json --mode replay --seed 42 --output result.json
```

---

## 4. Verification & Calibration

### Running Test Suite
```bash
pytest tests/ -v
```

### Generating Test Fixtures
```bash
python scripts/generate_fixtures.py
```

### Training & Serializing Baseline Classifier
```bash
python scripts/train_baseline_rf.py
```

### Running Statistical Calibration Evaluation
Evaluates Expected Calibration Error (ECE), Brier Score, and produces reliability diagrams on held-out validation samples:
```bash
python scripts/run_calibration_eval.py
```
Outputs are saved to `reports/calibration_reliability_diagram.png` and `reports/calibration_report.json`.

---

## 5. GNU Octave Integration Rule
If `octave-cli` and Octave DSP scripts are present in the environment, the bridge communicates via CLI/JSON handoff. If unavailable, `OctaveBridge` explicitly returns `capability_unavailable: True` and records the status in the evidence ledger audit trail. DSP capabilities are never faked.
