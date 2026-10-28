"""Веб-интерфейс финансового директора (ЛР5) на wsgiref.

Обработчики только разбирают форму, вызывают операции Application и рисуют HTML.
Финансовых формул здесь нет (ЛР5-А1): все числа берутся из Forecast/MonthReport.
"""
from html import escape
from urllib.parse import parse_qs, urlencode

from findirector.application import (Comparison, Forecast, PlanNotFoundError, PlanService,
                                     RepositoryError, new_plan_id)
from findirector.domain import MONTH_FIELDS, MONTH_NUMBERS, Plan, PlanValidationError

from .formatting import field_label, fmt_money, input_money, parse_int, parse_money

MONTH_ROWS = [
    ("quantity", "Количество услуг Q"),
    ("price", "Цена P, ₽"),
    ("unit_cost", "Переменные затраты V, ₽/услуга"),
    ("fixed_costs", "Постоянные расходы F, ₽"),
    ("paid_now_percent", "Оплата сразу A, %"),
]
DEFAULT_MONTH = {"quantity": "5", "price": "30000", "unit_cost": "10000",
                 "fixed_costs": "70000", "paid_now_percent": "50"}

CSS = """
:root{--fg:#1d2433;--muted:#5d6678;--line:#d9dee8;--bg:#fff;--soft:#f4f6fa;--accent:#2457c5;--bad:#b42318;--badbg:#fdecea;--ok:#067647}
@media (prefers-color-scheme: dark){:root{--fg:#e7eaf0;--muted:#a3abbb;--line:#3a4252;--bg:#161a22;--soft:#1f2430;--accent:#7aa2ff;--bad:#ff8a80;--badbg:#3a1d1d;--ok:#6ce9a6}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,Segoe UI,sans-serif;color:var(--fg);background:var(--bg)}
header{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header b{font-size:17px}header a{color:var(--accent);text-decoration:none}
main{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:8px 0 16px}h2{font-size:17px;margin:24px 0 8px}
table{border-collapse:collapse;width:100%;margin:8px 0}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:right;vertical-align:top}
th:first-child,td:first-child{text-align:left}thead th{background:var(--soft)}
input,select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:5px 8px;width:100%;max-width:180px;text-align:right}
input[name=name]{max-width:360px;text-align:left}select{text-align:left;max-width:320px}
.err input,input[aria-invalid=true]{border-color:var(--bad);background:var(--badbg)}
.msg{color:var(--bad);font-size:13px;display:block}
.box{border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0;background:var(--soft)}
.box.bad{border-color:var(--bad);background:var(--badbg)}.box.ok{border-color:var(--ok)}
.neg{color:var(--bad);font-weight:600}.tag{display:block;font-size:12px;color:var(--bad)}
button{font:inherit;padding:7px 16px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer;margin-right:8px}
button.sec{background:transparent;color:var(--accent)}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:end;margin-bottom:8px}.row label{display:flex;flex-direction:column;gap:4px}
.scroll{overflow-x:auto}.muted{color:var(--muted)}
"""

# П-Ф6: любое изменение ввода скрывает прежний результат до пересчёта.
JS = """
document.querySelectorAll('form[data-hides]').forEach(function(f){
  function stale(){var r=document.getElementById(f.dataset.hides);if(r){r.hidden=true;}
    var s=document.getElementById(f.dataset.hides+'-stale');if(s){s.hidden=false;}}
  f.addEventListener('input',stale);f.addEventListener('change',stale);
});
"""


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(title)}</title><style>{CSS}</style></head><body>"
            f"<header><b>Финдиректор</b><a href='/'>Планы</a><a href='/plan'>Новый план</a>"
            f"<a href='/compare'>Сравнение</a></header><main>{body}</main><script>{JS}</script></body></html>")


def money_cell(amount, negative_label: bool = False) -> str:
    if amount < 0:
        tag = "<span class='tag'>Не хватает денег</span>" if negative_label else ""
        return f"<td class='neg'>{fmt_money(amount)}{tag}</td>"
    return f"<td>{fmt_money(amount)}</td>"


def plan_to_form(plan: Plan) -> dict[str, str]:
    form = {"id": plan.id, "name": plan.name, "opening_cash": input_money(plan.opening_cash)}
    for m in plan.months:
        p = m.params
        form.update({f"m{m.number}_quantity": str(p.quantity), f"m{m.number}_price": input_money(p.price),
                     f"m{m.number}_unit_cost": input_money(p.unit_cost),
                     f"m{m.number}_fixed_costs": input_money(p.fixed_costs),
                     f"m{m.number}_paid_now_percent": str(p.paid_now_percent)})
    return form


def form_to_plan(form: dict[str, str]) -> Plan:
    """Строки формы -> Plan. Бросает PlanValidationError со всеми ошибками полей."""
    months = []
    for n in MONTH_NUMBERS:
        months.append({f: (parse_int if f in ("quantity", "paid_now_percent") else parse_money)(
            form.get(f"m{n}_{f}", "")) for f in MONTH_FIELDS})
    return Plan.create(form.get("id", ""), form.get("name", ""), parse_money(form.get("opening_cash", "")),
                       months)


def render_forecast(f: Forecast) -> str:
    rows = [("Выручка", lambda r: r.revenue, False), ("Маржинальный доход", lambda r: r.margin, False),
            ("Расходы", lambda r: r.expenses, False), ("Прибыль", lambda r: r.profit, False),
            ("Поступления", lambda r: r.cash_receipts, False),
            ("Деньги на конец месяца", lambda r: r.closing_cash, True),
            ("Задолженность клиентов", lambda r: r.closing_receivables, False)]
    head = "".join(f"<th>Месяц {m.number}</th>" for m in f.months)
    body = "".join(f"<tr><td>{t}</td>{''.join(money_cell(v(m.report), lab) for m in f.months)}</tr>"
                   for t, v, lab in rows)
    t = f.totals
    totals = (f"<table><tbody><tr><td>Прибыль за три месяца</td>{money_cell(t.total_profit)}</tr>"
              f"<tr><td>Деньги после месяца 3 (C3)</td>{money_cell(t.closing_cash, True)}</tr>"
              f"<tr><td>Задолженность после месяца 3 (D3)</td>{money_cell(t.closing_receivables)}</tr>"
              f"<tr><td>Потребность в начальном финансировании</td>{money_cell(t.funding_need)}</tr>"
              f"</tbody></table>")
    return (f"<section id='result'><h2>Прогноз: {escape(f.plan_name)}</h2><div class='scroll'><table>"
            f"<thead><tr><th>Показатель, ₽</th>{head}</tr></thead><tbody>{body}</tbody></table></div>"
            f"<h2>Итоги</h2>{totals}</section>"
            f"<p id='result-stale' class='box' hidden>Данные изменены — нажмите «Рассчитать», "
            f"чтобы увидеть новый прогноз.</p>")


def render_plan_form(form: dict[str, str], errors: dict[str, str] | None = None,
                     forecast: Forecast | None = None, notice: str = "") -> str:
    errors = errors or {}

    def field(name: str, cls: str = "") -> str:
        err = errors.get(name)
        bad = " aria-invalid='true'" if err else ""
        msg = f"<span class='msg'>{escape(err)}</span>" if err else ""
        return (f"<input name='{name}' value='{escape(form.get(name, ''))}'{bad} "
                f"aria-label='{escape(field_label(name))}'{cls}>{msg}")

    err_box = ""
    if errors:
        items = "".join(f"<li><b>{escape(field_label(k))}</b>: {escape(v)}</li>" for k, v in errors.items())
        err_box = (f"<div class='box bad' role='alert'><b>Проверьте ввод — расчёт и сохранение "
                   f"не выполнены.</b><ul>{items}</ul></div>")
    month_rows = "".join(
        f"<tr><td>{title}</td>" + "".join(f"<td>{field(f'm{n}_{key}')}</td>" for n in MONTH_NUMBERS) + "</tr>"
        for key, title in MONTH_ROWS)
    plan_err = (f"<span class='msg'>{escape(errors['months'])}</span>" if "months" in errors else "")
    body = (f"<h1>План</h1>{notice}{err_box}"
            f"<form method='post' action='/plan' data-hides='result'>"
            f"<input type='hidden' name='id' value='{escape(form.get('id', ''))}'>"
            f"<div class='row'><label>Название{field('name')}</label>"
            f"<label>Начальные деньги, ₽{field('opening_cash')}</label></div>"
            f"<div class='scroll'><table><thead><tr><th>Параметр</th>"
            + "".join(f"<th>Месяц {n}</th>" for n in MONTH_NUMBERS)
            + f"</tr></thead><tbody>{month_rows}</tbody></table></div>{plan_err}"
            f"<button name='action' value='calculate'>Рассчитать</button>"
            f"<button name='action' value='save' class='sec'>Сохранить</button></form>")
    if forecast is not None:
        body += render_forecast(forecast)
    return page("План — Финдиректор", body)


def render_comparison(c: Comparison) -> str:
    rows = [("Прибыль за три месяца", "total_profit", False), ("Деньги C3", "closing_cash", True),
            ("Дебиторская задолженность D3", "closing_receivables", False),
            ("Потребность в финансировании", "funding_need", False)]
    body = "".join(f"<tr><td>{t}</td>{money_cell(getattr(c.left.totals, a), lab)}"
                   f"{money_cell(getattr(c.right.totals, a), lab)}</tr>" for t, a, lab in rows)
    return (f"<section id='cmp'><table><thead><tr><th>Показатель, ₽</th><th>{escape(c.left.plan_name)}</th>"
            f"<th>{escape(c.right.plan_name)}</th></tr></thead><tbody>{body}</tbody></table></section>"
            f"<p id='cmp-stale' class='box' hidden>Выбор изменён — нажмите «Сравнить».</p>")


class WebApp:
    """WSGI-приложение. service передаётся снаружи (сборка зависимостей в __main__)."""

    def __init__(self, service: PlanService):
        self.service = service

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        if method == "HEAD":
            method = "GET"
        path = environ.get("PATH_INFO", "/")
        query = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
        try:
            if path == "/" and method == "GET":
                return self._html(start_response, self.index())
            if path == "/plan" and method == "GET":
                return self._html(start_response, self.open_plan(query))
            if path == "/plan" and method == "POST":
                return self.post_plan(environ, start_response)
            if path == "/compare" and method == "GET":
                return self._html(start_response, self.compare(query))
            return self._html(start_response, page("Не найдено", "<h1>Страница не найдена</h1>"), "404 Not Found")
        except PlanNotFoundError as exc:
            return self._html(start_response, page("Не найдено",
                              f"<div class='box bad'>{escape(str(exc))}</div>"), "404 Not Found")
        except RepositoryError as exc:
            return self._html(start_response, page("Ошибка", f"<div class='box bad'>{escape(str(exc))}</div>"),
                              "500 Internal Server Error")

    @staticmethod
    def _html(start_response, html: str, status: str = "200 OK"):
        data = html.encode("utf-8")
        start_response(status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
        return [data]

    def index(self) -> str:
        plans = self.service.list_plans()
        rows = "".join(f"<tr><td><a href='/plan?{urlencode({'id': p.id})}'>{escape(p.name)}</a></td></tr>"
                       for p in plans) or "<tr><td class='muted'>Сохранённых планов пока нет</td></tr>"
        return page("Планы — Финдиректор",
                    f"<h1>Финансовые планы</h1><p class='muted'>Хватит ли денег, даже если есть прибыль?</p>"
                    f"<p><a href='/plan'><button>Создать план</button></a></p>"
                    f"<table><thead><tr><th>Сохранённые планы</th></tr></thead><tbody>{rows}</tbody></table>")

    def open_plan(self, query: dict) -> str:
        if "id" in query:
            notice = "<div class='box ok'>План сохранён.</div>" if query.get("saved") else ""
            return render_plan_form(plan_to_form(self.service.open_plan(query["id"])), notice=notice)
        form = {"id": new_plan_id(), "name": "Новый план", "opening_cash": "50000"}
        form.update({f"m{n}_{k}": v for n in MONTH_NUMBERS for k, v in DEFAULT_MONTH.items()})
        return render_plan_form(form)

    def post_plan(self, environ, start_response):
        size = int(environ.get("CONTENT_LENGTH") or 0)
        raw = environ["wsgi.input"].read(size).decode("utf-8")
        form = {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}
        action = form.pop("action", "calculate")
        try:
            plan = form_to_plan(form)
        except PlanValidationError as exc:                       # П-Ф5
            errors: dict[str, str] = {}
            for e in exc.errors:
                key = e.field.replace("months[", "m").replace("].", "_")
                errors.setdefault(key, e.message)
            return self._html(start_response, render_plan_form(form, errors), "422 Unprocessable Entity")
        if action == "save":
            self.service.save(plan)
            location = "/plan?" + urlencode({"id": plan.id, "saved": "1"})
            start_response("303 See Other", [("Location", location), ("Content-Length", "0")])
            return [b""]
        return self._html(start_response, render_plan_form(form, forecast=self.service.forecast(plan)))

    def compare(self, query: dict) -> str:
        plans = self.service.list_plans()

        def select(name: str) -> str:
            opts = "".join(f"<option value='{escape(p.id)}'{' selected' if query.get(name) == p.id else ''}>"
                           f"{escape(p.name)}</option>" for p in plans)
            return f"<select name='{name}'><option value=''>— выберите план —</option>{opts}</select>"

        body = (f"<h1>Сравнение планов</h1><form method='get' action='/compare' data-hides='cmp'>"
                f"<div class='row'><label>План 1{select('a')}</label><label>План 2{select('b')}</label>"
                f"<button>Сравнить</button></div></form>")
        if query.get("a") and query.get("b"):
            body += render_comparison(self.service.compare_saved(query["a"], query["b"]))
        elif "a" in query or "b" in query:
            body += "<div class='box bad'>Выберите два плана.</div>"
        if len(plans) < 2:
            body += "<p class='muted'>Для сравнения сохраните хотя бы два плана.</p>"
        return page("Сравнение — Финдиректор", body)
