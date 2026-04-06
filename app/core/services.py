import re

from django.core.paginator import EmptyPage, Paginator
from django.utils import timezone

from .exceptions import (
    DuplicateOrderError,
    DuplicateOrderWarning,
    DuplicateProviderError,
    PatientDataMismatchWarning,
    ValidationError,
)
from .models import CarePlan, Order, Patient, Provider
from .tasks import generate_care_plan


def create_order(data: dict, confirm: bool = False) -> CarePlan:
    npi = data.get('referring_provider_npi', '')
    provider_name = data.get('referring_provider', '')
    mrn = data.get('mrn', '')
    diagnosis = data.get('primary_diagnosis', '')

    # --- 格式验证（后端最终防线，前端 Zod 绕过也拦得住）---
    if not re.fullmatch(r'\d{10}', npi):
        raise ValidationError('NPI must be exactly 10 digits.')

    if not re.fullmatch(r'\d{6}', mrn):
        raise ValidationError('MRN must be exactly 6 digits.')

    if not re.fullmatch(r'[A-Z]\d{2}(\.\d{1,4})?', diagnosis, re.IGNORECASE):
        raise ValidationError('Primary diagnosis must be a valid ICD-10 code (e.g. M05.79, I10).')

    # --- Provider duplicate detection ---
    existing_provider = Provider.objects.filter(npi=npi).first()
    if existing_provider:
        if existing_provider.name != provider_name:
            raise DuplicateProviderError(
                f"NPI {npi} is already registered under '{existing_provider.name}', "
                f"but submitted name is '{provider_name}'. NPI is a national unique identifier."
            )
        provider = existing_provider
    else:
        provider = Provider.objects.create(npi=npi, name=provider_name)

    # --- Patient duplicate detection ---
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    dob = data.get('dob', '')

    existing_by_mrn = Patient.objects.filter(mrn=mrn).first()
    existing_by_name_dob = Patient.objects.filter(
        first_name=first_name, last_name=last_name, dob=dob
    ).first()

    if existing_by_mrn:
        if (existing_by_mrn.first_name != first_name
                or existing_by_mrn.last_name != last_name
                or str(existing_by_mrn.dob) != str(dob)):
            if not confirm:
                raise PatientDataMismatchWarning(warnings=[
                    f"MRN {mrn} already belongs to '{existing_by_mrn.first_name} {existing_by_mrn.last_name}' "
                    f"(DOB: {existing_by_mrn.dob}), but submitted data is '{first_name} {last_name}' "
                    f"(DOB: {dob}). Confirm to proceed using the existing record."
                ])
        patient = existing_by_mrn
    elif existing_by_name_dob:
        if not confirm:
            raise PatientDataMismatchWarning(warnings=[
                f"A patient named '{first_name} {last_name}' (DOB: {dob}) already exists "
                f"under MRN {existing_by_name_dob.mrn}, but submitted MRN is {mrn}. "
                f"Confirm to create a new record."
            ])
        patient = Patient.objects.create(
            mrn=mrn, first_name=first_name, last_name=last_name, dob=dob
        )
    else:
        patient = Patient.objects.create(
            mrn=mrn, first_name=first_name, last_name=last_name, dob=dob
        )

    # --- Order duplicate detection ---
    medication = data.get('medication_name', '')
    today = timezone.now().date()

    same_day_order = Order.objects.filter(
        patient=patient,
        medication=medication,
        created_at__date=today,
    ).first()
    if same_day_order:
        raise DuplicateOrderError(
            f"An order for '{medication}' was already submitted today for patient MRN {mrn}. "
            f"(Order #{same_day_order.pk})"
        )

    if not confirm:
        prior_order = Order.objects.filter(
            patient=patient,
            medication=medication,
        ).first()
        if prior_order:
            raise DuplicateOrderWarning(warnings=[
                f"Patient MRN {mrn} has a prior order for '{medication}' "
                f"(Order #{prior_order.pk}, date: {prior_order.created_at.date()}). "
                f"Confirm to create a new order."
            ])

    order = Order.objects.create(
        patient=patient,
        provider=provider,
        referring_provider_name=provider_name,
        medication=medication,
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
