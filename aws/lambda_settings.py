import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'lambda-only-not-for-web')
DEBUG = False
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = ['core']  # Prometheus、Celery 都不需要

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {'sslmode': 'require'},
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# LLM 配置保留，后续 generate Lambda 会用到
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai')
LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', '0.3'))
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-3-5-sonnet-latest')
CLAUDE_MAX_TOKENS = int(os.environ.get('CLAUDE_MAX_TOKENS', '2000'))
