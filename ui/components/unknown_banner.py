"""
UI UNKNOWN Signal Banner Component.
Displays first-class UNKNOWN state when evidence is insufficient or conflicts occur.
Upholds SpectralQ's core scientific principle: ABSTAIN WHEN EVIDENCE IS INSUFFICIENT.
"""

from typing import List, Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.styles.theme import get_theme_tokens
from ui.components.icons import get_icon_svg


def render_unknown_banner(result: NormalizedResult):
    """Renders prominent UNKNOWN state banner if the engine abstained."""
    if not result.is_unknown:
        return

    tokens = get_theme_tokens()
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

    shield_icon = get_icon_svg("shield_alert", size=22, color=tokens["fail_color"])

    st.markdown(
        f"""
        <div class="sq-unknown-banner">
            <div style="display:flex; align-items:flex-start; gap:0.75rem;">
                <div style="background:{tokens['fail_bg']}; border:1px solid {tokens['fail_color']};
                    border-radius:8px; width:38px; height:38px; display:flex; align-items:center;
                    justify-content:center; flex-shrink:0;">
                    {shield_icon}
                </div>
                <div>
                    <div style="font-size:1.05rem; font-weight:800; color:{tokens['fail_color']}; letter-spacing:0.02em;">
                        EPISTEMIC ABSTENTION · ZERO SPECULATIVE GUESSES
                    </div>
                    <div style="color:{tokens['text']}; font-size:0.84rem; line-height:1.5; margin-top:0.35rem;">
                        <strong>Scientific Principle:</strong> SpectralQ explicitly declines classification when observational evidence is insufficient, contradictory, or below physical sensitivity floors.
                        <br><br>
                        <strong>Abstention Rationale &amp; Conflicting Telemetry:</strong>
                        <ul style="margin-top: 0.3rem; margin-bottom: 0.5rem; padding-left: 1.2rem; font-size:0.8rem;">
                            {reasons_html}
                        </ul>
                        <span style="font-size:0.75rem; color:{tokens['text_muted']};">
                            Zero unverified guesses emitted. Evidence Ladder strictly capped at Level {result.ladder_level}.
                        </span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
