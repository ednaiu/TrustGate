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

- 12 детекторов `TG-D01..TG-D12`, включая dependency manifest scan.
- Безопасный запуск тестов в Docker: без сети, с лимитами CPU/RAM/PID.
- Mutation testing с фиксированным seed и лимитом мутантов: single-file и
  repo-flow через `--project-mutation`.
- Объяснимый Trust Score 0-100.
- CLI: `check`, `scan`, `report`, `history`, `dashboard`.
- Git workflow: `trustgate scan .` и `trustgate scan . --changed`.
- Dependency manifest scan для `pyproject.toml` и `requirements*.txt`.
- Optional project tests: `trustgate scan . --project-tests "python -m pytest -q"`.
- SARIF export для GitHub code scanning.
- GitHub Checks annotations JSON.
- Policy management: TOML-gates и роли `viewer`, `reviewer`, `maintainer`.
- SQLite persistence: `project -> scan runs -> findings -> detector trends`.
- Dashboard по истории проверок.
- GitHub Action для PR.
- JSON schema и HTML reports.
- Набор тестов для детекторов, scoring, sandbox, CLI и project scan.
- Воспроизводимый smoke benchmark: `experiment/static_benchmark.py`.
- External benchmark runner: confusion matrix, false positive analysis,
  сравнение с `ruff`, `flake8`, `bandit`, `semgrep` при наличии корпуса 100+
  реальных LLM samples.

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

4. Проверка проекта вместе с доверенной командой тестов и mutation layer:

```bash
trustgate scan . --project-tests "python -m pytest -q" --project-mutation
```

5. Политика merge decision:

```bash
trustgate scan . \
  --project-tests "python -m pytest -q" \
  --project-mutation \
  --policy trustgate.policy.toml \
  --user eva
```

6. Dashboard по истории:

```bash
trustgate scan . --save-history trustgate-history.sqlite
trustgate dashboard --db trustgate-history.sqlite --html trustgate-dashboard.html
```

7. GitHub Action в pull request: `BLOCK` падает, `REVIEW` оставляет summary,
   `PASS` проходит.

## Слабые места, которые я понимаю

- Поддерживается только Python.
- Часть проверок эвристическая: например, import hallucination зависит от
  списка популярных пакетов и локального окружения.
- Для сильной исследовательской защиты нужен внешний корпус 100+ реальных LLM
  samples. Runner уже есть, но сам корпус не подделывается и должен быть
  собран отдельно.

## План развития

Ближайший практический план:

1. Собрать и опубликовать внешний корпус 100+ LLM samples с разметкой.
2. Добавить JavaScript/TypeScript как следующий язык.
3. Добавить web-режим dashboard с авторизацией поверх текущей SQLite-модели.
4. Расширить policy roles до интеграции с GitHub teams.

Главная цель развития - сделать TrustGate не заменой линтеров, а отдельным
слоем контроля доверия к AI-generated коду.
