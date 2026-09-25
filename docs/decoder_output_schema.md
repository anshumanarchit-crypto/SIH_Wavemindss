# decoder_output.json Schema Documentation

**Owner:** Arpit (Stages 6 & 9: Demodulation, Carrier/Timing Recovery, Deinterleaving, FEC Decoding)  
**Consumer:** Archit (Hypothesis Verification & Evidence Ledger)  
**Schema Version:** `1.0.0`

---

## 1. Overview
The `decoder_output.json` contract conveys physical frame structure verification evidence. It details whether timing and carrier synchronization were achieved, whether frame synchronization patterns matched, the CRC validation outcome, and re-encoding residual BER.

---

## 2. Field Specifications

| Field | Type | Description | Constraints / Allowed Values |
| :--- | :--- | :--- | :--- |
| `schema_version` | `string` | Semantic contract version | Strictly `"1.0.0"` |
| `capture_id` | `string` | Capture identifier matching analysis | Non-empty string |
| `status` | `string` | High-level decoding status | `"ok"`, `"failed"`, `"unsupported"` |
| `interleaver_used`| `string` | Interleaving scheme tested | e.g., `"none"`, `"block"`, `"convolutional"` |
| `fec_used` | `string` | FEC scheme tested | e.g., `"conv_viterbi_k7"`, `"rs_255_223"`, `"ldpc"` |
| `decoded_bits` | `string` / `array[int]` / `int` | Decoded bit payload or count | Binary string, integer array, or integer length |
| `crc_status` | `string` | Integrity checksum verification | `"pass"`, `"fail"`, `"not_run"` |
| `reencode_ber` | `float` / `null` | Residual BER after re-encoding | $[0.0, 1.0]$ or `null` |
| `failure_reason` | `string` / `null` | Detailed diagnostic message | Required if status is `"failed"` or `"unsupported"` |

---

## 3. Epistemic Constraints & Invariants
- If `status` is `"unsupported"` (e.g., LDPC requested but unbuilt), `failure_reason` must explicitly state that the scheme is unsupported. Capability must never be fabricated.
- If `status` is `"failed"`, `failure_reason` cannot be null.
- A status of `"ok"` cannot be asserted if `crc_status` is `"fail"`.
