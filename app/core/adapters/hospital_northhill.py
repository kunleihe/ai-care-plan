from datetime import datetime
from typing import Any

from core.exceptions import ValidationError
from core.internal_types import InternalOrder, PatientInfo, ProviderInfo

from .base import BaseIntakeAdapter


class NorthHillHospitalAdapter(BaseIntakeAdapter):
    """
    Adapter for NorthHill Hospital.
    Characteristics:
    - Flat dict payload instead of Clinic B's nested structure
    - Different field naming: member_id, given_name, family_name, drug, etc.
    - Date format: YYYY-MM-DD
    - Clinical summary already comes as a single free-text field
    """

    SOURCE = "northhill_hospital"

    def parse(self, raw: Any) -> dict:
        if not isinstance(raw, dict):
            raise ValidationError(
                f"[NorthHill] Unsupported input type: {type(raw).__name__}"
            )
        return raw

    def transform(self, parsed: dict) -> InternalOrder:
        try:
            dob = datetime.strptime(parsed["birth_date"], "%Y-%m-%d").date()
        except KeyError:
            raise ValidationError("[NorthHill] Missing field: birth_date")
        except ValueError:
            raise ValidationError(
                f"[NorthHill] Unexpected dob format: '{parsed['birth_date']}'. "
                "Expected YYYY-MM-DD."
            )

        return InternalOrder(
            patient=PatientInfo(
                mrn=parsed.get("member_id", ""),
                first_name=parsed.get("given_name", ""),
                last_name=parsed.get("family_name", ""),
                dob=dob,
            ),
            provider=ProviderInfo(
                npi=parsed.get("ordering_physician_npi", ""),
                name=parsed.get("ordering_physician", ""),
            ),
            medication=parsed.get("drug", ""),
            diagnosis=parsed.get("primary_dx_code", ""),
            medical_notes=parsed.get("chart_summary", ""),
            source=self.SOURCE,
        )
