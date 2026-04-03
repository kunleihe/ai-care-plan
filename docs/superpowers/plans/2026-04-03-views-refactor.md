# Views Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 views.py 中的三类代码拆分到正确的文件，不改变任何功能。

**Architecture:** views.py 只做 HTTP 进出；serializers.py 做模型到 dict 的格式转换；services.py 做业务逻辑（DB 操作 + Celery 派发）。urls.py 和 models.py 不动。

**Tech Stack:** Django 4.x, Python 3.x, Celery, django.core.paginator

---

## 文件职责映射

| 文件 | 职责 |
|---|---|
| `app/core/views.py` | 解析 request，调 service/serializer，返回 JsonResponse / render / redirect |
| `app/core/services.py` | (新建) Patient/Provider/Order/CarePlan 创建，Celery 派发，DB 查询，分页 |
| `app/core/serializers.py` | (新建) CarePlan model → dict 格式转换，供各 API endpoint 使用 |

## 代码迁移映射表

| views.py 原位置 | 搬到 | 新函数 |
|---|---|---|
| `order_api` lines 23–51（创建 Patient/Provider/Order/CarePlan + delay） | services.py | `create_order(data)` |
| `form_view` lines 59–90（同上，重复逻辑） | services.py | `create_order(data)`（复用同一函数） |
| `care_plan_api` / `care_plan_status_api` 里的 `get(pk=plan_id)` | services.py | `get_care_plan(plan_id)` |
| `care_plan_list_api` lines 180–191（queryset + paginator + EmptyPage 处理） | services.py | `get_care_plan_page(page, page_size)` |
| `care_plan_batch_status_api` lines 236–237（`filter + dict`） | services.py | `get_batch_statuses(ids)` |
| `care_plan_api` lines 112–128（dict 拼装） | serializers.py | `serialize_care_plan_full(care_plan)` |
| `care_plan_status_api` lines 140–159（dict 拼装 + FAILED error） | serializers.py | `serialize_care_plan_status(care_plan)` |
| `care_plan_list_api` lines 193–205（每条记录 dict 拼装） | serializers.py | `serialize_care_plan_list_item(care_plan)` |
| `care_plan_batch_status_api` lines 239–256（每条 dict 拼装） | serializers.py | `serialize_batch_status_item(plan_id, care_plan_or_None)` |

---

## Task 1: 创建 services.py

**Files:**
- Create: `app/core/services.py`

- [ ] **Step 1: 创建 services.py**

```python
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
```

- [ ] **Step 2: 验证 import 正确**

```bash
cd /path/to/project && python -c "from app.core import services; print('OK')"
```

Expected: `OK`

---

## Task 2: 创建 serializers.py

**Files:**
- Create: `app/core/serializers.py`

- [ ] **Step 1: 创建 serializers.py**

```python
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
```

---

## Task 3: 重写 views.py（仅保留 HTTP 层）

**Files:**
- Modify: `app/core/views.py`

- [ ] **Step 1: 替换 views.py 全文**

```python
import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import CarePlan
from . import serializers, services


@csrf_exempt
def order_api(request):
    """React 前端用的 JSON POST 接口"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    care_plan = services.create_order(data)
    return JsonResponse({'care_plan_id': care_plan.id, 'status': care_plan.status}, status=201)


def form_view(request):
    if request.method == 'POST':
        data = {
            'mrn': request.POST['mrn'],
            'first_name': request.POST['first_name'],
            'last_name': request.POST['last_name'],
            'dob': request.POST['dob'],
            'referring_provider_npi': request.POST['referring_provider_npi'],
            'referring_provider': request.POST['referring_provider'],
            'medication_name': request.POST['medication_name'],
            'primary_diagnosis': request.POST['primary_diagnosis'],
            'additional_notes': request.POST.get('additional_notes', ''),
        }
        care_plan = services.create_order(data)
        return redirect('result', plan_id=care_plan.id)
    return render(request, 'form.html')


def result_view(request, plan_id):
    try:
        care_plan = services.get_care_plan(plan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)
    return render(request, 'result.html', {'care_plan': care_plan})


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

    paginator, page_obj = services.get_care_plan_page(page, page_size)

    if page_obj is None:
        return JsonResponse({
            'count': paginator.count,
            'next': None,
            'previous': None,
            'results': [],
        })

    results = [serializers.serialize_care_plan_list_item(cp) for cp in page_obj.object_list]
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

    care_plan_map = services.get_batch_statuses(normalized_ids)
    results = [
        serializers.serialize_batch_status_item(plan_id, care_plan_map.get(plan_id))
        for plan_id in normalized_ids
    ]
    return JsonResponse({'results': results})
```

---

## Task 4: 验证功能不变

- [ ] **Step 1: 检查 Django 能正常 import**

```bash
docker compose exec web python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 2: 验证路由绑定没有断**

```bash
docker compose exec web python manage.py show_urls | grep api
```

Expected: 所有 `/api/` 路由还存在。

- [ ] **Step 3: 手动 smoke test（如果服务在跑）**

```bash
# POST 提交一个 order
curl -X POST http://localhost:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{"mrn":"123456","first_name":"Test","last_name":"User","dob":"1990-01-01","referring_provider_npi":"1234567890","referring_provider":"Dr. Smith","medication_name":"Metformin","primary_diagnosis":"E11.9"}'

# GET 列表
curl http://localhost:8000/api/careplans/
```
