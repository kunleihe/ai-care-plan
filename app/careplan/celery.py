import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'careplan.settings')

app = Celery('careplan')

# 从 Django settings 里读所有 CELERY_ 开头的配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各 app 下的 tasks.py
app.autodiscover_tasks()
