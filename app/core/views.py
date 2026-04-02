from django.http import JsonResponse
from django.shortcuts import redirect, render

from .models import CarePlan, Order, Patient, Provider
from .tasks import generate_care_plan


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
