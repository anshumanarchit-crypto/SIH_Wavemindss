# truth.json Schema Documentation

**Owner:** Synthetic Signal Generator / Test Harness  
**Consumer:** Benchmarking, Calibration Evaluator, Unit/Integration Tests  
**Schema Version:** `1.0.0`

---

## 1. Overview
The `truth.json` contract defines ground-truth transmission parameters for synthetic signal captures and golden test vectors. It is strictly forbidden for real-world field captures.

---

## 2. Field Specifications

| Field | Type | Description | Constraints / Allowed Values |
| :--- | :--- | :--- | :--- |
| `schema_version` | `string` | Semantic contract version | Strictly `"1.0.0"` |
| `modulation` | `string` | True transmitted modulation | e.g. `"BPSK"`, `"QPSK"`, `"16-QAM"`, `"2-FSK"` |
| `sps` | `float` | True samples per symbol | $> 0.0$ |
| `roll_off` | `float` | Pulse-shaping filter excess bandwidth | $[0.0, 1.0]$ |
| `snr_db` | `float` | Simulated AWGN channel SNR in dB | Unbounded real number |
| `cfo_hz` | `float` | Injected Carrier Frequency Offset in Hz | Unbounded real number |
| `phase` | `float` | Carrier initial phase in radians | Unbounded real number |
| `interleaver` | `string` | True interleaving configuration | e.g. `"none"`, `"block"`, `"convolutional"` |
| `fec` | `string` | True Forward Error Correction scheme | e.g. `"none"`, `"conv_viterbi_k7"`, `"rs_255_223"` |
| `timing_bits` | `string` / `array[int]` / `int` | True bitstream pattern or length | Binary string, int array, or int count |
| `source_hash` | `string` | Cryptographic checksum of generator code | Non-empty hash string |
