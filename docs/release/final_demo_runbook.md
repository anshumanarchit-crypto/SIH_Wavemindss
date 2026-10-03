# SpectralQ SIH26147 — Final Evaluator Demo Runbook

**System:** SpectralQ Blind RF Signal Analysis & Intelligence Engine  
**Release Version:** 1.0.0 (Submission-Ready)  
**Host URL:** [http://localhost:8501](http://localhost:8501)

---

## 1. Quick Launch

### 1.1 Web GUI Launch
From the repository root:
```powershell
streamlit run app.py --server.headless true --server.port 8501
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

### 1.2 CLI Direct Analysis
To analyze any RF capture file from the command line:
```powershell
python -m spectralq.cli analyze sample_captures/01_BPSK_clean_20dB.wav --mode live
```

---

## 2. Recommended Evaluator Demonstration Journey

Follow this structured 10-step journey to evaluate the entire pipeline:

### Step 1: Launch Guided Evaluator Tour
- In the left sidebar, click the **🎯 Start Guided Demo** button.
- A tour guidance banner will appear at the top of the interface, providing engineering context and evaluator focus items for each step.

### Step 2: Mission Control (Workspace 1)
- **What to Observe:**
  - Ingest mode (`LIVE` vs `REPLAY` vs `SYNTHETIC`).
  - Top Modulation Hypothesis and Evidence Ladder Level (`L1` to `L5`).
  - Physical parameters: Symbol Baud Rate, CFO in Hz, SNR in dB, Occupied Bandwidth.
  - Final decision confidence score.

### Step 3: Signal Observatory (Workspace 2)
- **What to Observe:**
  - Interactive calibrated **IQ Constellation Plot** showing decision regions and EVM.
  - Power Spectral Density (PSD) and time-frequency **Waterfall Spectrogram**.
  - **Eye Diagram** displaying transition timing apertures.
  - Every extracted parameter displays explicit measurement method and confidence intervals.

### Step 4: Modulation & Feature Space (Workspace 3)
- **What to Observe:**
  - Higher-Order Statistics (HOS): Cumulants $C_{20}, C_{21}, C_{40}, C_{42}, C_{60}, C_{63}, C_{80}$.
  - Comparison between **Deterministic Rule-Based AMC** and **Machine Learning Random Forest AMC**.
  - 7-way class probability distribution with verified feature schema ordering.

### Step 5: Candidate Hypothesis Ranking (Workspace 4)
- **What to Observe:**
  - Multi-stage hypothesis evaluation across $7 \times 5 \times 5 = 175$ candidates.
  - Clear breakdown of why candidates were pruned or accepted based on physical SNR operational floors, demodulation success, and FEC checks.

### Step 6: Decoder & Bitstream Intelligence (Workspace 5)
- **What to Observe:**
  - Demodulation status, Costas loop carrier lock, and Gardner timing convergence.
  - **FEC Engine Telemetry:**
    - Option A Gallager LDPC (96, 3, 963) parity check matrix syndrome ($H \cdot c \equiv 0 \pmod 2$).
    - Reed-Solomon RS(255, 223) corrected symbol counts.
    - Convolutional Viterbi K=7 rate 1/2 traceback.
  - **Honest CRC Semantics:** Emits `NOT_RUN` on continuous unpacketized physical streams, and `PASS`/`FAIL` strictly on verified packet checksums.
  - **True Forward Re-Encode BER:** Re-encodes decoded payload through forward FEC encoder and compares against received symbols.

### Step 7: Evidence Ledger & Safe Abstention (Workspace 6)
- **What to Observe:**
  - Immutable evidence ledger recording status, check name, observed value, and source.
  - In the left sidebar, select **G7 (QPSK near threshold)** or **G10 (pure noise)**.
  - Notice the system safely abstains with `UNKNOWN` and provides a transparent justification rather than hallucinating an answer.

### Step 8: Wideband Multi-Emission Scanner (Workspace 7)
- **What to Observe:**
  - In the sidebar, select workspace **Wideband Scanner**.
  - Run the wideband energy detector on `G8_Wideband_4_emissions.cf32`.
  - Notice autonomous spectral segmentation and per-emission carrier isolation.

### Step 9: Signal Lab & Impairment Simulator (Workspace 8)
- **What to Observe:**
  - Select workspace **Signal Lab / Simulation**.
  - Configure modulation, carrier frequency offset (CFO), timing jitter, IQ imbalance, and AWGN noise.
  - Click **Generate & Run Blind Analysis** to observe real-time pipeline execution with strict simulation truth isolation.

### Step 10: Cryptographic Evidence Export (Workspace 9)
- **What to Observe:**
  - Select workspace **Provenance & Export**.
  - Click **📦 Download Official Evidence Bundle (.zip)**.
  - The system creates `SpectralQ_Evidence_Bundle_<capture_id>.zip`, validates the archive, and provides the download containing all 9 Pydantic contracts, SigMF metadata, plots, and SHA-256 checksum manifest.

---

## 3. Automated Test Suite Execution

Run all test suites to verify integrity:
```powershell
# 1. Run core integrity and regression tests
pytest tests/test_runtime_truth_isolation.py tests/test_golden_modulation_regression.py tests/test_crc_integrity.py tests/test_reencode_integrity.py tests/test_sample_captures_decoder_regression.py -v

# 2. Run fast subset of extended test suite
pytest tests/test_spectralq_extended_suite.py -k "not Fairness and not Calibration" -v
```
