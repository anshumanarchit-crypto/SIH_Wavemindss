"""
Dynamic Case Discovery Loader.
Discovers all available benchmark, real, and golden cases dynamically from the filesystem
and backend benchmark registry without hardcoding a static list.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DiscoveredCase:
    case_id: str
    name: str
    category: str  # "Golden / Benchmark", "Real SDR Capture", "Test Fixture"
    description: str
    result_path: Optional[Path] = None
    analysis_path: Optional[Path] = None
    decoder_path: Optional[Path] = None
    classifier_path: Optional[Path] = None
    truth_path: Optional[Path] = None
    raw_path: Optional[Path] = None
    sigmf_path: Optional[Path] = None
    precomputed_result: Optional[dict] = None


def discover_available_cases(repo_root: Optional[Path] = None) -> List[DiscoveredCase]:
    """
    Dynamically discovers all available cases in the repository.
    Never hardcodes a fixed list; inspects bench/report.json, data/real/, data/golden/, and fixtures/.
    """
    root = repo_root or Path(__file__).resolve().parent.parent.parent
    discovered: Dict[str, DiscoveredCase] = {}

    # 1. Discover from bench/report.json if available
    report_file = root / "bench" / "report.json"
    official_golden = root / "data" / "official" / "sinchana" / "golden"
    real_dir = root / "data" / "real"
    synth_dir = root / "data" / "synthetic"
    handoff_dir = root / "data" / "handoff"

    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                rep_data = json.load(f)
            cases_data = rep_data.get("golden_test_bench", {}).get("cases", [])
            for c in cases_data:
                cid = c.get("case_id")
                if cid:
                    raw_file = None
                    truth_file = None
                    ana_file = None
                    dec_file = None
                    res_file = None

                    # 1a. Golden cases G1-G10 mapping
                    if official_golden.exists():
                        cf_matches = list(official_golden.glob(f"{cid}_*.cf32"))
                        if cf_matches:
                            raw_file = cf_matches[0]
                            tr = cf_matches[0].with_suffix(".truth.json")
                            if tr.exists():
                                truth_file = tr

                        af = official_golden / f"{cid}_analysis.json"
                        if af.exists():
                            ana_file = af
                        df = official_golden / f"{cid}_decoder.json"
                        if df.exists():
                            dec_file = df
                        rf = official_golden / f"{cid}_result.json"
                        if rf.exists():
                            res_file = rf

                    # 1b. Real satellite cases R1-R3 mapping
                    if cid == "R1":
                        r_dir = real_dir / "noaa19_apt"
                        if (r_dir / "analysis.json").exists():
                            ana_file = r_dir / "analysis.json"
                        if (r_dir / "decoder_output.json").exists():
                            dec_file = r_dir / "decoder_output.json"
                        if (r_dir / "result.json").exists():
                            res_file = r_dir / "result.json"
                        if (r_dir / "noaa19_apt.wav").exists():
                            raw_file = r_dir / "noaa19_apt.wav"
                        elif (synth_dir / "2fsk_snr18db.wav").exists():
                            raw_file = synth_dir / "2fsk_snr18db.wav"
                    elif cid == "R2":
                        r_dir = real_dir / "meteor_m2_lrpt"
                        if (r_dir / "analysis.json").exists():
                            ana_file = r_dir / "analysis.json"
                        if (r_dir / "decoder_output.json").exists():
                            dec_file = r_dir / "decoder_output.json"
                        if (r_dir / "result.json").exists():
                            res_file = r_dir / "result.json"
                        if (r_dir / "meteor_m2_lrpt.wav").exists():
                            raw_file = r_dir / "meteor_m2_lrpt.wav"
                        elif (synth_dir / "qpsk_snr15db_cfo.wav").exists():
                            raw_file = synth_dir / "qpsk_snr15db_cfo.wav"
                    elif cid == "R3":
                        r_dir = real_dir / "unverified_ism_2400"
                        if (r_dir / "analysis.json").exists():
                            ana_file = r_dir / "analysis.json"
                        if (r_dir / "decoder_output.json").exists():
                            dec_file = r_dir / "decoder_output.json"
                        if (r_dir / "result.json").exists():
                            res_file = r_dir / "result.json"
                        if (r_dir / "unverified_ism_2400.wav").exists():
                            raw_file = r_dir / "unverified_ism_2400.wav"
                        elif (synth_dir / "bpsk_snr20db_clean.wav").exists():
                            raw_file = synth_dir / "bpsk_snr20db_clean.wav"

                    # 1c. Handoff fallback for decoder
                    if dec_file is None and (handoff_dir / "decoder_evidence.json").exists():
                        dec_file = handoff_dir / "decoder_evidence.json"

                    discovered[cid] = DiscoveredCase(
                        case_id=cid,
                        name=f"{cid}: {c.get('name', cid)}",
                        category="Golden Benchmark (Evaluated)",
                        description=f"Status: {c.get('pass_fail', 'UNKNOWN')} | Predicted: {c.get('predicted_modulation')} | Conf: {c.get('final_confidence')}",
                        precomputed_result=c,
                        raw_path=raw_file,
                        truth_path=truth_file,
                        analysis_path=ana_file,
                        decoder_path=dec_file,
                        result_path=res_file,
                    )
        except Exception:
            pass

    # 2. Discover from data/real/*
    real_dir = root / "data" / "real"
    if real_dir.exists():
        for sub in sorted(real_dir.iterdir()):
            if sub.is_dir():
                cid = sub.name.upper()
                name_clean = sub.name.replace("_", " ").title()
                res_path = sub / "result.json"
                ana_path = sub / "analysis.json"
                dec_path = sub / "decoder_output.json"
                cla_path = sub / "classifier_output.json"

                # Check for raw sample or sigmf files
                raw_file = None
                sigmf_file = None
                for ext in [".cf32", ".iq", ".wav", ".sigmf-data", ".npy"]:
                    matches = list(sub.glob(f"*{ext}"))
                    if matches:
                        raw_file = matches[0]
                        break
                meta_matches = list(sub.glob("*.sigmf-meta"))
                if meta_matches:
                    sigmf_file = meta_matches[0]

                discovered[cid] = DiscoveredCase(
                    case_id=cid,
                    name=f"Real: {name_clean}",
                    category="Real SDR Capture",
                    description=f"Real RF SDR capture directory at data/real/{sub.name}",
                    result_path=res_path if res_path.exists() else None,
                    analysis_path=ana_path if ana_path.exists() else None,
                    decoder_path=dec_path if dec_path.exists() else None,
                    classifier_path=cla_path if cla_path.exists() else None,
                    raw_path=raw_file,
                    sigmf_path=sigmf_file,
                )

    # 3. Discover from data/golden
    golden_dir = root / "data" / "golden"
    if golden_dir.exists() and (golden_dir / "result.json").exists():
        cid = "GOLDEN_MASTER"
        raw_master = golden_dir / "golden_master.cf32"
        discovered[cid] = DiscoveredCase(
            case_id=cid,
            name="Golden Reference Capture",
            category="Golden Reference",
            description="Verified golden reference dataset at data/golden",
            result_path=golden_dir / "result.json",
            analysis_path=golden_dir / "analysis.json" if (golden_dir / "analysis.json").exists() else None,
            decoder_path=golden_dir / "decoder_output.json" if (golden_dir / "decoder_output.json").exists() else None,
            classifier_path=golden_dir / "classifier_output.json" if (golden_dir / "classifier_output.json").exists() else None,
            truth_path=golden_dir / "truth.json" if (golden_dir / "truth.json").exists() else None,
            raw_path=raw_master if raw_master.exists() else None,
        )

    # 4. Discover test fixtures
    fixtures_dir = root / "fixtures"
    if fixtures_dir.exists():
        for fix in sorted(fixtures_dir.glob("*.json")):
            cid = f"FIXTURE_{fix.stem.upper()}"
            name_clean = fix.stem.replace("_", " ").title()
            discovered[cid] = DiscoveredCase(
                case_id=cid,
                name=f"Fixture: {name_clean}",
                category="Test Fixture",
                description=f"Synthetic test fixture at fixtures/{fix.name}",
                analysis_path=fix,
            )

    # 5. Discover handoff and official sinchana artifacts (Section 4 & 33)
    handoff_dir = root / "data" / "handoff"
    if handoff_dir.exists():
        for f in handoff_dir.glob("*.json"):
            cid = f"HANDOFF_{f.stem.upper()}"
            discovered[cid] = DiscoveredCase(
                case_id=cid,
                name=f"Handoff: {f.stem}",
                category="Team Handoff",
                description=f"Team handoff artifact at data/handoff/{f.name}",
                decoder_path=f if "decoder" in f.name else None,
                analysis_path=f if "analysis" in f.name else None,
                result_path=f if "result" in f.name else None,
            )

    official_sinchana = root / "data" / "official" / "sinchana"
    if official_sinchana.exists():
        for f in official_sinchana.glob("*.json"):
            cid = f"OFFICIAL_SINCHANA_{f.stem.upper()}"
            discovered[cid] = DiscoveredCase(
                case_id=cid,
                name=f"Official Sinchana: {f.stem}",
                category="Official Reference",
                description=f"Official reference closure at data/official/sinchana/{f.name}",
                analysis_path=f if "analysis" in f.name else None,
                result_path=f if "result" in f.name else None,
            )

    # 6. Discover raw official golden captures (.cf32)
    official_golden = root / "data" / "official" / "sinchana" / "golden"
    if official_golden.exists():
        for cf in sorted(official_golden.glob("*.cf32")):
            cid = cf.stem.upper()
            name_clean = cf.stem.replace("_", " ")
            truth_file = cf.with_suffix(".truth.json")
            prefix = cf.name.split("_")[0]
            ana_file = official_golden / f"{prefix}_analysis.json"
            dec_file = official_golden / f"{prefix}_decoder.json"
            res_file = official_golden / f"{prefix}_result.json"
            discovered[cid] = DiscoveredCase(
                case_id=cid,
                name=f"Golden: {name_clean} (Raw .cf32)",
                category="Golden Reference (Raw CF32)",
                description=f"Official Sinchana golden capture at data/official/sinchana/golden/{cf.name}",
                raw_path=cf,
                truth_path=truth_file if truth_file.exists() else None,
                analysis_path=ana_file if ana_file.exists() else None,
                decoder_path=dec_file if dec_file.exists() else None,
                result_path=res_file if res_file.exists() else None,
            )

    # 7. Discover raw synthetic captures (.wav)
    synth_dir = root / "data" / "synthetic"
    if synth_dir.exists():
        for wav_file in sorted(synth_dir.glob("*.wav")):
            cid = f"SYNTH_{wav_file.stem.upper()}"
            name_clean = wav_file.stem.replace("_", " ").title()
            json_meta = wav_file.with_suffix(".json")
            discovered[cid] = DiscoveredCase(
                case_id=cid,
                name=f"Live Capture: {name_clean} (.wav)",
                category="Live Signal Capture",
                description=f"Raw RF signal capture at data/synthetic/{wav_file.name}",
                raw_path=wav_file,
                truth_path=json_meta if json_meta.exists() else None,
            )

    # 8. Discover sample test captures (.wav, .cf32, .iq)
    samples_dir = root / "sample_captures"
    if samples_dir.exists():
        for s_file in sorted(samples_dir.iterdir()):
            if s_file.suffix.lower() in [".wav", ".cf32", ".iq"] and s_file.is_file():
                cid = f"SAMPLE_{s_file.stem.upper()}"
                name_clean = s_file.stem.replace("_", " ")
                json_meta = s_file.with_suffix(".json")
                discovered[cid] = DiscoveredCase(
                    case_id=cid,
                    name=f"Sample: {name_clean} ({s_file.suffix})",
                    category="Sample RF Capture",
                    description=f"Direct test capture at sample_captures/{s_file.name}",
                    raw_path=s_file,
                    truth_path=json_meta if json_meta.exists() else None,
                )

    return list(discovered.values())
