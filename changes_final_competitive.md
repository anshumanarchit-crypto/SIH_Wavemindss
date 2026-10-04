# SpectralQ SIH26147 — Final Competitive Hardening Change Specification

## Purpose

This document is the **authoritative last-mile change list** for taking the current
SpectralQ SIH26147 release candidate from a strong submission candidate toward a
**95+ evaluator-grade implementation**.

This document does **not** promise a 95/100 or 100/100 score. Selection depends on
the evaluator, competing teams, presentation, and actual runtime behaviour.

The goal is to eliminate the remaining technical attack points while preserving the
already-working project.

---

# 1. CURRENT BASELINE

The current build already demonstrates substantial working functionality:

- authoritative HypothesisEngineV1 integration
- candidate-aware winning decoder execution
- truth isolation
- real G1-G10 official capture execution
- Viterbi/K=7 integration on G2 and G6
- genuine re-encode BER on supported convolutional cases
- explicit UNKNOWN handling
- CRC semantics
- ML classifier integration
- evidence ledger
- GUI and visualization stack
- wideband scanner
- WAV/IQ/CF32 ingestion
- release artifact generation

Current reported release state:

`RELEASE_CANDIDATE_WITH_LIMITATIONS`

Do not undo these working capabilities.

---

# 2. REMAINING HIGH-PRIORITY GAPS

The final hardening work is concentrated in these areas:

## P0 — Mandatory

1. True candidate-specific decoder evaluation
2. Blind RS / concatenated FEC identification on representative official captures
3. Blind LDPC path or a stronger, explicit side-information workflow
4. Robust G9/G7 abstention semantics
5. Complete official G1-G10 capability reporting
6. Honest extended-suite verification
7. Final provenance consistency
8. Final clean release archive

## P1 — High-value competitive improvements

9. Hypothesis evidence-gap visualization
10. FEC/interleaver proof visualization
11. Receiver verification score transparency
12. Better unknown/explanation semantics
13. Stronger adversarial robustness evaluation
14. More meaningful class-wise validation

---

# 3. P0.1 — TRUE CANDIDATE-SPECIFIC DECODER SEARCH

## Problem

The hypothesis engine can generate and rank 175 modulation × interleaver × FEC
triples, but the final implementation must not imply that all 175 candidates were
fully decoded if only a small subset actually reached decoder execution.

## Required architecture

Use:

DSP
→ Rule + ML evidence
→ Candidate generation
→ Coarse pruning
→ Candidate-specific decoding/evaluation
→ Candidate verification
→ Ranking
→ Winner

## Required candidate representation

Each evaluated candidate must include:

- modulation
- interleaver
- FEC
- candidate status
- evidence score
- decoder status
- verification status
- CRC status where applicable
- re-encode BER where applicable
- rejection/pruning reason

## Efficiency requirement

Do NOT blindly run an expensive full receiver stack for all 175 candidates if
that destroys runtime.

Use a two-stage strategy:

### Stage A — cheap physical pruning

Use:

- modulation compatibility
- SNR floor
- bandwidth
- symbol-rate compatibility
- feature likelihood
- classifier probability
- signal type

### Stage B — real receiver verification

Run actual demodulation/deinterleaving/FEC only for surviving candidates.

The result must report:

- generated count
- pruned count
- decoder-evaluated count
- verified count

Never claim more evaluations than actually occurred.

## Acceptance test

Add:

`tests/test_candidate_decoder_search.py`

It must prove that at least two competing candidates reach the real decoder on
a controlled case and that the winner comes from actual verification evidence.

---

# 4. P0.2 — BLIND RS IDENTIFICATION

## Target

G3:

`8-PSK + RS(255,223) + diagonal interleaver`

## Requirement

Do not inject the known G3 configuration.

The system must evaluate candidate RS + interleaver configurations and use actual
decoder evidence.

For RS candidates record:

- block length compatibility
- symbol/block validity
- corrected symbol count if available
- syndrome/error result
- payload recovery
- re-encode result where meaningful

## Acceptance

A valid G3 path should produce either:

### Preferred

`8-PSK + RS(255,223) + diagonal`

with genuine verification evidence.

### Acceptable fallback

UNKNOWN with explicit explanation that:

- modulation may be established
- FEC candidates were evaluated
- RS could not be conclusively verified

But do NOT claim full blind FEC identification unless it actually happened.

---

# 5. P0.3 — BLIND CONCATENATED FEC

## Target

G5:

`2-FSK + RS + convolutional`

## Required chain

2-FSK demodulation
→ candidate interleaver handling
→ convolutional/Viterbi stage
→ RS stage in the actual implemented order
→ verification
→ evidence

Use the repository's existing ConcatenatedCodec rather than inventing another
codec implementation.

Record:

- inner code result
- outer code result
- recovered payload length
- verification
- re-encode where applicable

## Acceptance

Preferred:

`2-FSK + concatenated`

with genuine decoder evidence.

Otherwise:

honest UNKNOWN/PARTIAL.

No hardcoded G5 path.

---

# 6. P0.4 — LDPC

## Current reality

LDPC exists as a genuine Gallager (96, 3, 963) implementation, but the blind
hypothesis registry currently treats it as unsupported because the runtime lacks
enough reliable side information for blind discovery.

## Do NOT break the system trying to force this.

Choose one of the following.

### Preferred option

Implement a **side-information-assisted LDPC mode** that requires explicit
code-dimension metadata or user-selected candidate constraints.

Clearly label:

`LDPC — SIDE INFORMATION REQUIRED`

Then show:

- LDPC candidate
- code dimensions
- syndrome
- iterations
- convergence
- verification

### Best-case option

If inexpensive and stable, add blind candidate evaluation specifically for the known
supported `(96,3,963)` block dimensions.

Do not generalize beyond what is actually implemented.

## Critical honesty

Never claim:

`FULL BLIND LDPC IDENTIFICATION`

unless the runtime genuinely performs it.

---

# 7. P0.5 — G7/G9 ABSTENTION HARDENING

## G7

G7 is a near-threshold signal.

The system should use:

- low hypothesis separation
- demod quality
- FEC verification failure
- cross-window inconsistency
- physical uncertainty

to determine whether to abstain.

Do not force a known answer.

## G9

G9 must not become a confident wrong modulation.

The general mechanism should be:

poor evidence
+
headerless/swapped-IQ ambiguity
+
high EVM
+
no receiver verification

→ UNKNOWN

Do not write:

`if G9: UNKNOWN`

Use signal properties.

## Acceptance

Add adversarial tests with renamed/repackaged files proving G9 behaviour is
capture-independent.

---

# 8. P0.6 — FIX CONFIDENCE SEMANTICS

Separate:

- `raw_ml_probability`
- `calibrated_ml_probability`
- `final_evidence_confidence`
- `decision_confidence`

If calibrated ML probability is unavailable:

`calibrated_ml_probability = null`

Do not silently copy raw ML probability into the calibrated field.

For UNKNOWN cases, explicitly label what the confidence refers to.

Recommended UI wording:

`Decision: UNKNOWN`

`Decision Confidence: 87%`

rather than an ambiguous generic `Confidence: 87%`.

---

# 9. P0.7 — OFFICIAL G1-G10 VALIDATION MATRIX

The validation generator must use the actual official files under:

`data/official/sinchana/golden/`

For every case record:

- file path
- SHA256
- source mode
- sample-rate source
- modulation result
- FEC result
- interleaver result
- decoder result
- verification result
- confidence
- ladder
- UNKNOWN
- UNKNOWN reason
- runtime

Truth fields are validation-only.

## Separate score columns

Do not collapse everything into one accuracy number.

Generate separate:

- modulation accuracy
- FEC identification accuracy
- interleaver identification accuracy
- successful decoder verification rate
- safe abstention rate

This makes the report much more evaluator-defensible.

---

# 10. P0.8 — SOURCE PROVENANCE

For actual official captures:

`source_mode = REAL`

Do not label them `synthetic`.

Store:

- SHA256
- source file
- metadata source
- sample-rate source
- execution mode
- timestamp
- run ID

For simulation:

`source_mode = SIMULATION`

For replay:

`source_mode = REPLAY`

For deterministic tests:

`source_mode = TEST/STUB`

No ambiguity.

---

# 11. P0.9 — LIVE FAILURE MUST NOT BECOME FAKE CLASSIFICATION

Production LIVE execution must follow:

real ingest
→ real analysis
→ result

If analysis fails:

`LIVE_ANALYSIS_FAILED`

then:

`UNKNOWN` or a clearly surfaced error state.

Never automatically execute the deterministic stub classifier in LIVE mode.

Stub execution remains available only under explicit TEST/STUB mode.

---

# 12. P0.10 — EXTENDED SUITE

Run the extended suite exactly ONCE after the implementation is stable.

Do not repeatedly rerun it.

If it passes:

record actual result.

If it fails:

fix the implementation if the failure is relevant.

If runtime cost is genuinely prohibitive:

record:

`NOT_VERIFIED`

and do not claim full release certification.

---

# 13. P0.11 — CROSS-LAYER CONSISTENCY

Automate consistency checks for:

`result.top_hypothesis == hypothesis_engine.winner`

`result.fec == decoder.fec_used`

`result.interleaver == decoder.interleaver_used`

`result.confidence == confidence_engine.final_confidence`

`result.calibration_status == actual_calibration_state`

`result.crc_status == decoder.crc_status`

`result.reencode_ber == decoder.reencode_ber`

`result.source_mode == actual_execution_mode`

`UI == backend`

Any mismatch is a release blocker.

---

# 14. P0.12 — RELEASE VERDICT

The verdict must be generated from machine-readable execution evidence.

Allowed:

- RELEASE_READY
- RELEASE_CANDIDATE_WITH_LIMITATIONS
- NOT_RELEASE_READY

Never hardcode a PASS count or release verdict.

---

# 15. P1 — HYPOTHESIS COMPETITIVE UX

Add a compact panel:

## WHY THIS HYPOTHESIS?

Show:

Winner
Runner-up
Score gap
Supporting evidence
Contradicting evidence
Verification status

Example:

Winner:
QPSK + Conv + Block

Score:
0.91

Runner-up:
QPSK + None + None

Score:
0.68

Gap:
0.23

Verification:
Viterbi PASS
Re-encode BER = 0

This is highly valuable during judging.

---

# 16. P1 — FEC/INTERLEAVER PROOF PANEL

For the selected hypothesis show:

Modulation
Interleaver
FEC
Decoder
CRC
Re-encode BER
Verification

Each value must be backend-derived.

---

# 17. P1 — UNKNOWN EXPLANATION PANEL

For UNKNOWN:

Why?
What passed?
What failed?
What is missing?
Highest defensible evidence ladder?
What additional information would resolve it?

This should be a visible part of the main result view.

---

# 18. P1 — ADVERSARIAL EVALUATION

Use renamed copies of official captures and modified path names to prove no
capture-ID logic remains.

Create tests for:

- renamed G7
- renamed G9
- copied G2 under arbitrary filename
- copied G3 under arbitrary filename

The answer must remain driven by signal data.

---

# 19. P1 — STRONGER ML EVALUATION

Do NOT retrain the model in this release pass.

Instead, improve reporting.

Report:

- per-class precision
- recall
- F1
- confusion matrix
- sample support
- SNR range
- impairment conditions

Do not advertise 100% accuracy without displaying the test-set size.

---

# 20. P1 — FINAL DEMO PATH

Optimize one evaluator path:

UPLOAD UNKNOWN CAPTURE

↓

REAL FORENSICS

↓

REAL SPECTRUM / WATERFALL

↓

RULE + ML

↓

WHY THIS HYPOTHESIS?

↓

TOP HYPOTHESIS

↓

FEC / INTERLEAVER PROOF

↓

DECODER VERIFICATION

↓

EVIDENCE LADDER

↓

CONFIDENCE / UNKNOWN

↓

EXPORT EVIDENCE BUNDLE

This should take as few clicks as practical.

---

# 21. P1 — PERFORMANCE

Measure:

- ingest
- DSP
- candidate pruning
- candidate verification
- decoder
- export
- total

Do not optimize correctness away for speed.

Use staged hypothesis pruning to keep the candidate search practical.

---

# 22. P1 — FINAL CLEAN RELEASE

Before packaging:

- git status
- git diff --check
- remove pycache
- remove pyc
- remove temporary logs
- remove secrets
- remove personal paths
- remove unrelated archives

Then:

commit

then:

verify clean tree

then:

package final ZIP

The ZIP must reproduce the committed release state.

---

# 23. FINAL ACCEPTANCE TARGET

The desired release state is:

### MUST PASS

- truth isolation
- canonical live pipeline
- real ML
- authoritative hypothesis engine
- candidate-specific decoding
- Viterbi runtime
- RS runtime or honest limitation
- concatenated runtime or honest limitation
- LDPC status consistency
- CRC semantics
- re-encode semantics
- G7 safe abstention
- G9 safe abstention
- official G1-G10 validation
- source provenance
- cross-layer consistency
- clean Git state
- clean installation

### SHOULD PASS

- blind RS identification
- blind concatenated identification
- improved G3/G5 results
- one-run extended suite
- adversarial renamed-capture tests
- stronger evaluator-facing hypothesis explanation

---

# 24. DO NOT DO

Do NOT:

- redesign the UI
- retrain the ML model
- invent a new DSP architecture
- add arbitrary features
- hardcode official answers
- make G3/G4/G5 appear successful artificially
- downgrade test standards
- hide UNKNOWN cases
- claim 100% accuracy from tiny samples
- claim full blind LDPC if it is not true
- claim 175 complete decoder trials unless that many actually run
- create release documentation before validation is complete

---

# 25. FINAL QUALITY BAR

A strong evaluator should be able to ask:

"Why modulation?"

and see evidence.

"Why this FEC?"

and see actual decoder evidence.

"Why this interleaver?"

and see candidate comparison.

"Where did BER come from?"

and see real re-encode comparison.

"Why UNKNOWN?"

and see contradictions and missing verification.

"Can I upload another file?"

and the same canonical runtime executes.

"Can you prove the result?"

and the evidence bundle contains the provenance chain.

That is the standard this final pass should achieve.

---

# 26. FINAL VERDICT RULE

Do not chase a cosmetic 100%.

A technically honest:

`RELEASE_READY`

with strong evidence is preferable to:

`100% VERIFIED`

with unsupported claims.

The objective is a **top-tier SIH evaluator experience backed by genuine RF/DSP
execution**, not a larger codebase.

