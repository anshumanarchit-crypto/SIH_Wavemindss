"""
UI UNKNOWN Signal Banner Component.
Displays first-class UNKNOWN state when evidence is insufficient or conflicts occur.
Upholds SpectralQ's core scientific principle: ABSTAIN WHEN EVIDENCE IS INSUFFICIENT.
"""

from typing import List, Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult


def render_unknown_banner(result: NormalizedResult):
    """Renders prominent UNKNOWN state banner if the engine abstained."""
    if not result.is_unknown:
        return

    reason = result.unknown_reason or "Evidence insufficient to make a defensible modulation/decoding decision."
    failed_checks: List[str] = result.failed_checks
    unavailable_checks: List[str] = result.unavailable_checks

    reasons_html = f"<li>{reason}</li>"
    if not result.rule_ml_agreement:
        reasons_html += f"<li>Rule AMC ({result.rule_prediction}) and ML Classifier ({result.ml_prediction}) conflict</li>"
    for fc in failed_checks[:3]:
        reasons_html += f"<li>Failed physical verification: <code>{fc}</code></li>"
    for uc in unavailable_checks[:2]:
        reasons_html += f"<li>Critical upstream feature absent: <code>{uc}</code></li>"

    st.markdown(
        f"""
        <div class="sq-unknown-banner">
            <div class="sq-unknown-title">
                ⚠️ UNKNOWN SIGNAL — DECISION ABSTENTION
            </div>
            <div class="sq-unknown-desc">
                <strong>Defensible Scientific Guarantee:</strong> SpectralQ explicitly abstains when observational evidence is insufficient, contradictory, or below physical operating thresholds.
                <br><br>
                <strong>Abstention Rationale &amp; Conflicting Evidence:</strong>
                <ul style="margin-top: 0.4rem; margin-bottom: 0.6rem; padding-left: 1.2rem;">
                    {reasons_html}
                </ul>
                <em>No unsupported or unverified guess has been made. Ladder Level capped at {result.ladder_level}.</em>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
