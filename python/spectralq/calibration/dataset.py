"""
Synthetic Dataset Generator with Instance-Level Isolation for SpectralQ.

DATASET SPLIT INVARIANT:
- Split strictly BY SIGNAL INSTANCE (never by sample).
- All sub-windows or features derived from a given signal instance ID
  MUST appear exclusively in either the train split or the evaluation split.

Generation Parameters & Real-World Justification:
- Modulations: BPSK, QPSK, 8-PSK, 16-QAM, 64-QAM, 2-FSK, 4-FSK
- SNR: 2 dB to 26 dB (reflecting operational receiver sensitivities)
- CFO: -400 Hz to +400 Hz (typical TCXO/crystal offset at VHF/UHF)
- Phase Offset: 0 to 2*pi uniform (uncalibrated initial LO phase)
- RRC roll-off: 0.20 to 0.35, SPS: 4 to 8 (standard digital satellite/terrestrial standards)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple
import numpy as np
from spectralq.hypothesis.registry import MODULATIONS
from spectralq.integration.classifier_adapter import CANONICAL_FEATURE_NAMES


@dataclass
class SignalInstanceRecord:
    instance_id: str
    true_modulation: str
    snr_db: float
    cfo_hz: float
    phase_rad: float
    roll_off: float
    sps: int
    features: Dict[str, float]


def generate_synthetic_signal_instance(
    instance_index: int,
    modulation: str,
    snr_db: float,
    cfo_hz: float,
    phase_rad: float,
    roll_off: float,
    sps: int,
    rng: np.random.Generator,
) -> SignalInstanceRecord:
    """
    Simulates physically plausible feature vectors for a specific modulation under channel impairments.
    """
    instance_id = f"SIG_INST_{instance_index:05d}_{modulation}_{int(snr_db)}dB"
    
    # Noise standard deviation based on SNR
    snr_linear = 10.0 ** (snr_db / 10.0)
    noise_sigma = 1.0 / np.sqrt(2.0 * snr_linear)

    # Base theoretical cumulants per modulation
    if modulation == "BPSK":
        c20 = 1.0 - 0.15 * (noise_sigma ** 2) + rng.normal(0, 0.02)
        c21 = 1.0 + noise_sigma ** 2
        c40 = -2.0 + rng.normal(0, 0.05)
        c42 = -2.0 + rng.normal(0, 0.05)
        cluster_count = 2.0
        silhouette = max(0.40, 0.95 - 0.02 * noise_sigma)
        intra_var = 0.04 + 0.1 * noise_sigma
        inter_dist = 2.0
        evm = 0.03 + 0.5 * noise_sigma
    elif modulation == "QPSK":
        c20 = rng.normal(0, 0.02)
        c21 = 1.0 + noise_sigma ** 2
        c40 = 1.0 - 0.2 * noise_sigma + rng.normal(0, 0.04)
        c42 = -1.0 + rng.normal(0, 0.03)
        cluster_count = 4.0
        silhouette = max(0.40, 0.90 - 0.03 * noise_sigma)
        intra_var = 0.06 + 0.1 * noise_sigma
        inter_dist = 1.414
        evm = 0.04 + 0.5 * noise_sigma
    elif modulation == "8-PSK":
        c20 = rng.normal(0, 0.02)
        c21 = 1.0 + noise_sigma ** 2
        c40 = rng.normal(0, 0.05)
        c42 = -1.0 + rng.normal(0, 0.03)
        cluster_count = 8.0
        silhouette = max(0.35, 0.82 - 0.04 * noise_sigma)
        intra_var = 0.08 + 0.12 * noise_sigma
        inter_dist = 0.765
        evm = 0.06 + 0.6 * noise_sigma
    elif modulation == "16-QAM":
        c20 = rng.normal(0, 0.02)
        c21 = 1.0 + noise_sigma ** 2
        c40 = -0.68 + rng.normal(0, 0.03)
        c42 = -0.68 + rng.normal(0, 0.03)
        cluster_count = 16.0
        silhouette = max(0.30, 0.75 - 0.05 * noise_sigma)
        intra_var = 0.10 + 0.15 * noise_sigma
        inter_dist = 0.632
        evm = 0.07 + 0.6 * noise_sigma
    elif modulation == "64-QAM":
        c20 = rng.normal(0, 0.02)
        c21 = 1.0 + noise_sigma ** 2
        c40 = -0.619 + rng.normal(0, 0.03)
        c42 = -0.619 + rng.normal(0, 0.03)
        cluster_count = 64.0
        silhouette = max(0.25, 0.65 - 0.06 * noise_sigma)
        intra_var = 0.12 + 0.18 * noise_sigma
        inter_dist = 0.308
        evm = 0.09 + 0.7 * noise_sigma
    elif modulation == "2-FSK":
        c20 = rng.normal(0, 0.03)
        c21 = 1.0 + noise_sigma ** 2
        c40 = rng.normal(0, 0.04)
        c42 = -0.95 + rng.normal(0, 0.03)
        cluster_count = 2.0
        silhouette = 0.25 + rng.uniform(-0.05, 0.05)  # Distinct low silhouette
        intra_var = 0.40 + 0.1 * noise_sigma
        inter_dist = 0.8
        evm = 0.20 + 0.5 * noise_sigma
    else:  # 4-FSK
        c20 = rng.normal(0, 0.03)
        c21 = 1.0 + noise_sigma ** 2
        c40 = rng.normal(0, 0.04)
        c42 = -0.90 + rng.normal(0, 0.03)
        cluster_count = 4.0
        silhouette = 0.22 + rng.uniform(-0.05, 0.05)  # Distinct low silhouette
        intra_var = 0.45 + 0.1 * noise_sigma
        inter_dist = 0.7
        evm = 0.25 + 0.5 * noise_sigma

    features = {
        "C20": float(c20),
        "C21": float(c21),
        "C40": float(c40),
        "C42": float(c42),
        "C60": float(rng.normal(0, 0.02)),
        "C63": float(rng.normal(0, 0.02)),
        "C80": float(rng.normal(0, 0.02)),
        "cluster_count": float(cluster_count),
        "silhouette": float(silhouette),
        "intra_var": float(intra_var),
        "inter_dist": float(inter_dist),
        "evm": float(evm),
        "phase_ambiguity_quality": float(max(0.1, 0.95 - 0.05 * noise_sigma)),
        "snr": float(snr_db),
        "baud": float(1.0e6),
    }

    return SignalInstanceRecord(
        instance_id=instance_id,
        true_modulation=modulation,
        snr_db=snr_db,
        cfo_hz=cfo_hz,
        phase_rad=phase_rad,
        roll_off=roll_off,
        sps=sps,
        features=features,
    )


def generate_synthetic_sweep(
    n_instances_per_class: int = 40,
    seed: int = 2026,
) -> List[SignalInstanceRecord]:
    """
    Generates a full synthetic sweep across all 7 canonical modulations,
    varying SNR, CFO, phase, roll-off, and SPS.
    """
    rng = np.random.default_rng(seed)
    records: List[SignalInstanceRecord] = []
    inst_idx = 0

    snr_levels = [4.0, 8.0, 12.0, 16.0, 20.0, 24.0]

    for mod in MODULATIONS:
        for _ in range(n_instances_per_class):
            snr = float(rng.choice(snr_levels) + rng.uniform(-1.0, 1.0))
            cfo = float(rng.uniform(-400.0, 400.0))
            phase = float(rng.uniform(0.0, 2 * np.pi))
            roll_off = float(rng.choice([0.20, 0.25, 0.30, 0.35]))
            sps = int(rng.choice([4, 6, 8]))

            rec = generate_synthetic_signal_instance(
                instance_index=inst_idx,
                modulation=mod,
                snr_db=snr,
                cfo_hz=cfo,
                phase_rad=phase,
                roll_off=roll_off,
                sps=sps,
                rng=rng,
            )
            records.append(rec)
            inst_idx += 1

    rng.shuffle(records)
    return records


def split_by_signal_instance(
    records: List[SignalInstanceRecord],
    test_ratio: float = 0.35,
    seed: int = 42,
) -> Tuple[List[SignalInstanceRecord], List[SignalInstanceRecord]]:
    """
    Splits records strictly by instance ID so that no instance ID appears in both splits.
    """
    unique_instance_ids = sorted(list(set(r.instance_id for r in records)))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique_instance_ids)

    n_test = int(len(unique_instance_ids) * test_ratio)
    test_ids: Set[str] = set(unique_instance_ids[:n_test])
    train_ids: Set[str] = set(unique_instance_ids[n_test:])

    # Critical Assertion: Strictly disjoint sets
    assert test_ids.isdisjoint(train_ids), "Instance IDs must be strictly disjoint between splits!"

    train_records = [r for r in records if r.instance_id in train_ids]
    test_records = [r for r in records if r.instance_id in test_ids]

    return train_records, test_records
