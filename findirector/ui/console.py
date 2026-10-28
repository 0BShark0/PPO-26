"""Консольная демонстрация (ЛР3): учебный сценарий 0% / 50% / 100% и сравнение."""
import sys
from decimal import Decimal

from findirector.application import Forecast, ForecastService
from findirector.domain import Plan

from .formatting import fmt_money


def training_plan(percent: int, name: str | None = None) -> Plan:
    month = {"quantity": 5, "price": Decimal(30000), "unit_cost": Decimal(10000),
             "fixed_costs": Decimal(70000), "paid_now_percent": percent}
    return Plan.create(f"training-{percent}", name or f"Оплата сразу {percent}%",
                       Decimal(50000), [month] * 3)


def print_forecast(forecast: Forecast, out=sys.stdout) -> None:
    rows = [
        ("Выручка", lambda r: r.revenue),
        ("Маржинальный доход", lambda r: r.margin),
        ("Расходы", lambda r: r.expenses),
        ("Прибыль", lambda r: r.profit),
        ("Поступления", lambda r: r.cash_receipts),
        ("Деньги на конец", lambda r: r.closing_cash),
        ("Задолженность клиентов", lambda r: r.closing_receivables),
    ]
    print(f"\n{forecast.plan_name}", file=out)
    print(f"{'':24}" + "".join(f"{'Месяц ' + str(m.number):>16}" for m in forecast.months), file=out)
    for title, value in rows:
        print(f"{title:24}" + "".join(f"{fmt_money(value(m.report)):>16}" for m in forecast.months),
              file=out)
    for m in forecast.months:
        if m.report.closing_cash < 0:
            print(f"  Месяц {m.number}: не хватает денег {fmt_money(m.report.funding_gap)} руб.", file=out)
    t = forecast.totals
    print(f"Итого прибыль: {fmt_money(t.total_profit)}; деньги C3: {fmt_money(t.closing_cash)}; "
          f"задолженность D3: {fmt_money(t.closing_receivables)}; "
          f"потребность в финансировании: {fmt_money(t.funding_need)}", file=out)


def main(out=sys.stdout) -> None:
    service = ForecastService()
    print("Финдиректор: прибыль есть — денег нет?", file=out)
    print("Старт 50 000 руб.; каждый месяц 5 сайтов по 30 000, V = 10 000, F = 70 000.", file=out)
    for percent in (0, 50, 100):
        print_forecast(service.forecast(training_plan(percent)), out)

    cmp = service.compare(training_plan(0, "Всё через месяц"), training_plan(50, "Половина сразу"))
    print("\nСравнение планов", file=out)
    print(f"{'':30}{cmp.left.plan_name:>18}{cmp.right.plan_name:>18}", file=out)
    for title, attr in (("Прибыль за 3 месяца", "total_profit"), ("Деньги C3", "closing_cash"),
                        ("Задолженность D3", "closing_receivables"),
                        ("Потребность в финансировании", "funding_need")):
        print(f"{title:30}{fmt_money(getattr(cmp.left.totals, attr)):>18}"
              f"{fmt_money(getattr(cmp.right.totals, attr)):>18}", file=out)
