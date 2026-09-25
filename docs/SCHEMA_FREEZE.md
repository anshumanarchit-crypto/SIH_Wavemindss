# SpectralQ Schema Freeze: `v1.0.0-FROZEN`

**Status:** FROZEN  
**Release Tag:** `v1.0.0-FROZEN`  
**Effective Date:** 2026-09-25  
**Sign-off:** Archit (System Architect & Decision Layer Lead)  
**Downstream Consumers:** Himanshu (Streamlit UI / Dashboard), Benchmark Evaluation Suite, Automated Regression Tests, Archival Replay Engine  

---

## 1. Schema Immutability Guarantee

Following full end-to-end integration with real outputs from teammates (Sinchana: `analysis.json`, Arpit: `decoder_output.json`, Harsh: `classifier_output.json`), the contract for **`result.json` (`ResultContract`) is formally FROZEN**.

> [!CRITICAL]
> **FIELD IMMUTABILITY POLICY:**
> No field documented herein may be renamed, removed, or changed in type.
> Downstream components (GUI visualization, demo dashboards, automated bench reports) depend strictly on this exact JSON schema.
> Any breaking change to this schema requires a formal project RFC and a major version bump to `v2.0.0`.

---

## 2. Frozen `result.json` Specification

### Top-Level Fields

| Field Name | Type | Mandatory? | Description & Downstream Invariants |
|---|---|---|---|
| `schema_version` | `string` | **Yes** | Semantic version tag. Strictly `"1.0.0"` under this freeze. |
| `capture_id` | `string` | **Yes** | Unique identifier for the evaluated signal capture. |
| `source_mode` | `string` | **Yes** | Ingest source mode: `"real"`, `"synthetic"`, `"replay"`, or `"stub"`. Never silently presented as live. |
| `capability_available` | `boolean` / `null` | Optional | Indicates whether live Octave/SDR hardware capability was online. |
| `ladder_level` | `string` | **Yes** | Deterministic ladder level: `"L1"`, `"L2"`, `"L3"`, `"L4"`, or `"L5"`. |
| `top_hypothesis` | `object` | **Yes** | Top-ranked hypothesis tuple: `{ "modulation": str, "interleaver": str, "fec": str }`. |
| `alternate_hypotheses` | `array[object]` | **Yes** | Ranked alternative hypotheses with prior, physical verification, and rank scores. |
| `ml_prediction` | `string` | **Yes** | Predicted modulation class from Harsh's Random Forest classifier. |
| `ml_probability` | `float` | **Yes** | Raw model probability $[0.0, 1.0]$. Strictly labeled `ml_probability` (never passed straight through as confidence). |
| `calibrated_ml_probability` | `float` / `null` | Optional | Calibrated probability from `CalibratedClassifierCV` (sigmoid scaling). |
| `rule_prediction` | `string` | **Yes** | Deterministic modulation AMC decision tree classification. |
| `rule_ml_agreement` | `boolean` | **Yes** | `true` if Rule AMC agrees with ML classifier, `false` otherwise. |
| `rule_ml_penalty` | `float` | **Yes** | Penalty applied to confidence score when Rule and ML disagree ($0.25$ or $0.0$). |
| `cross_window_agreement` | `float` | **Yes** | Temporal classification stability across sub-windows $[0.0, 1.0]$. |
| `evidence` | `array[object]` | **Yes** | Chronological immutable Evidence Ledger entries supporting the decision. |
| `failed_checks` | `array[string]` | **Yes** | Explicit list of check names that evaluated to `FAIL`. |
| `unavailable_checks` | `array[string]` | **Yes** | Explicit list of checks where upstream data was legitimately absent (`UNAVAILABLE`). |
| `final_confidence` | `float` | **Yes** | Defensible computed confidence $[0.0, 1.0]$ derived from calibrated probability, evidence score, and temporal agreement. |
| `confidence_version` | `string` | **Yes** | Model release tag for the confidence formula (e.g., `"n2-logistic-1.0.0"`). |
| `unknown` | `boolean` | **Yes** | `true` if system abstains due to low confidence ($\theta < 0.80$), SNR floor, or noise; `false` otherwise. |
| `unknown_reason` | `string` / `null` | Optional | Transparent human-readable explanation if `unknown` is `true`. |
| `provenance` | `object` | **Yes** | Run metadata: `{ "input_hash": str, "seed": int, "software_version": str, "generated_at": str }`. |

---

## 3. Sub-Object Schemas

### A. `top_hypothesis`
```json
{
  "modulation": "QPSK",
  "interleaver": "block",
  "fec": "conv_viterbi_k7"
}
```

### B. `alternate_hypotheses` Item
```json
{
  "modulation": "QPSK",
  "interleaver": "none",
  "fec": "ldpc",
  "prior_score": 0.85,
  "verification_score": 0.0,
  "total_score": 0.0,
  "status": "UNSUPPORTED",
  "rejection_reason": "FEC scheme 'LDPC' is unsupported in current release (never fabricated)"
}
```

### C. `evidence` Item
```json
{
  "evidence_id": "EV_CRC_REAL_METEOR_M2_LRPT_72K",
  "hypothesis_id": null,
  "source": "Arpit (Decoder)",
  "check_name": "crc_checksum_check",
  "status": "PASS",
  "value": null,
  "numeric_value": null,
  "normalized_value": null,
  "threshold": null,
  "provenance": null,
  "run_id": "RUN_REAL_REAL_METEOR_42",
  "explanation": "Payload CRC checksum verified with zero syndrome errors",
  "failure_reason": null
}
```

### D. `provenance` Block
```json
{
  "input_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
  "seed": 42,
  "software_version": "1.0.0",
  "generated_at": "2026-09-25T12:00:00.000000+00:00"
}
```

---

## 4. Upstream Integration Contract Invariants

1. **Sinchana (`analysis.json`)**:
   - `fs_source` must be one of `header`, `user`, `inferred`.
   - Parameter uncertainty intervals `[ci_lo, ci_hi]` must satisfy `ci_lo <= ci_hi`.
   - Feature absence is represented by `null` and mapped to `UNAVAILABLE` in the Evidence Ledger (never treated as `0.0` or passing).
2. **Arpit (`decoder_output.json`)**:
   - `status` must be `ok`, `failed`, or `unsupported`.
   - CRC results must be `pass`, `fail`, or `not_run`.
   - Re-encode BER residual is optional $[0.0, 1.0]$ or `null`.
3. **Harsh (`classifier_output.json`)**:
   - Feature vector MUST contain all 15 canonical features in exact deterministic order:
     `["C20", "C21", "C40", "C42", "C60", "C63", "C80", "cluster_count", "silhouette", "intra_var", "inter_dist", "evm", "phase_ambiguity_quality", "snr", "baud"]`.
   - Any mismatch in names, count, or ordering triggers a loud `FeatureCompatibilityError`.

---

## 5. Downstream Integration Guarantee

The SpectralQ team guarantees that this schema is production-stable for the SIH 2026 evaluation. Front-end UIs (Himanshu) and automated judge pipelines can safely consume this exact JSON shape.
