from typing import Type

from core.exceptions import ValidationError

from .base import BaseIntakeAdapter
from .clinic_b import ClinicBAdapter
from .hospital_northhill import NorthHillHospitalAdapter
from .manual_form import ManualFormAdapter

AdapterClass = Type[BaseIntakeAdapter]

_ADAPTER_REGISTRY: dict[str, AdapterClass] = {}


def register_adapter(adapter_cls: AdapterClass) -> None:
    """
    Register an adapter class by its SOURCE.

    新增数据源时：
    1. 新建一个继承 BaseIntakeAdapter 的 Adapter
    2. 给它定义唯一的 SOURCE
    3. 在这里调用 register_adapter(NewAdapter)
    """
    source = getattr(adapter_cls, "SOURCE", "")
    if not isinstance(source, str) or not source.strip():
        raise ValueError(
            f"{adapter_cls.__name__} must define a non-empty SOURCE string."
        )

    _ADAPTER_REGISTRY[source] = adapter_cls


def get_adapter(source: str) -> BaseIntakeAdapter:
    """
    Factory function that returns the adapter instance for the given source.
    """
    adapter_cls = _ADAPTER_REGISTRY.get(source)
    if adapter_cls is None:
        supported_sources = ", ".join(sorted(_ADAPTER_REGISTRY)) or "none"
        raise ValidationError(
            f"Unsupported source '{source}'. Supported sources: {supported_sources}."
        )

    return adapter_cls()


register_adapter(ManualFormAdapter)
register_adapter(ClinicBAdapter)
register_adapter(NorthHillHospitalAdapter)

__all__ = [
    "BaseIntakeAdapter",
    "ClinicBAdapter",
    "ManualFormAdapter",
    "NorthHillHospitalAdapter",
    "get_adapter",
    "register_adapter",
]
