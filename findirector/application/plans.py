"""Интерфейс хранилища (DIP) и прикладные операции с сохранёнными планами."""
import uuid
from dataclasses import dataclass
from typing import Protocol

from findirector.domain import Plan

from .forecast import Comparison, Forecast, ForecastService


@dataclass(frozen=True)
class PlanSummary:
    id: str
    name: str


class PlanNotFoundError(LookupError):
    def __init__(self, plan_id: str):
        self.plan_id = plan_id
        super().__init__(f"План не найден: {plan_id}")


class RepositoryError(RuntimeError):
    """Сбой хранилища; данные плана при этом не изменены."""


class PlanRepository(Protocol):
    """Реализуется в Infrastructure (ЛР4-А1)."""

    def save(self, plan: Plan) -> None: ...
    def list(self) -> list[PlanSummary]: ...
    def get(self, plan_id: str) -> Plan: ...   # PlanNotFoundError, если нет


def new_plan_id() -> str:
    return str(uuid.uuid4())


class PlanService:
    def __init__(self, repository: PlanRepository, forecasts: ForecastService | None = None):
        self._repository = repository
        self._forecasts = forecasts or ForecastService()

    def save(self, plan: Plan) -> None:
        plan.check()                         # недопустимый план не сохраняется (П-Ф5)
        self._repository.save(plan)

    def list_plans(self) -> list[PlanSummary]:
        return self._repository.list()

    def open_plan(self, plan_id: str) -> Plan:
        return self._repository.get(plan_id)

    def forecast(self, plan: Plan) -> Forecast:
        return self._forecasts.forecast(plan)

    def compare(self, left: Plan, right: Plan) -> Comparison:
        return self._forecasts.compare(left, right)

    def compare_saved(self, left_id: str, right_id: str) -> Comparison:
        return self._forecasts.compare(self.open_plan(left_id), self.open_plan(right_id))
