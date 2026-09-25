# GNU Octave Bridge Directory

This directory contains external GNU Octave (`.m`) DSP scripts when provided by Sinchana.

If GNU Octave or `octave-cli` is absent from the host machine:
- SpectralQ automatically surfaces `capability_unavailable: True`.
- The bridge reports this status in the evidence ledger audit trail.
- DSP capabilities are never faked or fabricated.
