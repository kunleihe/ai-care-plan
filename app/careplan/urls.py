from django.urls import path, include

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('', include('core.urls')),
]
