# Диаграмма компонентов (ЛР2-Д1)

Модульный монолит: четыре слоя — подпакеты одного пакета `findirector`, один процесс, одна БД.
Стрелка — направление зависимости (кто кого импортирует). Domain ни от чего не зависит.

```mermaid
flowchart TB
    subgraph MONO["Монолит findirector (один процесс)"]
        UI["<b>UI</b><br/>findirector.ui<br/>web.py, console.py"]
        APP["<b>Application</b><br/>findirector.application<br/>ForecastService, PlanService,<br/>PlanRepository — интерфейс"]
        DOM["<b>Domain</b><br/>findirector.domain<br/>MonthPlan, Plan, MonthCalculator,<br/>MonthReport, PlanTotals"]
        INF["<b>Infrastructure</b><br/>findirector.infrastructure<br/>SqlitePlanRepository"]
        MAIN["__main__.py<br/>точка сборки зависимостей"]
    end
    DB[("SQLite<br/>findirector.db")]

    UI -->|вызывает операции| APP
    UI -->|строит план, читает отчёт| DOM
    APP -->|использует формулы| DOM
    INF -.->|реализует PlanRepository| APP
    INF -->|восстанавливает Plan| DOM
    INF --> DB
    MAIN --> UI
    MAIN -->|создаёт и передаёт в PlanService| INF
```
