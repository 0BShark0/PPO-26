"""ЛР3-Т1, ЛР3-Т2: прогноз трёх месяцев и сравнение (примеры ПР1–ПР8 из requirements.md)."""
import unittest
from dataclasses import replace
from decimal import Decimal as D

from findirector.application import ForecastService
from findirector.domain import PlanValidationError

from .helpers import kopecks_plan, month, seasonal_plan, training
from findirector.domain import Plan


def column(forecast, attr):
    return [getattr(m.report, attr) for m in forecast.months]


class ForecastExamplesTest(unittest.TestCase):
    def setUp(self):
        self.service = ForecastService()

    def assert_totals(self, f, profit, c3, d3, need):
        t = f.totals
        self.assertEqual((t.total_profit, t.closing_cash, t.closing_receivables, t.funding_need),
                         (D(profit), D(c3), D(d3), D(need)))

    def test_deferred_payment_example(self):                     # ПР1, A = 0%
        f = self.service.forecast(training(0))
        self.assertEqual(column(f, "cash_receipts"), [0, 150000, 150000])
        self.assertEqual(column(f, "closing_cash"), [-70000, -40000, -10000])
        self.assertEqual(column(f, "closing_receivables"), [150000] * 3)
        self.assertEqual(column(f, "revenue"), [150000] * 3)
        self.assertEqual(column(f, "margin"), [100000] * 3)
        self.assertEqual(column(f, "expenses"), [120000] * 3)
        self.assertEqual(column(f, "profit"), [30000] * 3)
        self.assert_totals(f, 90000, -10000, 150000, 70000)

    def test_half_payment_example(self):                         # ПР2, A = 50% (= ручной расчёт ЛР2-Т1)
        f = self.service.forecast(training(50))
        self.assertEqual(column(f, "cash_receipts"), [75000, 150000, 150000])
        self.assertEqual(column(f, "closing_cash"), [5000, 35000, 65000])
        self.assertEqual(column(f, "closing_receivables"), [75000] * 3)
        self.assert_totals(f, 90000, 65000, 75000, 0)

    def test_full_payment_example(self):                         # ПР3, A = 100%
        f = self.service.forecast(training(100))
        self.assertEqual(column(f, "cash_receipts"), [150000] * 3)
        self.assertEqual(column(f, "closing_cash"), [80000, 110000, 140000])
        self.assert_totals(f, 90000, 140000, 0, 0)

    def test_no_sales_example(self):                             # ПР4
        plan = Plan.create("none", "Без продаж", D(50000), [month(q=0, a=100)] * 3)
        f = self.service.forecast(plan)
        self.assertEqual(column(f, "revenue"), [0] * 3)
        self.assertEqual(column(f, "margin"), [0] * 3)
        self.assertEqual(column(f, "profit"), [-70000] * 3)
        self.assertEqual(column(f, "closing_cash"), [-20000, -90000, -160000])
        self.assert_totals(f, -210000, -160000, 0, 160000)

    def test_zero_closing_cash_example(self):                    # ПР5
        f = self.service.forecast(training(0, cash="120000"))
        self.assertEqual(column(f, "closing_cash"), [0, 30000, 60000])
        self.assertEqual(f.months[0].report.funding_gap, 0)
        self.assert_totals(f, 90000, 60000, 150000, 0)

    def test_invalid_percent_example(self):                      # ПР6
        with self.assertRaises(PlanValidationError) as ctx:
            Plan.create("bad", "Ошибка", D(50000), [month(), month(a=101), month()])
        self.assertEqual(ctx.exception.fields(), {"months[2].paid_now_percent"})

    def test_kopecks_example(self):                              # ПР8
        f = self.service.forecast(kopecks_plan())
        r = f.months[0].report
        self.assertEqual((r.revenue, r.margin, r.expenses, r.profit, r.cash_receipts, r.closing_receivables),
                         (D("999.99"), D("699.69"), D("800.85"), D("199.14"), D("330.00"), D("669.99")))
        self.assertEqual(column(f, "closing_cash"), [D("529.16"), D("728.30"), D("927.44")])
        self.assert_totals(f, "597.42", "927.44", "669.99", 0)

    def test_months_with_different_parameters(self):             # ЛР3-Т1: разные месяцы
        f = self.service.forecast(seasonal_plan())
        self.assertEqual(column(f, "revenue"), [60000, 192000, 240000])
        self.assertEqual(column(f, "margin"), [40000, 126000, 160000])
        self.assertEqual(column(f, "profit"), [-30000, 56000, 85000])
        self.assertEqual(column(f, "cash_receipts"), [0, 156000, 336000])
        self.assertEqual(column(f, "closing_cash"), [-70000, -50000, 131000])
        self.assertEqual(column(f, "closing_receivables"), [60000, 96000, 0])
        self.assert_totals(f, 111000, 131000, 0, 70000)


class ForecastBehaviourTest(unittest.TestCase):
    def setUp(self):
        self.service = ForecastService()

    def test_receivables_are_carried_to_next_month(self):        # ЛР3-Т2
        f = self.service.forecast(training(50))
        for prev, cur in zip(f.months, f.months[1:]):
            # поступления месяца = его оплата сразу + задолженность предыдущего месяца
            paid_now = cur.report.revenue - cur.report.closing_receivables
            self.assertEqual(cur.report.cash_receipts, paid_now + prev.report.closing_receivables)

    def test_cash_is_carried_and_forecast_continues_after_negative(self):   # П-Б5, П-Б6
        f = self.service.forecast(training(0))
        self.assertLess(f.months[0].report.closing_cash, 0)
        self.assertEqual(len(f.months), 3)
        for prev, cur in zip(f.months, f.months[1:]):
            r = cur.report
            self.assertEqual(r.closing_cash, prev.report.closing_cash + r.cash_receipts - r.expenses)

    def test_funding_need_is_max_not_sum(self):                  # ЛР3-Ф2
        f = self.service.forecast(training(0))
        gaps = [m.report.funding_gap for m in f.months]
        self.assertEqual(sum(gaps), 120000)
        self.assertEqual(f.totals.funding_need, 70000)

    def test_last_month_receivables_are_not_added_to_cash(self):
        f = self.service.forecast(training(0))
        self.assertEqual(f.totals.closing_cash, -10000)
        self.assertEqual(f.totals.closing_receivables, 150000)

    def test_extra_funding_lifts_every_month_equally(self):
        base = column(self.service.forecast(training(0)), "closing_cash")
        lifted = column(self.service.forecast(training(0, cash="120000")), "closing_cash")
        self.assertEqual([b + 70000 for b in base], lifted)
        self.assertEqual(min(lifted), 0)

    def test_repeated_calculation_starts_from_plan_inputs(self):  # П-Ф6
        plan = training(50)
        first = self.service.forecast(plan)
        self.service.forecast(training(0))
        self.assertEqual(first, self.service.forecast(plan))

    def test_input_plan_is_not_changed(self):
        plan = training(50)
        snapshot = replace(plan)
        self.service.forecast(plan)
        self.service.compare(plan, training(0))
        self.assertEqual(plan, snapshot)
        self.assertEqual(plan.opening_cash, D(50000))

    def test_changed_plan_recalculates(self):                    # ПР7, вторая часть
        before = self.service.forecast(training(50, plan_id="p"))
        after = self.service.forecast(training(100, plan_id="p"))
        self.assertNotEqual(before.totals, after.totals)
        self.assertEqual((after.totals.closing_cash, after.totals.closing_receivables), (140000, 0))


class CompareTest(unittest.TestCase):
    def test_compare_two_plans(self):                            # ПР7, ЛР3-Ф3
        c = ForecastService().compare(training(0, name="Всё через месяц"),
                                      training(50, name="Половина сразу"))
        self.assertEqual((c.left.plan_name, c.right.plan_name), ("Всё через месяц", "Половина сразу"))
        self.assertEqual(c.left.totals.total_profit, c.right.totals.total_profit)
        self.assertEqual((c.left.totals.closing_cash, c.right.totals.closing_cash), (-10000, 65000))
        self.assertEqual((c.left.totals.closing_receivables, c.right.totals.closing_receivables), (150000, 75000))
        self.assertEqual((c.left.totals.funding_need, c.right.totals.funding_need), (70000, 0))

    def test_plans_are_independent(self):
        service = ForecastService()
        alone = service.forecast(training(50))
        self.assertEqual(service.compare(training(0), training(50)).right, alone)


if __name__ == "__main__":
    unittest.main()
