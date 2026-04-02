from django.urls import path
from . import views

urlpatterns = [
    # Django template 原有路由（保留）
    path('', views.form_view, name='form'),
    path('result/<int:plan_id>/', views.result_view, name='result'),
    # JSON API（React 前端用）
    path('api/orders/', views.order_api, name='order_api'),
    path('api/careplans/', views.care_plan_list_api, name='care_plan_list_api'),
    path('api/careplans/statuses/', views.care_plan_batch_status_api, name='care_plan_batch_status_api'),
    path('api/careplan/<int:plan_id>/status/', views.care_plan_status_api, name='care_plan_status_api'),
    path('api/care-plans/<int:plan_id>/', views.care_plan_api, name='care_plan_api'),
]
