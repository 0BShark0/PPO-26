"""Ядро одного месяца: параметры, расчёт и отчёт (П-Б1–П-Б6, П-Б9)."""
from dataclasses import dataclass
from decimal import Decimal

from .errors import FieldError, PlanValidationError
from .money import ZERO, check_money, round_money, to_money


def _check_int(value, field: str, low: int, high: int | None, message: str) -> FieldError | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return FieldError(field, "ожидается целое число")
    if value < low or (high is not None and value > high):
        return FieldError(field, message)
    return None


@dataclass(frozen=True)
class MonthPlan:
    """Параметры одного месяца. После создания не меняются; ошибки — PlanValidationError."""
    quantity: int            # Q — число услуг
    price: Decimal           # P — цена услуги
    unit_cost: Decimal       # V — переменные затраты на услугу
    fixed_costs: Decimal     # F — постоянные расходы месяца
    paid_now_percent: int    # A — процент оплаты в текущем месяце

    def __post_init__(self):
        errors = [e for e in (
            _check_int(self.quantity, "quantity", 0, None, "количество не может быть отрицательным"),
            check_money(self.price, "price"),
            check_money(self.unit_cost, "unit_cost"),
            check_money(self.fixed_costs, "fixed_costs"),
            _check_int(self.paid_now_percent, "paid_now_percent", 0, 100,
                       "процент оплаты должен быть целым от 0 до 100"),
        ) if e]
        if errors:
            raise PlanValidationError(errors)
        for name in ("price", "unit_cost", "fixed_costs"):
            object.__setattr__(self, name, to_money(getattr(self, name)))


@dataclass(frozen=True)
class MonthReport:
    """Результат месяца; отрицательные деньги показывают нехватку."""
    revenue: Decimal
    variable_costs: Decimal
    fixed_costs: Decimal
    cash_receipts: Decimal
    closing_cash: Decimal
    closing_receivables: Decimal

    @property
    def margin(self) -> Decimal:
        """Маржинальный доход = R − Q × V (П-Б1)."""
        return self.revenue - self.variable_costs

    @property
    def expenses(self) -> Decimal:
        """E = Q × V + F (П-Б2)."""
        return self.variable_costs + self.fixed_costs

    @property
    def profit(self) -> Decimal:
        """Прибыль = R − E (П-Б2)."""
        return self.revenue - self.expenses

    @property
    def funding_gap(self) -> Decimal:
        """Нехватка денег месяца = max(0, −C); при C = 0 дефицита нет (П-Б6)."""
        return max(ZERO, -self.closing_cash)


class MonthCalculator:
    """Чистый расчёт: не читает файлы/БД/время, не меняет вход."""

    def calculate(self, plan: MonthPlan, opening_cash: Decimal,
                  opening_receivables: Decimal) -> MonthReport:
        if not isinstance(plan, MonthPlan):
            raise TypeError("plan должен быть MonthPlan")
        # Прогнозный минус переносится из предыдущего месяца, а не обнуляется.
        errors = [e for e in (
            check_money(opening_cash, "opening_cash", allow_negative=True),
            check_money(opening_receivables, "opening_receivables"),
        ) if e]
        if errors:
            raise PlanValidationError(errors)

        revenue = plan.quantity * plan.price                                  # П-Б1
        variable_costs = plan.quantity * plan.unit_cost                       # П-Б1
        paid_now = round_money(revenue * plan.paid_now_percent / 100)         # П-Б3, П-Б9
        receipts = Decimal(opening_receivables) + paid_now                    # П-Б4
        closing_cash = Decimal(opening_cash) + receipts - variable_costs - plan.fixed_costs  # П-Б5
        receivables = revenue - paid_now                                      # П-Б3: остаток, без округления

        return MonthReport(revenue, variable_costs, plan.fixed_costs,
                           receipts, closing_cash, receivables)
