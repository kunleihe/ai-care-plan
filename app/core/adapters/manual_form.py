from datetime import datetime
from typing import Any

from core.exceptions import ValidationError
from core.internal_types import InternalOrder, PatientInfo, ProviderInfo

from .base import BaseIntakeAdapter


class ManualFormAdapter(BaseIntakeAdapter):
    """
    Adapter for the existing web form payload.
    Characteristics:
    - Flat dict payload with frontend field names
    - dob comes in as YYYY-MM-DD string
    - notes live in additional_notes
    """

    SOURCE = "manual_form"

    def parse(self, raw: Any) -> dict:
        if not isinstance(raw, dict):
            raise ValidationError(
                f"[manual_form] Unsupported input type: {type(raw).__name__}"
            )
        return raw

    def transform(self, parsed: dict) -> InternalOrder:
        try:
            dob = datetime.strptime(parsed["dob"], "%Y-%m-%d").date()
        except KeyError:
            raise ValidationError("[manual_form] Missing field: dob")
        except ValueError:
            raise ValidationError(
                f"[manual_form] Unexpected dob format: '{parsed['dob']}'. Expected YYYY-MM-DD."
            )

        return InternalOrder(
            patient=PatientInfo(
                mrn=parsed.get("mrn", ""),
                first_name=parsed.get("first_name", ""),
                last_name=parsed.get("last_name", ""),
                dob=dob,
            ),
            provider=ProviderInfo(
                npi=parsed.get("referring_provider_npi", ""),
                name=parsed.get("referring_provider", ""),
            ),
            medication=parsed.get("medication_name", ""),
            diagnosis=parsed.get("primary_diagnosis", ""),
            medical_notes=parsed.get("additional_notes", ""),
            source=self.SOURCE,
        )
