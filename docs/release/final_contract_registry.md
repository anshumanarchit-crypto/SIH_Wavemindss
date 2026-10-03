# SpectralQ — Final Data Contract Registry

**Generated:** 2026-09-28T23:15:00+05:30  
**Phase:** 6 — Canonical Data Contracts Freeze

---

## 1. Contract Overview & Principles

Every inter-module boundary in SpectralQ is strictly validated using typed schemas. All downstream consumers access upstream data through validated schemas or normalized adapters.

| # | Contract Name | Producer | Primary Consumer | Validation Class / Schema |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Capture/Input Contract** | Ingest Forensics (`core.io` / `forensics`) | DSP & Pipeline | `SignalData` / `SignalInputContract` |
| **2** | **Analysis Contract** | Sinchana Blind DSP (`core.features`) | ML & Classifier | `AnalysisContract` / `NormalizedAnalysis` |
| **3** | **Classifier Output Contract** | Harsh RF Classifier (`pipeline_classifier`) | Hypothesis Engine | `ClassifierOutputContract` |
| **4** | **Decoder Output Contract** | Arpit Decoder (`core.fec` / `decoder_api`) | Hypothesis & Evidence | `DecoderOutputContract` / `NormalizedDecoder` |
| **5** | **Bitstream Intelligence Contract**| Arpit Bitstream Analyzer (`bitintel`) | Decoder Workspace | `BitstreamIntelligenceContract` |
| **6** | **Evidence Item Contract** | Archit Evidence Ledger (`evidence.ledger`) | Hypothesis Engine & GUI | `EvidenceItem` / `NormalizedEvidence` |
| **7** | **Hypothesis Contract** | Archit Hypothesis Engine (`hypothesis.engine`)| Confidence Engine & GUI | `HypothesisCandidate` / `NormalizedHypothesis` |
| **8** | **Confidence Contract** | Archit Confidence Engine (`confidence.engine`)| Result Generator & GUI | `ConfidenceOutput` |
| **9** | **Final Result Contract** | Archit Pipeline Runner (`pipeline.runner`) | Streamlit GUI (`app.py`) | `ResultContract` / `NormalizedResult` |
| **10**| **Provenance Contract** | Cryptographic Digest (`core.io` / `pipeline`) | Evidence Bundle & GUI | `ProvenanceRecord` |
| **11**| **Visualization Artifact Contract** | Himanshu Extractor (`visualization.extractor`)| Plotly Signal Plots | `ObservatoryArtifacts` |

---

## 2. Detailed Contract Specifications

### 1. Capture / Input Contract (`SignalData`)
- **Producer:** `core.io.load_iq` / `python.spectralq.forensics.iq_loader`
- **Consumer:** DSP Feature Extractor, Visualizer
- **Required Fields:**
  - `samples`: `numpy.ndarray` (`complex64`, `float32`, or `int16`)
  - `sample_rate`: `float` (sampling rate in Hz; must be > 0.0 or `None` if awaiting user input)
  - `source_path`: `str` (absolute or relative path of raw file)
  - `source_format`: `str` (`"cf32"`, `"iq"`, `"wav"`, `"raw_binary"`)
- **Optional Fields:** `center_freq`, `metadata` (`dict`), `warnings` (`list[dict]`)
- **Validation Rules:** Negative or zero sample rates raise `ValueError`. Non-complex samples must have `is_complex=False`.

### 2. Analysis Contract (`AnalysisContract`)
- **Producer:** Sinchana Blind DSP (`core.features` / `python.spectralq.features.iq_extractor`)
- **Consumer:** Harsh RF Classifier, Archit Hypothesis Engine, Himanshu Observatory
- **Required Fields:**
  - `schema_version`: `"1.0.0"`
  - `capture_id`: `str`
  - `source_mode`: `SourceMode` (`"REAL"`, `"SYNTHETIC"`, `"REPLAY"`, `"STUB"`)
  - `fs_hz`: `float` (> 0)
  - `fs_source`: `str` (`"DETECTED"`, `"HEADER"`, `"USER_PROVIDED"`, `"INFERRED"`, `"REPLAY"`, `"SIMULATION"`, `"UNAVAILABLE"`)
  - `snr`: `Estimate[float]` (with `estimate`, `unit="dB"`, `ci_lo`, `ci_hi`, `method`)
  - `cfo`: `Estimate[float]` (with `estimate`, `unit="Hz"`, `ci_lo`, `ci_hi`, `method`)
  - `baud`: `Estimate[float]` (with `estimate`, `unit="Baud"`, `ci_lo`, `ci_hi`, `method`)
  - `bandwidth`: `Estimate[float]` (with `estimate`, `unit="Hz"`, `ci_lo`, `ci_hi`, `method`)
  - `features`: `FeaturesContract` (`cumulants` dict with `C20`, `C21`, `C40`, `C42`, etc.)

### 3. Classifier Output Contract (`ClassifierOutputContract`)
- **Producer:** Harsh Random Forest Model (`python.spectralq.classifier.pipeline_classifier`)
- **Consumer:** Archit Hypothesis Engine, Himanshu Modulation Workspace
- **Required Fields:**
  - `schema_version`: `"1.0.0"`
  - `capture_id`: `str`
  - `source_mode`: `SourceMode`
  - `predicted_class`: `str` (`"BPSK"`, `"QPSK"`, `"8PSK"`, `"16QAM"`, `"64QAM"`, `"2FSK"`, `"4FSK"`, `"UNKNOWN"`)
  - `probabilities`: `dict[str, float]` (summing to 1.0 within floating point tolerance)
  - `top_probability`: `float` (range `[0.0, 1.0]`)
  - `model_version`: `str`
- **Optional Fields:** `calibrated_probabilities`, `brier_score`, `ece`

### 4. Decoder Output Contract (`DecoderOutputContract`)
- **Producer:** Arpit Decoder Core (`core.fec`, `core.demodulation`, `python.spectralq.decoder_api`)
- **Consumer:** Archit Evidence Engine, Himanshu Decoder Workspace
- **Required Fields:**
  - `schema_version`: `"1.0.0"`
  - `capture_id`: `str`
  - `status`: `str` (`"OK"`, `"FAILED"`, `"UNSUPPORTED"`, `"UNKNOWN"`)
  - `decoded_bits_count`: `int` (>= 0)
- **Optional Fields:**
  - `fec_used`: `str` (`"conv_viterbi_k7"`, `"reed_solomon_255_223"`, `"none"`, etc.)
  - `interleaver_used`: `str` (`"block"`, `"diagonal"`, `"none"`)
  - `crc_status`: `str` (`"PASS"`, `"FAIL"`, `"NOT_RUN"`)
  - `reencode_ber`: `float` (`[0.0, 1.0]`)
  - `evm_percent`: `float`
  - `failure_reason`: `str`
  - `decoded_bits_preview`: `str`

### 5. Final Result Contract (`ResultContract`)
- **Producer:** Archit Integration Runner (`python.spectralq.pipeline.runner`)
- **Consumer:** Himanshu Streamlit GUI, Evidence Bundle Exporter
- **Required Fields:**
  - `schema_version`: `"1.0.0"`
  - `capture_id`: `str`
  - `source_mode`: `SourceMode`
  - `input_hash`: `str` (SHA-256 of raw input)
  - `ladder_level`: `str` (`"L1"`, `"L2"`, `"L3"`, `"L4"`, `"L5"`)
  - `top_hypothesis`: `HypothesisContract`
  - `final_confidence`: `float` (`[0.0, 1.0]`)
  - `rule_ml_agreement`: `bool`
  - `evidence_ledger`: `list[EvidenceItemContract]`
  - `provenance`: `ProvenanceContract`
