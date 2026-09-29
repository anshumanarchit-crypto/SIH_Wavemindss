# 📡 SpectralQ Raw Signal Test Captures Matrix (25 Benchmark Files)

This directory contains 25 genuine raw RF signal captures in `.wav`, `.cf32`, and `.iq` formats designed to thoroughly exercise and verify all pipeline stages across the **Modulation & Hypotheses** and **Decoder & Bitstream** workspaces in SpectralQ.

---

## 📂 Master Signal & Pipeline Stage Architecture Matrix

| # | Filename | Format | Mod | SNR | Sample Rate ($f_s$) | Demod (S1) | De-Intl (S2) | Inner FEC (S3) | Outer FEC (S4) | Frame Sync & CRC (S5) | Primary Test Target / Verification Focus |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **01** | `01_BPSK_clean_20dB.wav` | Stereo WAV | BPSK | 20 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Clean high-SNR baseline; uncoded framed burst |
| **02** | `02_QPSK_with_CFO_15dB.wav` | Stereo WAV | QPSK | 15 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Carrier Frequency Offset (CFO) tracking & lock |
| **03** | `03_2FSK_satellite_18dB.wav` | Stereo WAV | 2-FSK | 18 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | Continuous satellite stream (Rule 9: no false CRC fail) |
| **04** | `04_16QAM_high_density_22dB.wav` | Stereo WAV | 16-QAM | 22 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Multi-level 16-QAM constellation & framing |
| **05** | `05_QPSK_low_snr_5dB.wav` | Stereo WAV | QPSK | 5 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | Low SNR boundary condition; constellation clustering |
| **06** | `06_BPSK_conv_viterbi.wav` | Stereo WAV | BPSK | 18 dB | 100 kHz | **ACTIVE** | BYPASS | **RATE 1/2 (K=7)** | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | CCSDS ASM preamble + Viterbi Rate 1/2 ($K=7$) |
| **07** | `07_QPSK_uncoded_golden.cf32` | Binary CF32 | QPSK | 35 dB | 800 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Official Golden $G_1$: Uncoded baseline reference |
| **08** | `08_BPSK_conv_block.cf32` | Binary CF32 | BPSK | 15 dB | 800 kHz | **ACTIVE** | **BLOCK (16x34)** | **RATE 1/2 (K=7)** | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Official Golden $G_2$: Block de-interleaver + Viterbi |
| **09** | `09_8PSK_RS_diagonal.cf32` | Binary CF32 | 8-PSK | 35 dB | 800 kHz | **ACTIVE** | **DIAGONAL (40x51)** | BYPASS | **RS(255,223)** | <span style="color:green;font-weight:bold;">PASS</span> | Official Golden $G_3$: Diagonal de-interleaver + Outer RS |
| **10** | `10_16QAM_LDPC_pseudo.cf32` | Binary CF32 | 16-QAM | 20 dB | 800 kHz | **ACTIVE** | **PSEUDORANDOM** | BYPASS | **LDPC** | <span style="color:green;font-weight:bold;">PASS</span> | Official Golden $G_4$: Pseudorandom de-intl + LDPC |
| **11** | `11_2FSK_concatenated.cf32` | Binary CF32 | 2-FSK | 15 dB | 800 kHz | **ACTIVE** | **CONV (4x2)** | **CONCAT FEC** | **RS(255,223)** | <span style="color:green;font-weight:bold;">PASS</span> | Official Golden $G_5$: All stages active and passed |
| **12** | `12_Pure_AWGN_noise_only.cf32` | Binary CF32 | NOISE | < -10 dB | 800 kHz | <span style="color:red;font-weight:bold;">UNKNOWN</span> | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | Pure Gaussian noise; triggers Rule 12 abstention banner |
| **13** | `13_BPSK_raw_int16.iq` | Binary IQ | BPSK | 20 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Interleaved int16 signed integer SDR baseline |
| **14** | `14_QPSK_with_cfo_int16.iq` | Binary IQ | QPSK | 15 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Interleaved int16 SDR samples with carrier offset |
| **15** | `15_8PSK_carrier_locked_18dB.wav` | Stereo WAV | 8-PSK | 18 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | Continuous 12,000+ bitstream without false CRC FAIL |
| **16** | `16_BPSK_crc_fail_corrupted.wav` | Stereo WAV | BPSK | 22 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:red;font-weight:bold;">FAIL</span> | **CRC Blocked**: Valid header, intentionally corrupted payload |
| **17** | `17_QPSK_viterbi_crc_fail.wav` | Stereo WAV | QPSK | 18 dB | 100 kHz | **ACTIVE** | BYPASS | **RATE 1/2 (K=7)** | BYPASS | <span style="color:red;font-weight:bold;">FAIL</span> | **Inner FEC Active + CRC Fail**: Burst noise exceeds correction |
| **18** | `18_BPSK_conv_interleaved.cf32` | Binary CF32 | BPSK | 22 dB | 800 kHz | **ACTIVE** | **CONVOLUTIONAL** | **RATE 1/2 (K=7)** | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Official Golden $G_6$: Conv De-interleaver + Viterbi PASS |
| **19** | `19_QPSK_conv_near_threshold.cf32` | Binary CF32 | QPSK | 14 dB | 800 kHz | **ACTIVE** | BYPASS | **RATE 1/2 (K=7)** | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Official Golden $G_7$: Viterbi near threshold, De-intl BYPASS |
| **20** | `20_4FSK_multitone_15dB.wav` | Stereo WAV | 4-FSK | 18 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | M-ary 4-tone continuous FSK demodulation |
| **21** | `21_QPSK_severe_iq_imbalance.iq` | Binary IQ | QPSK | 18 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | Severe hardware distortion: 4 dB gain + 25° phase error |
| **22** | `22_BPSK_cfo_tracking_5kHz.wav` | Stereo WAV | BPSK | 20 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Carrier frequency offset (+5 kHz) tracked and recovered |
| **23** | `23_QPSK_ambiguous_multimodal_8dB.wav` | Stereo WAV | QPSK | 8 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | Multimodal jitter; exercises competitor hypothesis ranking |
| **24** | `24_Degraded_SNR_minus8dB_unknown.cf32` | Binary CF32 | DEGRADED | -8 dB | 800 kHz | <span style="color:red;font-weight:bold;">UNKNOWN</span> | BYPASS | BYPASS | BYPASS | <span style="color:gray;">UNCHECKED</span> | SNR -8 dB below sensitivity; Rule 12 UNKNOWN banner |
| **25** | `25_BPSK_uncoded_plain_frame.iq` | Binary IQ | BPSK | 25 dB | 100 kHz | **ACTIVE** | BYPASS | BYPASS | BYPASS | <span style="color:green;font-weight:bold;">PASS</span> | Plain baseline packet: all FEC/Interleavers bypassed |

---

## 🔍 How Each Pipeline Stage Behaves

### Stage 1: Demodulator
- **ACTIVE (Green Badge)**: Displayed whenever complex baseband samples are synchronized, symbol timing recovered, Costas/PLL carrier locked, and hard bits recovered.
- **UNKNOWN / FAILED (Red / Yellow Badge)**: Triggered when signal SNR is below 0 dB or consists purely of AWGN noise (e.g. `12_Pure_AWGN_noise_only.cf32`, `24_Degraded_SNR_minus8dB_unknown.cf32`).

### Stage 2: De-Interleaver
- **ACTIVE ([SCHEME] Blue Badge)**: Activated when bit-level shuffling is reversed (e.g. `BLOCK (16x34)` on `08`, `DIAGONAL (40x51)` on `09`, `PSEUDORANDOM` on `10`, `CONVOLUTIONAL` on `11` and `18`).
- **BYPASS (Gray Badge)**: Displayed when no interleaver was applied (e.g. `01`, `06`, `07`, `16`, `17`, `19`, `25`).

### Stage 3: Inner FEC (Viterbi / Convolutional)
- **RATE 1/2 (K=7) (Green Badge)**: Active on Rate 1/2 constraint length $K=7$ transmissions (e.g. `06`, `08`, `17`, `18`, `19`).
- **BYPASS (Gray Badge)**: Displayed when no convolutional inner code was applied (e.g. `01`, `07`, `09`, `16`, `22`, `25`).

### Stage 4: Outer FEC (Reed-Solomon / LDPC)
- **RS(255,223) / LDPC (Purple Badge)**: Active on block-coded transmissions (e.g. `09` with RS, `10` with LDPC, `11` with concatenated RS).
- **BYPASS (Gray Badge)**: Displayed when no outer block code was used.

### Stage 5: Frame Synchronization & CRC Check
- **PASS (Green Badge)**: Detected sync marker matches preamble AND computed CRC checksum matches the transmitted CRC field.
- **FAIL (Red Badge - BLOCKED)**: Sync marker found and packet header parsed, but channel errors corrupted the payload or CRC bytes (e.g. `16_BPSK_crc_fail_corrupted.wav` and `17_QPSK_viterbi_crc_fail.wav`).
- **UNCHECKED (Gray Badge)**: Continuous unpacketized streams where no packet framing protocol was present (e.g. NOAA satellite weather streams, continuous tone broadcasts; complies with Rule 9 invariant).

---

## 🧪 Testing in the UI

1. Open **`http://localhost:8501`**.
2. Go to **Live SDR / File Ingest** in the sidebar.
3. Upload any `.wav`, `.iq`, or `.cf32` file from this folder.
   - For `.wav`: Sampling rate is automatically detected.
   - For `.cf32`: Enter `800000` (800 kHz).
   - For `.iq`: Enter `100000` (100 kHz).
4. Click **"🚀 Analyze Signal via Backend"**.
5. Navigate to:
   - **🎯 Modulation & Hypotheses**: Inspect top classified modulation, competitor ranking, and Shannon entropy.
   - **🔓 Decoder & Bitstream**: Inspect the 5-stage architecture diagram, raw bits explorer, hex dump, and payload preview.
