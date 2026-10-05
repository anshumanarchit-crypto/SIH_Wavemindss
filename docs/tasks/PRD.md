# SpectralQ SIH26147 — FINAL RELEASE HARDENING PRD

STATUS:
FINAL HARDENING ONLY

IMPORTANT:
This is an existing mature project.

Do NOT rewrite the architecture.
Do NOT create a new application.
Do NOT add unrelated features.
Do NOT modify tests just to make them pass.

Complete exactly one task per Ralph iteration.

============================================================
TASK 1 — BASELINE + PROTECT CURRENT PASSING STATE
============================================================

Run:

pytest -q tests/test_candidate_decoder_search.py -s
pytest -q tests/test_runtime_truth_isolation.py
pytest -q tests/test_truth_isolation_runtime.py
pytest -q tests/test_crc_integrity.py
pytest -q tests/test_reencode_integrity.py
pytest -q tests/test_phase7_calibration.py

Record exact results in progress.txt.

Do not modify production code unless needed to preserve a broken baseline.

DONE WHEN:
Baseline is recorded and current passing behavior is known.

============================================================
TASK 2 — WIRE REAL CALIBRATION INTO LIVE VALIDATION
============================================================

Trace:

classifier
→ raw ML probability
→ calibration
→ calibrated probability
→ confidence
→ final_case_matrix.json.

Current known issue:

The live G1-G10 matrix may show:
calibration_status = NOT_AVAILABLE
calibrated_ml_probability = null

even though calibration infrastructure exists.

Fix the actual live integration.

Requirements:

raw_ml_probability remains raw.

calibrated_ml_probability appears only when the actual calibrator runs.

calibration_status must reflect reality.

Do not use heuristic multipliers.

Do not fabricate values.

Add or update tests.

Verify:

pytest -q tests/test_phase7_calibration.py

Regenerate validation artifacts.

DONE WHEN:
The live case matrix accurately reports actual calibration execution.

============================================================
TASK 3 — CRC LIVE SEMANTICS
============================================================

Inspect the real frame structure of the golden cases.

For every case determine:

A. CRC actually exists and can be checked
B. CRC does not exist
C. CRC cannot be checked because framing is unresolved.

Use:

PASS
FAIL
NOT_PRESENT
NOT_RUN

with an explicit reason.

Never fabricate CRC.

Never mark CRC PASS unless genuinely computed.

Preserve the existing CRC integrity tests.

Verify:

pytest -q tests/test_crc_integrity.py

DONE WHEN:
The live case matrix contains truthful, explicit CRC status.

============================================================
TASK 4 — EXACT MODEL DEPENDENCY REPRODUCIBILITY
============================================================

Determine the exact scikit-learn version compatible with:

models/baseline_rf.joblib

Pin the compatible version in requirements.txt.

Inspect compatibility of:
numpy
scipy
joblib
threadpoolctl

Create a fresh environment.

Install requirements.

Load model.

Ensure no unexpected serialization version warning occurs.

DONE WHEN:
Fresh environment can load the shipped model reproducibly.

============================================================
TASK 5 — CANDIDATE DECODER REGRESSION LOCK
============================================================

DO NOT regress current passing candidate search.

Run:

pytest -q tests/test_candidate_decoder_search.py -s

It must remain:

3 passed
0 failed.

Explicitly verify:

G2:
BPSK + conv_viterbi_k7 + block
reencode BER = 0.0

G6:
BPSK + conv_viterbi_k7 + convolutional
reencode BER = 0.0

LDPC candidate genuinely reaches the LDPC decoder.

Requested FEC must never silently become none.

Requested interleaver must never silently become none.

DONE WHEN:
Candidate decoder suite passes without weakening assertions.

============================================================
TASK 6 — HYPOTHESIS / TRUTH / CACHE INTEGRITY
============================================================

Ensure authoritative winner is produced by HypothesisEngine.

No ML-only override.

No filename inference.

No case-ID inference.

No truth.json runtime access.

Candidate-specific cache isolation must be preserved.

Run:

pytest -q tests/test_runtime_truth_isolation.py
pytest -q tests/test_truth_isolation_runtime.py
pytest -q tests/test_adversarial_capture_renaming.py

DONE WHEN:
Winner and decoder state are consistent and truth isolation remains clean.

============================================================
TASK 7 — REGENERATE ALL VALIDATION ARTIFACTS
============================================================

Run:

python scripts/generate_validation_artifacts.py
python scripts/generate_validation_reports.py

Regenerate:

final_acceptance.json
final_case_matrix.json
final_runtime_manifest.json
classification_report.json
confusion_matrix.json
cross_layer_consistency.json

Eliminate stale contradictions.

Do not manually edit generated JSON.

Report separately:

decision safety
exact modulation accuracy
exact FEC accuracy
exact interleaver accuracy
exact receiver verification
safe UNKNOWN rate
false-confident rate.

Do NOT describe UNKNOWN as exact decoding.

DONE WHEN:
All reports match current runtime execution.

============================================================
TASK 8 — COMPLETE REGRESSION + UI
============================================================

Run:

pytest -q tests/test_spectralq_extended_suite.py
pytest -q tests/test_production_ui_v2.py
pytest -q tests/test_himanshu_gui.py
pytest -q

Required release state:

0 failed.

Critical release suite:
0 skipped.

If a failure is found:
fix production root cause.

Do not weaken test semantics.

DONE WHEN:
Full regression is green.

============================================================
TASK 9 — FINAL RELEASE PACKAGE
============================================================

Ensure:

git status clean

Commit final code.

Build:

spectralq_final_submission.zip

from exact HEAD.

Exclude:

.git
__pycache__
.pytest_cache
.venv
scratch
temporary files
nested ZIPs
credentials
machine-specific files.

Calculate SHA256.

DONE WHEN:
ZIP exactly matches verified HEAD.

============================================================
TASK 10 — FRESH ARCHIVE VERIFICATION + FREEZE
============================================================

Extract the final ZIP to:

FINAL_CLEAN_RELEASE_TEST

into an empty directory.

Create a fresh venv.

Install requirements.txt.

Run:

pytest -q tests/test_candidate_decoder_search.py -s
pytest -q tests/test_final_hardening_verification.py
pytest -q tests/test_spectralq_extended_suite.py
pytest -q tests/test_runtime_truth_isolation.py
pytest -q tests/test_crc_integrity.py
pytest -q tests/test_reencode_integrity.py

Then run a final application smoke test.

Compare outputs against release artifacts.

Only when:

Candidate decoder PASS
Final hardening PASS
Calibration live path PASS
CRC semantics PASS/N/A with reason
G2 BER 0
G6 BER 0
LDPC genuine attempt
Truth isolation PASS
Renaming PASS
Extended suite 29/29
Full regression 0 failed
UI PASS
Fresh install PASS
Fresh archive PASS
Git CLEAN
SHA256 recorded
Reports consistent

mark the project:

FROZEN

After FREEZE:
NO FEATURE DEVELOPMENT.
NO MODEL CHANGES.
NO DSP CHANGES.
NO THRESHOLD CHANGES.
NO TEST-GAMING.
NO REFACTORING.

Only final release documentation/packaging corrections are permitted.

============================================================
COMPLETION
============================================================

When all tasks are done, write:

RALPH COMPLETE

and record:

commit
archive
sha256
full test totals
candidate decoder result
final hardening result
calibration result
CRC result
G2 result
G6 result
LDPC result
truth isolation
extended suite
fresh archive verification
final limitations.

Never claim a result that was not actually observed.