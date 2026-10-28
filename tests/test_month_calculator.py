"""Ядро одного месяца: контрольные примеры К1–К10 стартового комплекта + маржинальный доход."""
import unittest
from decimal import Decimal as D

from findirector.domain import MonthCalculator, MonthPlan, PlanValidationError


def example(percent: int) -> MonthPlan:
    return MonthPlan(5, D(30000), D(10000), D(70000), percent)


class MonthCalculatorTest(unittest.TestCase):
    def setUp(self):
        self.calc = MonthCalculator()

    def test_full_payment_produces_profit_and_cash(self):                     # К1
        r = self.calc.calculate(example(100), D(50000), D(0))
        self.assertEqual((r.revenue, r.expenses, r.profit, r.closing_cash, r.closing_receivables),
                         (150000, 120000, 30000, 80000, 0))

    def test_deferred_payment_can_leave_profit_but_no_cash(self):             # К2
        r = self.calc.calculate(example(0), D(50000), D(0))
        self.assertEqual((r.profit, r.cash_receipts, r.closing_cash, r.funding_gap, r.closing_receivables),
                         (30000, 0, -70000, 70000, 150000))

    def test_half_payment_avoids_the_funding_gap(self):                       # К3
        r = self.calc.calculate(example(50), D(50000), D(0))
        self.assertEqual((r.cash_receipts, r.closing_cash, r.closing_receivables, r.profit),
                         (75000, 5000, 75000, 30000))

    def test_opening_receivables_are_collected_without_adding_revenue(self):  # К4
        r = self.calc.calculate(example(0), D(-70000), D(150000))
        self.assertEqual((r.revenue, r.cash_receipts, r.profit, r.closing_cash, r.closing_receivables),
                         (150000, 150000, 30000, -40000, 150000))

    def test_half_kopeck_rounds_payment_but_preserves_total_revenue(self):    # К5, П-Б9
        r = self.calc.calculate(MonthPlan(1, D("0.05"), D(0), D(0), 50), D(0), D(0))
        self.assertEqual((r.cash_receipts, r.closing_receivables, r.revenue), (D("0.03"), D("0.02"), D("0.05")))

    def test_no_sales_still_has_fixed_costs(self):                            # К6
        r = self.calc.calculate(MonthPlan(0, D(30000), D(10000), D(70000), 100), D(50000), D(0))
        self.assertEqual((r.revenue, r.profit, r.closing_cash), (0, -70000, -20000))

    def test_exactly_zero_cash_is_not_a_funding_gap(self):                    # К7
        r = self.calc.calculate(example(0), D(120000), D(0))
        self.assertEqual((r.closing_cash, r.funding_gap), (0, 0))

    def test_invalid_inputs_are_rejected(self):                               # К8
        for args in [(-1, D(1), D(0), D(0), 50), (1, D(-1), D(0), D(0), 50), (1, D(1), D(-1), D(0), 50),
                     (1, D(1), D(0), D(-1), 50), (1, D(1), D(0), D(0), -1), (1, D(1), D(0), D(0), 101),
                     (1, D("0.001"), D(0), D(0), 50), (1, 1.5, D(0), D(0), 50), (1.0, D(1), D(0), D(0), 50)]:
            with self.subTest(args=args), self.assertRaises(PlanValidationError):
                MonthPlan(*args)
        with self.assertRaises(PlanValidationError):
            self.calc.calculate(example(50), D(0), D(-1))
        with self.assertRaises(PlanValidationError):
            self.calc.calculate(example(50), D("0.001"), D(0))

    def test_price_below_unit_cost_produces_a_valid_loss(self):               # К9
        r = self.calc.calculate(MonthPlan(2, D(10), D(15), D(3), 100), D(100), D(0))
        self.assertEqual((r.revenue, r.expenses, r.profit, r.closing_cash, r.closing_receivables, r.funding_gap),
                         (20, 33, -13, 87, 0, 0))

    def test_repeated_calculation_does_not_accumulate_or_change_input(self):  # К10
        plan = example(50)
        first = self.calc.calculate(plan, D(50000), D(0))
        self.calc.calculate(example(0), D(50000), D(0))
        self.assertEqual(first, self.calc.calculate(plan, D(50000), D(0)))
        self.assertEqual(plan, example(50))

    # Маржинальный доход П-Б1 = R − Q × V
    def test_margin_positive(self):
        r = self.calc.calculate(example(50), D(50000), D(0))
        self.assertEqual(r.margin, 100000)                 # 150 000 − 50 000
        self.assertEqual(r.margin - r.fixed_costs, r.profit)

    def test_margin_negative_when_price_below_unit_cost(self):
        r = self.calc.calculate(MonthPlan(2, D(10), D(15), D(3), 100), D(100), D(0))
        self.assertEqual(r.margin, -10)                    # 20 − 30


if __name__ == "__main__":
    unittest.main()
