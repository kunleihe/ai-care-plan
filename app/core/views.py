import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .exceptions import ValidationError
from .models import CarePlan
from . import serializers, services


@csrf_exempt
def order_api(request, source: str = 'manual_form'):
    """React 前端用的 JSON POST 接口"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        raise ValidationError('Request body must be valid JSON.')

    confirm = bool(data.get('confirm', False))
    care_plan = services.create_order(data, source=source, confirm=confirm)
    return JsonResponse({'care_plan_id': care_plan.id, 'status': care_plan.status}, status=201)



def care_plan_api(request, plan_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        care_plan = services.get_care_plan(plan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)

    return JsonResponse(serializers.serialize_care_plan_full(care_plan))


def care_plan_status_api(request, plan_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        care_plan = services.get_care_plan(plan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)

    return JsonResponse(serializers.serialize_care_plan_status(care_plan))


def care_plan_list_api(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid page'}, status=400)

    try:
        page_size = int(request.GET.get('page_size', 20))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid page_size'}, status=400)

    status = request.GET.get('status')
    if status and status not in CarePlan.Status.values:
        return JsonResponse(
            {'error': f'Invalid status. Must be one of: {list(CarePlan.Status.values)}'},
            status=400,
        )

    patient_name = request.GET.get('patient_name', '').strip() or None

    paginator, page_obj, effective_page_size = services.get_care_plan_page(
        page, page_size, status=status, patient_name=patient_name,
    )

    if page_obj is None:
        return JsonResponse({
            'count': paginator.count,
            'page': page,
            'page_size': effective_page_size,
            'results': [],
        })

    results = [serializers.serialize_care_plan_list_item(cp) for cp in page_obj.object_list]
    return JsonResponse({
        'count': paginator.count,
        'page': page,
        'page_size': effective_page_size,
        'results': results,
    })


@csrf_exempt
def care_plan_batch_status_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    ids = data.get('ids')
    if not isinstance(ids, list):
        return JsonResponse({'error': 'ids must be a list'}, status=400)

    normalized_ids = []
    for raw_id in ids:
        try:
            normalized_ids.append(int(raw_id))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'All ids must be integers'}, status=400)

    care_plan_map = services.get_batch_statuses(normalized_ids)
    results = [
        serializers.serialize_batch_status_item(plan_id, care_plan_map.get(plan_id))
        for plan_id in normalized_ids
    ]
    return JsonResponse({'results': results})
