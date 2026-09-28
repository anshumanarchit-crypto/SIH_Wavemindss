# 📡 SpectralQ Raw Signal Test Captures

This directory contains genuine raw RF signal captures in `.wav`, `.cf32`, and `.iq` formats for testing SpectralQ's blind estimation, modulation classification, FEC demodulation, and signal observatory visualization.

---

## 📂 Available Test Signals

| Filename | Format | Ground Truth Modulation | SNR | Sampling Rate ($f_s$) | Special Characteristics |
|---|---|---|---|---|---|
| `01_BPSK_clean_20dB.wav` | Audio / SDR WAV (stereo I/Q) | **BPSK** | 20 dB | 100 kHz | Clean baseline, high SNR |
| `02_QPSK_with_CFO_15dB.wav` | Audio / SDR WAV (stereo I/Q) | **QPSK** | 15 dB | 100 kHz | Carrier Frequency Offset (CFO) present |
| `03_2FSK_satellite_18dB.wav` | Audio / SDR WAV (stereo I/Q) | **2-FSK** | 18 dB | 100 kHz | Frequency Shift Keying (NOAA satellite style) |
| `04_16QAM_high_density_22dB.wav` | Audio / SDR WAV (stereo I/Q) | **16-QAM** | 22 dB | 100 kHz | Multi-level amplitude & phase constellation |
| `05_QPSK_low_snr_5dB.wav` | Audio / SDR WAV (stereo I/Q) | **QPSK** | 5 dB | 100 kHz | Low SNR channel stress test |
| `06_BPSK_conv_viterbi.wav` | Audio / SDR WAV (stereo I/Q) | **BPSK** | 18 dB | 100 kHz | Encoded with Convolutional Code $K=7, r=1/2$ |
| `07_QPSK_uncoded_golden.cf32` | Raw Complex64 binary (`.cf32`) | **QPSK** | 35 dB | 800 kHz | Official Sinchana golden reference $G_1$ |
| `08_BPSK_conv_block.cf32` | Raw Complex64 binary (`.cf32`) | **BPSK** | 15 dB | 800 kHz | Official Sinchana golden reference $G_2$ (Conv + Block) |
| `09_8PSK_RS_diagonal.cf32` | Raw Complex64 binary (`.cf32`) | **8-PSK** | 35 dB | 800 kHz | Official Sinchana golden reference $G_3$ (Reed-Solomon) |
| `10_16QAM_LDPC_pseudo.cf32` | Raw Complex64 binary (`.cf32`) | **16-QAM** | 20 dB | 800 kHz | Official Sinchana golden reference $G_4$ (LDPC) |
| `11_2FSK_concatenated.cf32` | Raw Complex64 binary (`.cf32`) | **2-FSK** | 15 dB | 800 kHz | Official Sinchana golden reference $G_5$ (Concatenated) |
| `12_Pure_AWGN_noise_only.cf32` | Raw Complex64 binary (`.cf32`) | **NOISE ONLY** | < -10 dB | 800 kHz | Pure Gaussian noise (Triggers UNKNOWN abstention) |
| `13_BPSK_raw_int16.iq` | Raw interleaved int16 (`.iq`) | **BPSK** | 20 dB | 100 kHz | Interleaved 16-bit signed integer SDR samples |
| `14_QPSK_with_cfo_int16.iq` | Raw interleaved int16 (`.iq`) | **QPSK** | 15 dB | 100 kHz | Interleaved int16 with carrier offset |
| `15_8PSK_carrier_locked_18dB.wav` | Audio / SDR WAV (stereo I/Q) | **8-PSK** | 18 dB | 100 kHz | 8-ary phase shift keying |

---

## 🧪 How to Test in the SpectralQ Dashboard

### Method 1: Live SDR / File Ingest (Drag & Drop)
1. Open the SpectralQ dashboard at **`http://localhost:8501`**.
2. In the left sidebar under **Ingest Mode**, click **"Live SDR / File Ingest"**.
3. Drag & drop or browse to any file from the `sample_captures/` folder (e.g. `01_BPSK_clean_20dB.wav` or `08_BPSK_conv_block.cf32`).
4. If testing `.wav`: The sampling rate is automatically extracted from the WAV header.
   If testing `.cf32` or `.iq`: Keep the default sampling rate or enter `800000` for `.cf32` / `100000` for `.iq`.
5. Click **"🚀 Analyze Signal via Backend"**.
6. The entire live pipeline executes:
   - **Ingest & Energy Forensics**: File SHA-256 is computed; burst envelope is measured.
   - **Blind DSP Parameter Estimation**: Sinchana's algorithms compute Baud rate, SNR, CFO, and Occupied Bandwidth with 95% confidence intervals.
   - **Feature Extraction**: High-Order Cumulants ($C_{40}, C_{42}, C_{60}$) and constellation metrics are computed.
   - **Modulation AMC**: Harsh's ML model predicts modulation class and output probabilities.
   - **Demodulation & FEC**: Arpit's decoder demodulates symbols and verifies CRC / bitstream errors.
   - **Evidence Engine**: Archit's hypothesis ladder evaluates the candidate against physical rules.
7. Switch between workspaces in the sidebar:
   - **🔭 Signal Observatory**: Inspect the actual time-domain I/Q waveform, Welch Power Spectral Density (PSD) spectrum, constellation scatter, eye diagram, and extracted parameters table.
   - **🎯 Modulation & Hypotheses**: Inspect top hypothesis, alternate candidates, and ML probabilities.
   - **🔓 Decoder & Bitstream**: Inspect decoded bitstream preview, BER, and FEC metadata.
   - **⚖️ Evidence & Decision**: View the Evidence Ledger and ladder level.
   - **📦 Provenance & Export**: Download the official cryptographically hashed Evidence Bundle ZIP.

### Method 2: Replay / Case Explorer
1. In the sidebar, select **"Replay / Case Explorer"**.
2. Select any sample case from the dropdown (e.g., `Sample: 08 BPSK Conv Block (.cf32)` or `G2: BPSK + Conv K=7 + Block Interleave`).
3. Click **"🔄 Load Case Telemetry"**.
4. The dashboard instantly displays all signal plots and parameters from the genuine capture file.
