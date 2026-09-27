"""
UI Modulation Panel Component.
Renders detected modulation, ML vs Rule-AMC consensus, feature vector,
and candidate hypotheses table strictly using backend ordering.
"""

from typing import Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.analysis_adapter import NormalizedAnalysis


def render_modulation_panel(
    result: Optional[NormalizedResult],
    analysis: Optional[NormalizedAnalysis],
):
    """Renders the comprehensive modulation analysis panel."""
    st.markdown("### Modulation Classification & Hypothesis Space")

    if not result:
        st.info("No modulation results loaded.")
        return

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown("#### AMC & ML Classifier Consensus (N5)")
        st.write(f"**Top Confirmed Hypothesis:** `{result.top_hypothesis.modulation}`")
        st.write(f"**RandomForest ML Prediction:** `{result.ml_prediction}` (Probability: `{result.ml_probability:.3f}`)")
        if result.calibrated_ml_probability is not None:
            st.write(f"**Calibrated Probability (Sigmoid):** `{result.calibrated_ml_probability:.3f}`")
        st.write(f"**Deterministic Rule-Based AMC:** `{result.rule_prediction}`")

        # Agreement indicator
        if result.rule_ml_agreement:
            st.success(f"✓ Consensus Agreement: Rule AMC and ML Classifier agree on {result.ml_prediction} (Penalty: 0.00)")
        else:
            st.warning(
                f"⚠ Disagreement Penalty Applied: Rule AMC predicts {result.rule_prediction} while ML predicts {result.ml_prediction}. "
                f"Confidence penalty: -{result.rule_ml_penalty:.2f}"
            )

        st.write(f"**Temporal Cross-Window Stability:** `{result.cross_window_agreement * 100:.1f}%`")

    with col2:
        st.markdown("#### Physical & Statistical Features")
        if analysis and analysis.features:
            cum = analysis.features.cumulants
            st.markdown(
                f"""
                - **HOS Cumulants:**
                  - $C_{{20}} = {cum.get('C20', 0.0):.4f}$ • $C_{{21}} = {cum.get('C21', 1.0):.4f}$
                  - $C_{{40}} = {cum.get('C40', 0.0):.4f}$ • $C_{{42}} = {cum.get('C42', 0.0):.4f}$
                  - $C_{{60}} = {cum.get('C60', 0.0):.4f}$ • $C_{{63}} = {cum.get('C63', 0.0):.4f}$
                - **Constellation Clustering:**
                  - Cluster count: `{analysis.features.cluster_count}`
                  - Silhouette score: `{analysis.features.silhouette:.3f}`
                  - Intra-cluster variance: `{analysis.features.intra_var:.4f}`
                  - Inter-cluster distance: `{analysis.features.inter_dist:.4f}`
                - **EVM:** `{analysis.features.evm:.4f}`
                - **Phase Ambiguity Quality:** `{analysis.features.phase_ambiguity_quality if analysis.features.phase_ambiguity_quality is not None else 'N/A'}`
                """
            )
        else:
            st.info("Feature extraction metrics unavailable for this capture.")

    # Alternate Hypotheses Table
    if result.alternate_hypotheses:
        st.markdown("#### Candidate Hypotheses Ranking (Backend Ordered)")
        table_rows = []
        for i, alt in enumerate(result.alternate_hypotheses, start=1):
            table_rows.append({
                "Rank": i,
                "Modulation": alt.modulation,
                "Interleaver": alt.interleaver,
                "FEC": alt.fec,
                "Prior Score": f"{alt.prior_score:.3f}" if alt.prior_score is not None else "N/A",
                "Verification": f"{alt.verification_score:.3f}" if alt.verification_score is not None else "N/A",
                "Total Score": f"{alt.total_score:.4f}" if alt.total_score is not None else "N/A",
                "Status": alt.status,
                "Rejection Reason": alt.rejection_reason or "None",
            })
        st.dataframe(table_rows, use_container_width=True)
    else:
        st.caption("No alternative candidate hypotheses recorded in result contract.")
