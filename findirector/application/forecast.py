"""Прогноз трёх месяцев и сравнение планов (ЛР3-Ф1–Ф3).

Здесь только последовательность расчёта; формулы — в Domain (ЛР3-А1).
"""
from dataclasses import dataclass
from decimal import Decimal

from findirector.domain import MonthCalculator, MonthReport, Plan, PlanTotals


@dataclass(frozen=True)
class MonthResult:
    number: int
    report: MonthReport


@dataclass(frozen=True)
class Forecast:
    plan_id: str
    plan_name: str
    months: tuple[MonthResult, ...]
    totals: PlanTotals


@dataclass(frozen=True)
class Comparison:
    left: Forecast
    right: Forecast


class ForecastService:
    """Без состояния: каждый вызов начинается с исходных данных плана (П-Ф6)."""

    def __init__(self, calculator: MonthCalculator | None = None):
        self._calculator = calculator or MonthCalculator()

    def forecast(self, plan: Plan) -> Forecast:
        if not isinstance(plan, Plan):
            raise TypeError("plan должен быть Plan")
        plan.check()                                   # П-Б8, П-Б10

        cash: Decimal = plan.opening_cash
        receivables = Decimal("0.00")                  # до первого месяца задолженности нет (П-Б4)
        results = []
        for month in plan.months:                      # месяцы 1, 2, 3
            report = self._calculator.calculate(month.params, cash, receivables)
            results.append(MonthResult(month.number, report))
            # П-Б5: конечные C и D становятся начальными; минус не обнуляется (П-Б6)
            cash, receivables = report.closing_cash, report.closing_receivables

        totals = PlanTotals.from_reports(r.report for r in results)   # П-Б7
        return Forecast(plan.id, plan.name, tuple(results), totals)

    def compare(self, left: Plan, right: Plan) -> Comparison:
        """Каждый план считается независимо; входы не меняются (Plan неизменяем)."""
        return Comparison(self.forecast(left), self.forecast(right))
