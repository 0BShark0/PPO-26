"""Построители контрольных планов из docs/requirements.md."""
from decimal import Decimal as D

from findirector.domain import Plan


def month(q=5, p="30000", v="10000", f="70000", a=50) -> dict:
    return {"quantity": q, "price": D(p), "unit_cost": D(v), "fixed_costs": D(f), "paid_now_percent": a}


def training(a: int, cash="50000", plan_id=None, name=None) -> Plan:
    """Учебный сценарий: Q = 5, P = 30 000, V = 10 000, F = 70 000 во всех месяцах."""
    return Plan.create(plan_id or f"training-{a}", name or f"Учебный {a}%", D(cash), [month(a=a)] * 3)


def kopecks_plan(plan_id="kopecks", name="Копейки") -> Plan:
    """ПР8."""
    return Plan.create(plan_id, name, D("1000.01"), [month(3, "333.33", "100.10", "500.55", 33)] * 3)


def seasonal_plan() -> Plan:
    """План с разными параметрами месяцев (ЛР3-Т1)."""
    return Plan.create("seasonal", "Сезонный", D("20000"), [
        month(2, "30000", "10000", "70000", 0),
        month(6, "32000", "11000", "70000", 50),
        month(8, "30000", "10000", "75000", 100),
    ])
