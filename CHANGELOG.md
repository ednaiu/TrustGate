# История Изменений

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
