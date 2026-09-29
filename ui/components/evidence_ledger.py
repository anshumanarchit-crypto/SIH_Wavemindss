"""
UI Evidence Ledger Component.
Renders the complete, immutable evidence chain collected by Decision Layer.
Each item clearly exposes ID, source, check name, status, value, explanation, and failure rationale.
"""

from typing import Optional
import streamlit as st
from ui.adapters.result_adapter import NormalizedResult
from ui.adapters.evidence_adapter import summarize_evidence


def render_evidence_ledger(result: Optional[NormalizedResult]):
    """Renders the categorized, searchable Evidence Ledger."""
    st.markdown("### Immutable Evidence Ledger & Verification Chain")

    if not result:
        st.info("No evidence ledger loaded.")
        return

    summary = summarize_evidence(result)

    # Metric counts banner
    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
    with mcol1:
        st.metric("Total Audited Checks", summary.total_checks)
    with mcol2:
        st.metric("Passed Checks", summary.passed_count)
    with mcol3:
        st.metric("Failed Checks", summary.failed_count)
    with mcol4:
        st.metric("Unavailable Checks", summary.unavailable_count)
    with mcol5:
        st.metric("Not Run", summary.not_run_count)

    # Contradictions / Warnings section if present
    if summary.contradictions:
        with st.expander("🚨 Contradictions & Disagreements Detected", expanded=True):
            for c in summary.contradictions:
                st.error(f"• {c}")

    if summary.warnings:
        with st.expander("⚠️ Missing Upstream Contracts / Unavailable Features", expanded=False):
            for w in summary.warnings:
                st.warning(f"• {w}")

    # Render category breakdown
    for cat_name, items in summary.categories.items():
        with st.expander(f"📁 {cat_name} ({len(items)} checks)", expanded=True):
            table_data = []
            for it in items:
                status_icon = "✓ PASS" if it.status == "PASS" else (
                    "✕ FAIL" if it.status == "FAIL" else (
                        "⊘ UNAVAIL" if it.status == "UNAVAILABLE" else it.status
                    )
                )
                val_disp = str(it.numeric_value) if it.numeric_value is not None else (
                    str(it.value) if it.value is not None else "N/A"
                )
                table_data.append({
                    "Evidence ID": it.evidence_id,
                    "Source": it.source,
                    "Check Name": it.check_name,
                    "Status": status_icon,
                    "Observed Value": val_disp,
                    "Threshold": str(it.threshold) if it.threshold is not None else "N/A",
                    "Explanation": it.explanation,
                    "Failure Reason": it.failure_reason or "—",
                })
            st.dataframe(table_data, use_container_width=True)
