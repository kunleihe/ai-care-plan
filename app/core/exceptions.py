class BaseAppException(Exception):
    """所有业务异常的基类。子类只需覆盖 http_status / code。"""
    http_status: int = 500
    code: str = 'INTERNAL_ERROR'

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def to_response_dict(self) -> dict:
        return {
            'code': self.code,
            'message': self.message,
        }


# ── 三种基础类型 ──────────────────────────────────────────────────────────────

class ValidationError(BaseAppException):
    """输入格式不对（NPI 不是 10 位、MRN 格式错误等）"""
    http_status = 400
    code = 'VALIDATION_ERROR'

    def to_response_dict(self) -> dict:
        return {
            'code': self.code,
            'message': 'Validation failed.',
            'details': [self.message],
        }


class BlockError(BaseAppException):
    """业务规则强制阻止，不可跳过（同 NPI 不同 Provider 名字）"""
    http_status = 409
    code = 'BLOCK_ERROR'

    def to_response_dict(self) -> dict:
        return {
            'code': self.code,
            'message': self.message,
            'warnings': [],
        }


class WarningException(BaseAppException):
    """
    业务警告，用户确认后可继续。

    warnings: list  —— 具体原因列表，可以同时有多条
    data: dict      —— 可选，返回给前端的结构化数据
    """
    http_status = 409
    code = 'DUPLICATE_WARNING'

    def __init__(self, warnings: list, *, data: dict | None = None):
        self.warnings = warnings
        self.data = data or {}
        # message 保持泛化，不含 PHI，具体信息在 warnings list 里
        super().__init__('Potential duplicate detected. Please review and confirm.')

    def to_response_dict(self) -> dict:
        return {
            'code': self.code,
            'message': self.message,
            'warnings': self.warnings,
            'requires_confirmation': True,
            'data': self.data,
        }


# ── 具体业务异常（继承上面三类，只覆盖 code） ─────────────────────────────────

class DuplicateProviderError(BlockError):
    code = 'DUPLICATE_PROVIDER'


class PatientDataMismatchWarning(WarningException):
    code = 'PATIENT_DATA_MISMATCH'


class DuplicateOrderError(BlockError):
    code = 'DUPLICATE_ORDER'


class DuplicateOrderWarning(WarningException):
    code = 'DUPLICATE_ORDER_WARNING'
