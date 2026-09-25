# SpectralQ Dataset Directive: Feature Extraction & Training Protocol

**Target Audience:** Machine Learning Engineers (Harsh / Training Team) & System Architects  
**Problem Statement:** PS SIH26147 (NTRO), SIH 2026  
**Module:** Phase 5 — ML Integration & N5 Hybrid Modulation Identification

---

## 1. Ground Truth & Feature Source Directive

> [!CRITICAL]
> **NEVER train directly on pre-extracted feature files from third-party sources.**
> Public datasets provide raw I/Q samples only. None ship pre-extracted cumulant, cluster, or EVM features matching SpectralQ's strict schema (`analysis.json`), and none contain FEC-coded or interleaved digital streams.

### Mandatory Training Feature Protocol
All training and validation feature vectors must be generated using **SpectralQ's own extraction code**:

1. **Synthetic Sweep (Primary Ground Truth)**:
   - Generated through SpectralQ's own forward encoding chain (`data/synthetic/`):
     - Source bits -> FEC encoder (Conv K=7, RS(255,223), Concatenated) -> Interleaver (Block, Convolutional, Diagonal, Pseudo-random) -> Mapper (BPSK, QPSK, 8-PSK, 16-QAM, 64-QAM, 2-FSK, 4-FSK) -> Pulse Shaping (RRC roll-off 0.20 to 0.40, SPS 4 to 16) -> Channel Impairments (SNR 0 dB to 30 dB, CFO -500 Hz to +500 Hz, AWGN, multipath Rayleigh/Rician, phase noise).
   - Features extracted via `spectralq.analysis` / Sinchana's feature extraction pipeline.
   - Ground truth strictly recorded in `truth.json` conforming to `TruthContract`.

2. **External Public Raw I/Q Datasets (Secondary Sanity Check Only)**:
   - Datasets:
     - **RadioML** (RadioML2016.10a, RadioML2018.01A)
     - **TorchSig / Sig53**
     - **Panoradio**
     - **CSPB.ML.2018R2**
   - **Usage Restriction**: Use external raw I/Q strictly by passing the raw I/Q through SpectralQ's ingest and feature extraction pipeline (`Sinchana (Blind Estimation + Feature Extraction)`).
   - These external datasets serve exclusively as out-of-distribution validation and sanity checks to verify that models trained on the synthetic sweep do not overfit to synthetic channel models.

---

## 2. Feature Schema & Ordering Specification

Feature vectors must strictly match the following 15 canonical features in deterministic order:

| Index | Feature Name | Source Block in `analysis.json` | Physical Meaning |
|---|---|---|---|
| 0 | `C20` | `features.cumulants.C20` | 2nd-order cumulant $E[s^2]$ (distinguishes real 1D vs complex 2D) |
| 1 | `C21` | `features.cumulants.C21` | 2nd-order cumulant $E[\|s\|^2]$ (signal power normalization) |
| 2 | `C40` | `features.cumulants.C40` | 4th-order cumulant $Cum(s, s, s, s)$ (separates QPSK from PSK/QAM) |
| 3 | `C42` | `features.cumulants.C42` | 4th-order cumulant $Cum(s, s, s^*, s^*)$ (QAM constellation dispersion) |
| 4 | `C60` | `features.cumulants.C60` | 6th-order cumulant |
| 5 | `C63` | `features.cumulants.C63` | 6th-order mixed cumulant |
| 6 | `C80` | `features.cumulants.C80` | 8th-order cumulant |
| 7 | `cluster_count` | `features.cluster.count` | K-means / DBSCAN estimated constellation cluster count |
| 8 | `silhouette` | `features.cluster.silhouette` | Cluster separation quality $[-1.0, 1.0]$ |
| 9 | `intra_var` | `features.cluster.intra_var` | Intra-cluster variance |
| 10 | `inter_dist` | `features.cluster.inter_dist` | Inter-cluster Euclidean distance |
| 11 | `evm` | `features.evm` | Error Vector Magnitude |
| 12 | `phase_ambiguity_quality` | `features.phase_ambiguity_quality` | Constellation rotational symmetry quality $[0.0, 1.0]$ |
| 13 | `snr` | `estimates.snr.value` | Estimated SNR (dB) |
| 14 | `baud` | `estimates.baud.value` | Estimated symbol rate (Hz) |

---

## 3. Classifier Architecture & Output Invariants

1. **Model Architecture**:
   - Baseline classifier: `scikit-learn.ensemble.RandomForestClassifier`.
   - **No deep learning / CNNs** in the decision integration layer.
2. **Probability Invariant**:
   - Output from `model.predict_proba()` is strictly named `ml_probability`.
   - Under no circumstances may raw `ml_probability` be called "final confidence" or "calibrated confidence". Calibration occurs in Phase 7; confidence fusion occurs in Phase 6.
