import json
import logging
from datetime import datetime
from typing import Any

from core.exceptions import ValidationError
from core.internal_types import InternalOrder, PatientInfo, ProviderInfo

from .base import BaseIntakeAdapter

logger = logging.getLogger(__name__)


class ClinicBAdapter(BaseIntakeAdapter):
    """
    Adapter for Clinic B (small downtown clinic).
    Characteristics:
    - Abbreviated field names: pt, fname, lname, npi_num, dx, rx
    - Nested structure: patient info under "pt", provider under "provider", etc.
    - Date format: MM/DD/YYYY (American style)
    - Rich clinical data (allergies, med_hx, clinical_notes) → collapsed into medical_notes
    """

    SOURCE = "clinic_b"

    def __init__(self):
        self._raw: Any = None  # preserved as-is for debugging / audit trail

    def parse(self, raw: Any) -> dict:
        # Always store the original input before touching it
        self._raw = raw

        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                logger.error("[ClinicB] JSON parse failed. raw=%r error=%s", raw, e)
                raise ValidationError(f"[ClinicB] Invalid JSON: {e}")

        if isinstance(raw, dict):
            return raw

        raise ValidationError(f"[ClinicB] Unsupported input type: {type(raw).__name__}")

    def transform(self, parsed: dict) -> InternalOrder:
        # Pull required top-level sections
        try:
            pt = parsed["pt"]
            provider = parsed["provider"]
            dx = parsed["dx"]
            rx = parsed["rx"]
        except KeyError as e:
            raise ValidationError(f"[ClinicB] Missing required section: {e}")

        # dob: Clinic B uses "MM/DD/YYYY", InternalOrder needs a date object
        try:
            dob = datetime.strptime(pt["dob"], "%m/%d/%Y").date()
        except KeyError:
            raise ValidationError("[ClinicB] Missing field: pt.dob")
        except ValueError:
            raise ValidationError(
                f"[ClinicB] Unexpected dob format: '{pt['dob']}'. Expected MM/DD/YYYY."
            )

        return InternalOrder(
            patient=PatientInfo(
                mrn=pt.get("mrn", ""),
                first_name=pt.get("fname", ""),
                last_name=pt.get("lname", ""),
                dob=dob,
            ),
            provider=ProviderInfo(
                npi=provider.get("npi_num", ""),
                name=provider.get("name", ""),
            ),
            medication=rx.get("med_name", ""),
            diagnosis=dx.get("primary", ""),
            medical_notes=self._build_notes(parsed),
            source=self.SOURCE,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    def _build_notes(self, parsed: dict) -> str:
        """
        Clinic B sends rich clinical context that doesn't map to a single field.
        Collapse allergies + medication history + clinical notes into one string
        so none of it gets lost when the order flows through the system.
        """
        parts = []

        if allergies := parsed.get("allergies"):
            parts.append("Allergies: " + ", ".join(allergies))

        if med_hx := parsed.get("med_hx"):
            lines = "\n".join(f"  - {m}" for m in med_hx)
            parts.append(f"Medication History:\n{lines}")

        if notes := parsed.get("clinical_notes"):
            parts.append(f"Clinical Notes: {notes}")

        return "\n\n".join(parts)
