# TrustGate для ITMO STARS

Автор: Eva Iusupova ([github.com/iusupovaeva-debug](https://github.com/iusupovaeva-debug))
Репозиторий: `github.com/ednaiu/TrustGate`
Направление: 09.03.02 "Информационные системы и технологии"

## Коротко

TrustGate - это инструмент для проверки Python-кода, который мог быть написан
с помощью LLM. Он запускается в репозитории или CI и выдает понятный вердикт:
`PASS`, `REVIEW` или `BLOCK`.

Главная идея: обычные линтеры хорошо ловят стиль и часть security-проблем, но
хуже работают с типичными ошибками LLM: выдуманные библиотеки, похожие на
настоящие API, опасные quick fixes, заглушки вместо решения и слабые тесты.

## Почему это информационная система

В проекте есть не только алгоритм анализа, но и полный поток обработки данных:

1. Источник данных - git-репозиторий, PR-diff или отдельный Python-файл.
2. Обработка - статические детекторы, dependency manifest scan, sandboxed
   pytest, mutation testing.
3. Хранение результата - JSON-отчет по схеме.
4. Представление - Markdown для CI, HTML для демонстрации, SARIF для GitHub
   code scanning.
5. Интеграция - CLI и GitHub Action.

Это делает TrustGate небольшим quality-gate для процесса разработки, а не
разовым скриптом.

## Что уже сделано

- 11 AST-детекторов `TG-D01..TG-D11`.
- Безопасный запуск тестов в Docker: без сети, с лимитами CPU/RAM/PID.
- Mutation testing с фиксированным seed и лимитом мутантов.
- Объяснимый Trust Score 0-100.
- CLI: `check`, `scan`, `report`.
- Git workflow: `trustgate scan .` и `trustgate scan . --changed`.
- Dependency manifest scan для `pyproject.toml` и `requirements*.txt`.
- Optional project tests: `trustgate scan . --project-tests "python -m pytest -q"`.
- SARIF export для GitHub code scanning.
- GitHub Action для PR.
- JSON schema и HTML reports.
- Набор тестов для детекторов, scoring, sandbox, CLI и project scan.
- Воспроизводимый smoke benchmark: `experiment/static_benchmark.py`.

## Личный вклад

Я проектировала TrustGate как понятную систему из небольших модулей:

- `detectors.py` - правила поиска дефектов;
- `sandbox.py` - безопасный запуск тестов;
- `mutation.py` - генерация мутантов;
- `scoring.py` - расчет баллов;
- `scan.py` - работа с git/project workflow;
- `action.yml` - запуск в CI.

Код специально оставлен простым: без тяжелого фреймворка и без "магии", чтобы
можно было объяснить каждое решение на собеседовании.

## Что можно показать на демо

1. Проверка отдельного решения:

```bash
trustgate check examples/block_solution.py.example --no-sandbox --html report.html
```

2. Проверка всего проекта:

```bash
trustgate scan . --json project-report.json --html project-report.html --sarif trustgate.sarif
```

3. Проверка только измененных файлов:

```bash
trustgate scan . --changed --base HEAD
```

4. Проверка проекта вместе с доверенной командой тестов:

```bash
trustgate scan . --project-tests "python -m pytest -q"
```

5. GitHub Action в pull request: `BLOCK` падает, `REVIEW` оставляет summary,
   `PASS` проходит.

## Слабые места, которые я понимаю

- Mutation testing пока полноценно работает для одного файла с pytest; project
  scan умеет запускать доверенную команду тестов, но не генерирует мутанты для
  всего репозитория.
- Поддерживается только Python.
- Часть проверок эвристическая: например, import hallucination зависит от
  списка популярных пакетов и локального окружения.
- Для сильной исследовательской защиты нужен большой benchmark с метриками
  против `ruff`, `flake8`, `bandit` и `semgrep`; маленький smoke benchmark уже
  лежит в репозитории.

## План развития

Ближайший практический план:

1. Расширить benchmark до 100+ LLM-решений: precision, recall, F1, false
   positive rate.
2. Добавить project-level mutation testing.
3. Сохранять историю проверок в SQLite.
4. Добавить GitHub Checks annotations поверх SARIF.
5. Расширить поддержку языков: JavaScript/TypeScript как следующий кандидат.

Главная цель развития - сделать TrustGate не заменой линтеров, а отдельным
слоем контроля доверия к AI-generated коду.
