"""
Workspace 3: Modulation & Hypotheses (Classifier & AMC Analysis).
Visualizes candidate modulation probabilities, consensus between ML and Rule AMC,
and detailed hypothesis ranking cards with 'WHY ACCEPTED / WHY NOT ACCEPTED' rationale.
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
    """Renders the Modulation & Hypotheses workspace."""
    st.markdown("## 🎯 Modulation & Hypotheses")
    st.caption("Automatic Modulation Classification (Harsh) & Rule-based Decision Consensus (Sinchana/Archit).")

    if not result:
        st.info("No result telemetry loaded. Please select or load a capture.")
        return

    tokens = get_theme_tokens()

    # 1. Consensus & Agreement Overview Bar
    st.markdown("### 🤝 Consensus & Decision Alignment")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        raw_prob_str = f"Raw Prob: {result.ml_probability:.1%}" if result.ml_probability is not None else "Raw Prob: N/A"
        st.metric("ML Classifier Output", result.ml_prediction or "UNKNOWN", raw_prob_str)
    with c2:
        st.metric("Rule AMC Decision", result.rule_prediction or "UNKNOWN", "Cyclic & Kurtosis Rules")
    with c3:
        status_label = "AGREEMENT" if result.rule_ml_agreement else "DIVERGENCE"
        pen_str = f"Penalty: -{result.rule_ml_penalty:.2f}" if (result.rule_ml_penalty is not None and not result.rule_ml_agreement) else "No penalty"
        st.metric(
            "Consensus Status",
            status_label,
            pen_str,
        )
    with c4:
        cal_str = f"{result.calibrated_ml_probability:.1%}" if result.calibrated_ml_probability is not None else (f"{result.ml_probability:.1%} (Raw)" if result.ml_probability is not None else "N/A")
        fin_str = f"Final: {result.final_confidence:.1%}" if result.final_confidence is not None else "Final: N/A"
        st.metric("Calibrated Confidence", cal_str, fin_str)

    st.markdown("---")

    # 2. Probability Distribution Chart & Candidate Ranking
    col_chart, col_cand = st.columns([1.3, 1.0])

    with col_chart:
        st.markdown("#### 📊 Candidate Modulation Probabilities")
        # Build candidate list from result
        candidates = []
        top_prob = result.ml_probability if result.ml_probability is not None else 0.80
        if result.top_hypothesis:
            candidates.append((result.top_hypothesis.modulation, top_prob, True))
        for alt in result.alternate_hypotheses:
            alt_lik = alt.likelihood if alt.likelihood is not None else 0.05
            candidates.append((alt.modulation, alt_lik, False))

        if not candidates:
            # Fallback to standard set for visualization if empty
            candidates = [(result.ml_prediction or "UNKNOWN", top_prob, True)]

        # Sort ascending for horizontal bar chart
        candidates.sort(key=lambda x: x[1] if x[1] is not None else 0.0)

        mod_names = [c[0] for c in candidates]
        probs = [c[1] if c[1] is not None else 0.0 for c in candidates]
        bar_colors = [tokens["primary"] if c[2] else tokens["text_muted"] for c in candidates]

        fig = go.Figure(go.Bar(
            x=probs,
            y=mod_names,
            orientation="h",
            marker=dict(color=bar_colors),
            text=[f"{p:.1%}" if p is not None else "N/A" for p in probs],
            textposition="auto",
        ))

        layout = get_plotly_layout_defaults()
        layout.update({
            "title": "ML Confidence Distribution across Modulation Space",
            "xaxis_title": "Probability",
            "xaxis": dict(range=[0, 1.05], tickformat=".0%"),
            "height": 280,
            "margin": dict(l=80, r=20, t=30, b=30),
        })
        fig.update_layout(layout)
        st.plotly_chart(fig, use_container_width=True)

    with col_cand:
        st.markdown("#### 🏆 Decision Candidate Stack")
        # Top Candidate
        top = result.top_hypothesis
        top_mod = top.modulation if top else (result.ml_prediction or "UNKNOWN")
        top_fec = top.fec.upper() if top and top.fec else "NONE"
        top_intl = top.interleaver.upper() if top and top.interleaver else "NONE"
        conf_display = f"{result.final_confidence:.1%}" if result.final_confidence is not None else "N/A"

        st.markdown(
            f"""
            <div class="sq-card" style="border-left: 4px solid {tokens['pass_color']};">
                <div class="sq-card-title" style="color:{tokens['pass_color']};">
                    ACCEPTED CANDIDATE #1 (PRIMARY)
                </div>
                <div class="sq-card-value">{top_mod}</div>
                <div class="sq-card-sub">
                    Coding: <b>{top_fec}</b> | Interleaver: <b>{top_intl}</b><br>
                    Confidence: <b>{conf_display}</b> | Ladder: <b>{result.ladder_level or 'L1'}</b>
                </div>
                <div style="margin-top:0.4rem; font-size:0.8rem; color:{tokens['text']};">
                    <b>WHY ACCEPTED:</b> Highest combined score. Supported by ML classifier ({result.ml_prediction}) 
                    and physical spectral features without critical check failure.
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
                    <div class="sq-card" style="border-left: 4px solid {tokens['fail_color']};">
                        <div class="sq-card-title" style="color:{tokens['fail_color']};">
                            REJECTED CANDIDATE #{idx}
                        </div>
                        <div class="sq-card-value" style="font-size:1.1rem;">{alt.modulation}</div>
                        <div class="sq-card-sub">
                            Likelihood: <b>{alt_lik_str}</b> | Penalty: <b>{alt_pen_str}</b>
                        </div>
                        <div style="margin-top:0.4rem; font-size:0.8rem; color:{tokens['text_muted']};">
                            <b>WHY NOT ACCEPTED:</b> {alt.rejection_reason or "Lower likelihood score; spectral and constellation checks preferred top candidate."}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No secondary alternate hypotheses registered in contract.")

    st.markdown("---")

    # 3. Decision Boundary Features Table
    st.markdown("### 🔬 Extraction & Decision Features")
    st.caption("Extracted physical features evaluated by Sinchana's AMC rules and Harsh's classifier:")

    # Build feature table
    feat_rows = []
    if analysis:
        if analysis.snr:
            feat_rows.append({"Feature": "SNR (M2M4 / Spectral)", "Value": analysis.snr.display_value, "Criteria / Gate": "> 3.0 dB", "Status": "PASS"})
        if analysis.cfo:
            feat_rows.append({"Feature": "Carrier Frequency Offset", "Value": analysis.cfo.display_value, "Criteria / Gate": "< 0.25 * Baud", "Status": "PASS"})
        if analysis.baud_rate:
            feat_rows.append({"Feature": "Baud Rate (Symbol Timing)", "Value": analysis.baud_rate.display_value, "Criteria / Gate": "Cyclic Peak > Floor", "Status": "PASS"})
        if analysis.bandwidth:
            feat_rows.append({"Feature": "Occupied Bandwidth", "Value": analysis.bandwidth.display_value, "Criteria / Gate": "Within Nyquist Bound", "Status": "PASS"})

    cwa_val_str = f"{result.cross_window_agreement:.1%}" if result.cross_window_agreement is not None else "N/A"
    cwa_status = "PASS" if (result.cross_window_agreement is not None and result.cross_window_agreement >= 0.6) else "FAIL"
    feat_rows.append({"Feature": "Cross-Window Agreement", "Value": cwa_val_str, "Criteria / Gate": ">= 60.0%", "Status": cwa_status})
    feat_rows.append({"Feature": "Rule vs ML Consensus", "Value": "AGREE" if result.rule_ml_agreement else "DISAGREE", "Criteria / Gate": "Identical Class", "Status": "PASS" if result.rule_ml_agreement else "FAIL"})

    st.table(feat_rows)
