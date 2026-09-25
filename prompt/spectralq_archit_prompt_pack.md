# SpectralQ — Archit Execution Prompt-Pack v2
**SIH26147 · NTRO · WaveMinds/NovaTrace · Repo: github.com/anshumanarchit-crypto/machine-learning-SIH**

---

## 0. What's upgraded here vs. the draft you pasted

Your draft (12 prompts) was structurally correct but had five real holes. This pack closes them:

1. **No JSON schemas anywhere** — "create versioned schemas" was said, never shown. Prompt 1 below now ships exact field-level schemas.
2. **"Weights must be validated" with no method** — the draft tells the agent to hand-pick `w1, w2, w3` and "validate" them, which is exactly the kind of unfalsifiable step a judge will puncture. Prompt 6 below replaces hand-picked weights with a **logistic regression fit on held-out data**, so the "weights" are literally regression coefficients you can print and defend.
3. **Rule-based path was undefined** — "interpretable rule-based classifier" with no grounding. Prompt 5 below ties it to the actual textbook method (cumulant-ratio decision tree, Swami & Sadler-style), with thresholds *derived empirically from your own sweep*, not invented numbers.
4. **No one computes the Evidence Ladder (L1–L5) field** — N1 is referenced everywhere in your plan but the draft never assigns who turns "which stages passed" into a ladder level. Prompt 4 now makes `ladder_level` a required, deterministically-computed field in Archit's own output, so Himanshu/Sinchana don't have to guess.
5. **No dataset sourcing directive** — Harsh's classifier needs training data; nothing in the draft says where it comes from or what's actually usable. Section 2 below gives you the corrected, verified answer.
6. **No environment/version guard** — `CalibratedClassifierCV`'s API differs across scikit-learn versions; the draft assumes a signature. Prompt 0.5 below makes the agent check before it writes code that silently breaks.

Everything else (team boundaries, ML feature list, stack, Octave-honesty rule) is preserved exactly as your team already agreed — I did not touch the architecture.

---

## 1. How to use this pack

- Paste **one prompt at a time**, in order: 0 → 0.5 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12.
- Do not paste two prompts in the same message. Each one ends with "at the end, do X" — wait for that output before continuing.
- If the agent ever says a number, percentage, or capability without a code path or test producing it, paste this back verbatim:
  > **"Stop. Show me the exact file and test that produced that number. If it doesn't exist, say so and mark it TODO."**
- Every prompt below contains its own copy of the non-negotiable rules. This is deliberate — coding agents lose earlier context faster than you'd like, and repetition here is cheap insurance against drift.

---

## 2. Dataset directive (verified — corrects your uploaded dataset doc)

Checked against current sources before writing this. Use this, not the raw doc, when Prompt 5/Harsh's training data comes up:

| Dataset | Verified fact | Fit for SpectralQ |
|---|---|---|
| **TorchSig / Sig53** | Confirmed: **53 signal classes across 6 modulation families**, ~5M synthetic samples, split into Clean/Impaired × Train/Validation. Your source doc says "50+" — that's imprecise, the real number is 53. | Good for classifier pretraining/sanity-checking, but it ships pre-impaired raw IQ, not cumulant/EVM/cluster features — you still have to run your own feature extraction on top. |
| **RadioML 2018.01A / 2016.10A** | Standard AMC benchmark, widely cited, HDF5/Pickle. Known in the literature to have label-quality issues at low SNR on the 2016 sets. | Same caveat as above — raw IQ only, no FEC/interleaving, so it's useless for testing your Hypothesis Engine (G2–G6), only for the modulation-ID sub-problem. |
| **Panoradio HF** | HF-band, 18 real-world modes (Morse, SSB, AM, Navtex, amateur digital), 2048 samples @ 6 kHz. | Actually your **best domain match** — your PS is explicitly HF/VHF/UHF and this is the only dataset in the list that's HF-specific rather than a generic modulation zoo. Worth more slide-credibility than RadioML for the "we tested against realistic HF traffic" claim. |
| **CSPB.ML.2018R2** | 8 PSK/QAM classes, long vectors (32,768 samples), cyclostationary-focused. | Genuinely useful for validating your cyclic-feature / cyclostationarity claims specifically — narrow but real fit. |
| **HISAR (IEEE DataPort)** | 26 classes — the source itself flags known label-quality issues. | Treat as a secondary cross-check only, never as ground truth on its own. |

**The gap none of these fill:** not one public dataset contains FEC-coded, interleaved bitstreams with header/payload structure. That's the whole point of your Hypothesis Engine (G2–G6 in your golden set). **You must generate those yourself** through Arpit's encode chain — this was already your plan, this just confirms no dataset shortcuts it.

**Directive for Prompt 5:** train the baseline classifier on cumulant/cluster/EVM features computed *by your own extraction code* running over (a) a synthetic sweep you control end-to-end, and (b) RadioML/TorchSig raw IQ as an external sanity check — never on someone else's pre-extracted feature file, since none matches your feature schema.

---

## PROMPT 0 — MASTER ARCHITECTURE / CONSTITUTION

```
You are the principal software architect and senior Python/ML engineer
implementing the Archit-owned portion of SpectralQ, SIH 2026, PS SIH26147 (NTRO).

Repository: https://github.com/anshumanarchit-crypto/machine-learning-SIH

ROLE
Build the evidence-first decision/integration layer: receive upstream signal
analysis, classifier output, and decoder output; search plausible explanations;
evaluate evidence; combine independent opinions; compute trustworthy, defensible
confidence; return UNKNOWN when evidence is insufficient.

THIS IS NOT A GREENFIELD DESIGN TASK. Preserve the architecture below exactly.

==================================================
PIPELINE (non-negotiable)
==================================================
RAW .IQ / .wav
    -> 1. Ingest + Forensics        (Sinchana)
    -> 2. Burst Detection            (Sinchana)
    -> 3. Blind Estimation           (Sinchana)
    -> 4. Feature Extraction         (Sinchana)
    -> capture.cf32 + analysis.json
    -> 5. Classifier                 (Harsh, integrated by you)
    -> 6. Demodulation               (Arpit)
    -> 7. Hypothesis Engine          (YOU)
    -> 8. Evidence Ledger + N2 Confidence (YOU)
    -> 9. Bitstream Intelligence     (Arpit)
    -> 10. Streamlit GUI + Evidence Bundle (Himanshu, consumes your result.json)

TEAM BOUNDARIES — do not cross these
Sinchana: DSP front end, ingest, burst detection, blind estimation, features,
          real-capture analysis (Octave where it genuinely exists).
Arpit:    demodulation, timing/carrier recovery, de-interleaving, FEC decoding.
Harsh:    baseline classifier training, benchmarking, accuracy/confusion/BER.
Himanshu: Streamlit GUI — consumes result.json, computes nothing itself.
Archit (you): integration, contracts, pipeline orchestration, Octave bridge
              (only where real), Hypothesis Engine, Evidence Ledger,
              N5 hybrid modulation ID, N2 confidence + calibration + UNKNOWN,
              Replay mode, release/reproducibility/CI.

==================================================
ML ARCHITECTURE (fixed)
==================================================
Signal-derived features ONLY — never raw constellation pixels, never CNN/
transformer/deep learning/cloud ML. Feature set:
  C20, C21, C40, C42, C60, C63, C80 (cumulants)
  M2M4-based SNR estimate
  phase/envelope statistics
  constellation cluster count, silhouette score, intra/inter-cluster distance
  cluster-count stability across sub-windows
  EVM
  phase-ambiguity resolution quality
  cyclic features (if present in the upstream analysis.json contract)

Baseline classifier: scikit-learn RandomForest (primary). GMM optional only if
already required elsewhere. No other architecture without documented proof the
baseline is impossible.

The trained classifier's raw probability is NEVER the final confidence:

    features
       |
   +---+---+
   |       |
 rule    trained ML
   |       |
prediction probability
   |       |
   +---+---+
       |
  agreement check (N5)
       |
  cross-window agreement
       |
  verification evidence (sync/CRC/re-encode)
       |
  confidence fusion (logistic-regression-fit, see Prompt 6)
       |
  calibration check (reliability diagram, ECE, Brier score)
       |
  final confidence, bounded [0,1]
       |
  +----+----+
  |         |
label     UNKNOWN

==================================================
N5 — HYBRID MODULATION ID
==================================================
Rule path and ML path run independently and BOTH predictions are preserved.
Disagreement is itself evidence and MUST reduce final confidence — never
silently pick one over the other.

==================================================
N2 — COMPUTED, CALIBRATED CONFIDENCE + UNKNOWN
==================================================
Forbidden: hardcoded 95%, any fixed constant, raw predict_proba() passed
through unchanged and called "confidence."
Required inputs: calibrated ML probability, cross-window agreement,
verification evidence score, rule-vs-ML agreement/disagreement.
Below a validated threshold -> UNKNOWN, always, no exceptions.

==================================================
EVIDENCE LADDER FIELD (new — you own computing this)
==================================================
Your result.json MUST include a deterministic `ladder_level` field, one of
L1 (detected) / L2 (characterised) / L3 (demodulated, internally consistent)
/ L4 (structure verified: sync+CRC or known frame) / L5 (independently
cross-checked). Compute it purely from which upstream stages actually
returned valid, non-stub, non-UNAVAILABLE data for this capture — do not
let the GUI or any other person infer it themselves.

==================================================
HYPOTHESIS ENGINE
==================================================
Hypothesis = modulation x interleaver x FEC.
Modulations: BPSK, QPSK, 8-PSK, 16-QAM, 64-QAM, 2-FSK, 4-FSK.
Interleavers: block, convolutional, diagonal, pseudo-random.
FEC: convolutional/Viterbi K=7, RS(255,223), concatenated, LDPC-if-actually-implemented.
LDPC MUST NEVER be faked — if unavailable, expose it as unsupported, not silently skipped.
Coarse-to-fine pruning using upstream measurements/classifier hints.

==================================================
EVIDENCE-FIRST PRINCIPLE
==================================================
Never output prediction+confidence alone. Always preserve: candidates
considered, ranking, ML prediction+probability, rule prediction, N5
agreement, window agreement, sync/CRC/re-encode evidence, rejection
reasons, ladder_level, UNKNOWN reason if applicable, full provenance.

==================================================
REPRODUCIBILITY — forbidden claims unless code+test prove them
==================================================
100% accuracy, "calibrated" (without a reliability diagram + ECE/Brier on
held-out data), zero false rejections, real-time support, Zigbee support,
Octave cross-validation, "58 tests / 100% coverage" without a coverage report.

==================================================
STACK
==================================================
Python, NumPy, SciPy, scikit-learn, Matplotlib, Streamlit, pytest. No React,
FastAPI, cloud services, databases, LLM/agent calls inside the pipeline
itself, microservices. Fully offline.

==================================================
OCTAVE RULE
==================================================
If Octave scripts genuinely exist and run: integrate via octave-cli, JSON
handoff, cache outputs. If they do NOT exist: build the correct interface/
adapter, mark it explicitly as stub/capability-unavailable, and never
pretend the bridge is live. Do not duplicate Sinchana's DSP work in Python
just to make a demo look complete.

==================================================
ENGINEERING RULES
==================================================
1. Inspect before modifying. 2. Never blind-overwrite working code.
3. Small, testable modules. 4. Deterministic seeds. 5. Type-hint public APIs.
6. Tests for every major component. 7. Preserve frozen contracts.
8. Never fabricate missing upstream data. 9. Fail loudly with useful errors.
10. Keep synthetic/replayed/real clearly distinguishable everywhere, including
    in field names, not just in comments. 11. No business logic in the GUI.
12. GUI only ever reads result.json. 13. Confidence is computed by Python
    code, never by an LLM at runtime. 14. Never say "calibrated" unless the
    calibration validation script actually ran and its output is saved.
    15. Keep a full audit trail of every evidence item.

==================================================
FIRST ACTION — before writing any implementation code
==================================================
1. Inspect the repository state (empty/new/partial).
2. State an implementation plan mapped to the architecture above.
3. Identify which upstream interfaces are missing today.
4. Identify what can be stubbed immediately vs. what truly needs Sinchana/
   Arpit/Harsh's real output.
5. Identify contradictions between existing files (if any) and this spec.
6. Do NOT invent missing code to fill gaps.
7. Then stop and wait for the next prompt (Phase 1). Implement nothing beyond
   this inspection yet.

Do not redesign the project. Do not add unrelated features. Do not substitute
a different ML architecture. Do not skip ahead to later phases.
```

---

## PROMPT 0.5 — ENVIRONMENT & DEPENDENCY VERIFICATION (new)

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 0.5:
ENVIRONMENT VERIFICATION. Do not write pipeline code yet.

1. Report the exact Python version and the exact installed version of numpy,
   scipy, scikit-learn, matplotlib, streamlit, pytest.

2. Specifically check the installed scikit-learn's CalibratedClassifierCV
   signature (method='sigmoid'/'isotonic' argument name and any deprecation
   or replacement, e.g. newer estimator-wrapping APIs). Do NOT assume a
   signature from memory — introspect the installed package (help(), inspect
   module, or the package's own changelog file if bundled) and report exactly
   what argument names and defaults exist in THIS environment.

3. Check whether GNU Octave / octave-cli is present on this machine at all
   (subprocess check). Report true/false. This determines whether Prompt 2's
   bridge runs in LIVE-capable mode or must default to stub-only.

4. Create requirements.txt (or update it) pinned to what's actually
   installed and tested, not aspirational versions.

5. Report all of this as a short table. Do not proceed to Phase 1 in this
   same response — stop after the report.
```

---

## PROMPT 1 — REPOSITORY + CONTRACTS

```
Continue from the SpectralQ Archit architecture already established.
Implement ONLY Phase 1: REPOSITORY FOUNDATION + DATA CONTRACTS.

Repository: https://github.com/anshumanarchit-crypto/machine-learning-SIH

Required structure (adapt physically if it improves packaging, but preserve
this conceptual separation):
/
+-- octave/
+-- python/spectralq/
|   +-- __init__.py
|   +-- contracts/
|   +-- pipeline/
|   +-- hypothesis/
|   +-- evidence/
|   +-- confidence/
|   +-- calibration/
|   +-- integration/
|   +-- replay/
+-- tests/
+-- data/{golden,real,replay}/
+-- bench/
+-- docs/
+-- requirements.txt
+-- README.md

Create versioned, field-level JSON schemas (with a "schema_version" field in
every one) for:

analysis.json (from Sinchana):
  schema_version, capture_id, source_mode: real|synthetic|replay,
  fs_hz, fs_source: header|user|inferred,
  bursts: [{start_ms, end_ms, power}],
  estimates: {baud: {value, ci_lo, ci_hi, method},
              cfo: {...}, bandwidth: {...}, snr: {...}},
  features: {cumulants: {C20, C21, C40, C42, C60, C63, C80},
             cluster: {count, silhouette, intra_var, inter_dist},
             evm, phase_ambiguity_quality, cyclic: {...} | null}

decoder_output.json (from Arpit):
  schema_version, capture_id, status: ok|failed|unsupported,
  interleaver_used, fec_used, decoded_bits, crc_status: pass|fail|not_run,
  reencode_ber | null, failure_reason | null

classifier_output.json (from Harsh, via your adapter):
  schema_version, capture_id, window_id, ml_prediction, ml_probabilities: {},
  calibrated_probability | null, model_version, feature_vector_used

truth.json (synthetic/golden only):
  schema_version, modulation, sps, roll_off, snr_db, cfo_hz, phase,
  interleaver, fec, timing_bits, source_hash

result.json (your final output — freeze this once Prompt 11 completes):
  schema_version, capture_id, source_mode, ladder_level: L1..L5,
  top_hypothesis: {modulation, interleaver, fec},
  alternate_hypotheses: [...],
  ml_prediction, ml_probability, calibrated_ml_probability,
  rule_prediction, rule_ml_agreement: bool, rule_ml_penalty,
  cross_window_agreement, evidence: [ {evidence_id, source, check_name,
    status: PASS|FAIL|NOT_RUN|UNAVAILABLE|CONFLICT, value, explanation} ],
  final_confidence, confidence_version, unknown: bool, unknown_reason | null,
  provenance: {input_hash, seed, software_version, generated_at}

Field states that must never be confused anywhere in these schemas:
known | estimated | hypothesized | unsupported | unavailable | replayed |
synthetic | real.

Write full documentation for each schema under /docs.

Build validation functions that reject malformed input with clear errors —
not silent coercion.

Create pytest fixtures: one valid example of each schema above, plus at
least one deliberately malformed example per schema that must fail
validation. Write tests proving:
  - valid data validates
  - malformed data fails with a specific, useful error
  - schema_version mismatches are caught
  - provenance fields survive round-trip serialization
  - real/synthetic/replay state cannot be silently swapped

Do NOT implement the hypothesis engine, calibration, or GUI code yet.

At the end:
1. Show the final directory tree.
2. Summarize every schema in one paragraph each.
3. Run pytest and paste the exact output.
4. List, explicitly, what is still blocked on Sinchana/Arpit/Harsh/Himanshu.
Do not claim anything is "done" unless the pasted pytest output proves it.
```

---

## PROMPT 2 — OCTAVE/PYTHON BRIDGE + PIPELINE PLUMBING

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 2:
PIPELINE PLUMBING + OCTAVE/PYTHON BRIDGE.

Use the Phase 0.5 report to decide: if octave-cli was NOT detected, build
this phase in stub-only mode by default and say so explicitly — do not
silently assume Octave will be available at demo time.

A. Build an octave_bridge module supporting:
   - invoking octave-cli non-interactively when a real Octave function exists
   - timeout handling, stdout/stderr capture, non-zero exit handling
   - JSON parsing with clear parse-failure errors
   - deterministic output paths and provenance metadata
   Detect the actual available function name/signature rather than assuming
   one (e.g. analyse_capture(...)) exists verbatim.

B. If Octave is unavailable: provide a deterministic stub adapter that
   returns schema-valid analysis.json marked source_mode="stub",
   capability_available=false. Never mark stub output as live.

C. Build pipeline.run(capture) that:
   1. accepts a capture path
   2. invokes the bridge (live or stub, whichever applies)
   3. validates the returned analysis.json against the Phase 1 schema
   4. obtains decoder output and classifier output (stubbed for now if
      Arpit/Harsh haven't delivered real modules yet)
   5. passes everything into your decision engine (stubbed pass-through
      for now — real logic starts Phase 3)
   6. produces a schema-valid result.json

D. Build a CLI: `spectralq analyze <file>` that prints whether execution
   was LIVE, STUB, or REPLAY for every stage, not just overall.

E. Integration tests covering: successful bridge call, timeout, Octave
   missing, malformed JSON, non-zero exit, full stub-to-stub pipeline run,
   provenance survives the whole chain.

F. A named smoke test: stub analysis.json + stub decoder output + stub ML
   output -> pipeline.run() -> valid result.json. This must pass before
   you report Phase 2 complete.

Do not implement hypothesis ranking yet.

At the end: run pytest and paste output; show the CLI command and its
console output; show one full example result.json; state in one line per
stage whether it is LIVE or STUB right now. Never describe a stub as
"Octave integration."
```

---

## PROMPT 3 — HYPOTHESIS ENGINE

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 3:
HYPOTHESIS ENGINE V1.

Hypothesis = modulation x interleaver x FEC, from the fixed lists in
Prompt 0. LDPC must be marked unsupported wherever it isn't actually
implemented — never silently dropped or faked as passing.

Implement, in order:
1. Candidate generation (full cross-product, tagged with support status)
2. Coarse pruning using upstream classifier/rule hints and measurement
   plausibility (e.g. decoded-length incompatibility with a code family
   deprioritizes that candidate; a modulation the classifier confidently
   excludes is deprioritized, never hard-deleted without a fallback path)
3. Fine evaluation per surviving candidate
4. Evidence collection per candidate (sync/pattern match, CRC/checksum,
   re-encode comparison/BER — each explicitly PASS/FAIL/NOT_RUN/UNAVAILABLE)
5. Deterministic ranking

For every hypothesis object, persist: modulation, interleaver, fec, status,
evidence list, failed checks, unsupported components, final rank score.

Do NOT invent a confidence percentage at this stage — that belongs only to
Phase 6. This stage produces ranking and evidence, nothing else.

Tests required: candidate generation completeness, pruning correctness,
LDPC-unavailable handling, evidence state handling (all four states
reachable and distinguishable), deterministic ranking given identical
input, one full G1-style pass, one full G2-style pass.

Build a human-readable debug dump of ranked hypotheses (for your own use
in the viva, not the GUI).

At the end: show one clean G1 case end-to-end, one G2 case end-to-end,
the ranked hypothesis list for each, and a one-paragraph explanation of
WHY the top hypothesis won each time. Run pytest and paste output.
```

---

## PROMPT 4 — EVIDENCE LEDGER + LADDER LEVEL

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 4:
EVIDENCE LEDGER + LADDER LEVEL COMPUTATION.

Build the Evidence Ledger abstraction. Each evidence item must contain at
minimum: evidence_id, hypothesis_id, source, check_name, status (PASS|
FAIL|NOT_RUN|UNAVAILABLE|CONFLICT), numeric_value if applicable,
normalized_value if applicable, threshold if applicable, provenance,
a deterministic run identifier, human-readable explanation, and a
failure_reason if relevant.

Evidence sources to support: Sinchana's analysis output, ML classifier,
rule-based classifier, cross-window agreement, sync/pattern matching,
CRC/checksum, re-encode/BER comparison, phase-ambiguity resolver, decoder
result, hypothesis engine ranking.

Unsupported or NOT_RUN evidence must never silently become a positive
score anywhere downstream — enforce this with a test, not just a comment.

NEW IN THIS PHASE — compute `ladder_level` deterministically:
  L1 = a burst/signal was detected, nothing more
  L2 = characterised: baud/CFO/modulation family estimated with intervals
  L3 = demodulated to bits, internally consistent (no decoder failure)
  L4 = structure verified: sync word AND/OR CRC pass, or a recognized frame
  L5 = independently cross-checked (e.g. a second decoder/tool agrees)
Write this as a pure function of which upstream stage outputs are present
and valid for this capture — not a manual flag anyone sets by hand. Test
it against at least one example per level, including a capture that
deliberately stops at L2 (this must produce a valid, non-error result,
not a crash — a partial result is a correct result).

Integrate the ledger and ladder_level into result.json per the Phase 1
schema. A result must contain: top hypothesis, alternates, full evidence
trail, failed checks, unavailable checks, ladder_level, provenance.

Do not build any GUI code — Himanshu owns rendering this.

Tests: evidence append/serialize/deserialize, conflict handling, missing-
evidence handling, deterministic output given identical input, provenance
propagation through the full chain, all five ladder levels reachable and
correctly assigned on constructed examples.

At the end: run pytest and paste output; show one worked example at L2
and one at L4, with their full evidence trails printed.
```

---

## PROMPT 5 — ML INTEGRATION + N5 HYBRID MODULATION ID

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 5:
ML INTEGRATION + N5 HYBRID MODULATION IDENTIFICATION.

Harsh owns training the baseline classifier. You own integration,
calibration interface, and the rule-vs-ML decision logic. Do not retrain
or replace Harsh's classifier architecture from inside this module.

Primary classifier: scikit-learn RandomForest. No CNN/deep learning.

DATASET DIRECTIVE (for whoever runs training, document this even if Harsh
executes it): public datasets (RadioML, TorchSig/Sig53, Panoradio,
CSPB.ML.2018R2) provide raw IQ only — none ship pre-extracted cumulant/
cluster/EVM features matching this project's schema, and none contain
FEC-coded/interleaved streams. Training features MUST be produced by
running this project's own extraction code over (a) a synthetic sweep
generated through the project's own encode chain, and (b) external raw
IQ from the datasets above as a secondary sanity check only — never
train directly on someone else's pre-made feature file.

A. Build a classifier adapter (not a hard dependency on one sklearn
   internals version): load model, validate feature name/order match
   against the Phase 1 schema, predict class + probability distribution,
   preserve model_version and training metadata. Never call raw
   predict_proba() output "final confidence" anywhere — name it
   ml_probability explicitly, distinct from calibrated_ml_probability
   which does not exist until Phase 7.

B. Implement/consume the rule-based path as a genuine, explainable
   decision procedure over the cumulant ratios (the standard family of
   cumulant-based AMC decision trees — e.g. using sign/magnitude
   relationships among C40, C42, C21 to separate PSK orders from QAM).
   DO NOT hardcode textbook threshold numbers from memory — derive the
   actual thresholds empirically from your own synthetic sweep (Phase 10
   dataset) and store them as a versioned, documented configuration, not
   magic numbers buried in code. Output must include: predicted class,
   which features/thresholds drove the decision, and a decision path a
   human can read.

C. N5 fusion:
     agreement = (rule_prediction == ml_prediction)
   Both predictions are always preserved in the output — never overwrite
   one with the other. Disagreement must be recorded as an explicit
   evidence item consumable by Phase 6's confidence engine, with a
   documented, non-hidden effect (reduces confidence — exact mechanism
   in Phase 6).

D. Cross-window support: run classification independently over multiple
   sub-windows of the same capture. Report per-window prediction, per-
   window probability, an agreement ratio in [0,1], and the count of
   windows analyzed. Do not hide or drop unstable windows from the report.

Tests: agreement case (rule==ml), disagreement case (rule!=ml) — verify
both predictions survive unchanged and disagreement evidence is recorded;
cross-window agreement computed correctly on a constructed 4-window
example with 3 matching + 1 outlier.

Do NOT implement final confidence yet — that is Phase 6.

At the end: run pytest and paste output; show one sample ML output, one
sample rule output (with its decision path printed), one N5 agreement
object, one N5 disagreement object.
```

---

## PROMPT 6 — N2 CONFIDENCE ENGINE (fit, not hand-picked)

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 6:
N2 COMPUTED CONFIDENCE ENGINE.

Goal: replace the hardcoded 95.0% with a defensible, computed confidence.
NEVER use a constant. NEVER pass a classifier probability straight through
as final confidence.

INPUTS: calibrated_ml_probability (Phase 7 fills this in — until then,
use raw ml_probability and mark the field provisional), cross_window_
agreement, evidence_score, rule_ml_agreement/penalty.

EVIDENCE SCORE — define precisely:
  Consider only evidence items with status in {PASS, FAIL} (exclude
  NOT_RUN and UNAVAILABLE from the denominator — they are not evidence
  of anything). evidence_score = count(PASS) / (count(PASS)+count(FAIL)).
  If no evidence was evaluated at all, evidence_score = 0.0 and the
  result must carry a "no_verification_possible" flag — never default
  this to a hidden 0.5 or similar.

WEIGHT DETERMINATION — do this properly, not by hand-picking numbers:
  Build a small held-out calibration set (synthetic signals with known
  ground truth, disjoint from anything used to train the classifier or
  the rule thresholds — split BY SIGNAL INSTANCE, never by sample).
  For each instance, compute (calibrated_ml_probability or provisional
  ml_probability, cross_window_agreement, evidence_score, rule_ml_
  agreement as 0/1) as features, and whether the top hypothesis matched
  ground truth (0/1) as the label. Fit a logistic regression on this set.
  The fitted coefficients ARE your w1..w4 — print them, store them
  versioned in a config file, and this is what lets you say in a viva
  "here are the weights and here is the data they were fit on" instead
  of "we picked numbers that felt right." If you do not yet have enough
  held-out data to fit this meaningfully (document the minimum N you'd
  want), fall back explicitly to manually-set weights BUT the output
  must be labeled "manual_weights: true" and must NOT be called
  calibrated anywhere until Phase 7 actually validates it.

  raw_hybrid_score = logistic_regression.predict_proba(features) if fitted,
  else the manual linear combination, clipped to [0,1] either way.

RULE-VS-ML PENALTY: implemented as one of the four input features to the
logistic regression above (not a separately bolted-on subtraction) so its
actual learned effect is transparent rather than asserted.

Produce this object: prediction, ml_probability, calibrated_ml_probability
(null until Phase 7), cross_window_agreement, evidence_score,
rule_prediction, ml_prediction, rule_ml_agreement, raw_hybrid_score,
final_confidence, confidence_version, weight_source: "fitted"|"manual".

Tests — construct four labeled cases and assert final_confidence behaves
correctly relative to each other (not exact values, since those depend on
your fitted weights):
  A: strong ML + strong window agreement + strong evidence + rule agrees
     -> confidence in top quartile
  B: strong ML + poor window agreement + weak evidence + rule disagrees
     -> confidence substantially lower than A
  C: moderate ML + excellent verification + agreement -> moderate/high
  D: strong ML + strong rule/ML disagreement -> confidence measurably
     reduced vs. an otherwise-identical agreeing case
Also assert: output always in [0,1], deterministic given identical input,
no hardcoded 95 anywhere in the codebase (grep for it as a test).

At the end: run pytest and paste output; print the fitted logistic
regression coefficients (or state explicitly that manual weights are in
use and why); show one full worked example of each of cases A-D with
actual computed numbers.
```

---

## PROMPT 7 — CALIBRATION + RELIABILITY DIAGRAM

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 7:
CONFIDENCE CALIBRATION + RELIABILITY DIAGRAM.

Use labelled synthetic data, split BY SIGNAL INSTANCE (never by sample —
samples from one generated signal must never appear on both sides of the
split). Vary modulation, SNR, phase offset, CFO, and timing across the
sweep; document the exact generation parameters used — do not call this
"realistic" without justifying it against real captures where possible.

A. Classifier calibration: wrap the trained RandomForest with
   CalibratedClassifierCV using whatever exact API the Phase 0.5 report
   confirmed for the installed scikit-learn version — do not assume a
   signature from memory. Architecture stays: RandomForest -> probability
   calibration -> calibrated_ml_probability. Fill this field into the
   Phase 6 confidence engine's previously-null field once available.

B. Reliability diagram: bucket predictions into confidence deciles
   (0-10%, ..., 90-100%). Per bucket compute mean predicted confidence
   and empirical accuracy. Plot both against the ideal diagonal. Report
   per-bucket sample count (a bucket with n<10 should be flagged as low-
   confidence-in-the-calibration-estimate-itself, not silently plotted
   as if it were reliable).

C. Compute and report actual calibration metrics: Expected Calibration
   Error (ECE) and Brier score, both on the held-out set, both saved to
   a machine-readable file — not just eyeballed off the plot.

D. Critical distinction to preserve in code and naming: raw ML
   probability != calibrated ML probability != final hybrid confidence.
   If you want to claim the FINAL hybrid confidence itself is calibrated
   (not just the underlying ML probability), you must run this same
   reliability-diagram/ECE/Brier procedure again on the final_confidence
   output specifically, using a calibration set disjoint from Phase 6's
   weight-fitting set. Do not reuse the same split for both fitting and
   validating — that inflates the calibration metric dishonestly.

Store outputs under bench/: calibration_object, reliability_diagram.png,
calibration_metrics.json (must include dataset id, split details, N,
seed).

Tests: split-by-instance correctness (assert no instance ID appears on
both sides), calibration pipeline runs end-to-end, reliability-bin
construction handles empty/low-count buckets correctly, deterministic
given fixed seed.

At the end: run the calibration; generate and describe the actual plot;
report the actual ECE and Brier numbers; then say explicitly, in one
sentence, whether this system is or is not currently entitled to be
called "calibrated" — and if not yet, what's missing. Never say
"calibrated" just because the code path exists.
```

---

## PROMPT 8 — UNKNOWN ABSTENTION (G7, G10)

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 8:
UNKNOWN ABSTENTION SYSTEM.

Core rule: if final_confidence is below a validated threshold, return
UNKNOWN with a preserved reason. Never return a low-confidence best guess
labeled as if it were a real answer.

THRESHOLD DETERMINATION: do not pick 0.5 or 0.7 because it sounds
reasonable. Using the Phase 7 held-out calibration set, sweep candidate
thresholds and report the false-accept rate (confidently wrong) and
false-reject rate (correctly known but called UNKNOWN) at each. Choose a
threshold against an explicit, stated operating point (e.g. "minimize
false-accept rate subject to false-reject rate <= X%") and document the
rationale, the dataset it came from, and the resulting rates — not a
single unjustified number.

G7 (QPSK near-threshold SNR): construct/consume this case; verify
behavior transitions appropriately as SNR approaches the threshold region
— the system must not confidently emit a wrong label there. Preserve raw
ml_probability, calibrated_ml_probability, raw_hybrid_score,
final_confidence, and output label for inspection.

G10 (noise only): construct/consume this case. Expected: UNKNOWN, every
time, regardless of what the raw classifier alone would have guessed. If
the classifier alone produces a strong wrong-class score, the evidence
system must still override it to UNKNOWN — record this override
explicitly in the evidence ledger so it's visible, not silently hidden.

If a low-SNR reject guard already exists elsewhere in the pipeline,
integrate with it rather than building a second, conflicting one.

Tests: clean known signal -> confident correct label; near-threshold
signal -> transition behavior; noise-only -> UNKNOWN; high-ML/weak-
evidence case -> UNKNOWN or reduced confidence, your choice, but explain
which and why; rule/ML disagreement case -> visibly reduced confidence;
unsupported modulation -> explicit unsupported state, not a silent
default guess; missing evidence -> does not count as passing evidence.

At the end: run pytest and paste output; show G7 and G10 results with the
actual computed numbers at each stage, not just the final label.
```

---

## PROMPT 9 — REPLAY MODE

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 9:
REPLAY MODE.

Every successful upstream analysis result gets a deterministic cache
artifact, keyed so that a different capture can never accidentally reuse
the wrong cache (hash the input file, not just a filename). Cache
metadata: capture_id/hash, analysis schema_version, timestamp, source
mode, generation parameters where synthetic.

If Octave (or any live upstream stage) is unavailable: auto-detect this,
allow explicit Replay-mode selection, validate the cached schema before
using it, continue through the rest of the pipeline normally. Replay
output must be labeled REPLAY in result.json's source_mode field —
never silently presented as LIVE. Never auto-fallback from a failed live
run to Replay without surfacing that state change to whoever's running
the demo.

Cache corruption must fail loudly, not silently return stale/garbage
data. Add explicit CLI states: LIVE, REPLAY, STUB, ERROR — the CLI output
from Phase 2 should already show per-stage state; extend it to show
Replay explicitly.

Tests: cache write/read round-trip, cache invalidation, wrong-capture
cache mismatch is caught, corrupted cache fails loudly (not silently),
missing-Octave triggers correct fallback path, Replay result is
schema-equivalent to a live result modulo the source_mode field.

At the end: run pytest and paste output; demonstrate one live-or-stub run
and one Replay run side by side, showing the source_mode field differs
and nothing else about the schema breaks.
```

---

## PROMPT 10 — GOLDEN SET + BENCHMARK INTEGRATION

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 10:
GOLDEN TEST BENCH + INTEGRATION VALIDATION.

Golden set (generate via the project's own encode chain — see the
Dataset Directive: no public dataset provides these):
G1  QPSK, uncoded
G2  BPSK + convolutional K=7 + block interleave
G3  8-PSK + RS(255,223) + diagonal interleave
G4  16-QAM + LDPC + pseudo-random interleave + CFO/phase offset
G5  2-FSK/4-FSK + concatenated coding
G6  BPSK + convolutional interleave + fading
G7  QPSK near-threshold SNR
G8  wideband, 4 emissions (only if the scanner exists — else skip and say so)
G9  headerless raw int16, big-endian, I/Q swapped
G10 noise only
R1-R3  real IQ + public satellite recordings, for ladder-level validation
       on genuinely real data

Not every case is yours to generate (G3/G4/G5/G6 need Arpit's encoder,
G1/G9 need Sinchana's ingest). Build the interfaces so each case can flow
through your engine once the upstream piece exists; use stubs honestly
where it doesn't yet.

For each available case, record: input id, synthetic/real/replay, true
modulation if known, predicted modulation, final_confidence, unknown
state, ladder_level, hypothesis rank, full evidence, rule/ML predictions
and agreement, pass/fail against ground truth, runtime.

Classifier reporting: train/test size, split-by-instance confirmation,
accuracy, confusion matrix, per-class results, accuracy-vs-SNR if
available.

Confidence reporting: calibration result (from Phase 7), reliability
diagram reference, chosen threshold and its rationale (from Phase 8),
coverage/abstention rate, any incorrect-but-confident cases found (report
these honestly — they are the most important failure mode to disclose).

LEAKAGE GUARD: write an explicit test proving no signal instance appears
on both sides of any train/test/calibration split anywhere in the system.

Store seeds, config, model version, feature version, and test data
identifiers for full reproducibility. Every number in the final report
must trace to a file under bench/.

Success criterion is NOT "100% accuracy" — it is measurable performance,
honest failure reporting, reproducibility, evidence-backed confidence, and
correct UNKNOWN behavior on G7/G10.

At the end: generate bench/report.json and bench/report.md. Do not report
success on anything that actually failed. Run pytest and paste output.
```

---

## PROMPT 11 — REAL TEAM INTEGRATION

```
Continue the SpectralQ Archit implementation. Implement ONLY Phase 11:
REAL TEAM INTEGRATION — replace stubs with actual outputs from Sinchana,
Arpit, and Harsh.

SINCHANA: consume real analysis.json. Do not recompute her DSP features.
Validate schema, provenance, known-vs-estimated fields, uncertainty
fields, sub-window info, feature availability (some features may be
legitimately absent — handle that as UNAVAILABLE, not as zero).

ARPIT: consume real decoder output — demodulated bits, decoder status,
interleaver/FEC result, CRC result if present, BER/re-encode evidence if
present, explicit failure status if decoding failed. Do not duplicate his
decoder logic inside your integration layer.

HARSH: consume real classifier predictions and probabilities. Validate
feature name/order compatibility against your Phase 1 schema explicitly
— if his feature vector doesn't match, fail loudly with a specific
mismatch report, don't silently reorder and hope. Do not retrain his
model inside this integration layer.

Run the full chain: analysis -> feature/classifier integration -> rule
path -> N5 -> hypothesis engine -> evidence ledger -> ladder_level ->
calibrated probability -> hybrid confidence -> UNKNOWN threshold ->
result.json.

Once result.json is confirmed working end-to-end with real (not stub)
data from all three teammates: FREEZE the schema. Document the freeze
explicitly in /docs with a version tag. Do not casually rename fields
after this point — anyone downstream (Himanshu, benchmark scripts) is now
depending on this exact shape.

REAL DATA: run against whatever real captures the team has, and public
recordings once provenance/licensing is confirmed. The "Zigbee" label
must NOT be carried into this system — use "real IQ capture, protocol not
independently verified" unless someone has actually checked the capture's
measured parameters (sample rate, burst bandwidth/duration) against
802.15.4's documented PHY and confirmed a match.

At the end: run the full end-to-end chain on real inputs; report which
ladder level each real capture actually reached, honestly, including any
that only got to L2; show one or two full example result.json files; run
pytest and paste output.
```

---

## PROMPT 12 — FINAL AUDIT, RELEASE, DEMO HARDENING

```
You are now performing the FINAL ENGINEERING AUDIT of the Archit
implementation. Add no new architecture, no new features, no redesign.
Audit only what has actually been built.

1. ARCHITECTURE AUDIT — confirm the implementation still matches:
   analysis.json -> ML+rule path -> N5 -> hypothesis engine -> evidence
   ledger + ladder_level -> N2 confidence -> UNKNOWN -> result.json.
   Flag any unauthorized deviation.

2. FAKE-CLAIM AUDIT — grep the entire repository (code, README, docs,
   comments) for: "95.0", "95%", "100% accuracy", "zero false rejection",
   "calibrated", "real-time", "Zigbee", "LDPC", "Octave", "100% coverage".
   For every hit, classify it as: real measured fact (cite the file/test
   that produced it) / test fixture / documentation / outdated claim /
   unsupported claim. Remove or correctly relabel anything unsupported.

3. CONFIDENCE AUDIT — no hardcoded confidence anywhere; raw ML probability
   is distinct from calibrated probability is distinct from hybrid score;
   final confidence always in [0,1]; N5 disagreement measurably reduces
   confidence; missing evidence never counts as positive; UNKNOWN is
   actually reachable.

4. CALIBRATION AUDIT — held-out data was genuinely used; no signal-
   instance leakage anywhere (rerun the Phase 10 leakage guard); a
   reliability diagram and ECE/Brier score exist and are saved; if these
   artifacts don't exist, the system must NOT be described as calibrated
   anywhere in the repo.

5. UNKNOWN AUDIT — rerun G7 and G10, paste the actual results.

6. EVIDENCE AUDIT — for one successful case, show why the top hypothesis
   won; for one uncertain/failed case, show why the system refused or how
   it ranked alternatives.

7. REPRODUCIBILITY — run the complete pytest suite, the CLI smoke test,
   the end-to-end test, the Replay test, and a clean-install test if the
   environment allows. Paste all actual output.

8. REPO HYGIENE — check README accuracy, install/clone commands actually
   point at this repo (not a placeholder), no secrets committed, no dead
   unused architecture, licenses present where required, deterministic
   test setup, clear version tags.

9. DEMO REQUIREMENT — confirm input -> analysis -> classifier -> rule
   path -> N5 -> hypotheses -> evidence -> confidence -> UNKNOWN/label ->
   result.json runs as one command, with the GUI doing zero computation.

10. FINAL REPORT — produce docs/FINAL_AUDIT.md containing: what's fully
    implemented, what's partial, what's stubbed, what's unsupported, what's
    tested, what's calibrated vs. not, the actual G7 result, the actual G10
    result, real-data results by ladder level, remaining risks, the exact
    demo command, and the exact supported modulation/FEC/interleaver list.
    Every line must distinguish REAL / SYNTHETIC / REPLAY / STUB /
    UNSUPPORTED. Do not inflate anything.

Finally: run pytest, run the CLI, leave the repo in a clean committable
state, and summarize exactly what changed in this final pass. Nothing in
this report may be a claim that can't be traced to a specific file or
test output you actually ran in this session.
```

---

## Appendix A — Definition of Done (master checklist, keep this open while working)

- [ ] No constant confidence value anywhere in the codebase (grep-verified)
- [ ] `ml_probability`, `calibrated_ml_probability`, `raw_hybrid_score`, `final_confidence` are four distinct, correctly-ordered fields — never conflated
- [ ] N5 disagreement is a first-class recorded evidence item, not a silent override
- [ ] `ladder_level` is computed, not manually set, and all five levels are reachable in tests
- [ ] LDPC is either really implemented or explicitly marked unsupported everywhere — never faked
- [ ] Reliability diagram + ECE + Brier score exist as saved files before the word "calibrated" appears anywhere
- [ ] Train/test/calibration splits are all by signal instance, with an explicit leakage-guard test
- [ ] UNKNOWN is reachable and is the actual output on G10 (noise) every time
- [ ] Replay output is labeled REPLAY, never presented as LIVE
- [ ] Every number in bench/report.md traces to a file
- [ ] README clone URL points at the real repo
- [ ] Git history shows incremental commits, not a single dump

## Appendix B — Kill-switch phrase

If the agent starts asserting results without showing the code/test that produced them, paste:

> **"Stop. Show me the exact file and test that produced that number. If it doesn't exist, say so and mark it TODO."**

If it starts adding scope (LDPC breadth, wideband scanner, protocol fingerprinting, Octave features not yet real):

> **"That's outside this phase. Note it as a roadmap item and return to the current prompt's scope only."**
