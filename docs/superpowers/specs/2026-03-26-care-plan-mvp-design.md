# Care Plan MVP — Design Spec

**Date:** 2026-03-26
**Status:** Approved

---

## Goal

A minimal end-to-end flow: medical assistant fills out a form, submits it, waits for OpenAI to generate a care plan, and sees the result on screen. No database, no async, no validation, no fancy tech.

---

## Stack

- Python / Django
- OpenAI Python SDK (`gpt-4o`)
- Docker (single container)
- API key passed via `.env`

---

## File Structure

```
ai-care-plan/
├── Dockerfile
├── docker-compose.yml
├── .env                   ← user provides (OPENAI_API_KEY, etc.)
├── requirements.txt
└── app/
    ├── manage.py
    ├── careplan/          ← Django project package
    │   ├── __init__.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    └── core/              ← single Django app with all logic
        ├── __init__.py
        ├── views.py
        ├── urls.py
        └── templates/
            ├── form.html
            └── result.html
```

---

## URLs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Show the patient input form |
| POST | `/` | Call OpenAI, store result, redirect to result page |
| GET | `/result/<uuid>` | Show the generated care plan |

---

## In-Memory Store

Module-level dict in `views.py`:

```python
care_plans = {}
# { "550e8400-...": { "patient": { ...form fields... }, "care_plan_text": "..." } }
```

Keyed by UUID generated at POST time. Survives within the process; resets on container restart.

---

## Form Fields

| Field | Type | Required |
|-------|------|----------|
| Patient First Name | text | yes |
| Patient Last Name | text | yes |
| Patient MRN | text | yes |
| Patient Date of Birth | date | yes |
| Referring Provider | text | yes |
| Primary Diagnosis (ICD-10) | text | yes |
| Medication Name | text | yes |
| Additional Notes | textarea | no |

---

## LLM Call

- Model: `gpt-4o`
- Sync (blocks until response)
- System prompt instructs the model to output a care plan in exactly 4 sections:
  1. Problem List / Drug Therapy Problems (DTPs)
  2. Goals (SMART)
  3. Pharmacist Interventions / Plan
  4. Monitoring Plan & Lab Schedule
- User message contains all form fields formatted as structured text

---

## Data Flow

```
GET /
  → render form.html

POST /
  → read form fields from request.POST
  → build prompt string
  → call openai.chat.completions.create(...) — blocks
  → generate uuid
  → care_plans[uuid] = { "patient": {...}, "care_plan_text": response }
  → redirect to /result/<uuid>

GET /result/<uuid>
  → look up care_plans[uuid]
  → render result.html with patient info + care plan text
```

---

## Docker

- Single container, Python base image
- `env_file: .env` in docker-compose.yml
- Exposes port 8000
- Django runs with `python manage.py runserver 0.0.0.0:8000`

---

## Out of Scope (MVP)

- Input validation / error handling
- Duplicate detection / warnings
- Database persistence
- Authentication
- PDF upload
- Export to CSV/TXT
- Tests
