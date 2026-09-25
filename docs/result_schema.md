# result.json Schema Documentation

**Owner:** Archit (Integration, Decision Layer, Confidence Fusion, Ladder Level)  
**Consumer:** Himanshu (Streamlit GUI — strictly read-only), External Evaluators  
**Schema Version:** `1.0.0`

---

## 1. Overview
The `result.json` contract represents the authoritative, frozen final output of the SpectralQ pipeline. It embodies the evidence-first principle: no prediction is ever provided without candidates considered, physical rejection reasons, cross-window consistency, and complete provenance.

---

## 2. Field Specifications

| Field | Type | Description | Constraints / Allowed Values |
| :--- | :--- | :--- | :--- |
| `schema_version` | `string` | Semantic contract version | Strictly `"1.0.0"` |
| `capture_id` | `string` | Identifier matching input capture | Non-empty string |
| `source_mode` | `string` | Capture provenance mode | `"real"`, `"synthetic"`, `"replay"` |
| `ladder_level` | `string` | Highest confirmed evidence tier | `"L1"`, `"L2"`, `"L3"`, `"L4"`, `"L5"` |
| `top_hypothesis` | `object` | Best evaluated modulation $\times$ FEC tuple | Object `{modulation, interleaver, fec}` |
| `alternate_hypotheses` | `array[object]` | Ranked alternative candidates with statuses | List of evaluated, pruned, and unsupported candidates |
| `ml_prediction` | `string` | Classifier top predicted label | Modulation string |
| `ml_probability` | `float` | Raw classifier probability | $[0.0, 1.0]$ |
| `calibrated_ml_probability` | `float` / `null` | Platt / Isotonic calibrated probability | $[0.0, 1.0]$ or `null` |
| `rule_prediction` | `string` | Independent rule-based prediction | Modulation string |
| `rule_ml_agreement` | `boolean` | Consensus between rule & ML paths | `true` if identical, `false` otherwise |
| `rule_ml_penalty` | `float` | Penalty applied to confidence on conflict | $[0.0, 1.0]$ |
| `cross_window_agreement` | `float` | Temporal stability score across sub-windows | $[0.0, 1.0]$ |
| `evidence` | `array[object]` | Granular audit trail of individual checks | Array of evidence check records |
| `final_confidence` | `float` | Defensible, fused confidence score | Strictly $[0.0, 1.0]$ |
| `confidence_version` | `string` | Version of confidence fusion formula | e.g. `"n2-logistic-1.0.0"` |
| `unknown` | `boolean` | Fallback flag for low-evidence captures | `true` if below threshold or unresolvable |
| `unknown_reason` | `string` / `null` | Standardized reason code for fallback | Required if `unknown == true` |
| `provenance` | `object` | Execution traceability metadata | `{input_hash, seed, software_version, generated_at}` |

---

## 3. Evidence Ladder (`ladder_level`)
- **`L1` (Detected):** Signal energy burst confirmed.
- **`L2` (Characterised):** Blind estimation, cumulants, SNR, and baud rate valid.
- **`L3` (Demodulated, Consistent):** Constellation resolved, EVM bounded.
- **`L4` (Structure Verified):** Sync detected AND (CRC valid OR re-encode BER $\le 0.05$).
- **`L5` (Independently Cross-Checked):** `L4` verified + cross-window stability ($\ge 0.80$) + N5 agreement.

## 4. Invariants
- If `unknown` is `true`, `unknown_reason` must not be null.
- Final confidence is strictly bounded in $[0.0, 1.0]$ and never hardcoded to 95%.
- Streamlit GUI consumes this contract as read-only; no confidence logic resides in the GUI.
