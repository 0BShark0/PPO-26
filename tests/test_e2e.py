"""ЛР5-Т1: сквозная проверка веб-интерфейса через WSGI (без сети и браузера).

Сценарий: создание двух планов -> расчёт -> сохранение -> сравнение -> «перезапуск»
(новое приложение на том же файле БД) -> открытие с теми же результатами ->
изменение -> пересчёт -> отказ при ошибочном вводе.
"""
import io
import os
import re
import tempfile
import unittest
from urllib.parse import parse_qs, urlencode, urlparse
from wsgiref.util import setup_testing_defaults

from findirector.application import PlanService
from findirector.infrastructure import SqlitePlanRepository
from findirector.ui.web import WebApp

NBSP = " "


class Client:
    def __init__(self, app):
        self.app = app

    def request(self, method, url, data=None):
        parsed = urlparse(url)
        body = urlencode(data or {}).encode("utf-8")
        environ = {"REQUEST_METHOD": method, "PATH_INFO": parsed.path, "QUERY_STRING": parsed.query,
                   "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body),
                   "CONTENT_TYPE": "application/x-www-form-urlencoded"}
        setup_testing_defaults(environ)
        result = {}

        def start_response(status, headers):
            result["status"], result["headers"] = int(status.split()[0]), dict(headers)

        html = b"".join(self.app(environ, start_response)).decode("utf-8")
        return result["status"], result["headers"], html


def plan_form(plan_id, name, cash, percent):
    form = {"id": plan_id, "name": name, "opening_cash": cash}
    for n in (1, 2, 3):
        form.update({f"m{n}_quantity": "5", f"m{n}_price": "30 000", f"m{n}_unit_cost": "10000",
                     f"m{n}_fixed_costs": "70000", f"m{n}_paid_now_percent": str(percent)})
    return form


def money(text):
    return text.replace(" ", NBSP)


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "e2e.db")
        self.client = self.start()

    def tearDown(self):
        self.tmp.cleanup()

    def start(self):
        return Client(WebApp(PlanService(SqlitePlanRepository(self.db))))

    def test_full_scenario(self):
        c = self.client
        # 1. Новый план: форма с новым идентификатором
        status, _, html = c.request("GET", "/plan")
        self.assertEqual(status, 200)
        self.assertRegex(html, r"name='id' value='[0-9a-f-]{36}'")

        # 2. Расчёт первого плана (A = 0%): видны месячные показатели, дефицит подписан
        status, _, html = c.request("POST", "/plan", {**plan_form("p1", "Всё через месяц", "50000", 0),
                                                      "action": "calculate"})
        self.assertEqual(status, 200)
        self.assertIn("id='result'", html)
        self.assertIn("Маржинальный доход", html)
        self.assertIn(money("−70 000,00"), html)
        self.assertIn("Не хватает денег", html)
        self.assertIn(money("70 000,00"), html)                  # потребность в финансировании
        self.assertEqual(SqlitePlanRepository(self.db).list(), [])   # расчёт не сохраняет

        # 3. Сохранение двух планов
        for form in (plan_form("p1", "Всё через месяц", "50000", 0),
                     plan_form("p2", "Половина сразу", "50000", 50)):
            status, headers, _ = c.request("POST", "/plan", {**form, "action": "save"})
            self.assertEqual(status, 303)
            self.assertIn("saved=1", headers["Location"])

        # 4. Сравнение
        _, _, cmp_before = c.request("GET", "/compare?a=p1&b=p2")
        for value in ("−10 000,00", "65 000,00", "150 000,00", "75 000,00", "70 000,00", "90 000,00"):
            self.assertIn(money(value), cmp_before)

        # 5. «Перезапуск»: новое приложение на том же файле БД, список и открытие
        c = self.start()
        _, _, index = c.request("GET", "/")
        self.assertIn("Всё через месяц", index)
        self.assertIn("Половина сразу", index)
        status, _, opened = c.request("GET", "/plan?id=p2")
        self.assertEqual(status, 200)
        self.assertIn("value='Половина сразу'", opened)
        self.assertIn("name='m3_paid_now_percent' value='50'", opened)
        _, _, cmp_after = c.request("GET", "/compare?a=p1&b=p2")
        self.assertEqual(self.section(cmp_before, "cmp"), self.section(cmp_after, "cmp"))

        # 6. Изменение второго плана (A = 100%), пересчёт и сохранение
        changed = plan_form("p2", "Половина сразу", "50000", 100)
        _, _, html = c.request("POST", "/plan", {**changed, "action": "calculate"})
        self.assertIn(money("140 000,00"), html)
        self.assertNotIn("Не хватает денег", html)
        c.request("POST", "/plan", {**changed, "action": "save"})
        self.assertEqual(len(SqlitePlanRepository(self.db).list()), 2)   # без дубликата
        _, _, cmp_new = c.request("GET", "/compare?a=p1&b=p2")
        self.assertIn(money("140 000,00"), cmp_new)

        # 7. Скрытие старого результата после правки (П-Ф6) — форма помечена data-hides
        self.assertIn("data-hides='result'", html)
        self.assertIn("id='result-stale' class='box' hidden", html)
        self.assertIn("data-hides='cmp'", cmp_new)

    def test_invalid_input_shows_field_and_does_not_save(self):     # ПР6, П-Ф5
        form = plan_form("bad", "", "-1", 50)
        form["m2_paid_now_percent"] = "101"
        form["m3_price"] = "тридцать"
        status, _, html = self.client.request("POST", "/plan", {**form, "action": "save"})
        self.assertEqual(status, 422)
        self.assertIn("расчёт и сохранение не выполнены", html)
        self.assertIn("Месяц 2, оплата сразу (A)", html)
        self.assertIn("процент оплаты должен быть целым от 0 до 100", html)
        self.assertIn("Название", html)
        self.assertIn("Месяц 3, цена (P)", html)
        self.assertIn("name='m2_paid_now_percent' value='101' aria-invalid='true'", html)
        self.assertNotIn("id='result'", html)
        self.assertEqual(SqlitePlanRepository(self.db).list(), [])

    def test_unknown_plan_is_404(self):
        status, _, html = self.client.request("GET", "/plan?id=nope")
        self.assertEqual(status, 404)
        self.assertIn("План не найден", html)

    @staticmethod
    def section(html, section_id):
        return re.search(rf"<section id='{section_id}'>.*?</section>", html, re.S).group(0)


if __name__ == "__main__":
    unittest.main()
