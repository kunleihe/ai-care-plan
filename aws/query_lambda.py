import json
import os
import sys

# ── 路径设置 ──────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.join(_HERE, '../app')
if os.path.isdir(_APP_DIR):
    # 本地开发：app/ 在 aws/ 的上级目录
    sys.path.insert(0, _APP_DIR)
# Lambda 里 core/ 已经在 zip 根目录（/var/task/），不需要额外加路径
sys.path.insert(0, _HERE)  # 让 lambda_settings 可以被找到（本地用）

# ── Django 初始化（模块级别 = 冷启动时只跑一次）──────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lambda_settings')
import django
django.setup()

# ── 现在才能 import Django ORM 相关模块 ───────────────────────────────────────
from core import serializers, services
from core.models import CarePlan


# ── 响应工具函数 ──────────────────────────────────────────────────────────────

def _ok(body: dict, status: int = 200) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body),
    }


def _err(message: str, status: int) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message}),
    }


# ── Lambda 入口 ───────────────────────────────────────────────────────────────

def handler(event, context):
    """
    API Gateway 触发，支持三个路由：
      GET /care-plans/{plan_id}         → 完整 care plan
      GET /care-plans/{plan_id}/status  → 仅状态（polling 用）
      GET /care-plans                   → 分页列表
    """
    method = event.get('httpMethod', '')
    path = event.get('path', '')
    path_params = event.get('pathParameters') or {}
    query_params = event.get('queryStringParameters') or {}

    if method != 'GET':
        return _err('Method not allowed', 405)

    plan_id_str = path_params.get('plan_id')

    # ── 单条查询（带或不带 /status 后缀）────────────────────────────────────
    if plan_id_str:
        try:
            plan_id = int(plan_id_str)
            care_plan = services.get_care_plan(plan_id)
        except (ValueError, CarePlan.DoesNotExist):
            return _err('Care plan not found', 404)

        if path.endswith('/status'):
            return _ok(serializers.serialize_care_plan_status(care_plan))
        return _ok(serializers.serialize_care_plan_full(care_plan))

    # ── 列表查询 ──────────────────────────────────────────────────────────────
    try:
        page = max(int(query_params.get('page', 1)), 1)
        page_size = int(query_params.get('page_size', 20))
    except (TypeError, ValueError):
        return _err('Invalid pagination params', 400)

    paginator, page_obj = services.get_care_plan_page(page, page_size)

    if page_obj is None:
        return _ok({'count': paginator.count, 'next': None, 'previous': None, 'results': []})

    return _ok({
        'count': paginator.count,
        'next': page + 1 if page_obj.has_next() else None,
        'previous': page - 1 if page_obj.has_previous() else None,
        'results': [serializers.serialize_care_plan_list_item(cp) for cp in page_obj.object_list],
    })
