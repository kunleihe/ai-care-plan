import re
from abc import ABC, abstractmethod
from typing import Any

from core.exceptions import ValidationError
from core.internal_types import InternalOrder


class BaseIntakeAdapter(ABC):
    """
    所有数据来源的 Adapter 都必须继承这个基类。
    数据流：raw → parse() → dict → transform() → InternalOrder → validate()
    """

    @abstractmethod
    def parse(self, raw: Any) -> dict:
        """
        处理「格式」差异：JSON string、嵌套结构、字段编码等。
        职责：把原始输入变成一个 Python dict。
        不做业务规则验证。
        """
        ...

    @abstractmethod
    def transform(self, parsed: dict) -> InternalOrder:
        """
        处理「语义」差异：字段重命名、类型转换（str → date）等。
        职责：把 dict 映射成 InternalOrder。
        dob 的 string-to-date 解析在这里做，不在 parse() 里做。
        """
        ...

    def validate(self, order: InternalOrder) -> None:
        """
        默认执行所有 adapter 共用的业务规则验证。
        子类如果有来源特有规则，可以 override 这个方法并在里面先调 super().
        不合法时 raise ValidationError，不返回 bool。
        不修改 order 本身。
        """
        label = self._source_label()

        if not re.fullmatch(r"\d{10}", order.provider.npi):
            raise ValidationError(
                f"[{label}] NPI must be exactly 10 digits, got: '{order.provider.npi}'"
            )

        if not re.fullmatch(r"\d{6}", order.patient.mrn):
            raise ValidationError(
                f"[{label}] MRN must be exactly 6 digits, got: '{order.patient.mrn}'"
            )

        if not re.fullmatch(r"[A-Z]\d{2}(\.\d{1,4})?", order.diagnosis, re.IGNORECASE):
            raise ValidationError(
                f"[{label}] Invalid ICD-10 code: '{order.diagnosis}'"
            )

        if not order.patient.first_name or not order.patient.last_name:
            raise ValidationError(
                f"[{label}] Patient first name and last name are required."
            )

        if not order.medication:
            raise ValidationError(f"[{label}] Medication name is required.")

    def process(self, raw: Any) -> InternalOrder:
        """
        模板方法：把三步串起来。子类不应该重写这个方法。
        调用方只需要 adapter.process(raw_data)，不用关心内部三步。
        """
        parsed = self.parse(raw)
        order = self.transform(parsed)
        self.validate(order)
        return order

    def _source_label(self) -> str:
        source = getattr(self, "SOURCE", "")
        if not isinstance(source, str) or not source.strip():
            return self.__class__.__name__
        return source
