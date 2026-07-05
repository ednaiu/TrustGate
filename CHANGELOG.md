# История Изменений

## 1.4.0 - 2026-07-05

- Детерминированный TG-D01: снапшот top-15000 PyPI в репозитории, first-party
  модули сканируемого проекта, локальное окружение - только по явному
  `--trust-local-env`. Typosquat-эвристика ограничена именами от 5 символов.
- Новые детекторы: TG-D13 (hallucinated keyword arguments, сверка с
  `inspect.signature` для whitelisted stdlib) и TG-D14 (placeholder-значения
  в строковых литералах). Version-guarded код исключен из D02/D13.
- Внешний бенчмарк выполнен: корпус 245 samples (SecurityEval/Copilot,
  LLM-решения с разметкой reference-тестами, инъекции дефектов, clean OSS),
  сравнение с ruff/flake8/bandit/semgrep, per-slice recall, ablation,
  FP-анализ. Результаты в `experiment/benchmark-result.json` и
  `docs/benchmark.md`.
- Калибровка порогов вердикта на корпусе: `BLOCK_ON_CRITICAL_COUNT` 3 -> 1
  (precision 1.0, FPR 0 на clean-группе); методика в
  `docs/scoring_rationale.md`, расчет в `experiment/calibrate.py`.
- Отчеты разбивают findings на `llm_specific` / `general_quality`.
- Baseline-инструменты в бенчмарке запускаются один раз на директорию
  корпуса; зафиксированы версии инструментов.

## 1.3.0 - 2026-07-04

- Добавлен project-level mutation testing: `trustgate scan . --project-mutation`.
- Добавлен policy management: TOML-gates, роли и влияние политики на verdict.
- Расширена SQLite-модель до `projects -> scan_runs -> scan_findings`.
- Добавлен HTML dashboard по истории и динамике detector findings.
- Добавлен GitHub Checks annotations JSON export.
- Добавлен external benchmark runner: confusion matrix, false positive analysis
  и сравнение с `ruff`, `flake8`, `bandit`, `semgrep`.
- Обновлены русские документы под новый repo-flow и честный 100+ corpus flow.

## 1.2.0 - 2026-07-04

- Добавлен SQLite history: `trustgate scan . --save-history`.
- Добавлен готовый GitHub workflow с SARIF upload и HTML artifact.
- Усилен Docker sandbox: `--cap-drop ALL`, `no-new-privileges`, read-only root,
  tmpfs для `/tmp`.
- Добавлены GitHub-derived examples с атрибуцией.
- Добавлен пример строгой политики `trustgate.policy.toml`.
- Добавлен документ `docs/scoring_rationale.md`.
- Markdown-документация переведена на русский.

## 1.1.0

- Добавлен project/git scan workflow: `trustgate scan .` и `--changed`.
- Добавлены проверки dependency manifests для `pyproject.toml` и
  `requirements*.txt`.
- Добавлена optional trusted project test command.
- Добавлен SARIF export для GitHub code scanning.
- Добавлены self-contained HTML reports.
- Добавлен общий analysis engine.
- GitHub Action получил `mode: scan`.
- Добавлены benchmark, competition, defense, taxonomy и threat-model docs.
- Добавлены demo examples, которые не загрязняют project scan.
- Добавлены тесты для project scan и HTML CLI output.

## 1.0.0 - 2026-07-04

Первый релиз.

- L1: 11 статических детекторов `TG-D01..TG-D11`.
- L2: Docker sandbox test runner.
- L3: AST mutation testing.
- Trust Score с объяснимыми penalties.
- CLI: `check`, `report`.
- JSON report и schema.
- GitHub Action.
- Experiment harness.
- 90+ тестов и coverage gate.
