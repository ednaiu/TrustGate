# TrustGate Overview

Author: Edna Iusupova ([github.com/ednaiu](https://github.com/ednaiu))
Repository: `github.com/ednaiu/TrustGate`

## In Short

TrustGate is a tool for checking Python code that may have been written with the
help of an LLM. It runs in a repository or in CI and produces a clear verdict:
`PASS`, `REVIEW` or `BLOCK`.

The core idea: ordinary linters are good at style and at part of the security
problems, but they work worse on typical LLM mistakes - invented libraries,
non-existent APIs and keyword arguments, placeholder values, stubs instead of a
solution.

In this project that idea is **measured**: on a corpus of 245 samples,
TrustGate's recall on the generated-code defect profile is 0.854 against 0.341
for bandit and 0.171 for semgrep, with zero false positives on clean code
(`docs/benchmark.md`, `experiment/benchmark-result.json`).

## Why This Is An Information System

The project contains not only an analysis algorithm but a full data processing
flow:

1. Data source - a git repository, a PR diff, or a single Python file.
2. Processing - static detectors, dependency manifest scan, sandboxed pytest,
   mutation testing.
3. Result storage - a JSON report following a schema.
4. Presentation - Markdown for CI, HTML for demos, SARIF for GitHub code
   scanning.
5. Integration - a CLI and a GitHub Action.

That makes TrustGate a small quality gate for the development process rather
than a one-off script.

## What Is Already Done

- 14 static detectors (`TG-D01..TG-D11`, `TG-D13..TG-D15`) plus the dependency
  manifest scan `TG-D12`.
- A deterministic verdict: hallucinated imports are checked against a committed
  snapshot of the top-15000 PyPI packages and the repository's first-party
  modules, not against the local environment (the local environment is an opt-in
  flag, `--trust-local-env`).
- An external benchmark on 245 samples: real Copilot code (SecurityEval, MSR
  2022), LLM solutions labeled by reference tests, clean OSS files; comparison
  against ruff, flake8, bandit, semgrep; ablation and FP analysis.
- Trust Score threshold calibration on the corpus: the rule "one critical
  finding = BLOCK" has precision 1.0 and FPR 0 (`docs/scoring_rationale.md`).
- Safe test execution in Docker: no network, with CPU/RAM/PID limits.
- Mutation testing with a fixed seed and a mutant limit: single-file and repo
  flow via `--project-mutation`.
- An explainable Trust Score 0-100 that splits findings into the
  "generated-code profile" and "general quality".
- CLI: `check`, `scan`, `report`, `history`, `dashboard`.
- Git workflow: `trustgate scan .` and `trustgate scan . --changed`.
- Dependency manifest scan for `pyproject.toml` and `requirements*.txt`.
- Optional project tests: `trustgate scan . --project-tests "python -m pytest -q"`.
- SARIF export for GitHub code scanning.
- GitHub Checks annotations JSON.
- Policy management: TOML gates and the `viewer`, `reviewer`, `maintainer` roles.
- SQLite persistence: `project -> scan runs -> findings -> detector trends`.
- A dashboard over the scan history.
- A GitHub Action for pull requests.
- A JSON schema and HTML reports.
- A test suite for detectors, scoring, sandbox, CLI and project scan
  (127 tests).
- A reproducible smoke benchmark: `experiment/static_benchmark.py`.
- A fully reproducible corpus pipeline: `generate_corpus.py` (LLM solutions) ->
  `build_corpus.py` (assembly with provenance) -> `benchmark_external.py`
  (metrics) -> `calibrate.py` (thresholds).

## Personal Contribution

I designed TrustGate as a comprehensible system built from small modules:

- `detectors.py` - the defect detection rules;
- `sandbox.py` - safe test execution;
- `mutation.py` - mutant generation;
- `scoring.py` - score computation;
- `scan.py` - the git/project workflow;
- `action.yml` - running in CI.

The code is deliberately kept simple: no heavy framework and no "magic", so
that every decision can be explained.

## What Can Be Shown In A Demo

1. Checking a single solution:

```bash
trustgate check examples/block_solution.py.example --no-sandbox --html report.html
```

2. Checking the whole project:

```bash
trustgate scan . --json project-report.json --html project-report.html --sarif trustgate.sarif
```

3. Checking only the changed files:

```bash
trustgate scan . --changed --base HEAD
```

4. Checking the project together with a trusted test command and the mutation
   layer:

```bash
trustgate scan . --project-tests "python -m pytest -q" --project-mutation
```

5. A merge decision policy:

```bash
trustgate scan . \
  --project-tests "python -m pytest -q" \
  --project-mutation \
  --policy trustgate.policy.toml \
  --user edna
```

6. The history dashboard:

```bash
trustgate scan . --save-history trustgate-history.sqlite
trustgate dashboard --db trustgate-history.sqlite --html trustgate-dashboard.html
```

7. The GitHub Action in a pull request: `BLOCK` fails, `REVIEW` leaves a
   summary, `PASS` goes through.

## Honest Limitations

- If the project tests or the mutation layer did not run, TrustGate no longer
  returns `PASS` on a partial analysis.
- Trusted project tests and project mutation are executed in an isolated
  temporary copy of the repository, not in the source tree.
- Full support currently exists for Python only.
- On classic CWE vulnerabilities the static layer's recall is below
  bandit/semgrep (0.20 against 0.28-0.29) - TrustGate complements them rather
  than replacing them; this is stated directly in `docs/benchmark.md`.

## Weak Spots I Am Aware Of

- Corpus v1 (245 samples) contains known label noise: the "defective" label for
  SecurityEval is inherited from the dataset's construction; the generative
  defect profile slice consists of controlled injections into real LLM code.
  Both facts are recorded in the provenance, and the recomputation scheme is
  fixed.
- Zero false positives on corpus v1 is a result on 74 clean samples (and it was
  earned: the 3 FPs of the first version were analyzed and eliminated through FP
  analysis), not a guarantee for arbitrary code; suppression is done with an
  inline comment.
- TG-D02/TG-D13 check attributes and signatures against the stdlib of the Python
  version TrustGate runs on; version-guarded code (`sys.version_info`) is
  excluded from the check.

## Development Plan

The nearest practical plan:

1. Extend the corpus to 500+ samples: more generator models, complex clean LLM
   code, less label noise through manual verification of the SecurityEval slice.
2. Add JavaScript/TypeScript as the next language.
3. Add a web dashboard mode with authentication on top of the current SQLite
   model.
4. Extend policy roles to integrate with GitHub teams.

The main goal of the development is to make TrustGate not a replacement for
linters, but a separate trust-control layer for AI-generated code.
