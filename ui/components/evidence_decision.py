"""
Workspace 5: Evidence & Decision (Audit Trail & Confidence Engine).
Ultra-premium cyber aesthetic:
- 5-Tier Hierarchical Verification Ladder with neon glowing milestone cards
- Verification Check Aggregates with Neon KPI Cards
- Interactive Forensic Evidence Ledger Table with filtering and instant search
- Mathematical Confidence Aggregation Breakdown with LaTeX Formulation
"""

from typing import Optional, List, Dict, Any
import streamlit as st

from ui.adapters import NormalizedResult, NormalizedAnalysis, NormalizedDecoder
from ui.styles.theme import get_theme_tokens, TOOLTIPS


LADDER_LEVELS = [
    ("L1", "Signal Detection", "Physical energy detected above noise floor. Center frequency, baud, and bandwidth resolved."),
    ("L2", "Modulation Identification", "Physical statistical cumulants and neural classifier agree on modulation candidate without severe penalty."),
    ("L3", "Blind Demodulation", "Carrier frequency offset corrected, symbol timing synchronized, constellation locked."),
    ("L4", "Coding & FEC Lock", "Interleaver matrix resolved, convolutional Viterbi and Reed-Solomon inner/outer FEC locked."),
    ("L5", "Frame & CRC Verified", "Preamble/sync word aligned, frame boundaries established, CRC polynomial verified with zero parity errors."),
]


def render_evidence_decision(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
    decoder: Optional[NormalizedDecoder],
) -> None:
    """Renders the Evidence & Decision workspace with a defense-grade cyber design."""
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div>
                <div style="font-size:1.4rem; font-weight:800; color:#f1f5f9; display:flex; align-items:center; gap:0.5rem;">
                    <span style="color:#10b981;">⚖️</span> EVIDENCE LEDGER &amp; DECISION ENGINE
                </div>
                <div style="font-size:0.75rem; color:#94a3b8; margin-top:2px;">
                    Stage 10: Hierarchical Verification Ladder (L1–L5), Cryptographic Audit Trail (SpectralQ), and Confidence Calibration
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span class="sq-badge badge-ladder">SpectralQ LEDGER V2.0</span>
                <span class="sq-pulse-dot emerald"></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not result:
        st.info("No result telemetry loaded. Please select or load a capture.")
        return

    tokens = get_theme_tokens()

    # 1. Prominent UNKNOWN Diagnosis (if Abstained)
    if result.is_unknown:
        st.markdown(
            f"""
            <div class="sq-unknown-banner">
                <div class="sq-unknown-title">
                    <span class="sq-pulse-dot rose"></span>
                    <span>PIPELINE ABSTENTION / UNKNOWN STATE DIAGNOSIS</span>
                </div>
                <div class="sq-unknown-desc">
                    <b>Primary Reason:</b> {result.unknown_reason or "Low confidence or ambiguous signal parameters."}<br><br>
                    <b>Why did SpectralQ abstain?</b> Rather than forcing an ungrounded or speculative classification, 
                    the decision engine triggered abstention because evidence was insufficient to guarantee operational reliability.<br>
                    <b>Failed Checks:</b> {', '.join(result.failed_checks) if result.failed_checks else 'None explicit; low SNR or consensus penalty'}<br>
                    <b>Resolution:</b> Collect higher SNR samples or wider capture bandwidth to resolve ambiguity.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Evidence Ladder Visualization (L1 - L5)
    st.markdown("### 🪜 Hierarchical Evidence Ladder Progression")
    st.caption("Verification milestones required to escalate confidence from physical detection to confirmed CRC decode:")

    current_ladder = result.ladder_level
    if decoder is not None:
        _crc_ok = getattr(decoder, "crc_passed", False)
        _ber_val = getattr(decoder, "reencode_ber", None)
        _sync_ok = getattr(decoder, "sync_word", None) is not None
        _ber_zero = _ber_val is not None and _ber_val == 0.0
        if _crc_ok or (_ber_zero and _sync_ok):
            current_ladder = "L5"

    ladder_cols = st.columns(5)
    ranks = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
    curr_rank = ranks.get(current_ladder, 1)

    for idx, (lvl, name, desc) in enumerate(LADDER_LEVELS):
        lvl_rank = ranks[lvl]
        is_current = (lvl == current_ladder)
        is_achieved = (lvl_rank <= curr_rank)

        with ladder_cols[idx]:
            border_col = "#38bdf8" if is_current else ("#10b981" if is_achieved else "rgba(148, 163, 184, 0.2)")
            bg_col = "rgba(56, 189, 248, 0.12)" if is_current else ("rgba(16, 185, 129, 0.08)" if is_achieved else "rgba(15, 23, 42, 0.5)")
            badge_html = "<span class='sq-badge badge-ladder'>CURRENT</span>" if is_current else (
                "<span class='sq-badge badge-pass'>ACHIEVED</span>" if is_achieved else "<span class='sq-badge badge-unavail'>PENDING</span>"
            )

            st.markdown(
                f"""
                <div style="background:{bg_col}; border:1px solid {border_col}; border-radius:12px;
                     padding:0.85rem 0.65rem; text-align:center; min-height:155px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="font-family:'JetBrains Mono'; font-weight:800; font-size:1.2rem; color:{border_col};">
                            {lvl}
                        </div>
                        <div style="font-weight:700; font-size:0.78rem; color:#f1f5f9; margin:2px 0;">
                            {name}
                        </div>
                        <div style="font-size:0.68rem; color:#94a3b8; line-height:1.3; margin:0.3rem 0;">
                            {desc}
                        </div>
                    </div>
                    <div style="margin-top:0.4rem;">
                        {badge_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 3. Evidence Check Summary Metrics
    st.markdown("### 📊 Forensic Verification Check Aggregates")
    all_evidence = result.evidence
    passed = [e for e in all_evidence if e.status == "PASS"]
    failed = [e for e in all_evidence if e.status == "FAIL"]
    unavail = [e for e in all_evidence if e.status == "UNAVAILABLE"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-blue">
                <div class="sq-card-header">
                    <span class="sq-card-label">TOTAL CHECKS AUDITED</span>
                    <span class="sq-badge badge-pass">100%</span>
                </div>
                <div class="sq-card-metric">{len(all_evidence)}</div>
                <div class="sq-card-subtext">Comprehensive Audit Suite</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        pass_pct = (len(passed) / len(all_evidence) * 100.0) if all_evidence else 0.0
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-emerald">
                <div class="sq-card-header">
                    <span class="sq-card-label">PASSED CHECKS</span>
                    <span class="sq-badge badge-pass">{pass_pct:.1f}%</span>
                </div>
                <div class="sq-card-metric" style="color:#10b981;">{len(passed)}</div>
                <div class="sq-card-subtext">Zero Syndrome Discrepancy</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        failed_pen_str = f"-{result.rule_ml_penalty:.2f} penalty" if (failed and result.rule_ml_penalty is not None) else "Zero Penalties Applied"
        st.markdown(
            f"""
            <div class="sq-neon-card {'sq-neon-card-rose' if failed else 'sq-neon-card-cyan'}">
                <div class="sq-card-header">
                    <span class="sq-card-label">FAILED CHECKS</span>
                    <span class="sq-badge {'badge-fail' if failed else 'badge-pass'}">{len(failed)}</span>
                </div>
                <div class="sq-card-metric" style="color:{'#f43f5e' if failed else '#38bdf8'};">{len(failed)}</div>
                <div class="sq-card-subtext">{failed_pen_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-amber">
                <div class="sq-card-header">
                    <span class="sq-card-label">UNAVAILABLE CHECKS</span>
                    <span class="sq-badge badge-warn">{len(unavail)}</span>
                </div>
                <div class="sq-card-metric">{len(unavail)}</div>
                <div class="sq-card-subtext">Optional Layer Inactive</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 4. Interactive Evidence Ledger Table
    st.markdown("### 📜 Forensic Evidence Ledger Audit Trail")
    st.caption("Inspect individual telemetry checks across physical DSP, ML AMC, and blind FEC decoding layers:")

    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    with f_col1:
        status_filter = st.selectbox(
            "Filter by Status:",
            ["ALL", "PASS", "FAIL", "UNAVAILABLE"],
            index=0,
            key="ev_status_filter",
        )
    def _clean_source(s_val: Optional[str]) -> str:
        if not s_val:
            return "SpectralQ Subsystem"
        t = str(s_val)
        import re
        for pat, rep in [
            (r"\bSinchana\s*\(Ingest\)", "DSP Ingest Engine"),
            (r"\bSinchana\s*\(Blind Estimation\)", "DSP Estimation Engine"),
            (r"\bSinchana\s*\(Features\)", "DSP Feature Extractor"),
            (r"\bArpit\s*\(Decoder\)", "FEC Decoder Engine"),
            (r"\bArchit\s*\(Evidence Ladder\)", "Evidence Ladder Engine"),
            (r"\bArchit\s*\(Decision Engine\)", "Decision Consensus Engine"),
            (r"\bHarsh\s*\(Classifier\)", "ML AMC Classifier"),
            (r"\bHimanshu\s*\(GUI\)", "SpectralQ UI"),
            (r"\bPrince\s*\(Lab\)", "Signal Simulation Engine"),
            (r"\bSinchana\b", "DSP Engine"),
            (r"\bArpit\b", "FEC Decoder"),
            (r"\bArchit\b", "Evidence Engine"),
            (r"\bHarsh\b", "ML Classifier"),
            (r"\bHimanshu\b", "SpectralQ"),
            (r"\bPrince\b", "Signal Lab"),
            (r"\bNTRO\b", "SpectralQ Defense"),
        ]:
            t = re.sub(pat, rep, t, flags=re.IGNORECASE)
        return t

    with f_col2:
        all_sources = sorted(list(set(_clean_source(e.source) for e in all_evidence))) if all_evidence else []
        source_filter = st.selectbox(
            "Filter by Source Subsystem:",
            ["ALL"] + all_sources,
            index=0,
            key="ev_source_filter",
        )
    with f_col3:
        search_query = st.text_input("Instant Search Check or Explanation:", placeholder="e.g. snr, viterbi, consensus", key="ev_search_input")

    # Filter checks
    filtered_evidence = all_evidence
    if status_filter != "ALL":
        filtered_evidence = [e for e in filtered_evidence if e.status == status_filter]
    if source_filter != "ALL":
        filtered_evidence = [e for e in filtered_evidence if _clean_source(e.source) == source_filter]
    if search_query:
        q = search_query.lower()
        filtered_evidence = [e for e in filtered_evidence if q in e.check_name.lower() or q in _clean_source(e.explanation).lower()]

    table_data = []
    for e in filtered_evidence:
        table_data.append({
            "ID": e.evidence_id,
            "Subsystem Source": _clean_source(e.source),
            "Verification Check": e.check_name,
            "Verdict": e.status,
            "Forensic Explanation": _clean_source(e.explanation),
        })

    st.dataframe(table_data, use_container_width=True, height=290)

    # 5. "Explain Decision" Interactive Drawer
    with st.expander("💡 Deep Dive: Mathematical Confidence Aggregation Formulation", expanded=False):
        st.markdown("#### Confidence Aggregation Mathematical Formulation")
        st.latex(r"C_{\text{final}} = P_{\text{ML}} \cdot (1 - \text{Penalty}_{\text{Consensus}}) \cdot \prod_{i} (1 - P_{\text{check}, i})")
        raw_prob_txt = f"{result.ml_probability:.4f}" if result.ml_probability is not None else "N/A"
        pen_txt = f"DIVERGENCE (-{result.rule_ml_penalty:.2f} penalty)" if (result.rule_ml_penalty is not None and not result.rule_ml_agreement) else ("CONSENSUS (0.00 penalty)" if result.rule_ml_agreement else "DISCORDANT")
        cal_prob_txt = f"{result.calibrated_ml_probability:.4f}" if result.calibrated_ml_probability is not None else (f"{result.ml_probability:.4f} (Uncalibrated)" if result.ml_probability is not None else "N/A")
        cwa_txt = f"{result.cross_window_agreement:.2f}" if result.cross_window_agreement is not None else "1.00"
        fin_conf_txt = f"{result.final_confidence:.4f}" if result.final_confidence is not None else "N/A"

        st.markdown(
            f"""
            - **Raw Softmax ML Probability:** `p = {raw_prob_txt}`
            - **AMC Rule-Consensus Status:** `{pen_txt}`
            - **Calibrated ML Probability:** `p_cal = {cal_prob_txt}`
            - **Multi-Window Agreement:** `alpha = {cwa_txt}`
            - **Final Defensible Confidence Score:** `C = {fin_conf_txt}`
            - **Decision System Engine:** `{result.confidence_version or 'SpectralQ Engine v2.0'}`
            """
        )
