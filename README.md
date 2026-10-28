# Финдиректор: прибыль и деньги (Python)

Симулятор финансового плана студии сайтов на три месяца: **хватит ли денег, даже если есть прибыль?**
Лабораторные работы ЛР1–ЛР5 курса ППО, реализованные на Python (вместо C#/.NET).

Архитектура — **модульный монолит**: один пакет, один процесс, одна БД SQLite.
Внешних зависимостей нет — нужен только Python 3.11+.

```
findirector/
  domain/          ЛР3  формулы П-Б1–П-Б9, план П-Б10, итоги П-Б7 (ни от чего не зависит)
  application/     ЛР3  прогноз 3 месяцев, сравнение, интерфейс PlanRepository, PlanService
  infrastructure/  ЛР4  SqlitePlanRepository (sqlite3, деньги в копейках)
  ui/              ЛР3/5 консоль и веб-интерфейс (wsgiref)
  __main__.py      точка запуска: сборка зависимостей
tests/             56 тестов unittest (домен, прогноз, SQLite, сквозной сценарий)
docs/              requirements.md (ЛР1), design.md + data.md (ЛР2/4), ui.md + e2e-protocol.md (ЛР5)
docs/diagrams/     use-cases, components, domain (классы), er — диаграммы Mermaid
tools/publish.py   сборка одного файла dist/findirector.pyz
```

## Команды

Сборка (проверка компиляции всех модулей):
```sh
python -m compileall -q findirector
```

Тесты:
```sh
python -m unittest -v
```

Запуск веб-интерфейса из исходников (откройте http://127.0.0.1:8000/):
```sh
python -m findirector
```

Консольная демонстрация учебного сценария:
```sh
python -m findirector console
```

Публикация одним файлом и запуск вне IDE:
```sh
python tools/publish.py
python dist/findirector.pyz --db findirector.db --port 8000
```

База `findirector.db` создаётся при первом запуске; путь меняется флагом `--db`.

## Диаграммы

Диаграммы записаны в формате [Mermaid](https://mermaid.js.org/) внутри файлов `docs/diagrams/*.md`
и рисуются без дополнительных программ:

- **GitHub** показывает их картинками прямо при открытии файла:
  [Use Case](docs/diagrams/use-cases.md), [компоненты](docs/diagrams/components.md),
  [классы](docs/diagrams/domain.md), [ER](docs/diagrams/er.md).
- **VS Code**: установите расширение «Markdown Preview Mermaid Support», откройте файл и нажмите `Ctrl+Shift+V`.
- **PNG/SVG** для отчёта: вставьте текст диаграммы в https://mermaid.live и нажмите «Export».

## Учебный сценарий

Старт 50 000 ₽; каждый месяц 5 услуг по 30 000 ₽, V = 10 000 ₽, F = 70 000 ₽.

| | A = 0% | A = 50% | A = 100% |
| --- | ---: | ---: | ---: |
| Деньги по месяцам | −70 000 / −40 000 / −10 000 | 5 000 / 35 000 / 65 000 | 80 000 / 110 000 / 140 000 |
| Прибыль за 3 месяца | 90 000 | 90 000 | 90 000 |
| Задолженность после месяца 3 | 150 000 | 75 000 | 0 |
| Нужно доп. денег на старте | 70 000 | 0 | 0 |
