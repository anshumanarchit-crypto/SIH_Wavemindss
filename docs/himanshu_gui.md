# SpectralQ GUI Architecture & User Interface Documentation

**Role:** Himanshu (Streamlit GUI, Visualization, Evidence-Bundle Presentation)  
**Task PS:** SIH26147 (NTRO) — SpectralQ  
**Release Tag:** `v1.0.0`  
**Status:** Production Ready  

---

## 1. Absolute Epistemic Boundary & Philosophy

SpectralQ is an **evidence-first blind signal intelligence system**. The Streamlit GUI (`app.py`, `ui/`) is **strictly a presentation and visualization view** of precomputed or orchestrator-emitted scientific evidence.

### What the GUI DOES:
- Strictly ingests and validates frozen contracts:
  - `result.json` (`ResultContract` v1.0.0-FROZEN)
  - `analysis.json` (`AnalysisContract`)
  - `decoder_output.json` (`DecoderOutputContract`)
  - `classifier_output.json` (`ClassifierOutputContract`)
- Renders an interactive 10-stage pipeline stepper.
- Visualizes time-domain waveforms, power spectral density (PSD), constellation diagrams, and burst activity timelines with explicit downsampling labels.
- Preserves the **UNKNOWN** state as a first-class citizen (abstains when evidence is insufficient or conflicting; never fabricates a guess).
- Preserves **UNSUPPORTED** states for unbuilt algorithms (e.g., LDPC) without converting them to failures or hiding them.
- Provides dynamic case exploration across Golden cases (G1-G10), real satellite captures (Meteor-M2, NOAA-19, ISM 2400), and custom fixtures.
- Generates SigMF-compliant metadata and provides discrete downloads for evidence bundle inspection.

### What the GUI NEVER Does:
- **Zero DSP logic:** Does not calculate FFT, M2M4 SNR, carrier frequency offsets, or timing recovery.
- **Zero classification mathematics:** Does not train models or run ML inference directly.
- **Zero confidence formulas:** Never computes or recalculates confidence scores from BER or feature weights.
- **Zero decoder logic:** Does not run Viterbi decoding, Reed-Solomon decoding, or deinterleaving.

---

## 2. Directory Architecture

```
sihkaamwala/
├── app.py                      # Main Streamlit application entry point
├── ui/
│   ├── __init__.py
│   ├── adapters/               # Contract-to-viewmodel translation (strictly non-coercive)
│   │   ├── __init__.py
│   │   ├── result_adapter.py   # ResultContract -> NormalizedResult
│   │   ├── analysis_adapter.py # AnalysisContract -> NormalizedAnalysis
│   │   ├── decoder_adapter.py  # DecoderOutputContract -> NormalizedDecoder
│   │   └── evidence_adapter.py # Categorization & contradiction aggregation
│   ├── loaders/                # Dynamic discovery & filesystem artifact loaders
│   │   ├── __init__.py
│   │   ├── case_discovery.py   # Dynamically scans bench/report.json, data/real/, etc.
│   │   └── artifact_loader.py  # JSON artifact loading & schema validation
│   ├── components/             # Reusable UI presentation widgets
│   │   ├── __init__.py
│   │   ├── header.py           # Application title, capture metadata, SHA-256
│   │   ├── unknown_banner.py   # Prominent UNKNOWN abstention callout
│   │   ├── summary_cards.py    # 8 canonical metric cards with provenance & CI
│   │   ├── pipeline_stepper.py # 10-stage interactive pipeline tracker
│   │   ├── modulation_card.py  # Modulation & AMC/ML consensus panel
│   │   ├── decoder_card.py     # Demodulation, FEC & BER panel
│   │   ├── bitstream_card.py   # Frame boundary & bitstream structure
│   │   ├── evidence_ledger.py  # Expandable evidence audit ledger
│   │   ├── forensics_card.py   # Physical capture parameters & endianness
│   │   └── bundle_exporter.py  # SigMF metadata & evidence downloads
│   ├── charts/                 # Signal visualization helpers
│   │   ├── __init__.py
│   │   └── signal_plots.py     # Waveform, PSD, Constellation, Burst timeline
│   ├── state/                  # Session state isolation
│   │   ├── __init__.py
│   │   └── session_state.py    # Tracks active case, tabs, and replay mode
│   └── styles/                 # Custom aerospace telemetry styling
│       ├── __init__.py
│       └── theme.py            # High-contrast dark engineering theme
└── tests/
    └── test_himanshu_gui.py    # Comprehensive 15-test GUI verification suite
```

---

## 3. UI Workspaces & Pages

1. **Header & Metadata Bar:**
   - Displays Capture ID, Execution Mode (`REPLAY`, `REAL`, `SYNTHETIC`), Ladder Level (`L1` to `L5`), Input SHA-256 hash, and ISO-8601 UTC timestamp.
2. **First-Class UNKNOWN Banner:**
   - Activated whenever `result.unknown == True`. Highlights the exact scientific abstention reasons (e.g. low SNR floor, rule/ML disagreement) and affirms that no unsupported guess was made.
3. **8 Canonical Telemetry Summary Cards:**
   - Modulation Scheme, Symbol Rate (Baud), Carrier Frequency Offset (CFO), Occupied Bandwidth, Estimated SNR, FEC, Interleaver Scheme, and Decision Confidence.
   - Shows value, units, source, status (`PASS`, `ESTIMATED`, `UNSUPPORTED`), and confidence interval bounds $[ci_{lo}, ci_{hi}]$.
4. **10-Stage Pipeline Traversal:**
   - Stages: Ingest $\rightarrow$ Forensics $\rightarrow$ Bursts $\rightarrow$ DSP Estimation $\rightarrow$ Modulation $\rightarrow$ Demodulation $\rightarrow$ FEC $\rightarrow$ Bitstream $\rightarrow$ Evidence Ledger $\rightarrow$ Decision.
   - Per-stage execution status (`LIVE`, `REPLAY`, `STUB`, `PASS`, `FAIL`, `UNSUPPORTED`).
5. **Interactive Telemetry Tabs:**
   - **Signal & Spectrogram:** Time-domain IQ waveform, PSD, constellation scatter, and burst activity timeline.
   - **Modulation & Consensus:** Harsh's RandomForest vs Archit's deterministic AMC consensus, calibrated probabilities, and candidate hypotheses rankings.
   - **Decoder & Bitstream:** Arpit's demodulation status, FEC scheme, interleaver, re-encode residual BER, CRC syndrome check, and physical frame boundaries (Preamble / Payload / CRC).
   - **Evidence Ledger:** Searchable, categorized table of all evidence ledger checks (`PASS`, `FAIL`, `UNAVAILABLE`, `NOT_RUN`, `CONFLICT`).
   - **Ingest Forensics:** Physical I/Q format, endianness, sampling rate source, center frequency, and cryptographic SHA-256 provenance.
   - **Evidence Bundle Export:** Generates SigMF metadata and provides one-click downloads for `result.json`, `analysis.json`, `decoder_output.json`, and `.sigmf-meta`. If PDF exporter is unbuilt, explicitly notes "PDF exporter unavailable" per contract.

---

## 4. Replay Mode & Dynamic Case Discovery

The GUI strictly distinguishes **LIVE** execution from **REPLAY** mode.
- In **Replay Mode**, previously generated and verified artifacts are loaded from disk (`bench/report.json`, `data/real/`, `data/golden/`).
- The case explorer dynamically discovers all available cases:
  - **G1-G10:** Golden Benchmark suite (uncoded, convolutional, RS, LDPC unsupported, near-threshold SNR, pure noise).
  - **R1-R3 / Real Captures:** NOAA-19 APT, Meteor-M2 LRPT, and Unverified ISM 2400.
  - **Test Fixtures:** Synthetic clean and impaired test vectors.
- Future benchmark cases (G11+) placed in standard directories are discovered automatically without modifying GUI code.

---

## 5. Running the Application

### Prerequisites:
```bash
pip install -e .
pip install streamlit
```

### Launch GUI:
```bash
streamlit run app.py
```

### Run GUI Automated Test Suite:
```bash
python -m pytest tests/test_himanshu_gui.py
```
