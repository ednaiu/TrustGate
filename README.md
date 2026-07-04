# TrustGate

Автор: Eva Iusupova ([github.com/iusupovaeva-debug](https://github.com/iusupovaeva-debug))

TrustGate - это инструмент оценки доверия к Python-коду, который мог быть
сгенерирован LLM. Он проверяет отдельный файл, весь репозиторий или измененные
файлы в git и отвечает на практический вопрос: **можно ли мержить этот патч?**

```bash
trustgate scan . --project-tests "python -m pytest -q" --project-mutation --sarif trustgate.sarif
```

Результат - объяснимый `Trust Score` от 0 до 100 и вердикт:

- `PASS` - можно принимать;
- `REVIEW` - нужен ручной review;
- `BLOCK` - высокий риск, CI должен упасть.

## Зачем

LLM-ассистенты часто пишут код с особым профилем дефектов: выдуманные импорты,
несуществующие API, опасные quick fixes, слабые тесты, заглушки и зависимости,
которые выглядят правдоподобно, но не существуют.

Обычные линтеры полезны, но они не дают отдельного risk score для
AI-generated патча. TrustGate добавляет такой слой поверх стандартного CI.

## Слои Проверки

| слой | что делает |
|------|------------|
| L1 static | 12 детекторов `TG-D01..TG-D12`: hallucinated imports/API, `eval/exec`, SQL string building, `shell=True`, `verify=False`, weak hashes, broad except, stubs, dead code, tautological asserts, suspicious dependencies |
| L2 dynamic | запускает pytest в Docker sandbox для single-file flow |
| L3 mutation | генерирует AST-мутанты и проверяет, убивают ли их тесты; работает и для single-file flow, и для repo-flow через `--project-mutation` |
| repo scan | проверяет git/project files, dependency manifests, optional project tests, policy gates, SARIF/HTML/JSON/GitHub annotations |

Код, который анализируется статически, не импортируется. Если выполняются тесты,
они запускаются только явно: single-file через Docker sandbox или project tests
через доверенную команду CI.

## Установка И Запуск

```bash
pip install -e ".[dev]"

trustgate check solution.py --tests test_solution.py --json report.json
trustgate check solution.py --no-sandbox --html report.html

trustgate scan . --json project-report.json
trustgate scan . --changed --base origin/main
trustgate scan . --project-tests "python -m pytest -q"
trustgate scan . --project-tests "python -m pytest -q" --project-mutation
trustgate scan . --sarif trustgate.sarif --github-annotations annotations.json --html trustgate.html
trustgate scan . --policy trustgate.policy.toml --user eva

trustgate history --db trustgate-history.sqlite
trustgate dashboard --db trustgate-history.sqlite --html trustgate-dashboard.html
trustgate report report.json
```

Коды выхода: `0 PASS`, `1 REVIEW`, `2 BLOCK`, `3 bad input`, `4 internal error`.

## GitHub Action

```yaml
- uses: ednaiu/TrustGate@v1
  with:
    mode: scan
    changed: "true"
    base: ${{ github.event.pull_request.base.sha }}
    project-tests: python -m pytest -q
    project-mutation: "true"
    policy: trustgate.policy.toml
    user: eva
    sarif: trustgate.sarif
    github-annotations: annotations.json
    html: trustgate-report.html
```

В репозитории также есть готовый workflow:
`.github/workflows/trustgate.yml`. Он генерирует SARIF, HTML и JSON-отчеты и
загружает SARIF в GitHub code scanning.

## Проверка И Демо

```bash
make test
make scan
make benchmark
make demo-report
```

Примеры лежат в `examples/`. Файлы называются `*.py.example`, чтобы обычный
`trustgate scan .` не считал демонстрационные уязвимости кодом самого проекта.

## Статус

- [x] 12 статических детекторов `TG-D01..TG-D12`;
- [x] Docker sandbox для single-file pytest;
- [x] mutation testing для single-file flow;
- [x] project/git scan: `trustgate scan .`, `--changed`;
- [x] dependency manifest scan для `pyproject.toml` и `requirements*.txt`;
- [x] optional project tests: `--project-tests`;
- [x] project-level mutation testing: `--project-mutation`;
- [x] policy management: merge gates и роли в TOML;
- [x] JSON, HTML и SARIF reports;
- [x] GitHub Checks annotations JSON;
- [x] SQLite persistence: project -> scan runs -> findings -> detector trends;
- [x] dashboard для истории: `trustgate dashboard`;
- [x] GitHub Action и SARIF upload workflow;
- [x] воспроизводимый smoke benchmark;
- [x] external benchmark runner для 100+ samples и сравнения с `ruff`,
  `flake8`, `bandit`, `semgrep`.

## Документация

- `docs/architecture.md` - архитектура;
- `docs/benchmark.md` - benchmark и план расширения корпуса;
- `docs/scoring_rationale.md` - обоснование score;
- `docs/threat_model.md` - модель угроз;
- `docs/defense_questions_ru.md` - вопросы для защиты;
- `docs/competition_ru.md` - описание для ITMO STARS.

## Ограничения

- Полная поддержка сейчас только для Python.
- Большой benchmark требует реальный внешний корпус 100+ LLM samples; проект
  содержит runner и схему запуска, но не подделывает эти данные.
- Некоторые проверки эвристические, поэтому возможны false positives.
