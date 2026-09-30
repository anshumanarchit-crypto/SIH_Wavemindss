"""
UI Components package.
Provides modular workspaces, navigation, telemetry summaries, and export tools.
"""

from ui.components.header import render_header
from ui.components.unknown_banner import render_unknown_banner
from ui.components.summary_cards import render_summary_cards
from ui.components.pipeline_stepper import render_pipeline_stepper
from ui.components.modulation_card import render_modulation_panel
from ui.components.decoder_card import render_decoder_panel
from ui.components.evidence_ledger import render_evidence_ledger
from ui.components.forensics_card import render_forensics_card
from ui.components.bundle_exporter import render_bundle_exporter, generate_sigmf_metadata
from ui.components.bitstream_card import render_bitstream_panel

# Production V2 Workspace Components
from ui.components.navigation import render_sidebar
from ui.components.mission_control import render_mission_control
from ui.components.signal_observatory import render_signal_observatory
from ui.components.modulation_hypotheses import render_modulation_hypotheses
from ui.components.decoder_bitstream import render_decoder_bitstream
from ui.components.evidence_decision import render_evidence_decision
from ui.components.provenance_export import render_provenance_export
from ui.components.signal_lab import render_signal_lab
from ui.components.wideband_scanner import render_wideband_scanner
from ui.components.run_trace import render_run_trace
from ui.components.synthetic_generator import render_synthetic_signal_generator

__all__ = [
    "render_header",
    "render_unknown_banner",
    "render_summary_cards",
    "render_pipeline_stepper",
    "render_modulation_panel",
    "render_decoder_panel",
    "render_evidence_ledger",
    "render_forensics_card",
    "render_bundle_exporter",
    "generate_sigmf_metadata",
    "render_bitstream_panel",
    "render_sidebar",
    "render_mission_control",
    "render_signal_observatory",
    "render_modulation_hypotheses",
    "render_decoder_bitstream",
    "render_evidence_decision",
    "render_provenance_export",
    "render_signal_lab",
    "render_wideband_scanner",
    "render_run_trace",
    "render_synthetic_signal_generator",
]
