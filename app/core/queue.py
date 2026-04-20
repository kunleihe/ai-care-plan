from __future__ import annotations

import json
from abc import ABC, abstractmethod


class BaseQueue(ABC):
    @abstractmethod
    def enqueue(self, care_plan_id: int) -> None: ...


class CeleryQueue(BaseQueue):
    def enqueue(self, care_plan_id: int) -> None:
        from .tasks import generate_care_plan
        generate_care_plan.delay(care_plan_id)


class NoQueue(BaseQueue):
    """用于测试：什么都不做。"""
    def enqueue(self, care_plan_id: int) -> None:
        pass
