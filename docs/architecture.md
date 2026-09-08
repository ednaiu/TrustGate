# Architecture

## Flows

```text
solution.py (+ tests)  -->  trustgate check
        |
        |-- L1  detectors.run_static      AST-only; for D02/D13 only whitelisted
        |                                 stdlib modules are imported
        |-- L2  sandbox.run_tests         Docker: no net, CPU/RAM/PID limits, ro-mount
        |-- L3  mutation.evaluate         AST mutators, only after a green baseline
        |
        '-- scoring.aggregate  ->  report.build  ->  Markdown/JSON/HTML

git repo / project dir  -->  trustgate scan
        |
        |-- Python file discovery via git ls-files / git diff / directory walk
        |-- L1 static analysis per file
        |-- dependency manifest check
        |-- optional trusted project tests
        |-- project-level verdict aggregation
        '-- Markdown/JSON/HTML/SARIF + SQLite history
```

## Modules

- `detectors.py` - static AST detectors `TG-D01..TG-D11`, `TG-D13..TG-D15`.
- `known_packages.py` - top-15000 PyPI snapshot (`data/pypi_top_packages.txt`),
  curated import aliases and Levenshtein for typo checks.
- `sandbox.py` - Docker runner for single-file pytest.
- `mutation.py` - AST mutators: comparisons, bool ops, int constants.
- `scoring.py` - penalties, thresholds, final verdict.
- `report.py` - Markdown/HTML/JSON reports.
- `engine.py` - shared single-file pipeline.
- `scan.py` - project/git workflow, dependency scan, SARIF.
- `history.py` - SQLite history for project scans.
- `cli.py` - the `check`, `scan`, `report`, `history` commands.

## Invariants

1. The static layer never imports the analyzed code (to inspect attributes and
   signatures only stdlib modules from a fixed allowlist are imported).
2. Mutations never run without a sandbox.
3. A missing dynamic/mutation verdict must not increase the score.
4. Project tests run only explicitly via `--project-tests`; project-level
   mutation runs only together with them via `--project-mutation`.
5. The verdict does not depend on locally installed packages
   (without an explicit `--trust-local-env`).
6. Two runs on identical input must produce identical reports, except timing.
7. Exit codes: `0 PASS`, `1 REVIEW`, `2 BLOCK`, `3 input`, `4 internal`.
