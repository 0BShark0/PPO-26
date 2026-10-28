"""Денежные значения: Decimal с точностью до копейки (П-Б8, П-Б9)."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .errors import FieldError

KOPECK = Decimal("0.01")
ZERO = Decimal("0.00")


def round_money(amount: Decimal) -> Decimal:
    """Округление до копейки; ROUND_HALF_UP в Python = MidpointRounding.AwayFromZero в .NET."""
    return amount.quantize(KOPECK, rounding=ROUND_HALF_UP)


def check_money(value, field: str, allow_negative: bool = False) -> FieldError | None:
    """Возвращает ошибку поля или None. float запрещён: двоичная дробь теряет копейки."""
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return FieldError(field, "ожидается сумма в рублях, например 30000 или 30000,50")
    amount = Decimal(value)
    if not amount.is_finite():
        return FieldError(field, "ожидается конечная сумма")
    if not allow_negative and amount < 0:
        return FieldError(field, "сумма не может быть отрицательной")
    try:
        exact = amount.quantize(KOPECK) == amount
    except InvalidOperation:
        exact = False
    if not exact:
        return FieldError(field, "сумма задаётся с точностью до копейки")
    return None


def to_money(value) -> Decimal:
    """Нормализует уже проверенное значение к виду 0.00."""
    return Decimal(value).quantize(KOPECK)
