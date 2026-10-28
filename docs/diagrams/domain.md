# Диаграмма классов (ЛР2-Д2)

План, три набора параметров месяца, результаты, расчёт и прикладные операции.
`margin`, `expenses`, `profit`, `funding_gap` — производные свойства (вычисляются, не хранятся).

```mermaid
classDiagram
    direction TB

    namespace domain {
        class MonthPlan {
            <<frozen>>
            +quantity : int
            +price : Decimal
            +unit_cost : Decimal
            +fixed_costs : Decimal
            +paid_now_percent : int
        }
        class PlanMonth {
            <<frozen>>
            +number : int
            +params : MonthPlan
        }
        class Plan {
            <<frozen>>
            +id : str
            +name : str
            +opening_cash : Decimal
            +months : tuple~PlanMonth~
            +check() None
            +month(number) MonthPlan
            +create(plan_id, name, opening_cash, months)$ Plan
        }
        class MonthCalculator {
            +calculate(plan, opening_cash, opening_receivables) MonthReport
        }
        class MonthReport {
            <<frozen>>
            +revenue : Decimal
            +variable_costs : Decimal
            +fixed_costs : Decimal
            +cash_receipts : Decimal
            +closing_cash : Decimal
            +closing_receivables : Decimal
            +margin() Decimal
            +expenses() Decimal
            +profit() Decimal
            +funding_gap() Decimal
        }
        class PlanTotals {
            <<frozen>>
            +total_profit : Decimal
            +closing_cash : Decimal
            +closing_receivables : Decimal
            +funding_need : Decimal
            +from_reports(reports)$ PlanTotals
        }
        class PlanValidationError {
            +errors : list~FieldError~
        }
    }

    namespace application {
        class MonthResult {
            <<frozen>>
            +number : int
            +report : MonthReport
        }
        class Forecast {
            <<frozen>>
            +plan_id : str
            +plan_name : str
            +months : tuple~MonthResult~
            +totals : PlanTotals
        }
        class Comparison {
            <<frozen>>
            +left : Forecast
            +right : Forecast
        }
        class ForecastService {
            +forecast(plan) Forecast
            +compare(left, right) Comparison
        }
        class PlanRepository {
            <<interface>>
            +save(plan) None
            +list() list~PlanSummary~
            +get(plan_id) Plan
        }
        class PlanService {
            +save(plan) None
            +list_plans() list~PlanSummary~
            +open_plan(plan_id) Plan
            +forecast(plan) Forecast
            +compare_saved(left_id, right_id) Comparison
        }
    }

    Plan "1" *-- "3" PlanMonth : months
    PlanMonth *-- MonthPlan : params
    MonthCalculator ..> MonthPlan : принимает
    MonthCalculator ..> MonthReport : возвращает
    PlanTotals ..> MonthReport : суммирует
    Plan ..> PlanValidationError : бросает
    ForecastService ..> MonthCalculator : 3 вызова, перенос C и D
    ForecastService ..> Forecast : создаёт
    Forecast *-- "3" MonthResult
    MonthResult --> MonthReport
    Forecast *-- PlanTotals
    Comparison o-- "2" Forecast
    PlanService --> PlanRepository
    PlanService --> ForecastService
```
