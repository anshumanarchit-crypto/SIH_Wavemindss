"""
SpectralQ Central Design System.
Defines master color tokens, typography scales, card variants, glow effects,
and Plotly dark/light theme configurations for defense/intelligence telemetry.
"""

from typing import Any, Dict

# Master Color System (Flagsheet Dark Specification)
DESIGN_TOKENS = {
    "dark": {
        # Base Backgrounds
        "bg_base": "#070A0F",
        "bg_secondary": "#0B1017",
        "surface_elevated": "#101720",
        "surface_higher": "#151D27",
        "surface_overlay": "#1A2433",
        
        # Borders
        "border_subtle": "rgba(255, 255, 255, 0.08)",
        "border_medium": "rgba(255, 255, 255, 0.14)",
        "border_accent": "rgba(83, 215, 255, 0.35)",
        "border_success": "rgba(53, 227, 154, 0.35)",
        "border_warning": "rgba(255, 184, 77, 0.35)",
        "border_error": "rgba(255, 98, 120, 0.35)",

        # Typography Colors
        "text_primary": "#F4F7FB",
        "text_secondary": "#A8B2C2",
        "text_tertiary": "#707C90",
        "text_muted": "#525E71",

        # Brand & RF Accents
        "accent_cyan": "#53D7FF",        # Primary RF Accent
        "accent_blue": "#5B8CFF",        # Secondary Electric Blue
        "accent_violet": "#9A7CFF",      # Ladder & Protocol
        "accent_magenta": "#F06BFF",     # Forensics & Burst
        
        # Semantic Status Colors
        "status_pass": "#35E39A",        # Success / Lock
        "status_pass_bg": "rgba(53, 227, 154, 0.12)",
        "status_warn": "#FFB84D",        # Warning / Degraded
        "status_warn_bg": "rgba(255, 184, 77, 0.12)",
        "status_fail": "#FF6278",        # Failure / Discrepancy
        "status_fail_bg": "rgba(255, 98, 120, 0.14)",
        "status_idle": "#707C90",        # Inactive / Bypass
        "status_idle_bg": "rgba(112, 124, 144, 0.12)",
        "status_ladder": "#9A7CFF",
        "status_ladder_bg": "rgba(154, 124, 255, 0.14)",

        # Interactive & Glow Effects
        "glow_cyan": "0 0 16px rgba(83, 215, 255, 0.22)",
        "glow_blue": "0 0 16px rgba(91, 140, 255, 0.22)",
        "glow_pass": "0 0 16px rgba(53, 227, 154, 0.22)",
        "glow_fail": "0 0 16px rgba(255, 98, 120, 0.22)",

        # Plotly Theme
        "plotly_template": "plotly_dark",
        "plot_bg": "#0B1017",
        "paper_bg": "#070A0F",
        "grid_color": "rgba(255, 255, 255, 0.05)",
        "zeroline_color": "rgba(255, 255, 255, 0.12)",
    },
    "light": {
        # Base Backgrounds
        "bg_base": "#F4F7FB",
        "bg_secondary": "#EBF0F6",
        "surface_elevated": "#FFFFFF",
        "surface_higher": "#F9FAFC",
        "surface_overlay": "#E2E8F0",
        
        # Borders
        "border_subtle": "#D8E0EA",
        "border_medium": "#B8C4D4",
        "border_accent": "#0969DA",
        "border_success": "#2DA44E",
        "border_warning": "#D4A72C",
        "border_error": "#FF8182",

        # Typography Colors
        "text_primary": "#152033",
        "text_secondary": "#5C6B7F",
        "text_tertiary": "#8A99AD",
        "text_muted": "#A0AEC0",

        # Brand & RF Accents
        "accent_cyan": "#0969DA",
        "accent_blue": "#0550AE",
        "accent_violet": "#8250DF",
        "accent_magenta": "#BF3989",
        
        # Semantic Status Colors
        "status_pass": "#1A7F37",
        "status_pass_bg": "#DAFBE1",
        "status_warn": "#9A6700",
        "status_warn_bg": "#FFF8C5",
        "status_fail": "#CF222E",
        "status_fail_bg": "#FFEBE9",
        "status_idle": "#57606A",
        "status_idle_bg": "#F6F8FA",
        "status_ladder": "#0969DA",
        "status_ladder_bg": "#DDF4FF",

        # Interactive & Glow Effects
        "glow_cyan": "0 2px 10px rgba(9, 105, 218, 0.15)",
        "glow_blue": "0 2px 10px rgba(5, 80, 174, 0.15)",
        "glow_pass": "0 2px 10px rgba(26, 127, 55, 0.15)",
        "glow_fail": "0 2px 10px rgba(207, 34, 46, 0.15)",

        # Plotly Theme
        "plotly_template": "plotly_white",
        "plot_bg": "#FFFFFF",
        "paper_bg": "#F4F7FB",
        "grid_color": "#E5E9F0",
        "zeroline_color": "#CBD5E1",
    }
}


def get_design_tokens(theme_name: str = "dark") -> Dict[str, Any]:
    """Returns the design token palette for the specified theme."""
    return DESIGN_TOKENS.get(theme_name, DESIGN_TOKENS["dark"])
