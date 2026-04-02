from django.urls import path
from . import views

urlpatterns = [
    # Django template 原有路由（保留）
    path('', views.form_view, name='form'),
    path('result/<int:plan_id>/', views.result_view, name='result'),
    # JSON API（React 前端用）
    path('api/orders/', views.order_api, name='order_api'),
    path('api/care-plans/<int:plan_id>/', views.care_plan_api, name='care_plan_api'),
]
