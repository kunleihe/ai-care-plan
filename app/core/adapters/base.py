from abc import ABC, abstractmethod
from typing import Any

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

    @abstractmethod
    def validate(self, order: InternalOrder) -> None:
        """
        验证转换后的数据是否符合业务规则。
        不合法时 raise ValidationError，不返回 bool。
        不修改 order 本身。
        """
        ...

    def process(self, raw: Any) -> InternalOrder:
        """
        模板方法：把三步串起来。子类不应该重写这个方法。
        调用方只需要 adapter.process(raw_data)，不用关心内部三步。
        """
        parsed = self.parse(raw)
        order = self.transform(parsed)
        self.validate(order)
        return order
