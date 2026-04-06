"""
Integration tests for HTTP API endpoints (core/views.py)

测试策略：
- 使用 Django TestClient 发真实 HTTP 请求
- 全栈测试：URL routing → view → service → DB → middleware → JSON response
- @patch mock 掉 Celery task，不需要 Redis 也能跑

覆盖范围：
  - POST /api/orders/ 的各种错误 + 成功路径
  - GET /api/care-plans/<id>/ 的 404 / 200
  - GET /api/careplans/ 的分页 + 错误参数
  - 方法限制（405）
"""
import json
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone

from core.models import CarePlan, Order, Patient, Provider

TASK_PATH = 'core.services.generate_care_plan'

VALID_PAYLOAD = {
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


def post_json(client, url, payload):
    """helper：发 POST JSON 请求"""
    return client.post(url, data=json.dumps(payload), content_type='application/json')


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/orders/
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderApi(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = '/api/orders/'

    # ── HTTP 方法限制 ─────────────────────────────────────────────────────────

    def test_get_returns_405(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_put_returns_405(self):
        response = self.client.put(self.url, content_type='application/json')
        self.assertEqual(response.status_code, 405)

    # ── JSON 解析错误 ─────────────────────────────────────────────────────────

    def test_invalid_json_body_returns_400(self):
        response = self.client.post(
            self.url, data='not valid json {{{', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    # ── 格式验证错误 → 400 + code: VALIDATION_ERROR ───────────────────────────

    def test_invalid_npi_returns_400_validation_error(self):
        payload = {**VALID_PAYLOAD, 'referring_provider_npi': '123'}
        response = post_json(self.client, self.url, payload)
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertEqual(body['code'], 'VALIDATION_ERROR')
        self.assertTrue(any('NPI' in d for d in body['details']))

    def test_invalid_mrn_returns_400_validation_error(self):
        payload = {**VALID_PAYLOAD, 'mrn': '12345'}  # 5 位
        response = post_json(self.client, self.url, payload)
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertEqual(body['code'], 'VALIDATION_ERROR')
        self.assertTrue(any('MRN' in d for d in body['details']))

    def test_invalid_diagnosis_returns_400_validation_error(self):
        payload = {**VALID_PAYLOAD, 'primary_diagnosis': 'not-valid'}
        response = post_json(self.client, self.url, payload)
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertEqual(body['code'], 'VALIDATION_ERROR')

    # ── 业务规则错误 → 409 ────────────────────────────────────────────────────

    def test_duplicate_provider_npi_different_name_returns_409(self):
        """同 NPI + 不同名 → 409 DUPLICATE_PROVIDER（不可跳过）"""
        Provider.objects.create(npi='1234567890', name='Dr. Jones')
        payload = {**VALID_PAYLOAD, 'referring_provider': 'Dr. Smith'}
        response = post_json(self.client, self.url, payload)
        self.assertEqual(response.status_code, 409)
        body = json.loads(response.content)
        self.assertEqual(body['code'], 'DUPLICATE_PROVIDER')

    @patch(TASK_PATH)
    def test_patient_data_mismatch_returns_409_with_warnings(self, mock_task):
        """同 MRN 但姓名不同 → 409 PATIENT_DATA_MISMATCH + warnings list"""
        Patient.objects.create(
            mrn='123456', first_name='Alice', last_name='Smith', dob='1990-01-01'
        )
        response = post_json(self.client, self.url, VALID_PAYLOAD)
        self.assertEqual(response.status_code, 409)
        body = json.loads(response.content)
        self.assertEqual(body['code'], 'PATIENT_DATA_MISMATCH')
        self.assertGreater(len(body['warnings']), 0)
        self.assertTrue(body['requires_confirmation'])

    @patch(TASK_PATH)
    def test_duplicate_order_same_day_returns_409_block_error(self, mock_task):
        """同患者 + 同药 + 今天 → 409 DUPLICATE_ORDER（不可跳过）"""
        # 第一次提交成功
        post_json(self.client, self.url, VALID_PAYLOAD)
        # 同天再次提交
        response = post_json(self.client, self.url, VALID_PAYLOAD)
        self.assertEqual(response.status_code, 409)
        body = json.loads(response.content)
        self.assertEqual(body['code'], 'DUPLICATE_ORDER')

    @patch(TASK_PATH)
    def test_duplicate_order_prior_day_returns_409_warning(self, mock_task):
        """历史重复（昨天），confirm=False → 409 DUPLICATE_ORDER_WARNING（可跳过）"""
        # 先提交一次，然后把 order 移到昨天
        post_json(self.client, self.url, VALID_PAYLOAD)
        Order.objects.all().update(created_at=timezone.now() - timedelta(days=1))

        response = post_json(self.client, self.url, VALID_PAYLOAD)
        self.assertEqual(response.status_code, 409)
        body = json.loads(response.content)
        self.assertEqual(body['code'], 'DUPLICATE_ORDER_WARNING')
        self.assertGreater(len(body['warnings']), 0)
        self.assertTrue(body['requires_confirmation'])

    # ── 成功路径 → 201 ────────────────────────────────────────────────────────

    @patch(TASK_PATH)
    def test_valid_order_returns_201_with_care_plan_id_and_pending_status(self, mock_task):
        response = post_json(self.client, self.url, VALID_PAYLOAD)
        self.assertEqual(response.status_code, 201)
        body = json.loads(response.content)
        self.assertIn('care_plan_id', body)
        self.assertEqual(body['status'], 'pending')
        self.assertEqual(CarePlan.objects.count(), 1)

    @patch(TASK_PATH)
    def test_confirm_true_bypasses_patient_mismatch_and_returns_201(self, mock_task):
        """confirm=True → 即使患者数据不符，也能成功提交"""
        Patient.objects.create(
            mrn='123456', first_name='Alice', last_name='Smith', dob='1990-01-01'
        )
        payload = {**VALID_PAYLOAD, 'confirm': True}
        response = post_json(self.client, self.url, payload)
        self.assertEqual(response.status_code, 201)

    @patch(TASK_PATH)
    def test_confirm_true_bypasses_duplicate_order_warning_and_returns_201(self, mock_task):
        """confirm=True → 有历史订单也能继续提交"""
        post_json(self.client, self.url, VALID_PAYLOAD)
        Order.objects.all().update(created_at=timezone.now() - timedelta(days=1))
        payload = {**VALID_PAYLOAD, 'confirm': True}
        response = post_json(self.client, self.url, payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 2)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/care-plans/<id>/
# ─────────────────────────────────────────────────────────────────────────────

class TestCarePlanDetailApi(TestCase):

    def setUp(self):
        self.client = Client()

    def _create_care_plan(self):
        provider = Provider.objects.create(npi='1234567890', name='Dr. Smith')
        patient = Patient.objects.create(
            mrn='123456', first_name='Jane', last_name='Doe', dob='1990-01-01'
        )
        order = Order.objects.create(
            patient=patient,
            provider=provider,
            referring_provider_name='Dr. Smith',
            medication='Metformin',
            diagnosis='M05.79',
        )
        return CarePlan.objects.create(order=order, status=CarePlan.Status.PENDING)

    def test_nonexistent_plan_returns_404(self):
        response = self.client.get('/api/care-plans/9999/')
        self.assertEqual(response.status_code, 404)
        body = json.loads(response.content)
        self.assertIn('error', body)

    def test_post_returns_405(self):
        response = self.client.post('/api/care-plans/1/')
        self.assertEqual(response.status_code, 405)

    def test_existing_plan_returns_200_with_correct_structure(self):
        care_plan = self._create_care_plan()
        response = self.client.get(f'/api/care-plans/{care_plan.id}/')
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body['id'], care_plan.id)
        self.assertIn('status', body)
        self.assertIn('patient', body)
        self.assertIn('order', body)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/careplans/  （分页列表）
# ─────────────────────────────────────────────────────────────────────────────

class TestCarePlanListApi(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = '/api/careplans/'

    def test_empty_list_returns_200_with_count_zero(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body['count'], 0)
        self.assertEqual(body['results'], [])

    def test_invalid_page_parameter_returns_400(self):
        response = self.client.get(f'{self.url}?page=abc')
        self.assertEqual(response.status_code, 400)

    def test_invalid_page_size_parameter_returns_400(self):
        response = self.client.get(f'{self.url}?page_size=abc')
        self.assertEqual(response.status_code, 400)

    def test_post_returns_405(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405)

    def test_out_of_range_page_returns_empty_results(self):
        """超出范围的 page → 返回空结果，不报错"""
        response = self.client.get(f'{self.url}?page=9999')
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body['results'], [])
        self.assertIsNone(body['next'])


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/careplans/statuses/  （批量状态查询）
# ─────────────────────────────────────────────────────────────────────────────

class TestBatchStatusApi(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = '/api/careplans/statuses/'

    def test_get_returns_405(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.url, data='not json', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_ids_not_list_returns_400(self):
        response = post_json(self.client, self.url, {'ids': 'not-a-list'})
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_ids_return_failed_status(self):
        response = post_json(self.client, self.url, {'ids': [9999, 8888]})
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        # 找不到的 id 返回 failed + error
        self.assertEqual(len(body['results']), 2)
        for item in body['results']:
            self.assertEqual(item['status'], 'failed')
