"""План на три месяца (П-Б10) и итоги прогноза (П-Б7)."""
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from .errors import FieldError, PlanValidationError
from .money import ZERO, check_money, to_money
from .month import MonthPlan, MonthReport

MONTH_NUMBERS = (1, 2, 3)
MONTH_FIELDS = ("quantity", "price", "unit_cost", "fixed_costs", "paid_now_percent")


@dataclass(frozen=True)
class PlanMonth:
    number: int
    params: MonthPlan


@dataclass(frozen=True)
class Plan:
    """Постоянный id, непустое название, деньги ≥ 0 и ровно месяцы 1, 2, 3."""
    id: str
    name: str
    opening_cash: Decimal
    months: tuple[PlanMonth, ...]

    def __post_init__(self):
        object.__setattr__(self, "months", tuple(self.months))
        self.check()
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "opening_cash", to_money(self.opening_cash))
        object.__setattr__(self, "months", tuple(sorted(self.months, key=lambda m: m.number)))

    def check(self) -> None:
        """Проверяет П-Б8 и П-Б10; бросает PlanValidationError со всеми ошибками."""
        errors: list[FieldError] = []
        if not isinstance(self.id, str) or not self.id.strip():
            errors.append(FieldError("id", "у плана должен быть идентификатор"))
        if not isinstance(self.name, str) or not self.name.strip():
            errors.append(FieldError("name", "название не может быть пустым"))
        if e := check_money(self.opening_cash, "opening_cash"):
            errors.append(e)
        numbers = [m.number for m in self.months if isinstance(m, PlanMonth)]
        if len(numbers) != len(self.months):
            errors.append(FieldError("months", "каждый месяц должен быть PlanMonth"))
        elif len(set(numbers)) != len(numbers):
            errors.append(FieldError("months", "номер месяца в плане должен быть уникальным"))
        elif sorted(numbers) != list(MONTH_NUMBERS):
            errors.append(FieldError("months", "план должен содержать ровно месяцы 1, 2 и 3"))
        if errors:
            raise PlanValidationError(errors)

    def month(self, number: int) -> MonthPlan:
        return next(m.params for m in self.months if m.number == number)

    @classmethod
    def create(cls, plan_id: str, name: str, opening_cash,
               months: Sequence[Mapping]) -> "Plan":
        """Собирает план из словарей {quantity, price, ...} для месяцев 1..3.

        Собирает ошибки всех полей сразу; имя поля месяца: "months[2].price".
        """
        errors: list[FieldError] = []
        plan_months: list[PlanMonth] = []
        for number, data in enumerate(months, start=1):
            try:
                plan_months.append(PlanMonth(number, MonthPlan(**{f: data.get(f) for f in MONTH_FIELDS})))
            except PlanValidationError as exc:
                errors += [FieldError(f"months[{number}].{e.field}", e.message) for e in exc.errors]
        try:
            # Если какой-то месяц невалиден, проверяем остальное с заглушками, чтобы показать все ошибки.
            filler = [PlanMonth(n, MonthPlan(0, ZERO, ZERO, ZERO, 0))
                      for n in range(1, len(months) + 1)] if errors else plan_months
            plan = cls(plan_id, name, opening_cash, tuple(filler))
        except PlanValidationError as exc:
            errors = [e for e in exc.errors] + errors
            plan = None
        if errors:
            raise PlanValidationError(errors)
        return plan


@dataclass(frozen=True)
class PlanTotals:
    """Итоги П-Б7."""
    total_profit: Decimal          # сумма прибыли трёх месяцев
    closing_cash: Decimal          # C3
    closing_receivables: Decimal   # D3 — показывается отдельно от денег
    funding_need: Decimal          # max(0, −min(C1, C2, C3)) — максимум, а не сумма дефицитов

    @classmethod
    def from_reports(cls, reports: Iterable[MonthReport]) -> "PlanTotals":
        reports = list(reports)
        if not reports:
            raise ValueError("нужен хотя бы один месяц")
        return cls(
            total_profit=sum((r.profit for r in reports), ZERO),
            closing_cash=reports[-1].closing_cash,
            closing_receivables=reports[-1].closing_receivables,
            funding_need=max(ZERO, -min(r.closing_cash for r in reports)),
        )
