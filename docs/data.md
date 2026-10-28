# Данные (ЛР2-Д5, уточнено в ЛР4-Д1)

Сохраняются **только исходные данные** плана. Отчёт (прогноз) не хранится — он вычисляется
из входов при каждом открытии, поэтому не может разойтись с формулами.

## Логическая модель (ЛР2)

| Сущность | Поле | Смысл | Ключ / ограничение |
| --- | --- | --- | --- |
| План | Идентификатор | Постоянный id (UUID), не меняется при редактировании | PK |
| План | Название | Имя плана | непустое |
| План | Начальные деньги | Деньги до месяца 1 | ≥ 0, до копейки |
| Месяц плана | План | Ссылка на план | FK → План |
| Месяц плана | Номер | 1, 2 или 3 | PK вместе с планом; уникален в плане |
| Месяц плана | Q | Количество услуг | целое ≥ 0 |
| Месяц плана | P, V, F | Цена, перем. затраты на услугу, пост. расходы | ≥ 0, до копейки |
| Месяц плана | A | Процент оплаты сразу | целое 0–100 |

Связь: один план — ровно три месяца (1 : 3), П-Б10. Диаграмма: [er.md](diagrams/er.md).

## Физическая схема SQLite (ЛР4)

Денежные значения хранятся **целым числом копеек** (`INTEGER`): `Decimal("1000.01") → 100001`.
Так нет двоичной погрешности `REAL`, и копейки не теряются (ЛР4-Т1).

```sql
PRAGMA foreign_keys = ON;

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
```

- Уникальность номера месяца в плане — составной первичный ключ `(plan_id, month_number)`.
- Проверка внешних ключей включается `PRAGMA foreign_keys = ON` при каждом подключении.
- Сохранение — одна транзакция: `INSERT … ON CONFLICT(id) DO UPDATE` плана,
  `DELETE` его месяцев, `INSERT` трёх месяцев. При ошибке — откат, прежняя версия плана остаётся.
- Схема создаётся при первом запуске (`CREATE TABLE IF NOT EXISTS`).
- «Ровно три месяца» гарантирует Domain (`Plan` нельзя создать с другим набором) — SQL-ограничение
  на количество строк в SQLite неудобно, поэтому проверка до записи.
