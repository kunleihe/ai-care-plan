from .models import CarePlan


def serialize_care_plan_full(care_plan: CarePlan) -> dict:
    order = care_plan.order
    patient = order.patient
    return {
        'id': care_plan.id,
        'status': care_plan.status,
        'content': care_plan.content,
        'patient': {
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'mrn': patient.mrn,
        },
        'order': {
            'medication': order.medication,
            'diagnosis': order.diagnosis,
            'referring_provider': order.referring_provider_name,
        },
    }


def serialize_care_plan_status(care_plan: CarePlan) -> dict:
    order = care_plan.order
    patient = order.patient
    data = {
        'id': care_plan.id,
        'status': care_plan.status,
        'content': care_plan.content if care_plan.status == CarePlan.Status.COMPLETED else None,
        'patient': {
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'mrn': patient.mrn,
        },
        'order': {
            'medication': order.medication,
            'diagnosis': order.diagnosis,
            'referring_provider': order.referring_provider_name,
        },
    }
    if care_plan.status == CarePlan.Status.FAILED:
        data['error'] = care_plan.content or 'Care plan generation failed. Please retry.'
    return data


def serialize_care_plan_list_item(care_plan: CarePlan) -> dict:
    order = care_plan.order
    patient = order.patient
    return {
        'id': care_plan.id,
        'status': care_plan.status,
        'patient_name': f'{patient.first_name} {patient.last_name}',
        'mrn': patient.mrn,
        'medication': order.medication,
        'diagnosis': order.diagnosis,
        'created_at': care_plan.created_at.isoformat(),
    }


def serialize_batch_status_item(plan_id: int, care_plan) -> dict:
    if care_plan is None:
        return {
            'id': plan_id,
            'status': 'failed',
            'error': 'Care plan not found',
        }
    item = {
        'id': care_plan.id,
        'status': care_plan.status,
    }
    if care_plan.status == CarePlan.Status.FAILED:
        item['error'] = care_plan.content or 'Care plan generation failed. Please retry.'
    return item
