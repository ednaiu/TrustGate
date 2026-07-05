# TrustGate для ITMO STARS

Автор: Eva Iusupova ([github.com/iusupovaeva-debug](https://github.com/iusupovaeva-debug))
Репозиторий: `github.com/ednaiu/TrustGate`
Направление: 09.03.02 "Информационные системы и технологии"

## Коротко

TrustGate - это инструмент для проверки Python-кода, который мог быть написан
с помощью LLM. Он запускается в репозитории или CI и выдает понятный вердикт:
`PASS`, `REVIEW` или `BLOCK`.

Главная идея: обычные линтеры хорошо ловят стиль и часть security-проблем, но
хуже работают с типичными ошибками LLM: выдуманные библиотеки, несуществующие
API и keyword-аргументы, placeholder-значения, заглушки вместо решения.

Эта идея в проекте **измерена**: на корпусе из 245 samples recall TrustGate на
дефект-профиле генеративного кода - 0.854 против 0.341 у bandit и 0.171 у
semgrep, при FPR 4.1% на чистом коде (`docs/benchmark.md`,
`experiment/benchmark-result.json`).

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

- 13 статических детекторов (`TG-D01..TG-D11`, `TG-D13`, `TG-D14`) плюс
  dependency manifest scan `TG-D12`.
- Детерминированный вердикт: hallucinated imports сверяются с закоммиченным
  снапшотом top-15000 PyPI и first-party модулями репозитория, а не с локальным
  окружением (локальное окружение - opt-in флаг `--trust-local-env`).
- Внешний бенчмарк на 245 samples: реальный код Copilot (SecurityEval, MSR
  2022), LLM-решения с разметкой по reference-тестам, clean OSS-файлы;
  сравнение с ruff, flake8, bandit, semgrep; ablation и FP-анализ.
- Калибровка порогов Trust Score на корпусе: правило "один critical finding =
  BLOCK" имеет precision 1.0 и FPR 0 (`docs/scoring_rationale.md`).
- Безопасный запуск тестов в Docker: без сети, с лимитами CPU/RAM/PID.
- Mutation testing с фиксированным seed и лимитом мутантов: single-file и
  repo-flow через `--project-mutation`.
- Объяснимый Trust Score 0-100 с разбивкой findings на "профиль генеративного
  кода" и "общее качество".
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
- Набор тестов для детекторов, scoring, sandbox, CLI и project scan
  (127 тестов).
- Воспроизводимый smoke benchmark: `experiment/static_benchmark.py`.
- Полный воспроизводимый пайплайн корпуса: `generate_corpus.py` (LLM-решения) ->
  `build_corpus.py` (сборка с provenance) -> `benchmark_external.py` (метрики) ->
  `calibrate.py` (пороги).

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

## Честные ограничения

- Если project tests или mutation layer не запускались, TrustGate больше не
  выдает `PASS` на partial analysis.
- Trusted project tests и project mutation выполняются в изолированной временной
  копии репозитория, а не в исходном дереве.
- Полная поддержка сейчас только для Python.
- На классических CWE-уязвимостях recall статического слоя ниже bandit/semgrep
  (0.14 против 0.28-0.29) - TrustGate дополняет их, а не заменяет; это прямо
  показано в `docs/benchmark.md`.

## Слабые места, которые я понимаю

- Корпус v1 (245 samples) содержит известный шум меток: label "defective" для
  SecurityEval унаследован от конструкции датасета; срез дефектов генеративного
  профиля - контролируемые инъекции в реальный LLM-код. Оба факта описаны в
  provenance, схема пересчета зафиксирована.
- 3 известных false positives - TG-D09 (stub detection) на OSS-файлах с
  намеренными no-op функциями; подавляются inline-комментарием.
- TG-D02/TG-D13 сверяют атрибуты и сигнатуры со stdlib той версии Python, на
  которой запущен TrustGate; version-guarded код (`sys.version_info`)
  исключается из проверки.

## План развития

Ближайший практический план:

1. Расширить корпус до 500+ samples: больше моделей-генераторов, сложный
   чистый LLM-код, снижение шума меток ручной верификацией SecurityEval-среза.
2. Добавить JavaScript/TypeScript как следующий язык.
3. Добавить web-режим dashboard с авторизацией поверх текущей SQLite-модели.
4. Расширить policy roles до интеграции с GitHub teams.

Главная цель развития - сделать TrustGate не заменой линтеров, а отдельным
слоем контроля доверия к AI-generated коду.
