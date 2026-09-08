# Changelog

## Unreleased

- Documentation, report strings and code comments translated to English;
  `docs/competition_ru.md` renamed to `docs/overview.md` and
  `docs/defense_questions_ru.md` to `docs/defense_questions.md`.

## 1.5.0 - 2026-07-05

- All false positives of corpus v1 eliminated: the "TODO/FIXME in a comment"
  subcheck was removed from TG-D09 (mature OSS code is full of long-lived TODOs;
  real stubs are caught by the function body, "TODO: implement" strings through
  TG-D14). FPs on the clean group: 3 -> 0, precision 0.946 -> 1.0.
- Security detectors strengthened with high-precision patterns: TG-D03 catches
  os.system with a non-literal and yaml.load without SafeLoader; TG-D06 catches
  ssl._create_unverified_context, CERT_NONE and check_hostname = False;
  TG-D07 catches random used for secrets, DES and MODE_ECB.
- New TG-D15 "insecure runtime defaults": tempfile.mktemp, debug=True,
  extractall() without filtering.
- Metrics on corpus v1: F1 0.467 -> 0.526, recall 0.310 -> 0.357, recall on
  SecurityEval 0.138 -> 0.200 with zero FPs. The benchmark and the calibration
  were re-run and the numbers in the docs updated.
- Partial -> REVIEW is reformulated in the README as a verdict honesty
  guarantee rather than a limitation.

## 1.4.0 - 2026-07-05

- Deterministic TG-D01: a top-15000 PyPI snapshot in the repository,
  first-party modules of the scanned project, and the local environment only
  with an explicit `--trust-local-env`. The typosquat heuristic is limited to
  names of 5 characters or more.
- New detectors: TG-D13 (hallucinated keyword arguments, checked against
  `inspect.signature` for whitelisted stdlib) and TG-D14 (placeholder values in
  string literals). Version-guarded code is excluded from D02/D13.
- The external benchmark was carried out: a corpus of 245 samples
  (SecurityEval/Copilot, LLM solutions labeled by reference tests, defect
  injections, clean OSS), comparison against ruff/flake8/bandit/semgrep,
  per-slice recall, ablation, FP analysis. Results in
  `experiment/benchmark-result.json` and `docs/benchmark.md`.
- Verdict threshold calibration on the corpus: `BLOCK_ON_CRITICAL_COUNT` 3 -> 1
  (precision 1.0, FPR 0 on the clean group); the methodology is in
  `docs/scoring_rationale.md`, the computation in `experiment/calibrate.py`.
- Reports split findings into `llm_specific` / `general_quality`.
- Baseline tools in the benchmark are run once over the corpus directory; the
  tool versions are pinned.

## 1.3.0 - 2026-07-04

- Added project-level mutation testing: `trustgate scan . --project-mutation`.
- Added policy management: TOML gates, roles, and the policy's effect on the
  verdict.
- Extended the SQLite model to `projects -> scan_runs -> scan_findings`.
- Added an HTML dashboard for the history and detector finding trends.
- Added GitHub Checks annotations JSON export.
- Added an external benchmark runner: confusion matrix, false positive analysis
  and comparison against `ruff`, `flake8`, `bandit`, `semgrep`.
- Updated the documentation for the new repo flow and the honest 100+ corpus
  flow.

## 1.2.0 - 2026-07-04

- Added SQLite history: `trustgate scan . --save-history`.
- Added a ready-made GitHub workflow with SARIF upload and an HTML artifact.
- Hardened the Docker sandbox: `--cap-drop ALL`, `no-new-privileges`,
  read-only root, tmpfs for `/tmp`.
- Added GitHub-derived examples with attribution.
- Added a strict example policy, `trustgate.policy.toml`.
- Added the `docs/scoring_rationale.md` document.
- Localized the Markdown documentation.

## 1.1.0

- Added the project/git scan workflow: `trustgate scan .` and `--changed`.
- Added dependency manifest checks for `pyproject.toml` and
  `requirements*.txt`.
- Added an optional trusted project test command.
- Added SARIF export for GitHub code scanning.
- Added self-contained HTML reports.
- Added a shared analysis engine.
- The GitHub Action gained `mode: scan`.
- Added benchmark, overview, defense, taxonomy and threat-model docs.
- Added demo examples that do not pollute the project scan.
- Added tests for the project scan and the HTML CLI output.

## 1.0.0 - 2026-07-04

First release.

- L1: 11 static detectors `TG-D01..TG-D11`.
- L2: Docker sandbox test runner.
- L3: AST mutation testing.
- Trust Score with explainable penalties.
- CLI: `check`, `report`.
- JSON report and schema.
- GitHub Action.
- Experiment harness.
- 90+ tests and a coverage gate.
