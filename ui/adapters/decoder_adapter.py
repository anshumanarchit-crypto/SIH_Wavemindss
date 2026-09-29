"""
UI Decoder Adapter.
Converts  DecoderOutputContract or legacy decoder evidence into normalized UI view models.
Strictly read-only; performs zero FEC decoding, deinterleaving, or BER calculations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from spectralq.contracts.schemas import DecoderOutputContract, validate_decoder_output_dict


class DecoderValidationError(Exception):
    """Raised when backend decoder data fails schema validation."""
    pass


@dataclass
class NormalizedDecoder:
    schema_version: str
    capture_id: str
    status: str  # "OK", "FAILED", "UNSUPPORTED"
    interleaver_used: str
    fec_used: str
    decoded_bits_count: int
    decoded_bits_preview: Optional[str]
    crc_status: str  # "PASS", "FAIL", "NOT_RUN"
    reencode_ber: Optional[float]
    failure_reason: Optional[str]
    source_exact_match: Optional[bool] = None
    reference_available: Optional[bool] = None
    reference_length: Optional[int] = None
    bit_errors: Optional[int] = None
    comparison_status: Optional[str] = None
    full_decoded_bits: Optional[str] = None
    raw_dict: Dict[str, Any] = field(default_factory=dict)

    @property
    def ber_display(self) -> str:
        """Honest display string for BER; never fabricates 0.0 when null."""
        if self.reencode_ber is None:
            return "N/A (Not Available)"
        if self.reencode_ber == 0.0:
            return "0.000000 (0 errors)"
        return f"{self.reencode_ber:.6f}"

    @property
    def ber(self) -> Optional[float]:
        return self.reencode_ber

    @property
    def evm_percent(self) -> Optional[float]:
        return self.raw_dict.get("evm_percent")

    @property
    def viterbi_used(self) -> bool:
        fec = (self.fec_used or "").lower()
        return "viterbi" in fec or "conv" in fec

    @property
    def reed_solomon_used(self) -> bool:
        fec = (self.fec_used or "").lower()
        return "rs" in fec or "reed" in fec

    @property
    def interleaver_type(self) -> str:
        return self.interleaver_used or "none"

    @property
    def crc_passed(self) -> bool:
        return (self.crc_status or "").upper() == "PASS"

    @property
    def crc_checked(self) -> bool:
        return (self.crc_status or "").upper() in ("PASS", "FAIL")

    @property
    def raw_bits(self) -> Optional[str]:
        return self.full_decoded_bits or self.raw_dict.get("raw_bits") or self.decoded_bits_preview

    @property
    def sync_word(self) -> Optional[str]:
        return self.raw_dict.get("sync_word")



def adapt_decoder(raw_data: Any) -> NormalizedDecoder:
    """
    Validates and adapts  decoder output into NormalizedDecoder.
    Also handles compatible decoder evidence formats safely without inventing values.
    """
    if isinstance(raw_data, DecoderOutputContract):
        contract = raw_data
        raw_dict = contract.model_dump()
    elif isinstance(raw_data, dict):
        if "decoder" in raw_data and isinstance(raw_data["decoder"], dict):
            dec_sub = raw_data["decoder"]
            dec_stat = dec_sub.get("status", "UNSUPPORTED")
            stat_norm = "OK" if str(dec_stat).upper() in ("SUCCESS", "OK") else str(dec_stat).upper()
            re_errs = dec_sub.get("re_encode_errors")
            bit_ct = int(dec_sub.get("bit_count", 0))
            ber_val = 0.0 if re_errs == 0 else (float(re_errs) / max(1, bit_ct) if re_errs is not None else None)
            crc_stat = "PASS" if dec_sub.get("success") else ("FAIL" if (re_errs and re_errs > 0) else "NOT_RUN")
            return NormalizedDecoder(
                schema_version=str(raw_data.get("schema_version", "spectralq-decoder-evidence-v1")),
                capture_id=str(raw_data.get("case_id", "UNKNOWN")),
                status=stat_norm,
                interleaver_used=str(dec_sub.get("interleaver", "NONE")),
                fec_used=str(dec_sub.get("fec", "NONE")),
                decoded_bits_count=bit_ct,
                decoded_bits_preview=None,
                crc_status=crc_stat,
                reencode_ber=ber_val,
                failure_reason=None if dec_sub.get("success") else (f"Re-encode errors: {re_errs}" if re_errs else None),
                source_exact_match=True if (re_errs == 0 and dec_sub.get("success")) else None,
                raw_dict=raw_data,
            )
        # First check if it matches official DecoderOutputContract
        elif "fec_used" in raw_data and "interleaver_used" in raw_data and "status" in raw_data:
            try:
                contract = validate_decoder_output_dict(raw_data)
                raw_dict = raw_data
            except Exception as e:
                raise DecoderValidationError(f"Invalid DecoderOutputContract: {e}") from e
        elif "decoder_status" in raw_data or "ber" in raw_data or ("fec" in raw_data and "interleaver" in raw_data):
            # Tolerant adapter for legacy decoder_evidence.json handoff
            raw_dict = raw_data
            status_val = raw_data.get("decoder_status", raw_data.get("status", "UNSUPPORTED"))
            status = "OK" if str(status_val).upper() in ("SUCCESS", "OK") else str(status_val).upper()
            fec = str(raw_data.get("fec", raw_data.get("fec_used", "UNKNOWN")))
            interleaver = str(raw_data.get("interleaver", raw_data.get("interleaver_used", "UNKNOWN")))
            reencode_ber = raw_data.get("reencode_ber", raw_data.get("ber"))
            if reencode_ber is None and raw_data.get("re_encode_errors") == 0:
                reencode_ber = 0.0
            crc = str(raw_data.get("crc_status", "PASS" if raw_data.get("success") else "NOT_RUN")).upper()
            bits = raw_data.get("decoded_bits", raw_data.get("output_bits", raw_data.get("bit_count", 0)))
            full_bits_str = None
            if isinstance(bits, list):
                bit_count = len(bits)
                full_bits_str = "".join(str(b) for b in bits)
                bit_str = full_bits_str[:64]
            elif isinstance(bits, str):
                bit_count = len(bits)
                full_bits_str = bits
                bit_str = bits[:64]
            else:
                bit_count = int(bits)
                bit_str = None
            return NormalizedDecoder(
                schema_version=str(raw_data.get("schema_version", "1.0.0")),
                capture_id=str(raw_data.get("capture_id", "UNKNOWN")),
                status=status,
                interleaver_used=interleaver,
                fec_used=fec,
                decoded_bits_count=bit_count,
                decoded_bits_preview=bit_str,
                crc_status=crc,
                reencode_ber=float(reencode_ber) if reencode_ber is not None else None,
                failure_reason=raw_data.get("failure_reason") or raw_data.get("warnings"),
                source_exact_match=raw_data.get("source_exact_match", True if reencode_ber == 0.0 else None),
                full_decoded_bits=full_bits_str,
                raw_dict=raw_dict,
            )
        else:
            raise DecoderValidationError("Dictionary does not match known decoder contract schema.")
    else:
        raise DecoderValidationError(f"Expected dict or DecoderOutputContract, got {type(raw_data)}")

    # Extract bit count and preview
    decoded_bits = contract.decoded_bits
    full_bits_str = None
    if isinstance(decoded_bits, str):
        full_bits_str = decoded_bits
        bit_count = len(decoded_bits)
        bit_preview = decoded_bits[:64] + ("..." if len(decoded_bits) > 64 else "")
    elif isinstance(decoded_bits, list):
        full_bits_str = "".join(str(b) for b in decoded_bits)
        bit_count = len(decoded_bits)
        bit_preview = full_bits_str[:64] + ("..." if len(decoded_bits) > 64 else "")
    elif isinstance(decoded_bits, int):
        bit_count = decoded_bits
        bit_preview = f"{decoded_bits} bits decoded"
    else:
        bit_count = 0
        bit_preview = None

    return NormalizedDecoder(
        schema_version=contract.schema_version,
        capture_id=contract.capture_id,
        status=contract.status.value.upper(),
        interleaver_used=contract.interleaver_used,
        fec_used=contract.fec_used,
        decoded_bits_count=bit_count,
        decoded_bits_preview=bit_preview,
        crc_status=contract.crc_status.value.upper(),
        reencode_ber=contract.reencode_ber,
        failure_reason=contract.failure_reason,
        source_exact_match=True if (contract.status.value == "ok" and contract.reencode_ber == 0.0) else (False if (contract.reencode_ber is not None and contract.reencode_ber > 0) else None),
        reference_available=raw_dict.get("reference_available", True if raw_dict.get("source_bit_errors") is not None or raw_dict.get("reference_length") is not None else None),
        reference_length=raw_dict.get("reference_length"),
        bit_errors=raw_dict.get("bit_errors", raw_dict.get("source_bit_errors")),
        comparison_status=raw_dict.get("comparison_status", "EXACT MATCH" if contract.reencode_ber == 0.0 else ("BIT ERRORS DETECTED" if (contract.reencode_ber is not None and contract.reencode_ber > 0) else None)),
        full_decoded_bits=full_bits_str,
        raw_dict=raw_dict,
    )
