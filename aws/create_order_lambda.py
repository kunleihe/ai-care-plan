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
from core.queue import BaseQueue


class SQSQueue(BaseQueue):
    def __init__(self, queue_url: str):
        self.queue_url = queue_url
        self._client = boto3.client('sqs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

    def enqueue(self, care_plan_id: int) -> None:
        self._client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps({'care_plan_id': care_plan_id}),
        )


_queue = SQSQueue(queue_url=os.environ['SQS_QUEUE_URL'])


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
        care_plan = services.create_order(body, source=source, confirm=confirm, queue=_queue)
    except ValidationError as e:
        return _err(e.message, 400)
    except BlockError as e:
        return {
            'statusCode': 409,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(e.to_response_dict()),
        }
    except WarningException as e:
        return {
            'statusCode': 409,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(e.to_response_dict()),
        }
    except Exception:
        return _err('Internal server error', 500)

    return _ok({'care_plan_id': care_plan.id, 'status': care_plan.status}, 201)
