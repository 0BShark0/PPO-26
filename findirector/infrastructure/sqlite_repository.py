"""SQLite-реализация PlanRepository (ЛР4). Денежные входы — целые копейки."""
import sqlite3
from contextlib import closing
from decimal import Decimal

from findirector.application import PlanNotFoundError, PlanSummary, RepositoryError
from findirector.domain import Plan, PlanMonth, MonthPlan

SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    id               TEXT    PRIMARY KEY,
    name             TEXT    NOT NULL CHECK (trim(name) <> ''),
    opening_cash_kop INTEGER NOT NULL CHECK (opening_cash_kop >= 0)
);
CREATE TABLE IF NOT EXISTS month_plans (
    plan_id          TEXT    NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    month_number     INTEGER NOT NULL CHECK (month_number IN (1, 2, 3)),
    quantity         INTEGER NOT NULL CHECK (quantity >= 0),
    price_kop        INTEGER NOT NULL CHECK (price_kop >= 0),
    unit_cost_kop    INTEGER NOT NULL CHECK (unit_cost_kop >= 0),
    fixed_costs_kop  INTEGER NOT NULL CHECK (fixed_costs_kop >= 0),
    paid_now_percent INTEGER NOT NULL CHECK (paid_now_percent BETWEEN 0 AND 100),
    PRIMARY KEY (plan_id, month_number)
);
"""


def to_kopecks(amount: Decimal) -> int:
    return int(amount * 100)          # amount уже проверен Domain: ровно до копейки


def from_kopecks(kopecks: int) -> Decimal:
    return (Decimal(kopecks) / 100).quantize(Decimal("0.01"))


class SqlitePlanRepository:
    """Создаёт схему при первом использовании. Каждое действие — своё подключение."""

    def __init__(self, path: str):
        self._path = path
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def save(self, plan: Plan) -> None:
        plan.check()
        try:
            with closing(self._connect()) as conn, conn:     # одна транзакция: commit или rollback
                conn.execute(
                    "INSERT INTO plans (id, name, opening_cash_kop) VALUES (?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET name = excluded.name, "
                    "opening_cash_kop = excluded.opening_cash_kop",
                    (plan.id, plan.name, to_kopecks(plan.opening_cash)))
                conn.execute("DELETE FROM month_plans WHERE plan_id = ?", (plan.id,))
                conn.executemany(
                    "INSERT INTO month_plans (plan_id, month_number, quantity, price_kop, "
                    "unit_cost_kop, fixed_costs_kop, paid_now_percent) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [(plan.id, m.number, m.params.quantity, to_kopecks(m.params.price),
                      to_kopecks(m.params.unit_cost), to_kopecks(m.params.fixed_costs),
                      m.params.paid_now_percent) for m in plan.months])
        except sqlite3.Error as exc:
            raise RepositoryError(f"Не удалось сохранить план: {exc}") from exc

    def list(self) -> list[PlanSummary]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT id, name FROM plans ORDER BY name, id").fetchall()
        return [PlanSummary(*row) for row in rows]

    def get(self, plan_id: str) -> Plan:
        with closing(self._connect()) as conn:
            head = conn.execute("SELECT id, name, opening_cash_kop FROM plans WHERE id = ?",
                                (plan_id,)).fetchone()
            if head is None:
                raise PlanNotFoundError(plan_id)
            rows = conn.execute(
                "SELECT month_number, quantity, price_kop, unit_cost_kop, fixed_costs_kop, "
                "paid_now_percent FROM month_plans WHERE plan_id = ? ORDER BY month_number",
                (plan_id,)).fetchall()
        months = tuple(PlanMonth(n, MonthPlan(q, from_kopecks(p), from_kopecks(v), from_kopecks(f), a))
                       for n, q, p, v, f, a in rows)
        return Plan(head[0], head[1], from_kopecks(head[2]), months)
