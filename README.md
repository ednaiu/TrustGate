# TrustGate

Автор: Eva Iusupova ([github.com/iusupovaeva-debug](https://github.com/iusupovaeva-debug))

TrustGate - это quality-gate для Python-кода с фокусом на дефект-профиль
генеративного кода: hallucinated imports и API, несуществующие kwargs,
заглушки, placeholder-значения, опасные quick fixes. Он проверяет отдельный
файл, весь репозиторий или измененные файлы в git и отвечает на практический
вопрос: **можно ли мержить этот патч?**

```bash
trustgate scan . --project-tests "python -m pytest -q" --project-mutation --sarif trustgate.sarif
```

Результат - объяснимый `Trust Score` от 0 до 100 и вердикт:

- `PASS` - можно принимать;
- `REVIEW` - нужен ручной review;
- `BLOCK` - высокий риск, CI должен упасть.

## Зачем

LLM-ассистенты часто пишут код с особым профилем дефектов: выдуманные импорты,
несуществующие API и keyword-аргументы, placeholder-значения вместо
конфигурации, заглушки вместо решения и зависимости, которые выглядят
правдоподобно, но не существуют.

Это утверждение в проекте измерено, а не задекларировано. На корпусе из 245
samples (реальный код Copilot из SecurityEval, LLM-решения, размеченные
reference-тестами, clean OSS-файлы - см. `docs/benchmark.md`):

| инструмент | precision | recall | F1 | FPR на clean | recall на профиле генеративного кода |
|------------|-----------|--------|-----|--------------|--------------------------------------|
| **TrustGate (static)** | **1.000** | 0.357 | **0.526** | **0.0%** | **0.854** |
| bandit | 0.962 | 0.298 | 0.455 | 2.7% | 0.341 |
| semgrep | 1.000 | 0.263 | 0.417 | 0.0% | 0.171 |
| ruff | 0.973 | 0.211 | 0.346 | 1.4% | 0.195 |
| flake8 | 0.841 | 0.801 | 0.820 | 35.1% | 0.415 |

TrustGate не заменяет bandit/semgrep (на классических CWE-уязвимостях они
сильнее) - он закрывает их слепую зону: дефекты, характерные для
сгенерированного кода, где его recall 85% против максимум 34% у baseline.

## Слои Проверки

| слой | что делает |
|------|------------|
| L1 static | 14 детекторов `TG-D01..TG-D11`, `TG-D13..TG-D15`: hallucinated imports/API/kwargs, `eval/exec/os.system/yaml.load`, SQL string building, `shell=True`, отключенная TLS-верификация, weak hashes/random/ECB, broad except, stubs, dead code, tautological asserts, placeholders, insecure defaults |
| manifest scan | `TG-D12`: подозрительные зависимости в `pyproject.toml` и `requirements*.txt` |
| L2 dynamic | запускает pytest в Docker sandbox для single-file flow |
| L3 mutation | генерирует AST-мутанты и проверяет, убивают ли их тесты; работает и для single-file flow, и для repo-flow через `--project-mutation` |
| repo scan | проверяет git/project files, dependency manifests, optional project tests, policy gates, SARIF/HTML/JSON/GitHub annotations |

Анализируемый код не исполняется; для проверки атрибутов и сигнатур (TG-D02,
TG-D13) импортируются только stdlib-модули из фиксированного белого списка.
Если выполняются тесты, они запускаются только явно: single-file через Docker
sandbox или project tests через доверенную команду CI.

Вердикт детерминирован: TG-D01/TG-D12 сверяются с закоммиченным снапшотом
top-15000 PyPI-пакетов и first-party модулями репозитория, а не с тем, что
случайно установлено на машине. Учет локального окружения - опциональный флаг
`--trust-local-env`.

Гарантия честности вердикта: partial analysis никогда не продается как PASS.
Если project tests или mutation layer не запускались, результат понижается до
REVIEW - неполная проверка не может выглядеть как полная.

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

- [x] 14 статических детекторов (`TG-D01..TG-D11`, `TG-D13..TG-D15`)
  + manifest scan `TG-D12`;
- [x] детерминированный вердикт: снапшот top-15000 PyPI + first-party модули;
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
- [x] внешний бенчмарк на 245 samples: сравнение с `ruff`, `flake8`, `bandit`,
  `semgrep`, per-slice recall, ablation, FP-анализ
  (`experiment/benchmark-result.json`);
- [x] калибровка порогов Trust Score на корпусе
  (`experiment/calibration-result.json`, `docs/scoring_rationale.md`).

## Документация

- `docs/architecture.md` - архитектура;
- `docs/benchmark.md` - benchmark и план расширения корпуса;
- `docs/scoring_rationale.md` - обоснование score;
- `docs/threat_model.md` - модель угроз;
- `docs/defense_questions_ru.md` - вопросы для защиты;
- `docs/competition_ru.md` - описание для ITMO STARS.

## Ограничения

- Полная поддержка сейчас только для Python.
- Корпус v1 - 245 samples; его состав и известный шум меток описаны в
  `docs/benchmark.md`. Это рабочая калибровка, а не финальное исследование.
- На классических CWE-уязвимостях (SecurityEval) recall статического слоя
  0.20 - ниже bandit/semgrep (0.28-0.29): широкие классы вроде XSS, open
  redirect и path traversal требуют taint-анализа, которого в TrustGate нет
  осознанно. TrustGate - дополнительный слой рядом с ними, а не замена.
- Ноль false positives на корпусе v1 - результат на 74 clean-сэмплах, а не
  гарантия: детекторы эвристические, на другом коде FP возможны и
  подавляются `# trustgate: ignore TG-DXX`.
