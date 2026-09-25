# analysis.json Schema Documentation

**Owner:** Sinchana (Stages 1–4: Ingest, Burst Detection, Blind Estimation, Feature Extraction)  
**Consumer:** Harsh (Stage 5 Classifier), Archit (Decision Layer)  
**Schema Version:** `1.0.0`

---

## 1. Overview
The `analysis.json` contract captures the complete output of the front-end DSP pipeline. It formalizes burst identification, sampling rate provenance, parameter estimations with statistical confidence intervals, and higher-order cumulant/cluster feature extractions.

---

## 2. Field Specifications

| Field | Type | Description | Allowed Values / Constraints |
| :--- | :--- | :--- | :--- |
| `schema_version` | `string` | Semantic contract version | Must strictly match `"1.0.0"` |
| `capture_id` | `string` | Unique identifier of the ingested signal | Non-empty string |
| `source_mode` | `string` | Operating mode of capture | `"real"`, `"synthetic"`, `"replay"` |
| `fs_hz` | `float` | Ingest sample rate in Hertz | $> 0.0$ |
| `fs_source` | `string` | Method used to determine sample rate | `"header"`, `"user"`, `"inferred"` |
| `bursts` | `array[object]` | Temporal intervals containing signal energy | List of burst objects |
| `estimates` | `object` | Blind parameter estimates with 95% CIs | Keys: `baud`, `cfo`, `bandwidth`, `snr` |
| `features` | `object` | Physical and statistical feature blocks | Blocks: `cumulants`, `cluster`, `evm`, `phase_ambiguity_quality`, `cyclic` |

### Parameter Estimate Object (`estimates.*`)
Each estimate (`baud`, `cfo`, `bandwidth`, `snr`) contains:
- `value` (`float`): Central point estimate.
- `ci_lo` (`float`): Lower bound of 95% confidence interval ($ci\_lo \le ci\_hi$).
- `ci_hi` (`float`): Upper bound of 95% confidence interval ($ci\_hi \ge ci\_lo$).
- `method` (`string`): Algorithm name (e.g., `"M2M4"`, `"cyclostationary"`, `"fft_energy"`).

### Cumulants Block (`features.cumulants`)
Normalized higher-order cumulants:
- `C20`, `C21`, `C40`, `C42`, `C60`, `C63`, `C80` (`float`)

### Cluster Block (`features.cluster`)
Constellation cluster metrics:
- `count` (`integer`): Estimated constellation points ($1 \le count \le 256$).
- `silhouette` (`float`): Clustering silhouette score ($-1.0 \le s \le 1.0$).
- `intra_var` (`float`): Mean intra-cluster variance ($\ge 0.0$).
- `inter_dist` (`float`): Mean Euclidean inter-cluster separation ($\ge 0.0$).

---

## 3. Strict Invariants
- `end_ms` $\ge$ `start_ms` for every burst.
- `ci_lo` $\le$ `ci_hi` for every parameter estimate.
- Extra fields are strictly forbidden (`extra="forbid"`).
- Types are non-coercive (`strict=True`).
