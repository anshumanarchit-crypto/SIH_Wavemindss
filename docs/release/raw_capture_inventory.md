# SpectralQ — Raw Capture Inventory

**Generated:** 2026-09-28T23:19:30+05:30  
**Phase:** 8 — Raw Capture Discovery & Sample Auditing

---

## 1. Epistemic Rule on Raw Captures

> [!IMPORTANT]
> **Zero Telemetry Assumption:** The existence of a JSON telemetry file (`analysis.json`, `result.json`) does **NOT** imply that raw IQ samples are present. When raw samples (`.cf32`, `.iq`, `.wav`) are absent, the Signal Observatory renders genuine `RAW VISUALIZATION UNAVAILABLE` notices. No synthetic waveforms or Gaussian noise are ever fabricated in production mode.

---

## 2. Discovered Raw RF Captures

| Capture Path | Type | File Size | SHA-256 Digest | Complex Samples | Sampling Rate | Center Freq | Metadata Source | Visualization Supported? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `data/official/sinchana/golden/G1_QPSK_uncoded.cf32` | CF32 | 131,072 B | `e2becef449e81ea4...` | 16,384 | 100,000 Hz | N/A | Companion `G1_QPSK_uncoded.truth.json` | **YES (Actual Baseband)** |
| `data/official/sinchana/golden/G2_BPSK_conv_block.cf32` | CF32 | 34,816 B | `e8648923f8f1c9b1...` | 4,352 | 100,000 Hz | N/A | Companion `G2_BPSK_conv_block.truth.json` | **YES (Actual Baseband)** |
| `data/official/sinchana/golden/G3_8PSK_RS_diagonal.cf32` | CF32 | 43,520 B | `97b154c3e557a49e...` | 5,440 | 100,000 Hz | N/A | Companion `G3_8PSK_RS_diagonal.truth.json` | **YES (Actual Baseband)** |
| `data/official/sinchana/golden/G4_16QAM_LDPC_pseudorandom.cf32` | CF32 | 1,536 B | `f468df6c1a95ea7c...` | 192 | 100,000 Hz | N/A | Companion `G4_16QAM_LDPC_pseudorandom.truth.json` | **YES (Actual Baseband)** |
| `data/official/sinchana/golden/G5_2FSK_RS_Conv_interleaved.cf32` | CF32 | 265,728 B | `b69f616917d79c6e...` | 33,216 | 100,000 Hz | N/A | Companion `G5_2FSK_RS_Conv_interleaved.truth.json` | **YES (Actual Baseband)** |
| `data/official/sinchana/golden/G5_2FSK_uncoded.cf32` | CF32 | 262,144 B | `234a8390be4a60bf...` | 32,768 | 100,000 Hz | N/A | Companion `G5_2FSK_uncoded.truth.json` | **YES (Actual Baseband)** |
| `data/official/sinchana/golden/G6_BPSK_conv_interleaved.cf32` | CF32 | 35,072 B | `e2d39c7370b33bc5...` | 4,384 | 100,000 Hz | N/A | Companion `G6_BPSK_conv_interleaved.truth.json` | **YES (Actual Baseband)** |
| `data/official/sinchana/golden/G7_QPSK_conv_near_threshold.cf32` | CF32 | 16,768 B | `3dd4a0dd37d29de2...` | 2,096 | 100,000 Hz | N/A | Companion `G7_QPSK_conv_near_threshold.truth.json` | **YES (Actual Baseband)** |
| `data/synthetic/16qam_snr22db.iq` | IQ | 8,448 B | `1060ae294f06ebe8...` | 1,056 | 100,000 Hz | N/A | Companion `16qam_snr22db.json` | **YES (Actual Baseband)** |
| `data/synthetic/16qam_snr22db.wav` | WAV | 8,506 B | `7f659fe5b6a0d6c4...` | 1,056 | 100,000 Hz | N/A | WAV RIFF Header (2 channels, 32-bit float) | **YES (Actual Baseband)** |
| `data/synthetic/2fsk_snr18db.iq` | IQ | 40,704 B | `26e24dda2f144d33...` | 5,088 | 100,000 Hz | N/A | Companion `2fsk_snr18db.json` | **YES (Actual Baseband)** |
| `data/synthetic/2fsk_snr18db.wav` | WAV | 40,762 B | `e3b1164af3eeb149...` | 5,088 | 100,000 Hz | N/A | WAV RIFF Header (2 channels, 32-bit float) | **YES (Actual Baseband)** |
| `data/synthetic/bpsk_fec_viterbi.iq` | IQ | 44,928 B | `6b027418b27c1956...` | 5,616 | 100,000 Hz | N/A | Companion `bpsk_fec_viterbi.json` | **YES (Actual Baseband)** |
| `data/synthetic/bpsk_fec_viterbi.wav` | WAV | 44,986 B | `05a6b8c1bdf427d6...` | 5,616 | 100,000 Hz | N/A | WAV RIFF Header (2 channels, 32-bit float) | **YES (Actual Baseband)** |
| `data/synthetic/bpsk_snr20db_clean.iq` | IQ | 19,904 B | `a79aec9a610d4952...` | 2,488 | 100,000 Hz | N/A | Companion `bpsk_snr20db_clean.json` | **YES (Actual Baseband)** |
| `data/synthetic/bpsk_snr20db_clean.wav` | WAV | 19,962 B | `9fc5401ab7c91a1a...` | 2,488 | 100,000 Hz | N/A | WAV RIFF Header (2 channels, 32-bit float) | **YES (Actual Baseband)** |
| `data/synthetic/qpsk_low_snr5db.iq` | IQ | 13,120 B | `a22bd38e29f44a06...` | 1,640 | 100,000 Hz | N/A | Companion `qpsk_low_snr5db.json` | **YES (Actual Baseband)** |
| `data/synthetic/qpsk_low_snr5db.wav` | WAV | 13,178 B | `b815b15b1b31f68f...` | 1,640 | 100,000 Hz | N/A | WAV RIFF Header (2 channels, 32-bit float) | **YES (Actual Baseband)** |
| `data/synthetic/qpsk_snr15db_cfo.iq` | IQ | 12,864 B | `a174a31b9b03e190...` | 1,608 | 100,000 Hz | N/A | Companion `qpsk_snr15db_cfo.json` | **YES (Actual Baseband)** |
| `data/synthetic/qpsk_snr15db_cfo.wav` | WAV | 12,922 B | `88bd2ee83f95aa1f...` | 1,608 | 100,000 Hz | N/A | WAV RIFF Header (2 channels, 32-bit float) | **YES (Actual Baseband)** |

---

## 3. Real Recorded Captures (Telemetry Replay)

The following benchmark datasets contain comprehensive telemetry JSON (`analysis.json`, `result.json`, `decoder_output.json`) but no raw baseband binary file in the repository tree. They execute in verified **REPLAY** mode:

1. `data/real/meteor_m2_lrpt/` (Meteor-M2 LRPT 72 kBaud QPSK)
2. `data/real/noaa19_apt/` (NOAA-19 APT 4.16 kHz FM/AM subcarrier)
3. `data/real/unverified_ism_2400/` (Unverified 2.4 GHz ISM burst)

For these three captures, the physical signal charts display explicit **`⚠️ RAW VISUALIZATION UNAVAILABLE`** panels, upholding the absolute Zero Fake Data rule.
