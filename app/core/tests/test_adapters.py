from datetime import date

from django.test import SimpleTestCase

from core.adapters import get_adapter, register_adapter
from core.adapters.base import BaseIntakeAdapter
from core.adapters.clinic_b import ClinicBAdapter
from core.adapters.hospital_northhill import NorthHillHospitalAdapter
from core.adapters.manual_form import ManualFormAdapter
from core.exceptions import ValidationError
from core.internal_types import InternalOrder, PatientInfo, ProviderInfo


class TestAdapterFactory(SimpleTestCase):
    def test_get_adapter_returns_manual_form_adapter_instance(self):
        adapter = get_adapter("manual_form")
        self.assertIsInstance(adapter, ManualFormAdapter)

    def test_get_adapter_returns_registered_adapter_instance(self):
        adapter = get_adapter("clinic_b")
        self.assertIsInstance(adapter, ClinicBAdapter)

    def test_unknown_source_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            get_adapter("unknown_source")

        self.assertIn("Unsupported source", ctx.exception.message)
        self.assertIn("clinic_b", ctx.exception.message)
        self.assertIn("manual_form", ctx.exception.message)
        self.assertIn("northhill_hospital", ctx.exception.message)

    def test_get_adapter_returns_northhill_adapter_instance(self):
        adapter = get_adapter("northhill_hospital")
        self.assertIsInstance(adapter, NorthHillHospitalAdapter)

    def test_register_adapter_allows_new_source_without_business_code_changes(self):
        class MockSourceAdapter(BaseIntakeAdapter):
            SOURCE = "mock_source"

            def parse(self, raw):
                return {"raw": raw}

            def transform(self, parsed):
                return InternalOrder(
                    patient=PatientInfo(
                        mrn="123456",
                        first_name="Jane",
                        last_name="Doe",
                        dob=date(1990, 1, 1),
                    ),
                    provider=ProviderInfo(
                        npi="1234567890",
                        name="Dr. Smith",
                    ),
                    medication="Test Med",
                    diagnosis="I10",
                    source=self.SOURCE,
                )

            def validate(self, order):
                return None

        register_adapter(MockSourceAdapter)

        adapter = get_adapter("mock_source")
        self.assertIsInstance(adapter, MockSourceAdapter)


class TestNorthHillHospitalAdapter(SimpleTestCase):
    def test_process_maps_flat_payload_into_internal_order(self):
        adapter = NorthHillHospitalAdapter()
        raw_data = {
            "member_id": "654321",
            "given_name": "John",
            "family_name": "Carter",
            "birth_date": "1985-07-14",
            "ordering_physician": "Dr. Adams",
            "ordering_physician_npi": "9876543210",
            "primary_dx_code": "E11.9",
            "drug": "Ozempic",
            "chart_summary": "Type 2 diabetes. A1c elevated.",
        }

        order = adapter.process(raw_data)

        self.assertEqual(order.source, "northhill_hospital")
        self.assertEqual(order.patient.mrn, "654321")
        self.assertEqual(order.patient.first_name, "John")
        self.assertEqual(order.patient.last_name, "Carter")
        self.assertEqual(order.patient.dob, date(1985, 7, 14))
        self.assertEqual(order.provider.name, "Dr. Adams")
        self.assertEqual(order.provider.npi, "9876543210")
        self.assertEqual(order.diagnosis, "E11.9")
        self.assertEqual(order.medication, "Ozempic")

    def test_process_rejects_invalid_birth_date_format(self):
        adapter = NorthHillHospitalAdapter()
        raw_data = {
            "member_id": "654321",
            "given_name": "John",
            "family_name": "Carter",
            "birth_date": "07/14/1985",
            "ordering_physician": "Dr. Adams",
            "ordering_physician_npi": "9876543210",
            "primary_dx_code": "E11.9",
            "drug": "Ozempic",
        }

        with self.assertRaises(ValidationError) as ctx:
            adapter.process(raw_data)

        self.assertIn("Expected YYYY-MM-DD", ctx.exception.message)

    def test_process_uses_base_validate_for_common_rules(self):
        adapter = NorthHillHospitalAdapter()
        raw_data = {
            "member_id": "654321",
            "given_name": "John",
            "family_name": "Carter",
            "birth_date": "1985-07-14",
            "ordering_physician": "Dr. Adams",
            "ordering_physician_npi": "987",
            "primary_dx_code": "E11.9",
            "drug": "Ozempic",
        }

        with self.assertRaises(ValidationError) as ctx:
            adapter.process(raw_data)

        self.assertIn("NPI must be exactly 10 digits", ctx.exception.message)
