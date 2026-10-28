"""ЛР3-Т3: отклонение недопустимых планов (П-Б8, П-Б10, П-Ф5)."""
import unittest
from decimal import Decimal as D

from findirector.domain import MonthPlan, Plan, PlanMonth, PlanValidationError

from .helpers import month, training


def months(*numbers):
    return tuple(PlanMonth(n, MonthPlan(5, D(30000), D(10000), D(70000), 50)) for n in numbers)


class PlanValidationTest(unittest.TestCase):
    def assert_fields(self, fields, build):
        with self.assertRaises(PlanValidationError) as ctx:
            build()
        self.assertEqual(ctx.exception.fields(), set(fields))

    def test_valid_training_plan(self):
        plan = training(50)
        self.assertEqual([m.number for m in plan.months], [1, 2, 3])
        self.assertEqual(plan.opening_cash, D("50000.00"))

    def test_negative_opening_cash_is_rejected(self):
        self.assert_fields({"opening_cash"}, lambda: training(50, cash="-1"))

    def test_fractional_kopeck_opening_cash_is_rejected(self):
        self.assert_fields({"opening_cash"}, lambda: training(50, cash="0.001"))

    def test_empty_name_is_rejected(self):
        self.assert_fields({"name"}, lambda: Plan("x", "   ", D(0), months(1, 2, 3)))

    def test_empty_id_is_rejected(self):
        self.assert_fields({"id"}, lambda: Plan("", "План", D(0), months(1, 2, 3)))

    def test_two_months_are_rejected(self):
        self.assert_fields({"months"}, lambda: Plan("x", "План", D(0), months(1, 2)))

    def test_four_months_are_rejected(self):
        self.assert_fields({"months"}, lambda: Plan("x", "План", D(0), months(1, 2, 3, 4)))

    def test_duplicate_month_number_is_rejected(self):
        self.assert_fields({"months"}, lambda: Plan("x", "План", D(0), months(1, 2, 2)))

    def test_wrong_month_numbers_are_rejected(self):
        self.assert_fields({"months"}, lambda: Plan("x", "План", D(0), months(0, 1, 2)))

    def test_months_are_ordered_by_number(self):
        plan = Plan("x", "План", D(0), months(3, 1, 2))
        self.assertEqual([m.number for m in plan.months], [1, 2, 3])

    def test_all_errors_are_reported_with_field_and_reason(self):        # П-Ф5
        with self.assertRaises(PlanValidationError) as ctx:
            Plan.create("x", "", D(-5), [month(), month(a=101), {**month(q=-1), "price": "abc"}])
        self.assertEqual(ctx.exception.fields(), {
            "name", "opening_cash", "months[2].paid_now_percent", "months[3].quantity", "months[3].price"})
        reasons = {e.field: e.message for e in ctx.exception.errors}
        self.assertIn("от 0 до 100", reasons["months[2].paid_now_percent"])

    def test_price_below_unit_cost_is_allowed(self):                     # П-Б8
        Plan.create("x", "Убыточный", D(0), [month(p="10", v="15")] * 3)

    def test_plan_is_immutable(self):
        plan = training(50)
        with self.assertRaises(AttributeError):
            plan.name = "Другое"


if __name__ == "__main__":
    unittest.main()
