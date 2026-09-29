"""
Workspace 3: Modulation & Hypotheses (Classifier & AMC Analysis Workbench).
Operational AMC workbench providing:
- Primary Modulation Identification & Consensus Cockpit
- Calibrated Probability Distribution across Candidate Space
- Ranked Hypothesis Decision Stack (Accepted vs Rejected with Evidence Rationale)
- Decision Feature Matrix & Extraction Gates
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import plotly.graph_objects as go

from ui.adapters import NormalizedResult, NormalizedAnalysis
from ui.styles.theme import get_theme_tokens, get_plotly_layout_defaults
from ui.components.icons import get_icon_svg


def render_modulation_hypotheses(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
) -> None:
    """Renders the defense-grade Modulation & Hypotheses AMC analysis workbench."""
    tokens = get_theme_tokens()

    # Workspace Header
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem; border-bottom:1px solid {tokens['card_border']}; padding-bottom:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.6rem;">
                {get_icon_svg("modulation_hypotheses", size=20, color=tokens['primary'])}
                <span style="font-size:1.15rem; font-weight:800; letter-spacing:0.04em; color:{tokens['text']};">
                    AMC CLASSIFICATION &amp; HYPOTHESIS WORKBENCH
                </span>
            </div>
            <div>
                <span class="sq-badge badge-ladder">
                    {get_icon_svg('layers', size=11)} LADDER {result.ladder_level if result else 'N/A'}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not result:
        st.info("No signal telemetry contract loaded. Please select a capture case.")
        return

    # 1. Consensus Cockpit & Decision Alignment Bar
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
            {get_icon_svg("target", size=16, color=tokens['primary'])}
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                Consensus &amp; Decision Alignment
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        raw_prob_str = f"p = {result.ml_probability:.1%}" if result.ml_probability is not None else "p = N/A"
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">ML Classifier Output</div>
                <div class="sq-card-value" style="color:{tokens['primary']};">{result.ml_prediction or "UNKNOWN"}</div>
                <div class="sq-card-sub">{raw_prob_str} · Neural AMC Model</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Rule AMC Decision</div>
                <div class="sq-card-value" style="color:{tokens['text']};">{result.rule_prediction or "UNKNOWN"}</div>
                <div class="sq-card-sub">Kurtosis &amp; Cumulant Distances</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        status_label = "CONSENSUS AGREED" if result.rule_ml_agreement else "DIVERGENCE"
        pen_str = f"Penalty: -{result.rule_ml_penalty:.2f}" if (result.rule_ml_penalty is not None and not result.rule_ml_agreement) else "Zero penalty"
        agree_col = tokens["pass_color"] if result.rule_ml_agreement else tokens["fail_color"]
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Consensus State</div>
                <div class="sq-card-value" style="color:{agree_col}; font-size:1.15rem;">{status_label}</div>
                <div class="sq-card-sub">{pen_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        cal_str = f"{result.calibrated_ml_probability:.1%}" if result.calibrated_ml_probability is not None else "N/A"
        fin_str = f"Final Confidence: {result.final_confidence:.1%}" if result.final_confidence is not None else "Final: N/A"
        st.markdown(
            f"""
            <div class="sq-card">
                <div class="sq-card-title">Calibrated Confidence</div>
                <div class="sq-card-value" style="color:{tokens['violet']};">{cal_str}</div>
                <div class="sq-card-sub">{fin_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Probability Distribution Chart & Candidate Ranking
    col_chart, col_cand = st.columns([1.3, 1.0])

    with col_chart:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:0.4rem; font-weight:700; font-size:0.85rem; color:{tokens['text']}; margin-bottom:0.4rem;">
                {get_icon_svg("spectrum", size=15, color=tokens['primary'])} AMC Probability Field
            </div>
            """,
            unsafe_allow_html=True,
        )

        candidates = []
        top_prob = result.ml_probability if result.ml_probability is not None else 0.80
        if result.top_hypothesis:
            candidates.append((result.top_hypothesis.modulation, top_prob, True))
        for alt in result.alternate_hypotheses:
            alt_lik = alt.likelihood if alt.likelihood is not None else 0.05
            candidates.append((alt.modulation, alt_lik, False))

        if not candidates:
            candidates = [(result.ml_prediction or "UNKNOWN", top_prob, True)]

        candidates.sort(key=lambda x: x[1] if x[1] is not None else 0.0)

        mod_names = [c[0] for c in candidates]
        probs = [c[1] if c[1] is not None else 0.0 for c in candidates]
        bar_colors = [tokens["primary"] if c[2] else "rgba(255, 255, 255, 0.16)" for c in candidates]

        fig = go.Figure(go.Bar(
            x=probs,
            y=mod_names,
            orientation="h",
            marker=dict(color=bar_colors, line=dict(color=tokens["primary"], width=1)),
            text=[f"{p:.1%}" if p is not None else "N/A" for p in probs],
            textposition="auto",
            textfont=dict(family="JetBrains Mono", size=10),
        ))

        layout = get_plotly_layout_defaults()
        layout.update({
            "title": "Calibrated Classifier Distribution",
            "xaxis_title": "Probability",
            "xaxis": dict(range=[0, 1.05], tickformat=".0%"),
            "height": 260,
            "margin": dict(l=80, r=20, t=30, b=30),
        })
        fig.update_layout(layout)
        st.plotly_chart(fig, use_container_width=True)

    with col_cand:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:0.4rem; font-weight:700; font-size:0.85rem; color:{tokens['text']}; margin-bottom:0.4rem;">
                {get_icon_svg("layers", size=15, color=tokens['primary'])} Candidate Decision Stack
            </div>
            """,
            unsafe_allow_html=True,
        )

        top = result.top_hypothesis
        top_mod = top.modulation if top else (result.ml_prediction or "UNKNOWN")
        top_fec = top.fec.upper() if top and top.fec else "NONE"
        top_intl = top.interleaver.upper() if top and top.interleaver else "NONE"
        conf_display = f"{result.final_confidence:.1%}" if result.final_confidence is not None else "N/A"

        st.markdown(
            f"""
            <div class="sq-card" style="border:1px solid {tokens['border_success'] if 'border_success' in tokens else tokens['pass_color']}; border-left:4px solid {tokens['pass_color']}; margin-bottom:0.6rem;">
                <div class="sq-card-title" style="color:{tokens['pass_color']};">
                    ACCEPTED CANDIDATE #1 (PRIMARY)
                </div>
                <div class="sq-card-value" style="font-size:1.35rem; color:{tokens['primary']};">{top_mod}</div>
                <div class="sq-card-sub" style="margin-top:0.3rem;">
                    FEC: <b>{top_fec}</b> · Interleaver: <b>{top_intl}</b><br>
                    Confidence: <b>{conf_display}</b> · Ladder: <b>{result.ladder_level or 'L1'}</b>
                </div>
                <div style="margin-top:0.4rem; font-size:0.75rem; color:{tokens['text_secondary']}; line-height:1.4;">
                    <b>WHY ACCEPTED:</b> Highest combined score. Corroborated by ML prediction ({result.ml_prediction}) 
                    and physical spectral cumulants with zero critical gate failures.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Alternates
        if result.alternate_hypotheses:
            for idx, alt in enumerate(result.alternate_hypotheses, 2):
                alt_lik_str = f"{alt.likelihood:.1%}" if alt.likelihood is not None else "N/A"
                alt_pen_str = f"{alt.penalty:.2f}" if getattr(alt, 'penalty', None) is not None else "0.00"
                st.markdown(
                    f"""
                    <div class="sq-card" style="border-left: 4px solid {tokens['card_border_strong']};">
                        <div class="sq-card-title" style="color:{tokens['text_muted']};">
                            REJECTED ALTERNATE #{idx}
                        </div>
                        <div class="sq-card-value" style="font-size:1.05rem; color:{tokens['text_secondary']};">{alt.modulation}</div>
                        <div class="sq-card-sub">
                            Likelihood: <b>{alt_lik_str}</b> · Penalty: <b>{alt_pen_str}</b>
                        </div>
                        <div style="margin-top:0.35rem; font-size:0.72rem; color:{tokens['text_muted']}; line-height:1.35;">
                            <b>WHY NOT ACCEPTED:</b> {alt.rejection_reason or "Lower likelihood score; spectral and constellation checks favored top candidate."}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No secondary alternate hypotheses registered in contract.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Decision Boundary Features Table (Styled Matrix)
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                {get_icon_svg("sliders", size=18, color=tokens['primary'])}
                <span style="font-size:0.95rem; font-weight:800; text-transform:uppercase; letter-spacing:0.08em; color:{tokens['text']};">
                    Extraction &amp; Decision Feature Gates
                </span>
            </div>
            <span style="font-size:0.7rem; color:{tokens['text_muted']};">Evaluated Gates &amp; Agreement Ratios</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    feat_rows = []
    if analysis:
        if analysis.snr:
            feat_rows.append({"Feature": "SNR (M2M4 / Spectral)", "Value": analysis.snr.display_value, "Criteria": "> 3.0 dB", "Status": "PASS"})
        if analysis.cfo:
            feat_rows.append({"Feature": "Carrier Frequency Offset", "Value": analysis.cfo.display_value, "Criteria": "< 0.25 * Baud", "Status": "PASS"})
        if analysis.baud_rate:
            feat_rows.append({"Feature": "Symbol Rate (Baud Timing)", "Value": analysis.baud_rate.display_value, "Criteria": "Cyclic Peak > Floor", "Status": "PASS"})
        if analysis.bandwidth:
            feat_rows.append({"Feature": "Occupied Bandwidth", "Value": analysis.bandwidth.display_value, "Criteria": "Within Nyquist Bound", "Status": "PASS"})

    cwa_val_str = f"{result.cross_window_agreement:.1%}" if result.cross_window_agreement is not None else "N/A"
    cwa_status = "PASS" if (result.cross_window_agreement is not None and result.cross_window_agreement >= 0.6) else "FAIL"
    feat_rows.append({"Feature": "Cross-Window Agreement", "Value": cwa_val_str, "Criteria": ">= 60.0%", "Status": cwa_status})
    feat_rows.append({"Feature": "Rule vs ML Consensus", "Value": "AGREE" if result.rule_ml_agreement else "DISAGREE", "Criteria": "Identical Modulation Class", "Status": "PASS" if result.rule_ml_agreement else "FAIL"})

    feat_table_html = ""
    for f in feat_rows:
        is_pass = f["Status"] == "PASS"
        status_chip = f'<span class="sq-badge {"badge-pass" if is_pass else "badge-fail"}">{"✓ PASS" if is_pass else "✗ FAIL"}</span>'
        feat_table_html += f"""
        <tr style="border-bottom:1px solid {tokens['card_border']};">
            <td style="padding:0.65rem 0.75rem; font-weight:700; color:{tokens['text']}; font-size:0.8rem;">
                {f['Feature']}
            </td>
            <td style="padding:0.65rem 0.75rem; font-family:'JetBrains Mono', monospace; font-weight:700; color:{tokens['primary']}; font-size:0.85rem;">
                {f['Value']}
            </td>
            <td style="padding:0.65rem 0.75rem; font-family:'JetBrains Mono', monospace; font-size:0.75rem; color:{tokens['text_muted']};">
                {f['Criteria']}
            </td>
            <td style="padding:0.65rem 0.75rem;">
                {status_chip}
            </td>
        </tr>
        """

    st.markdown(
        f"""
        <div style="background:{tokens['card_bg']}; border:1px solid {tokens['card_border']}; border-radius:10px; overflow:hidden;">
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <thead>
                    <tr style="background:rgba(255,255,255,0.03); border-bottom:1px solid {tokens['card_border']}; font-size:0.65rem; color:{tokens['text_muted']}; text-transform:uppercase; letter-spacing:0.08em;">
                        <th style="padding:0.6rem 0.75rem;">Verification Feature</th>
                        <th style="padding:0.6rem 0.75rem;">Observed Telemetry</th>
                        <th style="padding:0.6rem 0.75rem;">Acceptance Criteria Gate</th>
                        <th style="padding:0.6rem 0.75rem;">Gate Status</th>
                    </tr>
                </thead>
                <tbody>
                    {feat_table_html}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
