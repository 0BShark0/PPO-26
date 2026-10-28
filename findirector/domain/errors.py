"""Ошибки проверки ввода: какое поле и почему (П-Ф5)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldError:
    field: str     # машинное имя: "name", "opening_cash", "months[2].paid_now_percent"
    message: str   # причина по-русски


class PlanValidationError(ValueError):
    """План или месяц нарушает П-Б8/П-Б10. Содержит все найденные ошибки сразу."""

    def __init__(self, errors: list[FieldError]):
        self.errors = list(errors)
        super().__init__("; ".join(f"{e.field}: {e.message}" for e in self.errors))

    def fields(self) -> set[str]:
        return {e.field for e in self.errors}
