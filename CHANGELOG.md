# Changelog

## 1.1.0 — unreleased

- Added project/git scan workflow: `trustgate scan .` and `--changed`.
- Added self-contained HTML reports for single-file and project scans.
- Added shared analysis engine for CLI and scan use cases.
- Updated GitHub Action to support `mode: scan`.
- Added competition, taxonomy and threat-model documentation.
- Added demo examples that do not pollute project scans.
- Added tests for project scan and HTML CLI output.

## 1.0.0 — 2026-07-04

First release.

- L1: 11 static detectors for LLM-specific defects (TG-D01..TG-D11)
- L2: Docker sandbox test runner (no network, cpu/mem/pids limits)
- L3: own AST mutator, 3 operators, green-baseline guard
- Trust Score with explainable penalties, `weights.toml` config
- CLI (`check`, `report`), JSON report + schema, GitHub Action
- Experiment harness: corpus generation (2 LLM providers), defect
  injection, metrics vs flake8+bandit baseline
- 90+ tests, coverage gate 80%, CI matrix for Python 3.10-3.12
