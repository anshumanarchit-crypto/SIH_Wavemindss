# SpectralQ SIH26147 — LDPC Resolution & Status Report

**Release Component**: Forward Error Correction (FEC) — LDPC Subsystem  
**Capture Target**: Golden Case G4 (`G4_16QAM_LDPC_pseudorandom.cf32` / `bitsG4.txt`)  
**Status**: Genuine Decoding & Syndrome Verification Active (Option A)  
**Date**: October 2026  

---

## 1. Executive Summary

In earlier revisions of the codebase, the handling of LDPC-coded captures (specifically Golden Case G4) suffered from a major technical contradiction:
1. `python/spectralq/decoder/service.py` contained a hardcoded `golden_schemes` dictionary that forcibly set `crc_stat = PASS`, `is_success = True`, and `reencode_ber = 0.0` based on filename matching.
2. In reality, Sinchana's Golden Case G4 is a raw physical test waveform containing 96 bits under a CommPy Gallager (96, 3, 963) code, permuted with a pseudorandom interleaver (seed 42).
3. G4 is **not a packetized CCSDS/AX.25 framed transmission**. It contains **no frame headers, length fields, or CRC checksums**. Therefore, asserting `CRC PASS` was factually false and violated the core physical integrity of the receiver.

Under this final release, this contradiction has been completely eliminated in favor of **Option A: Full Genuine Mathematical Resolution**.

---

## 2. Technical Implementation Architecture

### 2.1 Code Construction
- **Code Family**: Gallager Regular LDPC $(n=96, d_v=3, d_c=6)$.
- **Parity Check Matrix**: $H \in \mathbb{F}_2^{48 \times 96}$, constructed deterministically via CommPy's standard Gallager generator with seed `963`.
- **Rank of $H$**: $\text{rank}(H) = 46$ over $\text{GF}(2)$, providing $k = 96 - 46 = 50$ independent information bits.
- **Generator Matrix**: Derived in systematic form $G = [I_k \mid P]$ via Gaussian elimination over $\mathbb{F}_2$.

### 2.2 Interleaver Inversion
The transmission interleaver permutes the 96 codeword bits using a deterministic pseudo-random permutation:
```python
deinterleaved_bits = pseudorandom_deinterleave(received_bits[:96], seed=42)
```

### 2.3 Parity-Check Syndrome Verification
Before invoking decoding or asserting validity, the syndrome $s$ is computed directly:
$$s = H \cdot c^T \pmod 2 \in \mathbb{F}_2^{48}$$
For the golden capture bitstream `bitsG4.txt` after pseudorandom deinterleaving:
$$\sum_{i=1}^{48} s_i = 0$$
The syndrome vector is **identically zero**, mathematically proving that the received vector is a valid codeword in the LDPC codebook.

### 2.4 Belief Propagation / Min-Sum Decoding
Decoding is executed via Min-Sum / Log-SPA Belief Propagation on the Tanner graph:
- Iterations: up to 50 iterations.
- Stopping Criterion: Syndrome $H \cdot \hat{c} = 0$.
- Extracted Information Bits: Length 50 recovered bitstream.

### 2.5 True Re-encode Bit Error Rate (BER)
To satisfy **Rule 11**, re-encode BER is computed strictly by executing the forward encoder:
1. Re-encode decoded information bits: $c_{\text{re}} = G^T \cdot \hat{m} \pmod 2$.
2. Interleave: $c_{\text{tx}} = \text{interleave}(c_{\text{re}}, \text{seed}=42)$.
3. Compare bit-for-bit against received hard bits:
   $$\text{BER} = \frac{1}{96} \sum_{j=1}^{96} |c_{\text{tx}, j} - r_j| = 0.0$$
Because the received bits match the re-encoded codeword with zero errors, the true computed BER is `0.0`.

---

## 3. CRC Semantics Resolution

Golden Case G4 reports:
- `status`: `DecoderStatus.OK` (demodulation, deinterleaving, syndrome verification, and LDPC decoding all succeeded).
- `fec_used`: `"ldpc"`
- `interleaver_used`: `"pseudorandom"`
- `reencode_ber`: `0.0` (computed from real re-encoding)
- `crc_status`: `CrcStatus.NOT_RUN`

**Why `NOT_RUN` is the only technically defensible status**:
Golden Case G4 represents raw physical-layer transmission. Without packet encapsulation (no sync word header + CRC-16 trailer), no CRC checksum exists on the wire. Reporting `CRC NOT_RUN` honestly documents that error detection was handled by the LDPC parity checks rather than an upper-layer CRC.

---

## 4. Verification Evidence

The LDPC implementation is validated by the following automated suites:
1. `tests/test_reencode_integrity.py::test_ldpc_reencode_ber_perfect` — Validates clean codeword decoding and re-encode BER = 0.0.
2. `tests/test_reencode_integrity.py::test_ldpc_reencode_ber_corrected_error` — Validates single-bit error correction on the Tanner graph, producing non-zero BER = 1/96.
3. `tests/test_truth_isolation_runtime.py` — Validates that LDPC decoding operates strictly on baseband bits without reading capture names or truth metadata.
