import os
import uuid

from django.shortcuts import render, redirect
from openai import OpenAI
from django.http import JsonResponse


# In-memory store. Resets when the container restarts.
care_plans = {}

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])


def form_view(request):
    if request.method == 'POST':
        patient = {
            'first_name': request.POST['first_name'],
            'last_name': request.POST['last_name'],
            'mrn': request.POST['mrn'],
            'dob': request.POST['dob'],
            'referring_provider': request.POST['referring_provider'],
            'primary_diagnosis': request.POST['primary_diagnosis'],
            'medication_name': request.POST['medication_name'],
            'additional_notes': request.POST.get('additional_notes', ''),
        }

        prompt = f"""Generate a clinical care plan for the following patient:

Patient: {patient['first_name']} {patient['last_name']}
MRN: {patient['mrn']}
Date of Birth: {patient['dob']}
Referring Provider: {patient['referring_provider']}
Primary Diagnosis (ICD-10): {patient['primary_diagnosis']}
Medication: {patient['medication_name']}
Additional Notes: {patient['additional_notes']}

Output exactly 4 sections with these headings:

1. Problem List / Drug Therapy Problems (DTPs)
   List drug therapy problems identified from the patient's clinical information.

2. Goals (SMART)
   - Primary Goal: quantifiable treatment goal with timeline
   - Safety Goal: safety-related goal
   - Process Goal: adherence/process goal

3. Pharmacist Interventions / Plan
   - Dosing & Administration
   - Premedication (if applicable)
   - Adverse Event Management

4. Monitoring Plan & Lab Schedule
   - Before first dose: required labs and checks
   - During treatment: monitoring frequency and parameters
   - After treatment: follow-up labs and timeline
"""

        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a clinical pharmacist generating care plans for specialty pharmacy patients. '
                        'Be specific, clinically accurate, and follow the exact output structure requested.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
        )

        care_plan_text = response.choices[0].message.content
        plan_id = str(uuid.uuid4())
        care_plans[plan_id] = {
            'patient': patient,
            'care_plan_text': care_plan_text,
        }

        return redirect('result', plan_id=plan_id)

    return render(request, 'form.html')


def result_view(request, plan_id):
    data = care_plans[plan_id]
    return render(request, 'result.html', {'data': data})


def care_plan_api(request, plan_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if plan_id not in care_plans:
        return JsonResponse({'error': 'Care plan not found'}, status=404)
    
    care_plan = care_plans[plan_id]
    return JsonResponse(care_plan, status=200)