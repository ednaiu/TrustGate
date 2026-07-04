# Архитектура

## Потоки

```text
solution.py (+ tests)  -->  trustgate check
        |
        |-- L1  detectors.run_static      AST-only, код не импортируется
        |-- L2  sandbox.run_tests         Docker: no net, CPU/RAM/PID limits, ro-mount
        |-- L3  mutation.evaluate         AST-мутаторы, только после green baseline
        |
        '-- scoring.aggregate  ->  report.build  ->  Markdown/JSON/HTML

git repo / project dir  -->  trustgate scan
        |
        |-- поиск Python-файлов через git ls-files / git diff / directory walk
        |-- L1 static analysis по файлам
        |-- проверка dependency manifests
        |-- optional trusted project tests
        |-- агрегация project-level verdict
        '-- Markdown/JSON/HTML/SARIF + SQLite history
```

## Модули

- `detectors.py` - статические AST-детекторы `TG-D01..TG-D11`.
- `known_packages.py` - база популярных пакетов и Levenshtein для typo checks.
- `sandbox.py` - Docker runner для single-file pytest.
- `mutation.py` - AST-мутаторы: comparisons, bool ops, int constants.
- `scoring.py` - penalties, thresholds, итоговый verdict.
- `report.py` - Markdown/HTML/JSON отчеты.
- `engine.py` - общий single-file pipeline.
- `scan.py` - project/git workflow, dependency scan, SARIF.
- `history.py` - SQLite history для project scans.
- `cli.py` - команды `check`, `scan`, `report`, `history`.

## Инварианты

1. Статический слой не импортирует проверяемый код.
2. Мутации не запускаются без sandbox.
3. Missing dynamic/mutation verdict не должен увеличивать score.
4. Project tests запускаются только явно через `--project-tests`.
5. Project-level mutation пока не подразумевается.
6. Два запуска на одинаковом input должны давать одинаковый report, кроме timing.
7. Exit codes: `0 PASS`, `1 REVIEW`, `2 BLOCK`, `3 input`, `4 internal`.
