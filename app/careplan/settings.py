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
