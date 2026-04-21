import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.join(_HERE, '../app')
if os.path.isdir(_APP_DIR):
    sys.path.insert(0, _APP_DIR)
sys.path.insert(0, _HERE)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lambda_settings')
import django
django.setup()

from core.llm import get_llm_service
from core.models import CarePlan


def _build_prompt(care_plan: CarePlan) -> str:
    order = care_plan.order
    patient = order.patient
    return f"""You are a clinical pharmacist. Generate a comprehensive care plan for the following patient.

Patient: {patient.first_name} {patient.last_name}, DOB: {patient.dob}
Medication: {order.medication}
Diagnosis (ICD-10): {order.diagnosis}
Medical Notes: {order.medical_notes or 'None'}
Referring Provider: {order.referring_provider_name}

Please structure your response with the following sections:
1. Problem List
2. Goals
3. Pharmacist Interventions
4. Monitoring Plan

Be specific and clinically appropriate."""


def _fake_llm_response(care_plan: CarePlan) -> str:
    order = care_plan.order
    patient = order.patient
    return f"""**[FAKE LLM - 仅用于测试]**

## 1. Problem List
- {order.diagnosis} requiring pharmacist management
- Patient: {patient.first_name} {patient.last_name}
- Medication: {order.medication}

## 2. Goals
- Achieve therapeutic drug levels within 2 weeks
- Minimize adverse effects and drug interactions
- Improve patient adherence to medication regimen

## 3. Pharmacist Interventions
- Conduct medication reconciliation on admission
- Educate patient on proper administration of {order.medication}
- Review for potential drug-drug interactions
- Coordinate with referring provider {order.referring_provider_name}

## 4. Monitoring Plan
- Check labs (BMP, CBC) at baseline and in 2 weeks
- Monitor for adverse effects at each visit
- Follow up phone call in 1 week to assess adherence
"""


def _process_one(care_plan_id: int) -> None:
    try:
        care_plan = CarePlan.objects.select_related('order__patient').get(pk=care_plan_id)
    except CarePlan.DoesNotExist:
        print(f'[sqs-worker] care plan {care_plan_id} not found, skipping')
        return

    care_plan.status = CarePlan.Status.PROCESSING
    care_plan.save(update_fields=['status'])
    print(f'[sqs-worker] processing care plan {care_plan_id}')

    if os.environ.get('USE_FAKE_LLM', '').lower() == 'true':
        content = _fake_llm_response(care_plan)
    else:
        prompt = _build_prompt(care_plan)
        llm_service = get_llm_service()
        content = llm_service.generate_text(prompt)

    care_plan.status = CarePlan.Status.COMPLETED
    care_plan.content = content
    care_plan.save(update_fields=['status', 'content'])
    print(f'[sqs-worker] care plan {care_plan_id} completed')


def handler(event, context):
    """
    SQS 触发：批量处理消息。
    每条消息 body = {"care_plan_id": <int>}

    使用 Partial Batch Response：只有失败的消息才会被重试，
    成功的消息不会因为同批次有失败而被重复处理。
    前提：Lambda Trigger 需开启 "Report batch item failures"。
    """
    batch_item_failures = []

    for record in event['Records']:
        try:
            body = json.loads(record['body'])
            care_plan_id = body['care_plan_id']
            _process_one(care_plan_id)
        except Exception as e:
            print(f'[sqs-worker] failed on record {record.get("messageId")}: {e}')
            # 只把失败的消息 ID 返回，SQS 只重试这些
            batch_item_failures.append({'itemIdentifier': record['messageId']})

    return {'batchItemFailures': batch_item_failures}
