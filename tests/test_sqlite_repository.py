"""ЛР4-Т1, ЛР4-Т2: интеграционные тесты SQLite-хранилища."""
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from decimal import Decimal as D

from findirector.application import ForecastService, PlanNotFoundError, PlanService
from findirector.domain import Plan, PlanValidationError
from findirector.infrastructure import SqlitePlanRepository

from .helpers import kopecks_plan, month, seasonal_plan, training


class SqliteRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "plans.db")
        self.repo = SqlitePlanRepository(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def reopen(self) -> SqlitePlanRepository:
        """Новый экземпляр хранилища на том же файле = перезапуск приложения."""
        return SqlitePlanRepository(self.path)

    def test_schema_is_created_on_first_run(self):
        with closing(sqlite3.connect(self.path)) as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"plans", "month_plans"} <= tables)

    def test_saved_values_including_kopecks_match_after_reopen(self):     # ЛР4-Т1
        plan = kopecks_plan()
        self.repo.save(plan)
        loaded = self.reopen().get(plan.id)
        self.assertEqual(loaded, plan)
        self.assertEqual(loaded.opening_cash, D("1000.01"))
        self.assertEqual(loaded.month(2).unit_cost, D("100.10"))
        self.assertEqual(loaded.month(3).fixed_costs, D("500.55"))

    def test_forecast_after_open_matches_original(self):                  # ЛР4-Т2
        service = ForecastService()
        for plan in (kopecks_plan(), seasonal_plan(), training(0)):
            self.repo.save(plan)
            self.assertEqual(service.forecast(self.reopen().get(plan.id)), service.forecast(plan))

    def test_resave_updates_all_data_without_duplicates(self):            # ЛР4-Т2, ЛР4-Ф2
        self.repo.save(training(50, plan_id="a", name="План A"))
        other = training(0, plan_id="b", name="План B")
        self.repo.save(other)
        changed = Plan.create("a", "План A (изменён)", D("777.77"),
                              [month(1, "1.11", "0.5", "10", 10), month(2, "2.22", "0", "20", 20),
                               month(3, "3.33", "1", "30", 30)])
        self.repo.save(changed)

        repo = self.reopen()
        self.assertEqual(len(repo.list()), 2)
        self.assertEqual(repo.get("a"), changed)
        self.assertEqual(repo.get("b"), other)
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM month_plans").fetchone()[0], 6)

    def test_list_returns_saved_plans(self):
        self.assertEqual(self.repo.list(), [])
        self.repo.save(training(0, plan_id="b", name="Б"))
        self.repo.save(training(50, plan_id="a", name="А"))
        self.assertEqual([(p.id, p.name) for p in self.repo.list()], [("a", "А"), ("b", "Б")])

    def test_open_missing_plan(self):
        with self.assertRaises(PlanNotFoundError):
            self.repo.get("missing")

    def test_invalid_plan_is_not_saved(self):                             # П-Ф5
        service = PlanService(self.repo)
        plan = training(50)
        object.__setattr__(plan, "name", "")     # обход неизменяемости — имитация испорченного объекта
        with self.assertRaises(PlanValidationError):
            service.save(plan)
        self.assertEqual(self.repo.list(), [])

    def test_foreign_keys_are_enforced(self):
        conn = self.repo._connect()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO month_plans VALUES ('nope', 1, 1, 1, 1, 1, 1)")
        finally:
            conn.close()

    def test_month_number_is_unique_in_plan(self):
        self.repo.save(training(50, plan_id="a"))
        conn = self.repo._connect()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO month_plans VALUES ('a', 1, 1, 1, 1, 1, 1)")
        finally:
            conn.close()

    def test_service_compares_saved_plans(self):
        service = PlanService(self.repo)
        service.save(training(0, plan_id="a"))
        service.save(training(50, plan_id="b"))
        c = PlanService(self.reopen()).compare_saved("a", "b")
        self.assertEqual((c.left.totals.funding_need, c.right.totals.funding_need), (70000, 0))


if __name__ == "__main__":
    unittest.main()
