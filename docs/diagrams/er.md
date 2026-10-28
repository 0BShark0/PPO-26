# ER-диаграмма (ЛР2-Д5, уточнена в ЛР4-Д1)

Типы SQLite и ограничения. Денежные поля — целые копейки (`*_kop`).
Составной первичный ключ `(plan_id, month_number)` обеспечивает уникальность номера месяца в плане (П-Б10).

```mermaid
erDiagram
    plans ||--|{ month_plans : "ровно 3 месяца (П-Б10)"

    plans {
        TEXT id PK "UUID, постоянный"
        TEXT name "NOT NULL, trim(name) <> ''"
        INTEGER opening_cash_kop "NOT NULL, >= 0"
    }

    month_plans {
        TEXT plan_id PK, FK "-> plans.id, ON DELETE CASCADE"
        INTEGER month_number PK "IN (1, 2, 3)"
        INTEGER quantity "NOT NULL, >= 0"
        INTEGER price_kop "NOT NULL, >= 0"
        INTEGER unit_cost_kop "NOT NULL, >= 0"
        INTEGER fixed_costs_kop "NOT NULL, >= 0"
        INTEGER paid_now_percent "NOT NULL, 0..100"
    }
```
