"""
Unit tests for core/services.py

测试策略：
- 继承 django.test.TestCase（每个 test 用事务回滚，互相隔离）
- @patch(TASK_PATH) mock 掉 Celery task，避免需要 Redis
- 覆盖所有验证分支 + 重复检测规则，目标 90%+ 覆盖率

覆盖范围：
  - 格式验证：NPI / MRN / ICD-10
  - Provider 重复检测
  - Patient 重复检测（MRN 冲突 / 姓名+DOB 冲突）
  - Order 重复检测（同天=ERROR / 不同天=WARNING）
  - Happy path
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from core.exceptions import (
    DuplicateOrderError,
    DuplicateOrderWarning,
    DuplicateProviderError,
    PatientDataMismatchWarning,
    ValidationError,
)
from core.models import CarePlan, Order, Patient, Provider
from core import services

# Celery task 在 services.py 里被引用的路径，patch 这里才生效
TASK_PATH = 'core.services.generate_care_plan'

# 所有字段都合法的基础数据，各测试 case 按需覆盖
VALID_DATA = {
    'referring_provider_npi': '1234567890',
    'referring_provider': 'Dr. Smith',
    'mrn': '123456',
    'primary_diagnosis': 'M05.79',
    'first_name': 'Jane',
    'last_name': 'Doe',
    'dob': '1990-01-01',
    'medication_name': 'Metformin',
    'additional_notes': '',
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. 输入格式验证
# ─────────────────────────────────────────────────────────────────────────────

class TestInputValidation(TestCase):
    """NPI / MRN / ICD-10 格式验证 — 后端的最终防线"""

    # ── NPI ──────────────────────────────────────────────────────────────────

    def test_npi_too_short_raises_validation_error(self):
        data = {**VALID_DATA, 'referring_provider_npi': '123456789'}  # 9 位
        with self.assertRaises(ValidationError) as ctx:
            services.create_order(data)
        self.assertIn('NPI', ctx.exception.message)

    def test_npi_too_long_raises_validation_error(self):
        data = {**VALID_DATA, 'referring_provider_npi': '12345678901'}  # 11 位
        with self.assertRaises(ValidationError):
            services.create_order(data)

    def test_npi_contains_letters_raises_validation_error(self):
        data = {**VALID_DATA, 'referring_provider_npi': '123456789A'}
        with self.assertRaises(ValidationError):
            services.create_order(data)

    def test_npi_empty_raises_validation_error(self):
        data = {**VALID_DATA, 'referring_provider_npi': ''}
        with self.assertRaises(ValidationError):
            services.create_order(data)

    # ── MRN ──────────────────────────────────────────────────────────────────

    def test_mrn_too_short_raises_validation_error(self):
        data = {**VALID_DATA, 'mrn': '12345'}  # 5 位
        with self.assertRaises(ValidationError) as ctx:
            services.create_order(data)
        self.assertIn('MRN', ctx.exception.message)

    def test_mrn_too_long_raises_validation_error(self):
        data = {**VALID_DATA, 'mrn': '1234567'}  # 7 位
        with self.assertRaises(ValidationError):
            services.create_order(data)

    def test_mrn_contains_letters_raises_validation_error(self):
        data = {**VALID_DATA, 'mrn': 'ABC123'}
        with self.assertRaises(ValidationError):
            services.create_order(data)

    def test_mrn_empty_raises_validation_error(self):
        data = {**VALID_DATA, 'mrn': ''}
        with self.assertRaises(ValidationError):
            services.create_order(data)

    # ── ICD-10 ────────────────────────────────────────────────────────────────

    def test_icd10_plain_text_raises_validation_error(self):
        data = {**VALID_DATA, 'primary_diagnosis': 'hypertension'}
        with self.assertRaises(ValidationError) as ctx:
            services.create_order(data)
        self.assertIn('ICD-10', ctx.exception.message)

    def test_icd10_all_digits_raises_validation_error(self):
        data = {**VALID_DATA, 'primary_diagnosis': '1234'}
        with self.assertRaises(ValidationError):
            services.create_order(data)

    def test_icd10_empty_raises_validation_error(self):
        data = {**VALID_DATA, 'primary_diagnosis': ''}
        with self.assertRaises(ValidationError):
            services.create_order(data)

    @patch(TASK_PATH)
    def test_icd10_simple_format_i10_passes(self, mock_task):
        """I10（字母+2位数字）是合法的 ICD-10"""
        data = {**VALID_DATA, 'primary_diagnosis': 'I10'}
        care_plan = services.create_order(data)
        self.assertIsNotNone(care_plan)

    @patch(TASK_PATH)
    def test_icd10_with_decimal_passes(self, mock_task):
        """Z87.891（含小数）也是合法的 ICD-10"""
        data = {**VALID_DATA, 'primary_diagnosis': 'Z87.891'}
        care_plan = services.create_order(data)
        self.assertIsNotNone(care_plan)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Provider 重复检测
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderDuplicateDetection(TestCase):
    """NPI 是全国唯一标识符，同 NPI 不同名字必须阻止"""

    @patch(TASK_PATH)
    def test_new_provider_is_created(self, mock_task):
        services.create_order(VALID_DATA)
        self.assertEqual(Provider.objects.count(), 1)
        self.assertEqual(Provider.objects.first().npi, '1234567890')

    @patch(TASK_PATH)
    def test_same_npi_same_name_reuses_existing_provider(self, mock_task):
        """同 NPI + 同名 → 复用，不多建"""
        existing = Provider.objects.create(npi='1234567890', name='Dr. Smith')
        services.create_order(VALID_DATA)
        self.assertEqual(Provider.objects.count(), 1)
        self.assertEqual(Provider.objects.first().pk, existing.pk)

    def test_same_npi_different_name_raises_duplicate_provider_error(self):
        """同 NPI + 不同名字 → DuplicateProviderError（不可跳过）
        面试点：为什么这里用 ERROR 而不是 WARNING？
        因为 NPI 是政府颁发的唯一号码，名字不符说明数据录入有问题。
        """
        Provider.objects.create(npi='1234567890', name='Dr. Jones')
        data = {**VALID_DATA, 'referring_provider': 'Dr. Smith'}
        with self.assertRaises(DuplicateProviderError) as ctx:
            services.create_order(data)
        self.assertIn('1234567890', ctx.exception.message)
        self.assertIn('Dr. Jones', ctx.exception.message)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Patient 重复检测（这是本次测试的核心）
# ─────────────────────────────────────────────────────────────────────────────

class TestPatientDuplicateDetection(TestCase):
    """
    两条检测路径：
    A. 同 MRN 但姓名/DOB 不符 → PatientDataMismatchWarning
    B. MRN 不存在，但姓名+DOB 已有另一条记录 → PatientDataMismatchWarning
    """

    def _make_patient(self, mrn='123456', first='Jane', last='Doe', dob='1990-01-01'):
        return Patient.objects.create(mrn=mrn, first_name=first, last_name=last, dob=dob)

    # ── A: 同 MRN，数据不符 ──────────────────────────────────────────────────

    def test_mrn_exists_name_mismatch_no_confirm_raises_warning(self):
        """同 MRN 但姓名不同，confirm=False → 必须抛出 PatientDataMismatchWarning"""
        self._make_patient(first='Alice', last='Smith')  # DB: Alice Smith
        with self.assertRaises(PatientDataMismatchWarning) as ctx:
            services.create_order(VALID_DATA, confirm=False)  # 提交 Jane Doe
        self.assertGreater(len(ctx.exception.warnings), 0)
        self.assertIn('123456', ctx.exception.warnings[0])

    def test_mrn_exists_dob_mismatch_no_confirm_raises_warning(self):
        """同 MRN 但 DOB 不同，confirm=False → PatientDataMismatchWarning"""
        self._make_patient(dob='1980-05-15')  # DB: 不同 DOB
        data = {**VALID_DATA, 'dob': '1990-01-01'}
        with self.assertRaises(PatientDataMismatchWarning):
            services.create_order(data, confirm=False)

    @patch(TASK_PATH)
    def test_mrn_exists_mismatch_with_confirm_uses_existing_patient(self, mock_task):
        """confirm=True → 强制使用 DB 里的现有 patient，不新建"""
        self._make_patient(first='Alice', last='Smith')
        care_plan = services.create_order(VALID_DATA, confirm=True)
        self.assertIsInstance(care_plan, CarePlan)
        # patient 数量没有增加
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Patient.objects.first().first_name, 'Alice')

    @patch(TASK_PATH)
    def test_mrn_exists_data_matches_no_warning(self, mock_task):
        """同 MRN + 完全相同的数据 → 直接复用，无任何异常"""
        self._make_patient()
        care_plan = services.create_order(VALID_DATA)
        self.assertIsInstance(care_plan, CarePlan)
        self.assertEqual(Patient.objects.count(), 1)

    # ── B: 姓名+DOB 已存在，MRN 不同 ─────────────────────────────────────────

    def test_name_dob_match_different_mrn_no_confirm_raises_warning(self):
        """姓名+DOB 已存在但 MRN 不同，confirm=False → PatientDataMismatchWarning"""
        self._make_patient(mrn='999999')  # DB: Jane Doe 对应 MRN 999999
        data = {**VALID_DATA, 'mrn': '123456'}  # 提交 Jane Doe + 新 MRN
        with self.assertRaises(PatientDataMismatchWarning) as ctx:
            services.create_order(data, confirm=False)
        self.assertGreater(len(ctx.exception.warnings), 0)

    @patch(TASK_PATH)
    def test_name_dob_match_different_mrn_with_confirm_creates_new_patient(self, mock_task):
        """confirm=True → 认可差异，创建新 patient 记录"""
        self._make_patient(mrn='999999')
        data = {**VALID_DATA, 'mrn': '123456'}
        care_plan = services.create_order(data, confirm=True)
        self.assertIsInstance(care_plan, CarePlan)
        self.assertEqual(Patient.objects.count(), 2)

    # ── 全新 patient ──────────────────────────────────────────────────────────

    @patch(TASK_PATH)
    def test_completely_new_patient_is_created_with_correct_fields(self, mock_task):
        services.create_order(VALID_DATA)
        self.assertEqual(Patient.objects.count(), 1)
        p = Patient.objects.first()
        self.assertEqual(p.mrn, '123456')
        self.assertEqual(p.first_name, 'Jane')
        self.assertEqual(p.last_name, 'Doe')
        self.assertEqual(str(p.dob), '1990-01-01')


# ─────────────────────────────────────────────────────────────────────────────
# 4. Order 重复检测（同天=ERROR 不可跳过，不同天=WARNING 可确认）
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderDuplicateDetection(TestCase):

    def _setup_existing_order(self, medication='Metformin', days_ago=0):
        """建一条现有 order；days_ago > 0 时把 created_at 移到过去"""
        provider = Provider.objects.create(npi='1234567890', name='Dr. Smith')
        patient = Patient.objects.create(
            mrn='123456', first_name='Jane', last_name='Doe', dob='1990-01-01'
        )
        order = Order.objects.create(
            patient=patient,
            provider=provider,
            referring_provider_name='Dr. Smith',
            medication=medication,
            diagnosis='M05.79',
        )
        if days_ago > 0:
            # auto_now_add 字段只能用 queryset.update() 绕过
            Order.objects.filter(pk=order.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )
        CarePlan.objects.create(order=order, status=CarePlan.Status.COMPLETED)
        return order

    @patch(TASK_PATH)
    def test_same_day_same_medication_raises_duplicate_order_error(self, mock_task):
        """同患者 + 同药 + 今天 → DuplicateOrderError（无论 confirm）"""
        self._setup_existing_order()
        with self.assertRaises(DuplicateOrderError) as ctx:
            services.create_order(VALID_DATA)
        self.assertIn('Metformin', ctx.exception.message)

    @patch(TASK_PATH)
    def test_prior_order_different_day_no_confirm_raises_warning(self, mock_task):
        """有历史订单（昨天），confirm=False → DuplicateOrderWarning（可跳过）"""
        self._setup_existing_order(days_ago=1)
        with self.assertRaises(DuplicateOrderWarning) as ctx:
            services.create_order(VALID_DATA, confirm=False)
        self.assertGreater(len(ctx.exception.warnings), 0)

    @patch(TASK_PATH)
    def test_prior_order_different_day_with_confirm_creates_new_order(self, mock_task):
        """confirm=True → 允许重复用药，创建新 order"""
        self._setup_existing_order(days_ago=1)
        care_plan = services.create_order(VALID_DATA, confirm=True)
        self.assertIsInstance(care_plan, CarePlan)
        self.assertEqual(Order.objects.count(), 2)

    @patch(TASK_PATH)
    def test_different_medication_no_duplicate_error(self, mock_task):
        """同患者，不同药 → 无重复错误"""
        self._setup_existing_order(medication='Lisinopril')
        data = {**VALID_DATA, 'medication_name': 'Metformin'}
        care_plan = services.create_order(data)
        self.assertIsInstance(care_plan, CarePlan)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Happy path（完整流程）
# ─────────────────────────────────────────────────────────────────────────────

class TestHappyPath(TestCase):

    @patch(TASK_PATH)
    def test_creates_all_objects_and_dispatches_celery_task(self, mock_task):
        """完整 happy path：4 个对象都被创建，Celery task 被 dispatch"""
        care_plan = services.create_order(VALID_DATA)

        # 所有对象都创建了
        self.assertEqual(Provider.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CarePlan.objects.count(), 1)

        # care plan 初始状态是 PENDING
        self.assertEqual(care_plan.status, CarePlan.Status.PENDING)

        # Celery task 被异步 dispatch 了（而不是同步执行）
        mock_task.delay.assert_called_once_with(care_plan.id)

    @patch(TASK_PATH)
    def test_create_order_uses_adapter_pipeline_for_northhill_source(self, mock_task):
        payload = {
            'source': 'northhill_hospital',
            'member_id': '654321',
            'given_name': 'John',
            'family_name': 'Carter',
            'birth_date': '1985-07-14',
            'ordering_physician': 'Dr. Adams',
            'ordering_physician_npi': '9876543210',
            'primary_dx_code': 'E11.9',
            'drug': 'Ozempic',
            'chart_summary': 'Type 2 diabetes. A1c elevated.',
        }

        care_plan = services.create_order(payload, source='northhill_hospital')

        self.assertEqual(care_plan.status, CarePlan.Status.PENDING)
        self.assertEqual(Provider.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        self.assertEqual(order.referring_provider_name, 'Dr. Adams')
        self.assertEqual(order.medication, 'Ozempic')
        self.assertEqual(order.diagnosis, 'E11.9')
        self.assertEqual(order.medical_notes, 'Type 2 diabetes. A1c elevated.')

        patient = Patient.objects.first()
        self.assertEqual(patient.mrn, '654321')
        self.assertEqual(patient.first_name, 'John')
        self.assertEqual(patient.last_name, 'Carter')

        mock_task.delay.assert_called_once_with(care_plan.id)
