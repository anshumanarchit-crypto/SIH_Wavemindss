# SpectralQ Data Contracts Overview & Epistemic Boundaries

## 1. System Pipeline & Data Handoffs

```
RAW .IQ / .wav
    -> 1. Ingest + Forensics        (Sinchana)
    -> 2. Burst Detection            (Sinchana)
    -> 3. Blind Estimation           (Sinchana)
    -> 4. Feature Extraction         (Sinchana)
    -> analysis.json                 [AnalysisContract]
    -> 5. Classifier                 (Harsh, via ClassifierOutputContract)
    -> 6. Demodulation               (Arpit, via DecoderOutputContract)
    -> 7. Hypothesis Engine          (Archit)
    -> 8. Evidence Ledger + N2 Conf  (Archit)
    -> 9. Bitstream Intelligence     (Arpit)
    -> result.json                   [ResultContract]
    -> 10. Streamlit GUI             (Himanshu, strictly read-only)
```

## 2. Epistemic State Separation

The SpectralQ architecture enforces strict semantic separation between eight epistemic states:

1. **`known`**: Physical ground truth (available exclusively in synthetic/golden test vectors via `truth.json`).
2. **`estimated`**: Quantities calculated blindly from signal observation with bounded confidence intervals (e.g. M2M4 SNR, cumulants).
3. **`hypothesized`**: Plausible transmitter parameter combinations actively searched by the Hypothesis Engine.
4. **`unsupported`**: Capabilities not present in the current software release (e.g. LDPC decoding). Explicitly declared, never fabricated or silently skipped.
5. **`unavailable`**: External dependencies that were not executed or found absent (e.g. Octave bridge when `octave-cli` is missing).
6. **`replayed`**: Data from recorded historical captures re-run under deterministic seed control.
7. **`synthetic`**: Mathematically simulated waveforms and test fixtures.
8. **`real`**: Live RF SDR capture files from the field.
