"""
SpectralQ — Extended Test Suite (v2): Realistic Impairments + System-Level Checks
===================================================================================

WHY THIS EXISTS
----------------
The original adversarial suite (G1-G10 + boundary/invariance/UNKNOWN/leakage
tests) checks whether the ML+rule+N5+confidence chain is honest on
synthetic, single-impairment signals. This file goes two directions further:

  A. REALISTIC COMPOUND IMPAIRMENTS — real receivers are never just "clean
     signal + AWGN." They have IQ gain/phase imbalance, DC offset from LO
     leakage, clipping under strong signals, a second emitter in the same
     band, and bursts that don't line up neatly with your capture window.
     None of this is exotic — it's Tuesday for anyone who's touched an SDR.

  B. SYSTEM-LEVEL / "IS THE ML LYING AT SCALE" CHECKS — these need volume
     (dozens to hundreds of pipeline calls) and answer questions no single
     test case can: Is final_confidence actually calibrated (ECE)? Does
     every class clear a recall floor, or is one easy class dragging the
     average? Is the pipeline deterministic? Does latency blow up on longer
     captures? Do float and quantized model paths agree? Does a "small fix"
     silently regress something that used to work (golden master)?

None of these are "does it get the easy case right" — that's G1-G10. These
are built to be hard to fake: a system that's actually doing the work will
pass all of them; a system doing the minimum to look done will fail several,
loudly, with a specific reason printed in the assertion message.

HOW TO USE
----------
1. Wire run_pipeline() exactly as you did for the original suite (same
   adapter contract: dotted-path get() on a result.json-shaped dict).
2. Optionally wire run_pipeline_quantized() if you have a separate
   int8/on-device inference path — only needed for TestQuantizationConsistency,
   everything else works without it (that class self-skips).
3. Optionally set TestRealCLIInvocation.CLI_CMD to your actual demo entry
   point — self-skips if left as None.
4. Set TestLatencyBudget.MAX_LATENCY_S to your real target before trusting
   that test's pass/fail.
5. pip install numpy scipy pytest --break-system-packages (if not already).
6. Run everything:        pytest test_spectralq_extended_suite.py -v -s
   Run just the fast half: pytest test_spectralq_extended_suite.py -v -s \\
                                -k "not Calibration and not Fairness and not GoldenMaster"

As with the original suite: if a test fails because a field name differs,
fix the adapter/get() calls — do not loosen the assertion to make it pass.
"""

import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent
if not (REPO_ROOT / "bench").exists() and (REPO_ROOT.parent / "bench").exists():
    REPO_ROOT = REPO_ROOT.parent

# Wire real pipeline entry point
from spectralq.pipeline.runner import run_samples


# =====================================================================
# 0. PIPELINE ADAPTERS
# =====================================================================

def run_pipeline(iq: np.ndarray, fs_hz: float, meta: dict | None = None) -> dict:
    """Real SpectralQ pipeline adapter running full live DSP and ML pipeline."""
    meta = meta or {}
    res = run_samples(iq=iq, fs_hz=fs_hz, meta=meta, mode="live")
    d = res.result.model_dump(mode="json")
    # Adapter contract: normalize internal hyphenated modulation names (e.g. '8-PSK' -> '8PSK')
    if "top_hypothesis" in d and isinstance(d["top_hypothesis"], dict):
        if "modulation" in d["top_hypothesis"]:
            d["top_hypothesis"]["modulation"] = d["top_hypothesis"]["modulation"].replace("-", "")
    if "ml_prediction" in d and isinstance(d["ml_prediction"], str):
        d["ml_prediction"] = d["ml_prediction"].replace("-", "")
    if "rule_prediction" in d and isinstance(d["rule_prediction"], str):
        d["rule_prediction"] = d["rule_prediction"].replace("-", "")
    return d


def run_pipeline_quantized(iq: np.ndarray, fs_hz: float, meta: dict | None = None) -> dict:
    """Optional: your INT8/on-device inference path. Only TestQuantizationConsistency
    needs this — leave unimplemented and that class will self-skip."""
    raise NotImplementedError(
        "run_pipeline_quantized() not wired up — TestQuantizationConsistency will skip."
    )


def get(result: dict, path: str, default=None):
    cur = result
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


# =====================================================================
# 1. SIGNAL GENERATORS (same core generator as the original suite)
# =====================================================================

CONST = {
    "BPSK": np.array([1, -1]),
    "QPSK": np.exp(1j * (np.pi / 4 + np.arange(4) * np.pi / 2)),
    "8PSK": np.exp(1j * (2 * np.pi * np.arange(8) / 8)),
    "16QAM": np.array(
        [complex(i, q) for i in (-3, -1, 1, 3) for q in (-3, -1, 1, 3)]
    ) / np.sqrt(10),
    "64QAM": np.array(
        [complex(i, q) for i in range(-7, 8, 2) for q in range(-7, 8, 2)]
    ) / np.sqrt(42),
}


def gen_symbols(mod: str, n_symbols: int, rng: np.random.Generator) -> np.ndarray:
    if mod in ("2FSK", "4FSK"):
        n_tones = 2 if mod == "2FSK" else 4
        idx = rng.integers(0, n_tones, n_symbols)
        tones = np.linspace(-1, 1, n_tones)
        return tones[idx]
    alphabet = CONST[mod]
    idx = rng.integers(0, len(alphabet), n_symbols)
    return alphabet[idx]


def synth_capture(
    mod: str,
    n_symbols: int = 4000,
    sps: int = 8,
    fs_hz: float = 200_000.0,
    snr_db: float = 20.0,
    cfo_hz: float = 0.0,
    phase_offset_rad: float = 0.0,
    fading: bool = False,
    seed: int = 0,
) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(seed)

    if mod in ("2FSK", "4FSK"):
        freqs = gen_symbols(mod, n_symbols, rng) * (fs_hz / (4 * sps))
        phase = 2 * np.pi * np.cumsum(np.repeat(freqs, sps)) / fs_hz
        iq = np.exp(1j * phase)
    else:
        symbols = gen_symbols(mod, n_symbols, rng)
        iq = np.repeat(symbols, sps)

    t = np.arange(len(iq)) / fs_hz
    iq = iq * np.exp(1j * (2 * np.pi * cfo_hz * t + phase_offset_rad))

    if fading:
        fade_env = np.abs(
            rng.normal(0, 1, len(iq) // 200 + 1)
            + 1j * rng.normal(0, 1, len(iq) // 200 + 1)
        )
        fade_env = np.repeat(fade_env, 200)[: len(iq)]
        fade_env = fade_env / fade_env.mean()
        iq = iq * fade_env

    sig_power = np.mean(np.abs(iq) ** 2)
    noise_power = sig_power / (10 ** (snr_db / 10))
    noise = np.sqrt(noise_power / 2) * (
        rng.normal(0, 1, len(iq)) + 1j * rng.normal(0, 1, len(iq))
    )
    iq_noisy = (iq + noise).astype(np.complex64)

    truth = dict(
        modulation=mod, sps=sps, fs_hz=fs_hz, snr_db=snr_db, cfo_hz=cfo_hz,
        phase_offset_rad=phase_offset_rad, fading=fading, seed=seed,
    )
    return iq_noisy, truth


# =====================================================================
# 2. NEW IMPAIRMENT GENERATORS
# =====================================================================

def apply_iq_imbalance(iq: np.ndarray, gain_db: float = 0.5, phase_deg: float = 3.0) -> np.ndarray:
    """Standard receiver IQ gain+phase imbalance model."""
    g = 10 ** (gain_db / 20.0)
    phi = math.radians(phase_deg)
    I, Q = iq.real, iq.imag
    Q_out = g * (Q * math.cos(phi) - I * math.sin(phi))
    return (I + 1j * Q_out).astype(iq.dtype)


def apply_dc_offset(iq: np.ndarray, offset_frac: float = 0.3) -> np.ndarray:
    """LO-leakage-style DC offset, sized relative to signal RMS."""
    sig_rms = np.sqrt(np.mean(np.abs(iq) ** 2))
    offset = offset_frac * sig_rms * (1 + 1j)
    return (iq + offset).astype(iq.dtype)


def apply_clipping(iq: np.ndarray, clip_frac: float = 0.4) -> np.ndarray:
    """Hard amplitude clip at clip_frac of the signal's peak (smaller = harsher)."""
    peak = np.max(np.abs(iq))
    thresh = clip_frac * peak
    mag = np.abs(iq)
    scale = np.minimum(1.0, thresh / np.maximum(mag, 1e-12))
    return (iq * scale).astype(iq.dtype)


def mix_signals(iq_a: np.ndarray, iq_b: np.ndarray, sir_db: float = 3.0) -> np.ndarray:
    """Sum two captures with iq_b scaled to hit the target signal-to-interference ratio."""
    n = min(len(iq_a), len(iq_b))
    a, b = iq_a[:n], iq_b[:n]
    pa = np.mean(np.abs(a) ** 2)
    pb = np.mean(np.abs(b) ** 2)
    target_pb = pa / (10 ** (sir_db / 10))
    b_scaled = b * np.sqrt(target_pb / max(pb, 1e-12))
    return (a + b_scaled).astype(np.complex64)


def random_search_perturb(iq, run_pipeline_fn, fs_hz, truth, budget_frac=0.03, iters=25, seed=0):
    """Black-box fragility probe: adds unstructured noise worth budget_frac of
    signal RMS, repeatedly, and reports the first flip found (or None)."""
    rng = np.random.default_rng(seed)
    sig_rms = np.sqrt(np.mean(np.abs(iq) ** 2))
    budget = budget_frac * sig_rms
    base = run_pipeline_fn(iq, fs_hz, truth)
    base_label = get(base, "top_hypothesis.modulation")
    for i in range(iters):
        perturb = budget * (rng.normal(0, 1, len(iq)) + 1j * rng.normal(0, 1, len(iq))) / np.sqrt(2)
        candidate = (iq + perturb).astype(iq.dtype)
        r = run_pipeline_fn(candidate, fs_hz, truth)
        if get(r, "top_hypothesis.modulation") != base_label and get(r, "final_confidence", 0) > 0.7:
            return True, i, r
    return False, None, None


# =====================================================================
# A. REALISTIC COMPOUND IMPAIRMENTS
# =====================================================================

class TestIQImbalance:
    """FAILURE MEANS: feature extraction implicitly assumes a perfectly
    balanced receiver front end. Real hardware never is — a few percent
    gain/phase imbalance is normal and must not break an otherwise-easy call."""

    @pytest.mark.parametrize("gain_db,phase_deg", [(0.3, 2.0), (1.0, 5.0), (2.5, 8.0)])
    def test_mild_to_moderate_iq_imbalance_survives(self, gain_db, phase_deg):
        iq, truth = synth_capture("16QAM", snr_db=20.0, seed=10)
        imbalanced = apply_iq_imbalance(iq, gain_db=gain_db, phase_deg=phase_deg)
        r = run_pipeline(imbalanced, truth["fs_hz"], truth)
        pred = get(r, "top_hypothesis.modulation")
        conf = get(r, "final_confidence", 0.0)
        if gain_db <= 1.0 and phase_deg <= 5.0:
            assert pred == "16QAM", (
                f"Realistic receiver IQ imbalance ({gain_db}dB gain, {phase_deg}deg "
                f"phase) on a clean 20dB signal flipped the prediction to {pred} — "
                f"imbalance likely isn't being corrected or tolerated at all."
            )
        elif pred != "16QAM":
            assert get(r, "unknown") or conf < 0.6, (
                f"At the higher end of realistic imbalance, wrong prediction "
                f"{pred} was still reported at confidence={conf}."
            )


class TestDCOffset:
    """FAILURE MEANS: LO leakage / DC offset (extremely common in
    direct-conversion receivers) isn't being removed before feature
    extraction — a normal receiver imperfection reads as part of the signal."""

    @pytest.mark.parametrize("offset_frac", [0.1, 0.3, 0.6])
    def test_dc_offset_at_realistic_levels(self, offset_frac):
        iq, truth = synth_capture("QPSK", snr_db=18.0, seed=12)
        offset_iq = apply_dc_offset(iq, offset_frac=offset_frac)
        r = run_pipeline(offset_iq, truth["fs_hz"], truth)
        pred = get(r, "top_hypothesis.modulation")
        if offset_frac <= 0.3:
            assert pred == "QPSK", (
                f"A {offset_frac:.0%}-of-RMS DC offset (normal LO-leakage range) "
                f"broke classification — check for a missing mean-removal step "
                f"before cumulant computation."
            )


class TestClippingSaturation:
    """FAILURE MEANS: cumulant-based features are highly sensitive to hard
    clipping (it directly corrupts the higher-order moments they're built
    from). The system should degrade gracefully under saturation, not stay
    falsely confident."""

    @pytest.mark.parametrize("clip_frac", [0.7, 0.4, 0.15])
    def test_clipping_degrades_confidence_not_silently_wrong(self, clip_frac):
        iq, truth = synth_capture("8PSK", snr_db=20.0, seed=13)
        clipped = apply_clipping(iq, clip_frac=clip_frac)
        r = run_pipeline(clipped, truth["fs_hz"], truth)
        pred = get(r, "top_hypothesis.modulation")
        conf = get(r, "final_confidence", 0.0)
        if pred != "8PSK":
            assert get(r, "unknown") or conf < 0.6, (
                f"Clipping at {clip_frac:.0%} of peak amplitude produced a "
                f"WRONG and CONFIDENT ({conf}) prediction ({pred}) instead of hedging."
            )


class TestCoChannelInterference:
    """FAILURE MEANS: with a second, weaker emitter present in the same
    capture (very common in any real spectrum), the system silently reports
    one of the two signals with high confidence instead of reflecting the
    added ambiguity — a classic way a demo looks great on isolated bursts
    and falls apart on a real recording."""

    @pytest.mark.parametrize("sir_db", [10.0, 3.0, 0.0])
    def test_interferer_reduces_confidence_or_flags_ambiguity(self, sir_db):
        iq_main, truth = synth_capture("QPSK", snr_db=20.0, seed=14)
        iq_interferer, _ = synth_capture("16QAM", snr_db=20.0, seed=15)
        mixed = mix_signals(iq_main, iq_interferer, sir_db=sir_db)
        r = run_pipeline(mixed, truth["fs_hz"], truth)
        pred = get(r, "top_hypothesis.modulation")
        conf = get(r, "final_confidence", 0.0)
        if sir_db <= 3.0:
            assert get(r, "unknown") or conf < 0.7, (
                f"At SIR={sir_db}dB (interferer nearly as strong as the signal "
                f"of interest), pipeline still reported {pred} at confidence="
                f"{conf} — co-channel interference isn't being detected at all."
            )


class TestBurstBoundaryInstability:
    """FAILURE MEANS: a capture that genuinely contains two different
    modulations back-to-back (a realistic scanner scenario — one window
    straddling two bursts) is silently collapsed into a single confident
    answer instead of surfacing instability via cross_window_agreement."""

    def test_modulation_switch_mid_capture_is_visible_in_the_output(self):
        iq_a, truth_a = synth_capture("BPSK", snr_db=20.0, n_symbols=2000, seed=16)
        iq_b, _ = synth_capture("64QAM", snr_db=20.0, n_symbols=2000, seed=17)
        iq = np.concatenate([iq_a, iq_b])
        r = run_pipeline(iq, truth_a["fs_hz"], truth_a)
        agreement = get(r, "cross_window_agreement")
        assert agreement is not None and agreement < 0.9, (
            f"A capture that is literally BPSK for the first half and 64QAM "
            f"for the second half reported cross_window_agreement={agreement} "
            f"— per-window predictions probably aren't independent, or aren't "
            f"being aggregated at all."
        )


class TestAdversarialPerturbationFragility:
    """FAILURE MEANS (soft signal, not an auto-disqualifier): the decision
    boundary is razor-thin — tiny, unstructured extra noise (far below what
    would push SNR into a genuinely hard range) is enough to flip a
    *confident* prediction. Black-box probe only (no model internals), so a
    flip here is a flag to investigate — and it usually correlates with a
    calibration problem (see TestConfidenceCalibration below)."""

    @pytest.mark.parametrize("mod", ["QPSK", "16QAM"])
    def test_small_noise_budget_does_not_flip_a_confident_label(self, mod):
        iq, truth = synth_capture(mod, snr_db=22.0, seed=20)
        base = run_pipeline(iq, truth["fs_hz"], truth)
        if get(base, "top_hypothesis.modulation") != mod or get(base, "final_confidence", 0) < 0.8:
            pytest.skip("Baseline isn't a confident correct call — nothing meaningful to probe.")

        flipped, at_iter, flip_result = random_search_perturb(
            iq, run_pipeline, truth["fs_hz"], truth, budget_frac=0.05, iters=20, seed=1
        )
        assert not flipped, (
            f"A random perturbation worth only ~5% of signal RMS flipped {mod} "
            f"to {get(flip_result, 'top_hypothesis.modulation')} while STILL "
            f"reporting confidence={get(flip_result, 'final_confidence')} "
            f"(found at search iteration {at_iter}) — decision boundary sits "
            f"very close to this clean operating point."
        )


# =====================================================================
# B. SYSTEM-LEVEL / "IS THE ML LYING AT SCALE" CHECKS
# =====================================================================

class TestDeterminism:
    """FAILURE MEANS: hidden nondeterminism (uninitialized RNG, unordered
    thread/window aggregation, stale buffers) makes every accuracy number
    you report reproducible only by luck."""

    def test_identical_input_identical_output(self):
        iq, truth = synth_capture("16QAM", snr_db=15.0, seed=101)
        results = [run_pipeline(iq.copy(), truth["fs_hz"], truth) for _ in range(5)]
        labels = {get(r, "top_hypothesis.modulation") for r in results}
        confs = [get(r, "final_confidence", 0.0) for r in results]
        assert len(labels) == 1, f"Same exact input produced different top labels across 5 runs: {labels}"
        assert max(confs) - min(confs) < 1e-6, (
            f"Same exact input produced varying confidence across 5 runs ({confs}) "
            f"— check for uninitialized RNG state, dict/set iteration-order "
            f"dependence, or races in window fusion."
        )


class TestConfidenceCalibration:
    """FAILURE MEANS: final_confidence is a number the model outputs but
    doesn't correspond to anything real. A well-calibrated 0.8 should be
    right ~80% of the time across many trials — not 50%, not 99%. This is
    the single most common way a "confidence engine" turns out to be
    decorative, and it's the test most demo pipelines skip because it needs
    volume (Expected Calibration Error)."""

    N_BINS = 5
    SNR_TRIALS = 12

    def test_expected_calibration_error_bounded(self):
        mods = ["BPSK", "QPSK", "8PSK", "16QAM", "64QAM"]
        snr_range = np.linspace(-4, 22, self.SNR_TRIALS)
        records = []
        for mod in mods:
            for i, snr in enumerate(snr_range):
                iq, truth = synth_capture(mod, snr_db=float(snr), seed=1000 + i)
                r = run_pipeline(iq, truth["fs_hz"], truth)
                if get(r, "unknown"):
                    continue  # abstentions excluded, not counted as wrong
                pred = get(r, "top_hypothesis.modulation")
                conf = get(r, "final_confidence", 0.0)
                records.append((conf, pred == mod))

        assert len(records) >= 20, "Too few non-abstaining predictions to measure calibration — widen the SNR sweep."

        bins = np.linspace(0, 1, self.N_BINS + 1)
        ece, total, report = 0.0, len(records), []
        for i in range(self.N_BINS):
            lo, hi = bins[i], bins[i + 1]
            bucket = (
                [(c, ok) for c, ok in records if lo <= c <= hi]
                if i == self.N_BINS - 1
                else [(c, ok) for c, ok in records if lo <= c < hi]
            )
            if not bucket:
                continue
            confs_b = [c for c, ok in bucket]
            oks_b = [ok for c, ok in bucket]
            acc = sum(oks_b) / len(oks_b)
            avg_conf = sum(confs_b) / len(confs_b)
            weight = len(bucket) / total
            ece += weight * abs(acc - avg_conf)
            report.append((round(lo, 2), round(hi, 2), len(bucket), round(acc, 2), round(avg_conf, 2)))

        assert ece < 0.20, (
            f"Expected Calibration Error = {ece:.3f} (want < 0.20). "
            f"Per-bin [lo, hi, n, accuracy, avg_confidence]: {report} — "
            f"confidence scores don't track real accuracy."
        )


class TestPerClassFairness:
    """FAILURE MEANS: aggregate accuracy looks fine because one or two easy
    classes drag the average up while a harder class is predicted almost at
    random, or almost never — a training-imbalance smell that a single
    "overall accuracy" number will never reveal."""

    def test_every_supported_class_clears_a_recall_floor(self):
        mods = ["BPSK", "QPSK", "8PSK", "16QAM", "64QAM", "2FSK", "4FSK"]
        floor = 0.7
        per_class = {}
        for mod in mods:
            correct, n = 0, 10
            for seed in range(n):
                iq, truth = synth_capture(mod, snr_db=18.0, seed=2000 + seed)
                r = run_pipeline(iq, truth["fs_hz"], truth)
                if get(r, "top_hypothesis.modulation") == mod:
                    correct += 1
            per_class[mod] = correct / n

        failing = {m: acc for m, acc in per_class.items() if acc < floor}
        assert not failing, (
            f"At a clean 18dB SNR, these classes are below the {floor:.0%} "
            f"recall floor: {failing}. Full breakdown: {per_class} — a class "
            f"this weak at high SNR usually means too few/no training examples."
        )

    def test_predictions_are_not_dominated_by_a_single_class(self):
        mods = ["BPSK", "QPSK", "8PSK", "16QAM", "64QAM", "2FSK", "4FSK"]
        preds = []
        for mod in mods:
            for seed in range(6):
                iq, truth = synth_capture(mod, snr_db=16.0, seed=3000 + seed)
                r = run_pipeline(iq, truth["fs_hz"], truth)
                preds.append(get(r, "top_hypothesis.modulation"))
        counts = Counter(preds)
        top_label, top_count = counts.most_common(1)[0]
        assert top_count / len(preds) < 0.5, (
            f"'{top_label}' accounts for {top_count}/{len(preds)} predictions "
            f"across a balanced batch of all 7 modulations — looks like a "
            f"majority-class shortcut. Full counts: {dict(counts)}"
        )


class TestOutOfDistributionRobustness:
    """FAILURE MEANS: the system was only ever validated on the SNR/fs grid
    used in development and silently guesses outside it, instead of
    recognizing it's outside its competence."""

    @pytest.mark.parametrize("snr_db", [-15.0, -10.0, 35.0])
    def test_extreme_snr_is_handled_safely(self, snr_db):
        iq, truth = synth_capture("QPSK", snr_db=snr_db, seed=42)
        r = run_pipeline(iq, truth["fs_hz"], truth)
        if snr_db < -8:
            assert get(r, "unknown") or get(r, "final_confidence", 1.0) < 0.5, (
                f"At {snr_db}dB SNR (well below usable range), pipeline still "
                f"returned a confident guess: {get(r, 'top_hypothesis.modulation')} "
                f"@ {get(r, 'final_confidence')}"
            )
        else:
            assert get(r, "top_hypothesis.modulation") == "QPSK", (
                f"Pipeline failed on an unusually CLEAN signal ({snr_db}dB) — "
                f"check for an amplitude-range assumption or overflow bug."
            )

    def test_unfamiliar_sample_rate_does_not_silently_misbehave(self):
        iq, truth = synth_capture("QPSK", snr_db=20.0, fs_hz=3_000_000.0, seed=8)
        r = run_pipeline(iq, truth["fs_hz"], truth)
        assert get(r, "ladder_level") is not None, (
            "No ladder_level at an unusual sample rate — likely an unguarded "
            "fs-dependent computation."
        )


class TestLatencyBudget:
    """FAILURE MEANS: a model that's accurate but too slow fails a real
    deployment just as hard as a wrong label does. Set MAX_LATENCY_S to your
    actual target before trusting this test's pass/fail — the number here is
    a placeholder."""

    MAX_LATENCY_S = 30.0  # Real software-DSP budget for 32k-sample burst on CPU

    def test_single_capture_latency(self):
        iq, truth = synth_capture("QPSK", snr_db=15.0, seed=1)
        t0 = time.perf_counter()
        run_pipeline(iq, truth["fs_hz"], truth)
        elapsed = time.perf_counter() - t0
        assert elapsed < self.MAX_LATENCY_S, (
            f"Single-capture inference took {elapsed:.2f}s, over the "
            f"{self.MAX_LATENCY_S}s budget. NOTE: this measures wall time on "
            f"whatever machine runs pytest — re-check on your actual target "
            f"hardware before trusting this number."
        )

    def test_latency_does_not_blow_up_on_longer_captures(self):
        """Catches an accidental O(n^2) step (e.g. a python-level loop over
        samples for something vectorizable) that passes on short test
        captures and only shows up live on a longer real recording."""
        iq_short, truth = synth_capture("QPSK", snr_db=15.0, n_symbols=1000, seed=1)
        iq_long, _ = synth_capture("QPSK", snr_db=15.0, n_symbols=8000, seed=1)

        t0 = time.perf_counter()
        run_pipeline(iq_short, truth["fs_hz"], truth)
        t_short = time.perf_counter() - t0

        t0 = time.perf_counter()
        run_pipeline(iq_long, truth["fs_hz"], truth)
        t_long = time.perf_counter() - t0

        ratio = t_long / max(t_short, 1e-6)
        assert ratio < 12.0, (
            f"8x more samples took {ratio:.1f}x longer ({t_short:.3f}s -> "
            f"{t_long:.3f}s) — worse than linear, check for a non-vectorized "
            f"loop somewhere in feature extraction."
        )


class TestQuantizationConsistency:
    """FAILURE MEANS: the float model you validated and the quantized/on-device
    model you'd actually ship disagree often enough that your bench numbers
    don't describe what a real deployment will see. Self-skips unless
    run_pipeline_quantized() is wired up."""

    def test_float_vs_quantized_agreement_rate(self):
        iq0, truth0 = synth_capture("QPSK", seed=0)
        try:
            run_pipeline_quantized(iq0, truth0["fs_hz"], truth0)
        except NotImplementedError:
            pytest.skip("run_pipeline_quantized() not wired up yet.")

        mods = ["BPSK", "QPSK", "8PSK", "16QAM", "64QAM"]
        agree, total = 0, 0
        for mod in mods:
            for seed in range(8):
                iq, truth = synth_capture(mod, snr_db=14.0, seed=4000 + seed)
                r_float = run_pipeline(iq, truth["fs_hz"], truth)
                r_quant = run_pipeline_quantized(iq, truth["fs_hz"], truth)
                total += 1
                if get(r_float, "top_hypothesis.modulation") == get(r_quant, "top_hypothesis.modulation"):
                    agree += 1
        rate = agree / total
        assert rate >= 0.90, (
            f"Float and quantized models only agree on {agree}/{total} "
            f"({rate:.0%}) cases — quantization is changing predictions often "
            f"enough that bench numbers won't match the deployed model."
        )


class TestStatelessness:
    """FAILURE MEANS: some global/mutable state (a cached CFO estimate, a
    running normalization constant, a leftover buffer) leaks between
    unrelated captures processed in the same process — invisible when every
    test restarts the interpreter, very visible once a real service starts
    processing a stream of back-to-back captures."""

    def test_back_to_back_captures_do_not_influence_each_other(self):
        iq_a, truth_a = synth_capture("BPSK", snr_db=25.0, seed=1)
        iq_b, truth_b = synth_capture("64QAM", snr_db=25.0, seed=2)

        base_a = run_pipeline(iq_a, truth_a["fs_hz"], truth_a)
        assert get(base_a, "top_hypothesis.modulation") == "BPSK"

        results_b = []
        for _ in range(3):
            run_pipeline(iq_a, truth_a["fs_hz"], truth_a)
            results_b.append(run_pipeline(iq_b, truth_b["fs_hz"], truth_b))

        labels_b = {get(r, "top_hypothesis.modulation") for r in results_b}
        assert labels_b == {"64QAM"}, (
            f"64QAM capture produced different labels ({labels_b}) depending "
            f"on what ran before it in the same process — suspect shared "
            f"mutable state between calls."
        )


class TestGoldenMasterRegression:
    """FAILURE MEANS: a "small fix" silently changed behavior on cases that
    used to work. Not a correctness test — it doesn't know what's "right" —
    it's a tripwire that fails loudly the moment output changes on a fixed
    reference set, so a regression gets caught before it's discovered live.
    Run once to record the baseline (auto-writes if missing), then leave it."""

    GOLDEN_PATH = REPO_ROOT / "bench" / "golden_master.json"
    UPDATE = os.environ.get("SPECTRALQ_UPDATE_GOLDEN", "").lower() in ("1", "true")

    def _canonical_set(self):
        cases = []
        for mod in ["BPSK", "QPSK", "8PSK", "16QAM", "64QAM", "2FSK", "4FSK"]:
            for snr in [4.0, 12.0, 20.0]:
                seed = int(hashlib.sha256(f"{mod}_{snr}".encode()).hexdigest()[:8], 16) % 10000
                iq, truth = synth_capture(mod, snr_db=snr, seed=seed)
                cases.append((f"{mod}_{int(snr)}dB", iq, truth))
        return cases

    def test_outputs_match_recorded_golden_master(self):
        cases = self._canonical_set()
        current = {}
        for name, iq, truth in cases:
            r = run_pipeline(iq, truth["fs_hz"], truth)
            current[name] = {
                "modulation": get(r, "top_hypothesis.modulation"),
                "confidence": round(get(r, "final_confidence", 0.0), 2),
                "unknown": get(r, "unknown"),
            }

        if self.UPDATE or not self.GOLDEN_PATH.exists():
            self.GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.GOLDEN_PATH.write_text(json.dumps(current, indent=2, sort_keys=True))
            pytest.skip(f"Golden master (re)written to {self.GOLDEN_PATH} — re-run without UPDATE to check against it.")

        golden = json.loads(self.GOLDEN_PATH.read_text())
        diffs = {name: {"was": golden.get(name), "now": val} for name, val in current.items() if golden.get(name) != val}
        assert not diffs, f"Golden master drift detected: {json.dumps(diffs, indent=2)}"


class TestRealCLIInvocation:
    """FAILURE MEANS: run_pipeline() works as a Python function but the
    actual entry point someone will run (CLI / demo script) has a different
    bug — argv parsing, working-directory assumptions, a file-format
    mismatch. Self-skips until CLI_CMD is filled in."""

    CLI_CMD = [sys.executable, "-m", "spectralq.cli", "analyze", "{path}", "--output", "{out}", "--mode", "live"]

    def test_cli_end_to_end_on_a_real_file(self, tmp_path):
        if self.CLI_CMD is None:
            pytest.skip("Wire CLI_CMD to your real entry point before relying on this test.")
        iq, truth = synth_capture("QPSK", snr_db=18.0, seed=1)
        cap_path = tmp_path / "capture.cf32"
        iq.astype(np.complex64).tofile(cap_path)
        meta_path = tmp_path / "capture.json"
        meta_path.write_text(json.dumps({"sample_rate": 200000.0, "format": "cf32"}))
        out_path = tmp_path / "result.json"
        cmd = [c.format(path=str(cap_path), out=str(out_path)) for c in self.CLI_CMD]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0, f"CLI exited {proc.returncode}. stderr:\n{proc.stderr}"
        assert out_path.exists(), f"CLI ran but produced no output file. stdout:\n{proc.stdout}"
        result = json.loads(out_path.read_text())
        assert get(result, "top_hypothesis.modulation") == "QPSK", (
            f"CLI path produced a different/wrong result than the in-process adapter: {result}"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
