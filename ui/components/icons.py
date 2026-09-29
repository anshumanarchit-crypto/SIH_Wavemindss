"""
SpectralQ Vector Iconography Engine.
High-precision Lucide-style inline SVG vector icons for defense/intelligence telemetry.
All icons are 24x24 viewBox, stroke-width 1.75, stroke-linecap="round", stroke-linejoin="round".
"""

from typing import Optional

ICONS = {
    # ── Workspaces ────────────────────────────────────────────────────────
    "mission_control": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/>'
        '<line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/>'
        '<line x1="12" y1="22" x2="12" y2="18"/><circle cx="12" cy="12" r="4"/>'
        '</svg>'
    ),
    "signal_observatory": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 6a6 6 0 1 0 6 6"/>'
        '<circle cx="12" cy="12" r="2"/><line x1="12" y1="12" x2="19" y2="5"/>'
        '</svg>'
    ),
    "modulation_hypotheses": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5" fill="{color}"/>'
        '<circle cx="16" cy="8" r="1.5" fill="{color}"/><circle cx="8" cy="16" r="1.5" fill="{color}"/>'
        '<circle cx="16" cy="16" r="1.5" fill="{color}"/><line x1="12" y1="3" x2="12" y2="21" stroke-dasharray="2 2"/>'
        '<line x1="3" y1="12" x2="21" y2="12" stroke-dasharray="2 2"/>'
        '</svg>'
    ),
    "decoder_bitstream": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>'
        '<circle cx="18" cy="7" r="1"/><circle cx="14" cy="7" r="1"/><circle cx="18" cy="11" r="1"/>'
        '</svg>'
    ),
    "evidence_decision": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<polyline points="9 12 11 14 15 10"/>'
        '</svg>'
    ),
    "provenance_export": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M12 2a10 10 0 0 0-6.88 17.23L7 21a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1.88-1.77A10 10 0 0 0 12 2z"/>'
        '<circle cx="12" cy="11" r="3"/><line x1="12" y1="18" x2="12.01" y2="18"/>'
        '</svg>'
    ),
    "signal_lab": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M6 2v6a6 6 0 0 0 6 6 6 6 0 0 0 6-6V2"/><line x1="4" y1="2" x2="20" y2="2"/>'
        '<line x1="6" y1="14" x2="3" y2="21a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1l-3-7"/>'
        '</svg>'
    ),
    "synthetic_generator": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/><line x1="9" y1="6" x2="15" y2="6"/>'
        '<line x1="6" y1="9" x2="6" y2="15"/><line x1="18" y1="9" x2="18" y2="15"/>'
        '<line x1="9" y1="18" x2="15" y2="18"/><line x1="8.5" y1="8.5" x2="15.5" y2="15.5"/>'
        '</svg>'
    ),
    "wideband_scanner": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M2 12h3l2-6 4 12 3-8 2 4h6"/>'
        '</svg>'
    ),
    "run_trace": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'
        '</svg>'
    ),

    # ── Telemetry & Actions ───────────────────────────────────────────────
    "waveform": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M3 12h2l3-9 4 18 3-12 2 6 2-3h3"/>'
        '</svg>'
    ),
    "spectrum": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<rect x="2" y="14" width="3" height="8" rx="1"/><rect x="7" y="8" width="3" height="14" rx="1"/>'
        '<rect x="12" y="3" width="3" height="19" rx="1"/><rect x="17" y="10" width="3" height="12" rx="1"/>'
        '<rect x="22" y="16" width="3" height="6" rx="1"/>'
        '</svg>'
    ),
    "check": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<polyline points="20 6 9 17 4 12"/>'
        '</svg>'
    ),
    "circle_check": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><polyline points="16 9 10 15 8 13"/>'
        '</svg>'
    ),
    "x": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
        '</svg>'
    ),
    "circle_x": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'
        '</svg>'
    ),
    "alert_triangle": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
        '</svg>'
    ),
    "shield_alert": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'
        '</svg>'
    ),
    "arrow_right": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>'
        '</svg>'
    ),
    "download": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" y1="15" x2="12" y2="3"/>'
        '</svg>'
    ),
    "refresh": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
        '</svg>'
    ),
    "info": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'
        '</svg>'
    ),
    "file": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '</svg>'
    ),
    "zap": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
        '</svg>'
    ),
    "target": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'
        '</svg>'
    ),
    "layers": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'
        '</svg>'
    ),
    "sliders": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/>'
        '<line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
        '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>'
        '</svg>'
    ),
    "logo_mark": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>'
        '<line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/>'
        '<circle cx="12" cy="9" r="2.5" fill="{color}"/>'
        '</svg>'
    ),
    "sun": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
        '<line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>'
        '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
        '</svg>'
    ),
    "moon": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
        '</svg>'
    ),
    "eye": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'
        '</svg>'
    ),
    "clock": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/>'
        '</svg>'
    ),
    "help_circle": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
        '</svg>'
    ),
    "activity": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
        '</svg>'
    ),
    "radio": (
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" class="{extra_class}">'
        '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>'
        '</svg>'
    ),
}

# Workspace to icon name mapping
WORKSPACE_ICON_KEYS = {
    "Mission Control": "mission_control",
    "Signal Observatory": "signal_observatory",
    "Modulation & Hypotheses": "modulation_hypotheses",
    "Decoder & Bitstream": "decoder_bitstream",
    "Evidence & Decision": "evidence_decision",
    "Provenance & Export": "provenance_export",
    "Signal Lab / Simulation": "signal_lab",
    "🧬 Synthetic Generator": "synthetic_generator",
    "Synthetic Generator": "synthetic_generator",
    "Wideband Scanner": "wideband_scanner",
    "Run Trace": "run_trace",
}


def get_icon_svg(
    name: str,
    size: int = 18,
    color: str = "currentColor",
    stroke: float = 1.75,
    extra_class: str = "",
) -> str:
    """Returns the raw SVG string for a named icon."""
    template = ICONS.get(name)
    if not template:
        template = ICONS["target"]
    return template.format(size=size, color=color, stroke=stroke, extra_class=extra_class)


def get_workspace_icon_svg(workspace_name: str, size: int = 18, color: str = "currentColor") -> str:
    """Returns the SVG string for a given workspace name."""
    icon_key = WORKSPACE_ICON_KEYS.get(workspace_name, "target")
    return get_icon_svg(icon_key, size=size, color=color)
