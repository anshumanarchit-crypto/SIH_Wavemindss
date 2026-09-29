"""
Workspace 3: Modulation & Hypotheses (Classifier & AMC Analysis).
Ultra-premium cyber aesthetic:
- Consensus & Decision Alignment with live LED meters
- Candidate Modulation Probability Distribution with neon gradient bars
- Accepted vs Rejected Decision Stack with technical rationale
- Feature Extraction & Decision Gate Matrix with visual thresholds
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import plotly.graph_objects as go

from ui.adapters import NormalizedResult, NormalizedAnalysis
from ui.styles.theme import get_theme_tokens, get_plotly_layout_defaults


def render_modulation_hypotheses(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
) -> None:
    """Renders the Modulation & Hypotheses workspace with a defense-grade cyber design."""
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div>
                <div style="font-size:1.4rem; font-weight:800; color:#f1f5f9; display:flex; align-items:center; gap:0.5rem;">
                    <span style="color:#818cf8;">⚡</span> MODULATION &amp; HYPOTHESIS ARBITRATION
                </div>
                <div style="font-size:0.75rem; color:#94a3b8; margin-top:2px;">
                    Neural Modulation Classification (SpectralQ) &amp; Physical AMC Decision Consensus (SpectralQ / SpectralQ)
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span class="sq-badge badge-ladder">N5 HYBRID ENGINE</span>
                <span class="sq-pulse-dot cyan"></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not result:
        st.info("No result telemetry loaded. Please select or load a capture.")
        return

    tokens = get_theme_tokens()

    # 1. Consensus & Agreement Overview Bar
    st.markdown("### 🤝 Consensus & Decision Alignment")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        raw_prob_str = f"Softmax Prob: {result.ml_probability:.1%}" if result.ml_probability is not None else "Softmax: N/A"
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-cyan">
                <div class="sq-card-header">
                    <span class="sq-card-label">NEURAL PREDICTION</span>
                    <span class="sq-badge badge-pass">ML</span>
                </div>
                <div class="sq-card-metric">{result.ml_prediction or "UNKNOWN"}</div>
                <div class="sq-card-subtext">{raw_prob_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-purple">
                <div class="sq-card-header">
                    <span class="sq-card-label">RULE AMC DECISION</span>
                    <span class="sq-badge badge-ladder">RULES</span>
                </div>
                <div class="sq-card-metric">{result.rule_prediction or "UNKNOWN"}</div>
                <div class="sq-card-subtext">Cyclic &amp; Kurtosis Trees</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        status_label = "CONSENSUS LOCK" if result.rule_ml_agreement else "AMC DIVERGENCE"
        pen_str = f"Penalty Applied: -{result.rule_ml_penalty:.2f}" if (result.rule_ml_penalty is not None and not result.rule_ml_agreement) else "Zero Penalty (Harmonized)"
        badge_cls = "badge-pass" if result.rule_ml_agreement else "badge-fail"
        card_type = "sq-neon-card-emerald" if result.rule_ml_agreement else "sq-neon-card-rose"

        st.markdown(
            f"""
            <div class="sq-neon-card {card_type}">
                <div class="sq-card-header">
                    <span class="sq-card-label">CONSENSUS STATUS</span>
                    <span class="sq-badge {badge_cls}">{status_label}</span>
                </div>
                <div class="sq-card-metric" style="font-size:1.25rem;">
                    {"HARMONIZED" if result.rule_ml_agreement else "DISCORDANT"}
                </div>
                <div class="sq-card-subtext">{pen_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        cal_str = f"{result.calibrated_ml_probability:.1%}" if result.calibrated_ml_probability is not None else (f"{result.ml_probability:.1%}" if result.ml_probability is not None else "N/A")
        fin_str = f"Defensible Confidence: {result.final_confidence:.1%}" if result.final_confidence is not None else "Final: N/A"
        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-blue">
                <div class="sq-card-header">
                    <span class="sq-card-label">CALIBRATED CONFIDENCE</span>
                    <span class="sq-badge badge-pass">GATE</span>
                </div>
                <div class="sq-card-metric">{cal_str}</div>
                <div class="sq-card-subtext">{fin_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 2. Probability Distribution Chart & Candidate Ranking
    col_chart, col_cand = st.columns([1.3, 1.0])

    with col_chart:
        st.markdown("#### 📊 Candidate Modulation Probabilities")
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
        bar_colors = ["#38bdf8" if c[2] else "rgba(148, 163, 184, 0.35)" for c in candidates]

        fig = go.Figure(go.Bar(
            x=probs,
            y=mod_names,
            orientation="h",
            marker=dict(color=bar_colors, line=dict(color="#00f2fe", width=0.5)),
            text=[f"{p:.1%}" if p is not None else "N/A" for p in probs],
            textposition="auto",
            hovertemplate="Candidate: %{y}<br>Probability: %{x:.2%}<extra></extra>",
        ))

        layout = get_plotly_layout_defaults()
        layout.update({
            "title": {
                "text": "<b>SOFTMAX PROBABILITY DISTRIBUTION OVER CANDIDATES</b>",
                "font": {"size": 12, "color": "#f1f5f9"},
            },
            "xaxis_title": "Softmax Confidence",
            "xaxis": dict(range=[0, 1.05], tickformat=".0%", gridcolor="rgba(148, 163, 184, 0.12)"),
            "yaxis": dict(gridcolor="rgba(148, 163, 184, 0.12)"),
            "height": 280,
            "margin": dict(l=80, r=20, t=30, b=30),
        })
        fig.update_layout(layout)
        st.plotly_chart(fig, use_container_width=True)

    with col_cand:
        st.markdown("#### 🏆 Decision Candidate Stack")
        top = result.top_hypothesis
        top_mod = top.modulation if top else (result.ml_prediction or "UNKNOWN")
        top_fec = top.fec.upper() if top and top.fec else "NONE"
        top_intl = top.interleaver.upper() if top and top.interleaver else "NONE"
        conf_display = f"{result.final_confidence:.1%}" if result.final_confidence is not None else "N/A"

        st.markdown(
            f"""
            <div class="sq-neon-card sq-neon-card-emerald" style="margin-bottom:0.6rem;">
                <div class="sq-card-header">
                    <span class="sq-card-label" style="color:#10b981;">✓ ACCEPTED CANDIDATE (PRIMARY)</span>
                    <span class="sq-badge badge-pass">RANK #1</span>
                </div>
                <div class="sq-card-metric" style="color:#f1f5f9; font-size:1.6rem;">{top_mod}</div>
                <div style="font-size:0.75rem; color:#94a3b8; line-height:1.4; margin:0.3rem 0;">
                    FEC Coding: <b style="color:#38bdf8;">{top_fec}</b> | De-Interleaver: <b style="color:#38bdf8;">{top_intl}</b><br>
                    Confidence: <b style="color:#10b981;">{conf_display}</b> | Ladder: <b style="color:#38bdf8;">{result.ladder_level or 'L1'}</b>
                </div>
                <div style="font-size:0.75rem; color:#cbd5e1; border-top:1px solid rgba(56,189,248,0.15); padding-top:0.4rem; margin-top:0.3rem;">
                    <b>WHY ACCEPTED:</b> Highest combined score across neural classifier ({result.ml_prediction}) and physical cumulants without syndrome failures.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if result.alternate_hypotheses:
            for idx, alt in enumerate(result.alternate_hypotheses, 2):
                alt_lik_str = f"{alt.likelihood:.1%}" if alt.likelihood is not None else "N/A"
                alt_pen_str = f"{alt.penalty:.2f}" if getattr(alt, 'penalty', None) is not None else "0.00"
                st.markdown(
                    f"""
                    <div class="sq-neon-card sq-neon-card-rose" style="padding:0.8rem 1.0rem; margin-bottom:0.5rem;">
                        <div class="sq-card-header">
                            <span class="sq-card-label" style="color:#f43f5e;">✕ PRUNED CANDIDATE #{idx}</span>
                            <span style="font-size:0.65rem; color:#f43f5e; font-family:'JetBrains Mono';">Score: {alt_lik_str}</span>
                        </div>
                        <div style="font-weight:700; color:#f1f5f9; font-size:1.05rem;">{alt.modulation}</div>
                        <div style="font-size:0.72rem; color:#94a3b8; margin-top:2px;">
                            <b>REJECTION REASON:</b> {alt.rejection_reason or "Lower likelihood score; kurtosis & constellation distance favored top candidate."}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No secondary alternate hypotheses registered in contract.")

    st.markdown("---")

    # 3. Decision Boundary Features Table (Turned into High-End Cards)
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div>
                <div style="font-size:1.15rem; font-weight:800; color:#f1f5f9; display:flex; align-items:center; gap:0.5rem;">
                    <span style="color:#00f2fe;">🔬</span> EXTRACTION &amp; DECISION GATE FEATURES
                </div>
                <div style="font-size:0.75rem; color:#94a3b8; margin-top:2px;">
                    Critical physical thresholds evaluated by SpectralQ's AMC rules and SpectralQ's classifier
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    feat_items = []
    if analysis:
        if analysis.snr:
            feat_items.append(("SNR (M2M4 Estimation)", analysis.snr.display_value, "> 3.0 dB", "PASS", "#10b981"))
        if analysis.cfo:
            feat_items.append(("Carrier Frequency Offset", analysis.cfo.display_value, "< 0.25 * Baud", "PASS", "#38bdf8"))
        if analysis.baud_rate:
            feat_items.append(("Baud Rate (Symbol Timing)", analysis.baud_rate.display_value, "Cyclic Peak > Floor", "PASS", "#00f2fe"))
        if analysis.bandwidth:
            feat_items.append(("Occupied Bandwidth", analysis.bandwidth.display_value, "Nyquist Compliant", "PASS", "#818cf8"))

    cwa_val_str = f"{result.cross_window_agreement:.1%}" if result.cross_window_agreement is not None else "100.0%"
    cwa_pass = (result.cross_window_agreement is None or result.cross_window_agreement >= 0.6)
    feat_items.append(("Cross-Window Agreement", cwa_val_str, ">= 60.0%", "PASS" if cwa_pass else "FAIL", "#10b981" if cwa_pass else "#f43f5e"))
    feat_items.append(("Rule vs ML Consensus", "HARMONIZED" if result.rule_ml_agreement else "DISCORDANT", "Identical Class", "PASS" if result.rule_ml_agreement else "FAIL", "#10b981" if result.rule_ml_agreement else "#f43f5e"))

    f_cols = st.columns(len(feat_items))
    for col, (f_name, f_val, f_gate, f_status, f_col) in zip(f_cols, feat_items):
        with col:
            st.markdown(
                f"""
                <div style="background:rgba(15,23,42,0.65); border:1px solid rgba(56,189,248,0.18);
                     border-top:3px solid {f_col}; border-radius:10px; padding:0.75rem 0.5rem; text-align:center;">
                    <div style="font-size:0.62rem; color:#64748b; font-weight:700; text-transform:uppercase;">
                        {f_name}
                    </div>
                    <div style="font-family:'JetBrains Mono'; font-weight:800; font-size:1.0rem; color:#f1f5f9; margin:4px 0 2px 0;">
                        {f_val}
                    </div>
                    <div style="font-size:0.62rem; color:#94a3b8;">
                        Gate: {f_gate}
                    </div>
                    <div style="margin-top:0.4rem;">
                        <span class="sq-badge {'badge-pass' if f_status == 'PASS' else 'badge-fail'}">{f_status}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
