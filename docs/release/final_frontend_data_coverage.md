# SpectralQ — Final Frontend Data Coverage & Contract Mapping Audit

**Corpus / Problem:** SIH26147 (Blind RF Signal Analysis)  
**System:** SpectralQ Autonomous RF Signal Observatory  
**Component:** User Interface (Himanshu GUI) Integration Layer  
**Date:** September 2026  
**Status:** FULLY VERIFIED & INTEGRATED  

---

## 1. Executive Summary

This document certifies that **zero mock, placeholder, or synthetic random data** exists in the production mode of the SpectralQ frontend. Every UI widget, KPI tile, waveform plot, spectral chart, parameter card, evidence ladder item, and forensic inspector component binds directly to validated Pydantic contract schemas emitted by the canonical pipeline stages:
- **Sinchana (DSP & Forensics):** `AnalysisContract`
- **Harsh (AMC Machine Learning):** `ClassifierOutputContract`
- **Archit (Rule AMC, N5 Consensus, Evidence Ladder):** `ResultContract`
- **Arpit (Demodulator & FEC Decoder Engine):** `DecoderOutputContract`

When raw IQ baseband samples are absent (such as in analysis-only JSON handoffs), the UI explicitly and truthfully renders `RAW VISUALIZATION UNAVAILABLE` with diagnostic provenance indicators, maintaining absolute scientific fidelity.

---

## 2. Complete Field-to-Contract Mapping Matrix

| UI Component | Field Displayed | Backend Contract | Schema Source Field | Provenance / Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **Header Status Bar** | Capture ID | `ResultContract` | `capture_id` | Preserved filename stem / content hash |
| | Schema Version | `ResultContract` | `schema_version` | Current semantic version (`1.0.0`) |
| | Source Mode Badge | `ResultContract` | `source_mode` | `real`, `replay`, `synthetic`, or `stub` |
| | Live Status Indicator | `ResultContract` | `capability_available` | Boolean capability flag |
| **Top Decision Banner** | Top Modulation | `ResultContract` | `top_hypothesis.modulation` | N5 Hybrid Consensus Winner |
| | Final Confidence | `ResultContract` | `final_confidence` | Archit N2 Defensible Confidence ($[0.0, 1.0]$) |
| | Confidence Level | `ResultContract` | Derived: `conf >= 0.85` | High / Medium / Low / Abstain |
| | Evidence Ladder Badge | `ResultContract` | `ladder_level` | `L1`, `L2`, `L3`, `L4`, or `L5` tier |
| | Abstention Alert | `ResultContract` | `unknown`, `unknown_reason` | Honest refusal on low confidence/imbalance |
| **Observatory: IQ Waveform** | I/Q Time Domain | Raw Baseband Array | `core.io.load_signal().samples` | Truthful float32 I/Q samples (never fabricated) |
| **Observatory: Spectrum** | PSD (dB/Hz) vs Freq | Raw Baseband Array | Computed Welch Periodogram | Accurate FFT power spectral density |
| **Observatory: Constellation** | Constellation Scatter | Raw Baseband Array | Matched-filtered / sliced IQ | Actual symbol constellation scatter |
| **Physical Estimates** | Baud Rate | `AnalysisContract` | `estimates.baud.value` + CI $[lo, hi]$ | Sinchana cyclic spectrum / cyclic moment |
| | Carrier Frequency Offset | `AnalysisContract` | `estimates.cfo.value` + CI $[lo, hi]$ | Sinchana FFT peak energy offset |
| | Bandwidth | `AnalysisContract` | `estimates.bandwidth.value` + CI $[lo, hi]$ | Sinchana 99% occupied bandwidth |
| | Signal-to-Noise Ratio | `AnalysisContract` | `estimates.snr.value` + CI $[lo, hi]$ | Sinchana M2M4 moments estimator |
| **Features & Cumulants** | 2nd Order Cumulant $C_{20}$ | `AnalysisContract` | `features.cumulants.C20` | Swami & Sadler (2000) magnitude $\|C_{20}\|$ |
| | 4th Order Cumulant $C_{40}$ | `AnalysisContract` | `features.cumulants.C40` | Swami & Sadler (2000) magnitude $\|C_{40}\|$ |
| | 4th Order Cumulant $C_{42}$ | `AnalysisContract` | `features.cumulants.C42` | Real kurtosis moment $C_{42}$ |
| | Error Vector Magnitude | `AnalysisContract` | `features.evm` | Actual mean error vector magnitude |
| | Constellation Clusters | `AnalysisContract` | `features.cluster.count` | KMeans/vectorized cluster estimation |
| | Cluster Silhouette | `AnalysisContract` | `features.cluster.silhouette` | Silhouette separation score |
| **ML & Consensus** | ML Top Prediction | `ClassifierOutputContract` | `ml_prediction` | Harsh Calibrated Random Forest |
| | ML Calibrated Probability | `ClassifierOutputContract` | `calibrated_probability` | Sigmoid-calibrated class probability |
| | Full Class Probabilities | `ClassifierOutputContract` | `ml_probabilities` | 7-way probability distribution |
| | Rule-Based AMC Guess | `ResultContract` | `rule_prediction` | Archit Deterministic Decision Tree |
| | Rule-ML Agreement | `ResultContract` | `rule_ml_agreement` | Agreement flag (disagreement incurs penalty) |
| **Decoder Telemetry** | Decoder Status | `DecoderOutputContract` | `status` | Arpit Viterbi/BCH/RS decoder state |
| | Interleaver Used | `DecoderOutputContract` | `interleaver_used` | Matrix / convolutional / none |
| | FEC Code Used | `DecoderOutputContract` | `fec_used` | Convolutional $r=1/2$, Reed-Solomon, etc. |
| | Decoded Bits Extracted | `DecoderOutputContract` | `decoded_bits` | Integer bit count extracted |
| | CRC Checksum Status | `DecoderOutputContract` | `crc_status` | `PASS`, `FAIL`, or `NOT_RUN` |
| | Re-encoded BER | `DecoderOutputContract` | `reencode_ber` | Bit error rate upon re-encoding |
| **Evidence & Forensics** | Evidence Ledger | `ResultContract` | `evidence` | List of `EvidenceItem` records with checks |
| | Forensic Provenance | `ResultContract` | `provenance.input_hash` | Cryptographic SHA-256 of input capture |
| | Execution Seed | `ResultContract` | `provenance.seed` | Deterministic pseudo-random seed |

---

## 3. Strict Truthfulness Invariants

1. **No Silent Fallback to Synthetic IQ**: If a user loads an analysis-only case (`.json` without companion `.cf32`/`.wav`), the UI displays an explicit warning notice:
   > `RAW VISUALIZATION UNAVAILABLE: Analysis loaded from validated telemetry envelope; no raw IQ samples were supplied with this capture.`
2. **Deterministic Confidence Only**: The confidence score displayed in the KPI tile is never hardcoded (`0.95` or similar), nor is it an unadjusted classifier probability passthrough. It is strictly computed by `ConfidenceEngine.compute_confidence()` as a weighted combination of physical evidence, cross-window agreement, and verification telemetry minus contradiction penalties.
3. **Evidence Ladder Accountability**: The displayed evidence ladder badge (`L1` to `L5`) is strictly evaluated by `compute_ladder_level()` based on verified stage deliverables:
   - **L1 (Detected):** Burst detected, but intervals incomplete.
   - **L2 (Characterised):** Baud, CFO, bandwidth, and SNR estimated with valid 95% confidence intervals.
   - **L3 (Demodulated):** Demodulated to bits with low EVM and zero decoder faults.
   - **L4 (Structured):** Preamble sync word matched and/or CRC checksum verified (`PASS`).
   - **L5 (Cross-Checked):** Independent cross-verification confirmed.
