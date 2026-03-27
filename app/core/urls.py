from django.urls import path
from . import views

urlpatterns = [
    path('', views.form_view, name='form'),
    path('result/<str:plan_id>/', views.result_view, name='result'),
    path('api/care-plans/<str:plan_id>/', views.care_plan_api, name='care_plan_api'),
]
