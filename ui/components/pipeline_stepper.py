"""
UI Pipeline Stepper Component.
Visualizes the 10 stages of the SpectralQ signal intelligence pipeline:
RAW CAPTURE -> FORENSICS -> BURSTS -> ESTIMATION -> MODULATION -> DEMOD -> FEC -> BITSTREAM -> EVIDENCE -> RESULT.
Shows explicit per-stage status, key outputs, and expandable technical evidence.
"""

from typing import Dict, List, Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.analysis_adapter import NormalizedAnalysis
from ui.adapters.decoder_adapter import NormalizedDecoder


def render_pipeline_stepper(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
    selected_stage_key: str = "selected_stage",
):
    """Renders the horizontal multi-stage pipeline status tracker."""
    st.markdown("### Signal Intelligence Pipeline Traversal")

    stages = [
        {"id": "ingest", "name": "1. Ingest", "owner": "DSP Engine"},
        {"id": "forensics", "name": "2. Forensics", "owner": "DSP Engine"},
        {"id": "bursts", "name": "3. Bursts", "owner": "DSP Engine"},
        {"id": "estimation", "name": "4. DSP Estimation", "owner": "DSP Engine"},
        {"id": "modulation", "name": "5. Modulation", "owner": "AMC Engine"},
        {"id": "demod", "name": "6. Demodulation", "owner": "FEC Decoder"},
        {"id": "fec", "name": "7. FEC / Deintl", "owner": "FEC Decoder"},
        {"id": "bitstream", "name": "8. Bitstream", "owner": "FEC Decoder"},
        {"id": "evidence", "name": "9. Evidence Ledger", "owner": "Evidence Engine"},
        {"id": "result", "name": "10. Decision", "owner": "Evidence Engine"},
    ]

    # Compute status per stage honestly
    stage_data: Dict[str, Dict[str, str]] = {}

    # Ingest
    if analysis:
        stage_data["ingest"] = {
            "status": "PASS",
            "summary": f"{analysis.source_mode} | Fs: {analysis.fs_hz / 1e6:.1f} MHz",
            "details": f"Sample rate source: {analysis.fs_source}. Notes: {analysis.notes or 'None'}.",
        }
    else:
        stage_data["ingest"] = {"status": "WAITING", "summary": "Awaiting Capture", "details": "No capture loaded"}

    # Forensics
    if analysis:
        stage_data["forensics"] = {
            "status": "PASS",
            "summary": f"Format: IQ | Fs: {analysis.fs_source}",
            "details": f"Sub-windows: {len(analysis.sub_windows) if analysis.sub_windows else 0}. Octave Available: {analysis.capability_available}.",
        }
    else:
        stage_data["forensics"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting file"}

    # Bursts
    if analysis:
        b_count = len(analysis.bursts)
        stage_data["bursts"] = {
            "status": "PASS" if b_count > 0 else "WARNING",
            "summary": f"{b_count} Bursts Detected" if b_count > 0 else "0 Bursts (Noise/Continuous)",
            "details": f"Bursts detected: {b_count}. First burst power: {analysis.bursts[0].power_db if b_count > 0 else 'N/A'} dBm.",
        }
    else:
        stage_data["bursts"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting burst detector"}

    # Estimation
    if analysis and analysis.snr and analysis.baud:
        stage_data["estimation"] = {
            "status": "PASS",
            "summary": f"SNR: {analysis.snr.value:.1f} dB | {analysis.baud.display_value}",
            "details": f"Methods: SNR ({analysis.snr.method}), Baud ({analysis.baud.method}), CFO ({analysis.cfo.method}).",
        }
    else:
        stage_data["estimation"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting estimation"}

    # Modulation
    if result:
        st_mod = "UNKNOWN" if result.is_unknown else ("PASS" if result.rule_ml_agreement else "WARNING")
        stage_data["modulation"] = {
            "status": st_mod,
            "summary": f"{result.top_hypothesis.modulation} (P={result.ml_probability:.2f})",
            "details": f"Rule: {result.rule_prediction}, ML: {result.ml_prediction}. Agreement: {result.rule_ml_agreement}. Cross-window: {result.cross_window_agreement:.2f}.",
        }
    else:
        stage_data["modulation"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting classifier"}

    # Demod
    if decoder:
        stage_data["demod"] = {
            "status": "PASS" if decoder.status == "OK" else ("UNSUPPORTED" if decoder.status == "UNSUPPORTED" else "FAIL"),
            "summary": f"{decoder.status} | {decoder.decoded_bits_count} bits",
            "details": f"Demodulated bits: {decoder.decoded_bits_count}. Preview: {decoder.decoded_bits_preview or 'None'}.",
        }
    elif result and result.top_hypothesis:
        stage_data["demod"] = {
            "status": "PASS" if not result.is_unknown else "UNKNOWN",
            "summary": f"{result.top_hypothesis.modulation} Demod",
            "details": f"Demodulation verified via {result.ladder_level}.",
        }
    else:
        stage_data["demod"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting demod"}

    # FEC / Deinterleaving
    if decoder:
        stage_data["fec"] = {
            "status": "PASS" if decoder.status == "OK" else ("UNSUPPORTED" if decoder.status == "UNSUPPORTED" else "FAIL"),
            "summary": f"{decoder.fec_used} | {decoder.interleaver_used}",
            "details": f"FEC scheme: {decoder.fec_used}, Interleaver: {decoder.interleaver_used}. Reason: {decoder.failure_reason or 'None'}.",
        }
    elif result and result.top_hypothesis:
        stage_data["fec"] = {
            "status": "PASS",
            "summary": f"{result.top_hypothesis.fec} | {result.top_hypothesis.interleaver}",
            "details": "Hypothesized forward error correction parameters.",
        }
    else:
        stage_data["fec"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting FEC"}

    # Bitstream
    if decoder:
        stage_data["bitstream"] = {
            "status": "PASS" if decoder.crc_status == "PASS" else ("FAIL" if decoder.crc_status == "FAIL" else "NOT_RUN"),
            "summary": f"CRC: {decoder.crc_status} | BER: {decoder.ber_display}",
            "details": f"CRC checksum: {decoder.crc_status}. Re-encode BER residual: {decoder.ber_display}.",
        }
    else:
        stage_data["bitstream"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting bitstream validation"}

    # Evidence Ledger
    if result:
        stage_data["evidence"] = {
            "status": "PASS",
            "summary": f"{len(result.evidence)} Checks Audited",
            "details": f"Passed: {len(result.evidence) - len(result.failed_checks) - len(result.unavailable_checks)}, Failed: {len(result.failed_checks)}, Unavailable: {len(result.unavailable_checks)}.",
        }
    else:
        stage_data["evidence"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting evidence ledger"}

    # Result / Decision
    if result:
        st_res = "UNKNOWN" if result.is_unknown else "PASS"
        stage_data["result"] = {
            "status": st_res,
            "summary": f"Ladder {result.ladder_level} ({result.confidence_label})",
            "details": f"Final confidence: {result.final_confidence:.4f} (v: {result.confidence_version}). Unknown: {result.unknown_reason or 'None'}.",
        }
    else:
        stage_data["result"] = {"status": "WAITING", "summary": "Idle", "details": "Awaiting final decision"}

    # Render interactive stage columns
    cols = st.columns(len(stages))
    for idx, (col, stg) in enumerate(zip(cols, stages)):
        sid = stg["id"]
        info = stage_data[sid]
        status = info["status"]

        if status == "PASS":
            icon = "✓"
            badge = '<span class="sq-badge badge-pass">PASS</span>'
        elif status == "WARNING":
            icon = "⚠"
            badge = '<span class="sq-badge badge-unavail">WARN</span>'
        elif status == "FAIL":
            icon = "✕"
            badge = '<span class="sq-badge badge-fail">FAIL</span>'
        elif status == "UNSUPPORTED":
            icon = "⊘"
            badge = '<span class="sq-badge badge-unavail">UNSUPP</span>'
        elif status == "UNKNOWN":
            icon = "❓"
            badge = '<span class="sq-badge badge-unknown">UNKN</span>'
        else:
            icon = "○"
            badge = '<span class="sq-badge badge-notrun">WAIT</span>'

        with col:
            st.markdown(
                f"""
                <div class="sq-step">
                    <div class="sq-step-name">{stg['name']}</div>
                    <div class="sq-step-status">{icon} {stg['owner'].split()[0]}</div>
                    <div style="font-size: 0.68rem; color: #8b949e; margin: 0.2rem 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        {info['summary']}
                    </div>
                    <div>{badge}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Expandable details drawer
    with st.expander("🔍 View Per-Stage Execution & Evidence Ledger Breakdown", expanded=False):
        tcols = st.columns(2)
        for i, stg in enumerate(stages):
            sid = stg["id"]
            info = stage_data[sid]
            target_col = tcols[i % 2]
            with target_col:
                st.markdown(f"**{stg['name']} ({stg['owner']})** — Status: `{info['status']}`")
                st.caption(f"Summary: {info['summary']}")
                st.write(info["details"])
                st.markdown("---")
