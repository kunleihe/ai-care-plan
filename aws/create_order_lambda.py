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

import boto3
from core import services
from core.exceptions import (
    BlockError,
    ValidationError,
    WarningException,
)

_sqs = boto3.client('sqs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
_QUEUE_URL = os.environ['SQS_QUEUE_URL']


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
    POST /orders  → 验证 + 存 DB + 发 SQS 消息
    """
    if event.get('httpMethod', '') != 'POST':
        return _err('Method not allowed', 405)

    try:
        body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        return _err('Invalid JSON body', 400)

    confirm = body.pop('confirm', False)
    source = body.pop('source', 'manual_form')

    try:
        care_plan = services.create_order(body, source=source, confirm=confirm, enqueue=False)
    except ValidationError as e:
        return _err(e.message, 400)
    except BlockError as e:
        # DuplicateProviderError / DuplicateOrderError — 不可跳过
        return {
            'statusCode': 409,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(e.to_response_dict()),
        }
    except WarningException as e:
        # DuplicateOrderWarning / PatientDataMismatchWarning — 需要前端 confirm
        return {
            'statusCode': 409,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(e.to_response_dict()),
        }
    except Exception:
        return _err('Internal server error', 500)

    _sqs.send_message(
        QueueUrl=_QUEUE_URL,
        MessageBody=json.dumps({'care_plan_id': care_plan.id}),
    )

    return _ok({'care_plan_id': care_plan.id, 'status': care_plan.status}, 201)
