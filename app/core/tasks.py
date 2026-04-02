import os

from celery import shared_task
from openai import OpenAI

from .models import CarePlan


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


@shared_task(bind=True, max_retries=3)
def generate_care_plan(self, care_plan_id: int):
    """
    异步生成 Care Plan。
    - bind=True        → self 是 task 实例，可以调 self.retry()
    - max_retries=3    → 最多重试 3 次（加上第一次共 4 次执行）
    - 退避策略：第 1 次重试等 10s，第 2 次 20s，第 3 次 40s（指数退避）
    """
    # ── Step 1: 拿到 care plan，标记为 processing ──────────────────────────
    try:
        care_plan = CarePlan.objects.select_related('order__patient').get(pk=care_plan_id)
    except CarePlan.DoesNotExist:
        # 记录找不到，直接放弃，不重试
        print(f'[celery] care plan {care_plan_id} not found, skipping')
        return

    care_plan.status = CarePlan.Status.PROCESSING
    care_plan.save(update_fields=['status'])
    print(f'[celery] processing care plan {care_plan_id} (attempt {self.request.retries + 1})')

    # ── Step 2: 调用 LLM ───────────────────────────────────────────────────
    try:
        if os.environ.get('USE_FAKE_LLM', '').lower() == 'true':
            content = _fake_llm_response(care_plan)
        else:
            client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': _build_prompt(care_plan)}],
                temperature=0.3,
            )
            content = response.choices[0].message.content
    except Exception as exc:
        # 指数退避：10s → 20s → 40s
        countdown = 10 * (2 ** self.request.retries)
        print(f'[celery] LLM failed ({type(exc).__name__}), retry in {countdown}s')

        try:
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            # 三次都失败了，写入 FAILED 状态
            care_plan.status = CarePlan.Status.FAILED
            care_plan.content = 'Care plan generation failed after 3 attempts. Please retry.'
            care_plan.save(update_fields=['status', 'content'])
            print(f'[celery] care plan {care_plan_id} permanently failed')
        return

    # ── Step 3: 保存结果 ───────────────────────────────────────────────────
    care_plan.status = CarePlan.Status.COMPLETED
    care_plan.content = content
    care_plan.save(update_fields=['status', 'content'])
    print(f'[celery] care plan {care_plan_id} completed successfully')
