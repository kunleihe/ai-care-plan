# Care Plan MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal Django app where a medical assistant fills out a patient form, waits for OpenAI to generate a care plan, and sees the result — all running in Docker with no database.

**Architecture:** Single Docker container running Django dev server. Two views: form (GET/POST `/`) and result (GET `/result/<uuid>/`). A module-level dict in `views.py` holds all care plans in memory. POST blocks on the OpenAI call, then redirects to the result page.

**Tech Stack:** Python 3.11, Django 4.2, OpenAI Python SDK, Docker / docker-compose

---

### Task 1: Docker and dependency files

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `requirements.txt`

- [ ] **Step 1: Create `requirements.txt`**

```
django>=4.2,<5.0
openai>=1.0
python-dotenv>=1.0
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./app:/app
```

- [ ] **Step 4: Create `.env.example`**

```
OPENAI_API_KEY=sk-...
DJANGO_SECRET_KEY=change-me-in-production
```

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example requirements.txt
git commit -m "feat: add docker and dependency files"
```

---

### Task 2: Django project scaffold

**Files:**
- Create: `app/manage.py`
- Create: `app/careplan/__init__.py`
- Create: `app/careplan/settings.py`
- Create: `app/careplan/urls.py`
- Create: `app/careplan/wsgi.py`

- [ ] **Step 1: Create `app/manage.py`**

```python
#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'careplan.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
```

- [ ] **Step 2: Create `app/careplan/__init__.py`**

```python
```
(empty file)

- [ ] **Step 3: Create `app/careplan/settings.py`**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-secret-key')

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'core',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
]

ROOT_URLCONF = 'careplan.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'careplan.wsgi.application'

DATABASES = {}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

- [ ] **Step 4: Create `app/careplan/urls.py`**

```python
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
]
```

- [ ] **Step 5: Create `app/careplan/wsgi.py`**

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'careplan.settings')
application = get_wsgi_application()
```

- [ ] **Step 6: Commit**

```bash
git add app/
git commit -m "feat: scaffold Django project"
```

---

### Task 3: Core app — views and URLs

**Files:**
- Create: `app/core/__init__.py`
- Create: `app/core/urls.py`
- Create: `app/core/views.py`

- [ ] **Step 1: Create `app/core/__init__.py`**

```python
```
(empty file)

- [ ] **Step 2: Create `app/core/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.form_view, name='form'),
    path('result/<str:plan_id>/', views.result_view, name='result'),
]
```

- [ ] **Step 3: Create `app/core/views.py`**

```python
import os
import uuid

from django.shortcuts import render, redirect
from openai import OpenAI

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
```

- [ ] **Step 4: Commit**

```bash
git add app/core/
git commit -m "feat: add form and result views with OpenAI call"
```

---

### Task 4: Templates

**Files:**
- Create: `app/core/templates/form.html`
- Create: `app/core/templates/result.html`

- [ ] **Step 1: Create `app/core/templates/form.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>New Care Plan</title>
  <style>
    body { font-family: sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
    label { display: block; margin-top: 16px; font-weight: bold; font-size: 14px; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 8px; margin-top: 4px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; }
    textarea { height: 80px; resize: vertical; }
    button { margin-top: 24px; padding: 10px 24px; background: #1a56db; color: white; border: none; border-radius: 4px; font-size: 15px; cursor: pointer; }
    button:hover { background: #1648c0; }
    .hint { font-size: 12px; color: #666; margin-top: 2px; }
    h1 { font-size: 22px; }
  </style>
</head>
<body>
  <h1>Generate Care Plan</h1>
  <form method="post">
    {% csrf_token %}

    <label for="first_name">Patient First Name</label>
    <input type="text" id="first_name" name="first_name" required>

    <label for="last_name">Patient Last Name</label>
    <input type="text" id="last_name" name="last_name" required>

    <label for="mrn">Patient MRN</label>
    <input type="text" id="mrn" name="mrn" required>

    <label for="dob">Date of Birth</label>
    <input type="date" id="dob" name="dob" required>

    <label for="referring_provider">Referring Provider</label>
    <input type="text" id="referring_provider" name="referring_provider" required>

    <label for="primary_diagnosis">Primary Diagnosis (ICD-10)</label>
    <input type="text" id="primary_diagnosis" name="primary_diagnosis" placeholder="e.g. M05.79" required>

    <label for="medication_name">Medication Name</label>
    <input type="text" id="medication_name" name="medication_name" required>

    <label for="additional_notes">Additional Notes <span style="font-weight:normal">(optional)</span></label>
    <textarea id="additional_notes" name="additional_notes" placeholder="Medication history, allergies, other diagnoses..."></textarea>

    <p class="hint">Generating the care plan may take 10–20 seconds.</p>
    <button type="submit">Generate Care Plan</button>
  </form>
</body>
</html>
```

- [ ] **Step 2: Create `app/core/templates/result.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Care Plan — {{ data.patient.first_name }} {{ data.patient.last_name }}</title>
  <style>
    body { font-family: sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; }
    h1 { font-size: 22px; }
    .meta { background: #f5f5f5; border-radius: 6px; padding: 16px; margin-bottom: 24px; font-size: 14px; line-height: 1.8; }
    .meta strong { display: inline-block; width: 160px; }
    pre { white-space: pre-wrap; font-family: sans-serif; font-size: 14px; line-height: 1.7; background: #fafafa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 20px; }
    a { color: #1a56db; font-size: 14px; }
    h2 { font-size: 16px; margin-top: 32px; }
  </style>
</head>
<body>
  <h1>Care Plan</h1>

  <div class="meta">
    <strong>Patient:</strong> {{ data.patient.first_name }} {{ data.patient.last_name }}<br>
    <strong>MRN:</strong> {{ data.patient.mrn }}<br>
    <strong>Date of Birth:</strong> {{ data.patient.dob }}<br>
    <strong>Referring Provider:</strong> {{ data.patient.referring_provider }}<br>
    <strong>Primary Diagnosis:</strong> {{ data.patient.primary_diagnosis }}<br>
    <strong>Medication:</strong> {{ data.patient.medication_name }}<br>
  </div>

  <h2>Generated Care Plan</h2>
  <pre>{{ data.care_plan_text }}</pre>

  <p><a href="{% url 'form' %}">← Generate another care plan</a></p>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add app/core/templates/
git commit -m "feat: add form and result templates"
```

---

### Task 5: First run verification

- [ ] **Step 1: Copy `.env.example` to `.env` and fill in your API key**

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

- [ ] **Step 2: Build and start the container**

```bash
docker-compose up --build
```

Expected output ends with:
```
Starting development server at http://0.0.0.0:8000/
```

- [ ] **Step 3: Open the form**

Navigate to `http://localhost:8000/` in your browser. You should see the patient intake form.

- [ ] **Step 4: Submit a test care plan**

Fill in sample values, e.g.:
- First Name: `Jane`
- Last Name: `Doe`
- MRN: `123456`
- DOB: `1965-04-12`
- Referring Provider: `Dr. Smith`
- Primary Diagnosis: `M05.79`
- Medication: `Methotrexate`

Click **Generate Care Plan**. Wait ~10–20 seconds. You should land on `/result/<uuid>/` with a 4-section care plan.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: care plan MVP complete"
```
