# 让 Django 启动时就加载 Celery app，这样 @shared_task 装饰器才能正确注册
from .celery import app as celery_app

__all__ = ('celery_app',)
