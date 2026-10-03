# SpectralQ — Final System Architecture

**Generated:** 2026-09-28T23:14:45+05:30  
**Phase:** 5 — Canonical Pipeline Architecture

---

## 1. End-to-End Blind RF Signal Analysis Architecture

```
RAW CAPTURE (.cf32, .iq, .wav)
      │
      ▼
INGEST & FORENSICS (Format, endianness, header vs user fs resolution)
      │
      ▼
BURST DETECTION (Energy envelope thresholding, burst boundary segmentation)
      │
      ▼
BLIND DSP ESTIMATION (Baud rate, Carrier Frequency Offset, Occupied Bandwidth, SNR)
      │
      ▼
FEATURE EXTRACTION (Higher-Order Cumulants C40/C42, Kurtosis, Skewness, Cyclic Features)
      │
      ├───────────────────────────────┬───────────────────────────────┐
      │                               │                               │
      ▼                               ▼                               │
RULE-BASED MODULATION AMC       ML CLASSIFIER (Harsh)                 │
(Decision tree thresholds)     (Calibrated Random Forest)             │
      │                               │                               │
      └───────────────────────┬───────┴───────────────────────────────┘
                              ▼
                  CONSENSUS & FUSION STAGE
                              │
                              ▼
                  DEMODULATION (Arpit Core)
                  (BPSK / QPSK / 8-PSK / 16-QAM / 2-FSK symbol slicer)
                              │
                              ▼
                  DEINTERLEAVING (Arpit Core)
                  (Block, Convolutional, Diagonal, Pseudorandom)
                              │
                              ▼
                  FORWARD ERROR CORRECTION (Arpit Core)
                  (Viterbi K=7 Rate 1/2, Reed-Solomon (255,223), LDPC)
                              │
                              ▼
                  BITSTREAM INTELLIGENCE (Arpit Core)
                  (Frame sync, preamble lock, entropy, run lengths, CRC check)
                              │
                              ▼
                  HYPOTHESIS ENGINE (Archit Core)
                  (Candidate generation, multi-stage hypothesis ranking)
                              │
                              ▼
                  EVIDENCE LEDGER (Archit Core)
                  (L1: Detect → L2: Characterize → L3: Demod → L4: FEC → L5: Verify)
                              │
                              ▼
                  CONFIDENCE & ABSTENTION ENGINE (Archit Core)
                  (Evidence-backed confidence scoring, threshold gating)
                              │
                              ▼
                  UNKNOWN / FINAL DECISION LOGIC (Archit Core)
                  (Abstains to UNKNOWN if SNR low, consensus diverges, or FEC fails)
                              │
                              ▼
                  HIMANSHU FRONTEND LAYER (app.py + ui/)
                  (Mission Control, Observatory, Hypotheses, Decoder, Evidence, Export)
                              │
                              ▼
                  EVIDENCE BUNDLE (.zip)
                  (Cryptographic provenance, JSON contracts, SigMF metadata, CSV)
```

---

## 2. Separation of Concerns & Subsystem Ownership

1. **Sinchana (DSP & Capture Ingest):**
   - Pure physical signal estimation.
   - Extracts sample format, sampling rate, burst timing, baud rate, CFO, bandwidth, and SNR.
   - Computes statistical moments and higher-order cumulants (C20, C21, C40, C42).
   - Generates and maintains ground-truth golden datasets (G1–G7).

2. **Harsh (Machine Learning & AMC):**
   - Trains and serves calibrated Random Forest modulation classifiers (`models/baseline_rf.joblib`).
   - Produces raw probability distributions and temperature/Platt calibrated probabilities.
   - Evaluates multiclass Brier scores, reliability diagrams, and expected calibration errors (ECE).

3. **Arpit (Demodulation, De-interleaving, FEC, Bitstream):**
   - Waveform recovery and constellation symbol decision slicing.
   - Matrix deinterleaving (block, convolutional, diagonal).
   - Trellis Viterbi decoding, Reed-Solomon error correction, syndrome calculation, and parity checks.
   - Framing, preamble detection, re-encode BER estimation, and CRC pass/fail verification.

4. **Archit (Hypothesis, Evidence Ledger, Confidence, UNKNOWN):**
   - Aggregates forensic, DSP, ML, and decoder evidence into an immutable ledger.
   - Tracks 5 levels of the Evidence Ladder (L1 through L5).
   - Computes deterministic confidence scores using configurable weight matrices.
   - Formulates the definitive decision, ensuring UNKNOWN is a first-class state upon insufficient evidence.

5. **Himanshu (Frontend, Observatory, UX, Presentation):**
   - Orchestrates the Streamlit user experience across 7 production workspaces.
   - Renders interactive Plotly charts (oscilloscope, spectrum analyzer, constellation, waterfall, eye diagram).
   - Adheres to the strict Zero Fake Data rule: renders honest "UNAVAILABLE" panels instead of fabricating samples.
   - Packages and signs the download-ready Evidence Bundle ZIP.
