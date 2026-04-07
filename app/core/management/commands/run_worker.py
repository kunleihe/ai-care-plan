import os

import redis
from django.core.management.base import BaseCommand

from core.llm import get_llm_service
from core.models import CarePlan


redis_client = redis.Redis.from_url(
    os.environ.get('REDIS_URL', 'redis://redis:6379/0'),
    decode_responses=True,
)

QUEUE_NAME = 'care_plan_queue'


def build_prompt(care_plan: CarePlan) -> str:
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


def process_care_plan(care_plan_id: str):
    # Step 1: mark as processing
    try:
        care_plan = CarePlan.objects.select_related('order__patient').get(pk=care_plan_id)
    except CarePlan.DoesNotExist:
        print(f"[worker] care plan {care_plan_id} not found in DB, skipping")
        return

    care_plan.status = CarePlan.Status.PROCESSING
    care_plan.save(update_fields=['status'])
    print(f"[worker] processing care plan {care_plan_id} ...")

    # Step 2: call LLM
    try:
        prompt = build_prompt(care_plan)
        llm_service = get_llm_service()
        content = llm_service.generate_text(prompt)
    except Exception as e:
        print(f"[worker] LLM call failed for care plan {care_plan_id}: {type(e).__name__}")
        care_plan.status = CarePlan.Status.FAILED
        care_plan.content = 'Care plan generation failed. Please retry.'
        care_plan.save(update_fields=['status', 'content'])
        return

    # Step 3: save result
    care_plan.status = CarePlan.Status.COMPLETED
    care_plan.content = content
    care_plan.save(update_fields=['status', 'content'])
    print(f"[worker] care plan {care_plan_id} completed")


class Command(BaseCommand):
    help = 'Run the care plan worker — pulls tasks from Redis and calls LLM'

    def handle(self, *args, **options):
        self.stdout.write('[worker] started, waiting for tasks ...')
        while True:
            # blpop blocks until a message arrives (timeout=0 means wait forever)
            result = redis_client.blpop(QUEUE_NAME, timeout=0) #阻塞等待，如果队列里没有任务，代码就停在这里
            if result is None:
                continue
            _, care_plan_id = result  # blpop returns (queue_name, value)
            process_care_plan(care_plan_id)
