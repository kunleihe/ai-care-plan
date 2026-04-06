from dataclasses import dataclass
from datetime import date


@dataclass
class PatientInfo:
    mrn: str          # 6-digit string, e.g. "123456"
    first_name: str
    last_name: str
    dob: date         # parsed date — adapters are responsible for string → date


@dataclass
class ProviderInfo:
    npi: str          # 10-digit string, e.g. "1234567890"
    name: str


@dataclass
class InternalOrder:
    patient: PatientInfo
    provider: ProviderInfo
    medication: str   # medication name
    diagnosis: str    # ICD-10 code, e.g. "G70.00"
    medical_notes: str = ""
    source: str = ""  # which adapter produced this: "clinic_b", "manual_form", etc.
