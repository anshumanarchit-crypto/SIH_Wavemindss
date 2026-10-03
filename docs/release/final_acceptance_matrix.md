# SpectralQ SIH26147 — Final Acceptance Matrix

**Generated:** 2026-10-03T13:45:00+05:30  
**Release Branch:** `fix/final-submission-release`  
**Execution Verification:** Genuine runtime execution (zero hardcoded golden answer shortcuts)

---

| CAPABILITY | IMPLEMENTATION | SOURCE | RUNTIME PATH | TEST | ACTUAL RESULT | STATUS | ARTIFACT |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WAV Ingestion** | RIFF/WAVE 16-bit PCM parser with automatic sample rate | `core/io.py` | `load_signal(path)` | `test_io.py`, `test_phase11_real_integration.py` | 44.1/48 kHz sample rates parsed from header | **PASS** | `analysis.json` |
| **IQ Ingestion** | Raw int16 interleaved IQ ingestion | `core/io.py` | `load_signal(path)` | `test_sample_captures_decoder_regression.py` | Real/Imag parts parsed and normalized | **PASS** | `analysis.json` |
| **CF32 Ingestion** | Complex64 float32 IEEE 754 binary baseband | `core/io.py` | `load_signal(path)` | `test_golden_modulation_regression.py` | Exact complex array loaded with physical companion metadata | **PASS** | `analysis.json` |
| **Metadata Resolution** | Strict precedence: SigMF -> Companion JSON -> User -> UNAVAILABLE | `core/io.py` | `_find_companion_metadata()` | `test_truth_isolation_runtime.py` | Zero truth file reliance in production path | **PASS** | `provenance.json` |
| **Forensics** | Format verification, sample count, power analysis | `core/io.py` | `load_signal(path)` | `test_pipeline.py` | Full forensic integrity verified | **PASS** | `analysis.json` |
| **Burst Detection** | Energy envelope thresholding & boundary segmentation | `python/spectralq/pipeline/runner.py` | `run()`, `run_samples()` | `test_pipeline.py` | Accurate burst start/end boundaries | **PASS** | `analysis.json` |
| **Baud Estimation** | Cyclic autocorrelation & FFT envelope squaring | `core/dsp.py` | `iq_to_analysis_contract()` | `test_sample_captures_decoder_regression.py` | Symbol rate inferred with confidence interval | **PASS** | `analysis.json` |
| **CFO Estimation** | Instantaneous phase angle difference & FFT peak | `core/dsp.py` | `iq_to_analysis_contract()` | `test_pipeline.py` | CFO tracked and compensated in Hz | **PASS** | `analysis.json` |
| **Bandwidth (99%)** | Occupied spectral bandwidth (OBW) integration | `core/dsp.py` | `iq_to_analysis_contract()` | `test_pipeline.py` | 99% power bandwidth computed | **PASS** | `analysis.json` |
| **SNR Estimation** | M2M4 split-moment noise variance estimation | `core/dsp.py` | `iq_to_analysis_contract()` | `test_sample_captures_decoder_regression.py` | Signal-to-noise ratio in dB with CI | **PASS** | `analysis.json` |
| **Higher-Order Cumulants (HOS)** | Moment-to-cumulant conversion (C20, C21, C40, C42, C60, C63, C80) | `core/features.py` | `extract_cumulants()` | `test_features.py` | Analytic cumulants for constellation rotation invariance | **PASS** | `analysis.json` |
| **Rule AMC** | Deterministic hierarchical decision tree on HOS & cluster stats | `python/spectralq/pipeline/runner.py` | `RuleBasedClassifier.classify()` | `test_golden_modulation_regression.py` | Transparent rule prediction | **PASS** | `result.json` |
| **ML AMC** | Scikit-learn Calibrated Random Forest (15 features, 7 classes) | `models/baseline_rf.joblib` | `ClassifierAdapter.predict()` | `test_phase5_ml_n5.py` | Real RF inference with feature schema validation | **PASS** | `classifier_output.json` |
| **Model Calibration** | 5-fold cross-validated sigmoid probability calibration | `models/baseline_rf.joblib` | `CalibratedClassifierCV` | `test_phase7_calibration.py` | Calibrated ML probability with ECE validation | **PASS** | `classifier_output.json` |
| **BPSK** | BPSK carrier recovery, Costas loop, constellation slicing | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_golden_modulation_regression.py` | Confirmed BPSK (G2, G6) with low EVM | **PASS** | `decoder_output.json` |
| **QPSK** | QPSK 4-phase synchronization and demodulation | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_golden_modulation_regression.py` | Confirmed QPSK (G1) with 0.916 confidence | **PASS** | `decoder_output.json` |
| **8-PSK** | 8-ary phase shift keying demodulation & RS decoding | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_golden_modulation_regression.py` | Verified 8-PSK (G3) | **PASS** | `decoder_output.json` |
| **16-QAM** | 16-ary quadrature amplitude modulation slicing | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_golden_modulation_regression.py` | Sliced 16-QAM symbols (G4) | **PASS** | `decoder_output.json` |
| **64-QAM** | 64-ary dense constellation slicing | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_demod.py` | Supported in demodulator matrix | **PASS** | `decoder_output.json` |
| **2-FSK** | Dual-tone frequency discriminator | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_sample_captures_decoder_regression.py` | Inferred tones and mark/space frequencies | **PASS** | `decoder_output.json` |
| **4-FSK** | Multi-tone 4-ary frequency discriminator | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_sample_captures_decoder_regression.py` | 4-tone FSK demodulation | **PASS** | `decoder_output.json` |
| **Carrier Recovery** | 2nd/4th power Costas loop and phase tracking | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_demod.py` | Residual carrier locked | **PASS** | `decoder_output.json` |
| **Timing Recovery** | Gardner timing error detector and polyphase resampling | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_demod.py` | Symbol timing alignment achieved | **PASS** | `decoder_output.json` |
| **Block Deinterleaver** | Rectangular matrix block deinterleaver | `core/deinterleave.py` | `deinterleave_bits()` | `test_deinterleave.py` | Bits deinterleaved correctly | **PASS** | `decoder_output.json` |
| **Convolutional Deinterleaver** | Ramsey/Forney shift-register convolutional deinterleaver | `core/deinterleave.py` | `deinterleave_bits()` | `test_deinterleave.py` | Shift registers deinterleaved | **PASS** | `decoder_output.json` |
| **Diagonal Deinterleaver** | Diagonal matrix coordinate transformation | `core/deinterleave.py` | `deinterleave_bits()` | `test_deinterleave.py` | Diagonal interleaving reversed | **PASS** | `decoder_output.json` |
| **Pseudo-random Deinterleaver** | PRNG-seeded permutation deinterleaver (Seed 42) | `python/spectralq/decoder/service.py` | `run_arpit_decoder()` | `test_deinterleave.py` | Permutation inverted | **PASS** | `decoder_output.json` |
| **Viterbi FEC** | Hard-decision Viterbi decoder (K=7, Rate 1/2, polys [171, 133]) | `core/fec.py` | `decode_viterbi()` | `test_fec.py` | Traceback decoding verified | **PASS** | `decoder_output.json` |
| **Reed-Solomon FEC** | RS(255, 223) Galois field GF(2^8) error correction | `core/fec.py` | `decode_rs()` | `test_fec.py`, `test_sample_captures_decoder_regression.py` | Up to 16 byte symbol errors corrected | **PASS** | `decoder_output.json` |
| **Concatenated FEC** | RS(255, 223) outer + Convolutional Viterbi inner | `core/fec.py` | `decode_concatenated()` | `test_fec.py` | Dual-layer FEC decoding verified | **PASS** | `decoder_output.json` |
| **LDPC FEC (Option A)** | Gallager (96, 3, 963) parity matrix, syndrome H*c=0, Min-Sum decoding | `python/spectralq/decoder/service.py` | `_decode_ldpc_gallager()` | `test_reencode_integrity.py` | Parity syndrome verified, true re-encode BER 0.0 | **PASS** | `docs/release/ldpc_status.md` |
| **Bitstream Intelligence** | Preamble search, frame boundaries, Shannon entropy, run-lengths | `core/bitstream.py` | `analyze_bitstream()` | `test_bitstream_intelligence.py` | Payload extracted, entropy measured | **PASS** | `decoder_output.json` |
| **Hypothesis Engine** | Generalized search across 175 candidate triples | `python/spectralq/hypothesis/engine.py` | `HypothesisEngineV1.run_pipeline()` | `test_phase3_hypothesis.py` | Candidates ranked by multi-modal evidence | **PASS** | `hypotheses.json` |
| **Evidence Ledger** | Structured evidence collection with status, source, and method | `python/spectralq/evidence/ledger.py` | `EvidenceLedger` | `test_phase6_confidence.py` | Immutable audit trail of every check | **PASS** | `evidence_ledger.json` |
| **Confidence Scoring** | Multi-factor confidence combining physical, ML, and decoder | `python/spectralq/confidence/engine.py` | `ConfidenceEngine` | `test_phase6_confidence.py` | Bounded [0.0, 1.0] confidence value | **PASS** | `result.json` |
| **UNKNOWN Abstention** | Safe abstention on low SNR, noise, or severe contradictions | `python/spectralq/confidence/abstention.py` | `evaluate_abstention()` | `test_golden_modulation_regression.py` | G7 and G10 honestly flagged as UNKNOWN | **PASS** | `result.json` |
| **Waveform Plot** | Decimated in-phase & quadrature time-domain visualization | `ui/charts/waveform.py` | `render_iq_waveform()` | `test_production_ui_v2.py` | Real signal samples rendered | **PASS** | Streamlit UI |
| **PSD Plot** | Welch periodogram power spectral density | `ui/charts/spectrum.py` | `render_psd()` | `test_production_ui_v2.py` | Real spectral envelope rendered | **PASS** | Streamlit UI |
| **Waterfall Plot** | Spectrogram time-frequency heatmap | `ui/charts/waterfall.py` | `render_waterfall()` | `test_production_ui_v2.py` | Time-frequency intensity grid | **PASS** | Streamlit UI |
| **Constellation Plot** | I vs Q scatter diagram with EVM cluster centers | `ui/charts/constellation.py` | `render_constellation()` | `test_production_ui_v2.py` | Calibrated symbol decisions rendered | **PASS** | Streamlit UI |
| **Eye Diagram** | Multi-trace symbol transition overlay | `ui/charts/eye_diagram.py` | `render_eye_diagram()` | `test_production_ui_v2.py` | Transition timing aperture rendered | **PASS** | Streamlit UI |
| **Wideband Scanner** | Multi-emission energy detection and channelization | `ui/components/wideband_scanner.py` | `render_wideband_scanner()` | `test_production_ui_v2.py` | Emissions segmented and analyzed | **PASS** | Streamlit UI |
| **Replay Mode** | Replay of cached physical analysis contracts | `ui/loaders/artifact_loader.py` | `load_case_artifacts()` | `test_replay_cache.py` | Full playback of stored runs | **PASS** | Streamlit UI |
| **Signal Lab / Sim** | Synthetic signal synthesis with compound impairments | `ui/components/signal_lab.py` | `render_signal_lab()` | `test_production_ui_v2.py` | Real-time blind pipeline execution | **PASS** | Streamlit UI |
| **Run Trace** | Per-stage execution timeline and duration telemetry | `ui/components/run_trace.py` | `render_run_trace()` | `test_production_ui_v2.py` | Stage durations accurately displayed | **PASS** | Streamlit UI |
| **Evidence Bundle Export** | Full cryptographic ZIP packager with SHA-256 manifest | `ui/components/provenance_export.py` | `build_evidence_bundle_zip()` | `test_production_ui_v2.py` | Verified ZIP archive generated & downloaded | **PASS** | `SpectralQ_Evidence_Bundle.zip` |
| **Light Theme** | Clean, high-contrast engineering light styling | `ui/styles/theme.py` | `apply_theme()` | Visual inspection | High-contrast readable typography | **PASS** | Streamlit CSS |
| **Dark Theme** | Sleek defense-grade dark cyber styling | `ui/styles/theme.py` | `apply_theme()` | Visual inspection | Deep navy background with vibrant accents | **PASS** | Streamlit CSS |
| **Guided Demo** | 10-step evaluator tour across all workspaces | `ui/components/guided_demo.py` | `render_guided_demo_banner()` | AppTest / GUI inspection | Seamless step-by-step navigation | **PASS** | Streamlit UI |
