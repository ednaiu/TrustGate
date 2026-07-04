# TrustGate

Trust scoring for LLM-generated Python code. Takes a file (and optionally its
tests), runs three layers of analysis and answers one question: **can this
patch be merged?**

```
$ trustgate check solution.py --tests test_solution.py
## TrustGate: BLOCK (score 20/100)

| line | detector | severity | message                                             | -pts |
|------|----------|----------|-----------------------------------------------------|------|
| 1    | TG-D01   | critical | import 'requsets' looks like a typo of 'requests'   | 25   |
| 5    | TG-D03   | critical | eval() on non-literal data                          | 25   |
```

## Why

LLM assistants produce code with a specific defect profile that classic
linters were never designed for: hallucinated imports and APIs, plausible but
wrong logic, silently swallowed errors, tests that assert nothing. TrustGate
targets exactly that profile.

## Layers

| | layer | what it does |
|---|-------|--------------|
| L1 | static | 11 AST detectors (TG-D01..TG-D11): hallucinated imports/attributes, eval/exec, SQL string building, shell=True, verify=False, weak hashes for secrets, broad except, stubs, dead code, tautological asserts |
| L2 | dynamic | runs the provided pytest suite in Docker: no network, 1 CPU, 512M RAM, 64 pids, read-only mount, 30s wall time |
| L3 | mutation | own AST mutator (compare/boolop/int-constant operators). If mutants survive the tests, the tests don't test much |

Findings are aggregated into a **Trust Score** (0-100) with explainable
per-finding penalties (`weights.toml`), then a verdict: PASS (>= 76),
REVIEW (40-75), BLOCK (<= 39, or 3+ critical findings).

The analyzed code is **never executed outside the sandbox** — L1 only parses.
No Docker? The tool degrades to static-only analysis and marks the report
`partial` (mutation analysis is disabled too, since it requires execution).

## Install & use

```
pip install -e ".[dev]"
trustgate check solution.py --tests test_solution.py --json report.json
trustgate report report.json        # re-render a saved report
```

Exit codes: 0 PASS, 1 REVIEW, 2 BLOCK, 3 bad input, 4 internal error.

## Status

- [x] L1 static layer, scoring, CLI, JSON report (schema in `schemas/`)
- [x] L2 sandbox runner (needs Docker; degrades gracefully without it)
- [x] L3 mutation analysis with a green-baseline guard
- [x] GitHub Action (`action.yml`): BLOCK fails the job, REVIEW passes with a summary
- [x] Experiment harness (`experiment/`): corpus generation for 2 LLM providers,
      seeded defect injection, metrics vs flake8+bandit baseline

Running the full experiment needs Docker and API keys
(`OPENAI_API_KEY`, `GIGACHAT_TOKEN`): `make experiment`.

## Limitations

- Python only.
- TG-D01 knows stdlib, the local environment and a bundled top-packages list;
  a rare legitimate package is reported as "unknown" (major), not critical.
- TG-D02 checks attributes only for a whitelist of stdlib modules; dynamic
  `getattr` access is out of scope.
- Mutation analysis needs a green test baseline: if the original tests already
  fail, L3 is skipped (`red_baseline`) instead of producing a garbage score.
