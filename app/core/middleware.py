from django.http import JsonResponse

from .exceptions import BaseAppException


class AppExceptionMiddleware:
    """
    统一异常处理中间件。

    认识两类异常：
    1. BaseAppException（项目自定义）→ 直接转成 JSON
    2. DRF ValidationError（如果将来引入 DRF）→ 转成相同格式

    其他所有异常不捕获，交给 Django 默认处理（开发时 500 页面 / 日志）。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, BaseAppException):
            return JsonResponse(
                exception.to_response_dict(),
                status=exception.http_status,
            )

        # DRF 兼容：将来加了 DRF serializer 验证时自动生效，不加则忽略
        try:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            if isinstance(exception, DRFValidationError):
                return JsonResponse({
                    'type': 'validation_error',
                    'code': 'VALIDATION_ERROR',
                    'message': 'Input validation failed.',
                    'detail': exception.detail,
                }, status=400)
        except ImportError:
            pass

        return None  # 其他异常不处理，交给 Django
