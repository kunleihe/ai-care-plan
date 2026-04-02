import json

from django.http import JsonResponse
from django.core.paginator import EmptyPage, Paginator
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import CarePlan, Order, Patient, Provider
from .tasks import generate_care_plan


@csrf_exempt
def order_api(request):
    """React 前端用的 JSON POST 接口"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

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

    return JsonResponse({'care_plan_id': care_plan.id, 'status': care_plan.status}, status=201)


def form_view(request):
    if request.method == 'POST':
        # Get or create Patient by MRN (unique identifier)
        patient, _ = Patient.objects.get_or_create(
            mrn=request.POST['mrn'],
            defaults={
                'first_name': request.POST['first_name'],
                'last_name': request.POST['last_name'],
                'dob': request.POST['dob'],
            },
        )

        provider, _ = Provider.objects.get_or_create(
            npi=request.POST['referring_provider_npi'],
            defaults={'name': request.POST['referring_provider']},
        )

        order = Order.objects.create(
            patient=patient,
            provider=provider,
            referring_provider_name=request.POST['referring_provider'],
            medication=request.POST['medication_name'],
            diagnosis=request.POST['primary_diagnosis'],
            medical_notes=request.POST.get('additional_notes', ''),
        )

        care_plan = CarePlan.objects.create(
            order=order,
            status=CarePlan.Status.PENDING,
        )

        # 派发 Celery 异步任务
        generate_care_plan.delay(care_plan.id)

        return redirect('result', plan_id=care_plan.id)

    return render(request, 'form.html')


def result_view(request, plan_id):
    try:
        care_plan = CarePlan.objects.select_related('order__patient').get(pk=plan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)
    return render(request, 'result.html', {'care_plan': care_plan})


def care_plan_api(request, plan_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        care_plan = CarePlan.objects.select_related('order__patient').get(pk=plan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)

    order = care_plan.order
    patient = order.patient
    return JsonResponse({
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
    })


def care_plan_status_api(request, plan_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        care_plan = CarePlan.objects.select_related('order__patient').get(pk=plan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)

    order = care_plan.order
    patient = order.patient
    response_data = {
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
        response_data['error'] = care_plan.content or 'Care plan generation failed. Please retry.'

    return JsonResponse(response_data)


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

    page_size = min(max(page_size, 1), 100)

    queryset = CarePlan.objects.select_related('order__patient').order_by('-created_at')
    paginator = Paginator(queryset, page_size)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({
            'count': paginator.count,
            'next': None,
            'previous': None,
            'results': [],
        })

    results = []
    for care_plan in page_obj.object_list:
        order = care_plan.order
        patient = order.patient
        results.append({
            'id': care_plan.id,
            'status': care_plan.status,
            'patient_name': f'{patient.first_name} {patient.last_name}',
            'mrn': patient.mrn,
            'medication': order.medication,
            'diagnosis': order.diagnosis,
            'created_at': care_plan.created_at.isoformat(),
        })

    return JsonResponse({
        'count': paginator.count,
        'next': page + 1 if page_obj.has_next() else None,
        'previous': page - 1 if page_obj.has_previous() else None,
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

    care_plans = CarePlan.objects.filter(pk__in=normalized_ids)
    care_plan_map = {care_plan.id: care_plan for care_plan in care_plans}

    results = []
    for plan_id in normalized_ids:
        care_plan = care_plan_map.get(plan_id)
        if not care_plan:
            results.append({
                'id': plan_id,
                'status': 'failed',
                'error': 'Care plan not found',
            })
            continue

        item = {
            'id': care_plan.id,
            'status': care_plan.status,
        }
        if care_plan.status == CarePlan.Status.FAILED:
            item['error'] = care_plan.content or 'Care plan generation failed. Please retry.'
        results.append(item)

    return JsonResponse({'results': results})
