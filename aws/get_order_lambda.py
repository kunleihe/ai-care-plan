import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.join(_HERE, '../app')
if os.path.isdir(_APP_DIR):
    sys.path.insert(0, _APP_DIR)
sys.path.insert(0, _HERE)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lambda_settings')
import django
django.setup()

from core import serializers, services
from core.models import Order


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


def handler(event, context):
    """
    GET /orders/{order_id}  → 订单详情 + care plan 状态/内容
    """
    method = event.get('httpMethod', '')
    path_params = event.get('pathParameters') or {}

    if method != 'GET':
        return _err('Method not allowed', 405)

    order_id_str = path_params.get('id')
    if not order_id_str:
        return _err('order_id is required', 400)

    try:
        order_id = int(order_id_str)
        order = services.get_order(order_id)
    except (ValueError, Order.DoesNotExist):
        return _err('Order not found', 404)

    return _ok(serializers.serialize_order_full(order))
