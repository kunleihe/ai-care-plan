from django.core.paginator import EmptyPage, Paginator

from .models import CarePlan, Order, Patient, Provider
from .tasks import generate_care_plan


def create_order(data: dict) -> CarePlan:
    patient, _ = Patient.objects.get_or_create(
        mrn=data['mrn'],
        defaults={
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'dob': data['dob'],
        },
    )
    provider, _ = Provider.objects.get_or_create(
        npi=data['referring_provider_npi'],
        defaults={'name': data['referring_provider']},
    )
    order = Order.objects.create(
        patient=patient,
        provider=provider,
        referring_provider_name=data['referring_provider'],
        medication=data['medication_name'],
        diagnosis=data['primary_diagnosis'],
        medical_notes=data.get('additional_notes', ''),
    )
    care_plan = CarePlan.objects.create(
        order=order,
        status=CarePlan.Status.PENDING,
    )
    generate_care_plan.delay(care_plan.id)
    return care_plan


def get_care_plan(plan_id: int) -> CarePlan:
    return CarePlan.objects.select_related('order__patient').get(pk=plan_id)


def get_care_plan_page(page: int, page_size: int):
    """Returns (paginator, page_obj). page_obj is None if page is out of range."""
    page_size = min(max(page_size, 1), 100)
    queryset = CarePlan.objects.select_related('order__patient').order_by('-created_at')
    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
        return paginator, page_obj
    except EmptyPage:
        return paginator, None


def get_batch_statuses(ids: list) -> dict:
    care_plans = CarePlan.objects.filter(pk__in=ids)
    return {cp.id: cp for cp in care_plans}
