# SpectralQ Frontend Data Coverage & Epistemic Mapping

## 1. System Overview & Epistemic Architecture
SpectralQ (PS: SIH26147, NTRO) implements an evidence-backed, blind RF signal intelligence and demodulation system. The presentation layer (Role: Himanshu) acts strictly as a **read-only consumer of upstream contracts**.

```
RAW RF CAPTURE (.cf32, .iq, .wav)
      ↓
[Stage 1-4] Sinchana (Forensics, Burst Detection, Blind DSP, CFO, SNR, Baud, BW)
      ↓
[Stage 5-6] Harsh (AMC Classifier, Cumulants, Class Probabilities)
      ↓
[Stage 7-9] Arpit (Blind Demodulator, De-interleaver, Viterbi, Reed-Solomon, Bitstream)
      ↓
[Stage 10]  Archit (Hypothesis Ranking, Evidence Ladder L1-L5, Confidence Engine, UNKNOWN Abstention)
      ↓
=============================================================================
PRODUCTION GUI (Himanshu): 7 Primary Workspaces & Interactive Guided Demo
=============================================================================
```

---

## 2. Teammate Output Mapping to UI Workspaces

### 2.1 Sinchana — Blind DSP & RF Parameter Estimation (Stages 1–4)
Contract: `AnalysisContract` (`analysis.json`)

| Parameter / Estimate | Upstream Source Field | UI Location & Presentation |
| :--- | :--- | :--- |
| **Center Frequency ($f_c$)** | `estimates.cfo` / `fc_hz` | • **Mission Control**: Metric card 1 (`CFO`)<br>• **Signal Observatory**: PSD center marker, physical parameter table |
| **Carrier Frequency Offset (CFO)** | `estimates.cfo.value`, `.ci_lo`, `.ci_hi`, `.method` | • **Mission Control**: Metric card 1 with tooltip<br>• **Modulation & Hypotheses**: Extraction feature table<br>• **Signal Lab**: Ground truth comparison row |
| **Signal-to-Noise Ratio (SNR)** | `estimates.snr.value`, `.ci_lo`, `.ci_hi`, `.method` | • **Mission Control**: Metric card 2 (`SNR`)<br>• **Signal Observatory**: Burst timeline SNR annotations, parameter card<br>• **Evidence Ledger**: `snr_floor_check` |
| **Symbol Rate (Baud)** | `estimates.baud.value`, `.unit` | • **Mission Control**: Metric card 4 (`Baud`)<br>• **Signal Observatory**: Physical parameter card |
| **Occupied Bandwidth** | `estimates.bandwidth.value`, `.unit` | • **Mission Control**: Metric card 5 (`Bandwidth`)<br>• **Signal Observatory**: PSD shaded bandwidth window ($f_c \pm \frac{BW}{2}$) |
| **Burst Boundaries & Intervals** | `bursts[].start_ms`, `.end_ms`, `.power` | • **Signal Observatory**: Interactive Plotly Burst Timeline & Temporal Power Envelope |
| **Higher-Order Cumulants ($C_{40}, C_{42}$)** | `features.cumulants` | • **Modulation & Hypotheses**: Feature extraction table & rule AMC checks |

---

### 2.2 Harsh — Automatic Modulation Classification (Stages 5–6)
Contract: `ClassifierOutputContract` (`classifier_output.json`) & `ResultContract` (`result.json`)

| Metric / Output | Upstream Source Field | UI Location & Presentation |
| :--- | :--- | :--- |
| **Primary Prediction** | `result.ml_prediction` | • **Mission Control**: Executive Decision highlight<br>• **Modulation & Hypotheses**: Consensus comparison column |
| **Raw Model Probability** | `result.ml_probability` | • **Mission Control**: Confidence bar<br>• **Modulation & Hypotheses**: Interactive Plotly horizontal bar distribution |
| **Candidate Distribution** | `classifier.probabilities` / `result.alternate_hypotheses` | • **Modulation & Hypotheses**: Full candidate modulation stack with probability bars |
| **Calibrated Probability** | `result.calibrated_ml_probability` | • **Modulation & Hypotheses**: Metric card 4 & Explain Decision drawer |
| **Cluster & Silhouette Metrics** | `features.cluster_count`, `features.silhouette` | • **Modulation & Hypotheses**: Decision feature table |

---

### 2.3 Arpit — Blind Demodulation, FEC Chain, & Bitstream (Stages 7–9)
Contract: `DecoderOutputContract` (`decoder_output.json`)

| Subsystem / Metric | Upstream Source Field | UI Location & Presentation |
| :--- | :--- | :--- |
| **Demodulator Status** | `decoder.status`, `decoder.decoded_bits_count` | • **Decoder & Bitstream**: Stage 1 diagram block (Active vs Bypass)<br>• **Decoder Summary**: Recovered bit count |
| **De-interleaver Matrix** | `decoder.interleaver_used` | • **Decoder & Bitstream**: Stage 2 diagram block (`BLOCK`, `CONVOLUTIONAL`, `NONE`)<br>• **Frame Structure Tab**: Interleaver configuration |
| **Inner FEC (Viterbi)** | `decoder.fec_used` | • **Decoder & Bitstream**: Stage 3 diagram block (`RATE 1/2 (K=7)` vs `BYPASS`) |
| **Outer FEC (Reed-Solomon)** | `decoder.fec_used` | • **Decoder & Bitstream**: Stage 4 diagram block (`RS(255,223)` vs `BYPASS`) |
| **Frame Sync Word & CRC** | `decoder.crc_status`, `decoder.raw_dict.sync_word` | • **Decoder & Bitstream**: Stage 5 diagram block (`PASS`, `FAIL`, `UNCHECKED`)<br>• **Frame Structure Tab**: Sync preamble & CRC polynomial |
| **Bit Error Rate (BER)** | `decoder.reencode_ber` / `decoder.ber` | • **Mission Control**: Metric card 8 (`BER`)<br>• **Decoder & Bitstream**: Error metrics card (honestly shows `UNAVAILABLE` when null, never fabricates 0.0) |
| **Constellation EVM** | `decoder.raw_dict.evm_percent` | • **Mission Control**: Metric card 3 (`EVM`)<br>• **Signal Observatory**: Constellation diagram title & EVM readout |
| **Bitstream Forensics** | `decoder.decoded_bits_preview`, raw bytes | • **Decoder & Bitstream**: 6-Tab Bitstream Explorer (`Bits`, `Hex Dump`, `Bytes & Entropy`, `Frame Structure`, `Payload Preview`, `Statistics`) |

---

### 2.4 Archit — Evidence Engine, Verification Ladder, & Consensus (Stage 10)
Contract: `ResultContract` (`result.json`)

| Engine Component | Upstream Source Field | UI Location & Presentation |
| :--- | :--- | :--- |
| **Evidence Ladder (L1–L5)** | `result.ladder_level` | • **Mission Control**: Badge & highlight card<br>• **Evidence & Decision**: Full 5-tier hierarchical interactive ladder with criteria |
| **Rule-Based AMC Prediction** | `result.rule_prediction` | • **Mission Control**: Consensus badge<br>• **Modulation & Hypotheses**: Consensus comparison column |
| **Rule vs ML Agreement** | `result.rule_ml_agreement`, `result.rule_ml_penalty` | • **Mission Control**: Executive Consensus badge<br>• **Modulation & Hypotheses**: Agreement status & penalty metric |
| **Evidence Ledger Audit Trail** | `result.evidence[]` (`id`, `source`, `check`, `status`, `explanation`) | • **Evidence & Decision**: Full interactive table with Status filter, Source filter, and live text search |
| **Failed / Skipped Checks** | `result.failed_checks`, `result.unavailable_checks` | • **Evidence & Decision**: Aggregated summary metrics & penalty impact |
| **UNKNOWN Abstention State** | `result.unknown`, `result.unknown_reason` | • **Top Banner**: High-visibility warning banner in Mission Control & Evidence workspaces<br>• **Evidence & Decision**: Detailed diagnosis callout with root cause and resolution guidance |
| **Provenance Audit Trail** | `result.provenance` (`input_hash`, `seed`, `software_version`, `generated_at`) | • **Provenance & Export**: Cryptographic audit section & SigMF metadata |

---

### 2.5 Signal Lab — Synthetic RF Impairment Testbench
Simulation Engine: `spectralq.visualization.simulation`

- **Epistemic Invariant**: Ground truth is used **exclusively for validation display**. Ground truth parameters are **never passed into the analysis pipeline**.
- **Interactive Controls**:
  - Modulation: BPSK, QPSK, 8-PSK, 16-QAM, 2-FSK, 4-FSK
  - SNR: -5 dB to +30 dB
  - Carrier Frequency Offset (CFO): -25 kHz to +25 kHz
  - Channel Impairments: AWGN, Rayleigh fading, Rician fading, Phase Noise (0–15° RMS)
  - Symbol Count: 512, 1024, 2048, 4096 symbols
  - Samples Per Symbol (SPS): 4, 8, 16
- **Validation Matrix**:
  - Side-by-side comparison table showing: Parameter, Ground Truth, Blind Pipeline Estimate, Estimation Error, and Tolerance Evaluation (`PASS` / `WARN` / `FAIL`).

---

## 3. Strict Epistemic Boundaries & Invariants Enforced

1. **Zero Fake Signals Policy**:
   - When raw sample recordings (`.cf32`, `.iq`, `.wav`) are absent, the Signal Observatory **never generates random noise or dummy sine waves**.
   - Instead, it prominently displays `RAW VISUALIZATION UNAVAILABLE` with the verified physical parameters that govern the capture.
2. **Honest BER Reporting**:
   - If ground truth is unavailable or BER is not calculated, the UI displays `UNAVAILABLE` or `N/A`. It never defaults to `0.000` or invents error counts.
3. **No In-UI Computation**:
   - The UI layer contains zero FFT calculations, zero neural network inference, zero Viterbi decoding, zero confidence math. It only formats and visualizes pre-computed contract artifacts.
4. **Official Evidence Bundling**:
   - Downloads a genuine, structured ZIP bundle named `SpectralQ_Evidence_Bundle_<capture_id>.zip` containing `result.json`, `analysis.json`, `decoder_output.json`, `capture.sigmf-meta`, `provenance.json`, `evidence_summary.csv`, and `observatory_artifacts.json`.

---

## 4. Evaluator Walkthrough Guide (Judges)

To demonstrate the full technical credibility of SpectralQ to NTRO evaluators:

1. **Activate Guided Demo Mode**:
   - Toggle `🎯 Guided Demo Mode (Judges)` in the sidebar.
2. **Step 1: Real Capture (Meteor-M2 LRPT)**:
   - Evaluates genuine off-air satellite telemetry.
   - Observe QPSK modulation lock, 72 kBaud rate, Ladder L4/L5, Viterbi + Reed-Solomon decoding.
3. **Step 2: Clean Baseline (G1 QPSK)**:
   - Observe perfect rule-ML AMC consensus, zero penalties, high confidence.
4. **Step 3: Blind CFO Recovery (G2 8-PSK)**:
   - Observe blind 4th-power carrier estimation recovering severe frequency offset.
5. **Step 4: Multipath AMC (G3 16-QAM)**:
   - Inspect Harsh's AMC classifier separating higher-order cumulants in dispersive channels.
6. **Step 5: De-interleaver & Bitstream (G4 FSK)**:
   - Inspect Arpit's de-interleaver resolving bitstream periodicity in the Bitstream Explorer.
7. **Step 6: Abstention & UNKNOWN (G5 Noisy)**:
   - Observe SpectralQ's deliberate refusal to guess under low SNR (1.2 dB), displaying the prominent UNKNOWN banner.
8. **Step 7: Signal Lab Simulation**:
   - Generate custom impaired signals and test blind pipeline estimation against isolated ground truth.
9. **Evidence Export**:
   - Navigate to **Provenance & Export** and download the official evidence bundle ZIP.
