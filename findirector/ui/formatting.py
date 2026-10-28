"""Разбор ввода и форматирование чисел для UI. Формул здесь нет."""
import re
from decimal import Decimal, InvalidOperation

NBSP = " "

FIELD_LABELS = {
    "id": "Идентификатор",
    "name": "Название",
    "opening_cash": "Начальные деньги",
    "months": "Месяцы плана",
    "quantity": "количество услуг (Q)",
    "price": "цена (P)",
    "unit_cost": "переменные затраты (V)",
    "fixed_costs": "постоянные расходы (F)",
    "paid_now_percent": "оплата сразу (A)",
}


def field_label(field: str) -> str:
    """'months[2].paid_now_percent' или 'm2_paid_now_percent' -> 'Месяц 2, оплата сразу (A)'."""
    match = re.fullmatch(r"months\[(\d+)\]\.(\w+)|m(\d+)_(\w+)", field)
    if match:
        number, name = match.group(1) or match.group(3), match.group(2) or match.group(4)
        return f"Месяц {number}, {FIELD_LABELS.get(name, name)}"
    return FIELD_LABELS.get(field, field)


def parse_money(text: str):
    """'30 000,50' -> Decimal('30000.50'). При ошибке возвращает строку как есть —
    Domain сообщит причину (поле и текст ошибки формирует одно место)."""
    cleaned = (text or "").strip().replace(" ", "").replace(NBSP, "").replace(",", ".")
    try:
        return Decimal(cleaned) if cleaned else text
    except InvalidOperation:
        return text


def parse_int(text: str):
    cleaned = (text or "").strip().replace(" ", "").replace(NBSP, "")
    try:
        return int(cleaned)
    except ValueError:
        return text


def fmt_money(amount: Decimal) -> str:
    """Decimal('-70000') -> '−70 000,00'."""
    text = f"{abs(amount):,.2f}".replace(",", NBSP).replace(".", ",")
    return ("−" if amount < 0 else "") + text


def input_money(amount: Decimal) -> str:
    """Значение для поля ввода: '30000' или '333,33'."""
    text = f"{amount:.2f}"
    return text[:-3] if text.endswith(".00") else text.replace(".", ",")
