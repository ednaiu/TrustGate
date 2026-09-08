# TrustGate

Author: Edna Iusupova ([github.com/ednaiu](https://github.com/ednaiu))

TrustGate is a quality gate for Python code focused on the defect profile of
generated code: hallucinated imports and APIs, non-existent kwargs, stubs,
placeholder values, dangerous quick fixes. It checks a single file, a whole
repository, or only the files changed in git, and answers one practical
question: **can this patch be merged?**

```bash
trustgate scan . --project-tests "python -m pytest -q" --project-mutation --sarif trustgate.sarif
```

The result is an explainable `Trust Score` from 0 to 100 and a verdict:

- `PASS` - safe to accept;
- `REVIEW` - needs manual review;
- `BLOCK` - high risk, CI should fail.

## Why

LLM assistants often write code with a distinctive defect profile: invented
imports, non-existent APIs and keyword arguments, placeholder values instead of
configuration, stubs instead of a solution, and dependencies that look
plausible but do not exist.

In this project that claim is measured, not declared. On a corpus of 245
samples (real Copilot code from SecurityEval, LLM solutions labeled by
reference tests, clean OSS files - see `docs/benchmark.md`):

| tool | precision | recall | F1 | FPR on clean | recall on the generated-code profile |
|------|-----------|--------|-----|--------------|--------------------------------------|
| **TrustGate (static)** | **1.000** | 0.357 | **0.526** | **0.0%** | **0.854** |
| bandit | 0.962 | 0.298 | 0.455 | 2.7% | 0.341 |
| semgrep | 1.000 | 0.263 | 0.417 | 0.0% | 0.171 |
| ruff | 0.973 | 0.211 | 0.346 | 1.4% | 0.195 |
| flake8 | 0.841 | 0.801 | 0.820 | 35.1% | 0.415 |

TrustGate does not replace bandit/semgrep (they are stronger on classic CWE
vulnerabilities) - it covers their blind spot: defects typical of generated
code, where its recall is 85% against at most 34% for the baselines.

## Analysis Layers

| layer | what it does |
|-------|--------------|
| L1 static | 14 detectors `TG-D01..TG-D11`, `TG-D13..TG-D15`: hallucinated imports/APIs/kwargs, `eval/exec/os.system/yaml.load`, SQL string building, `shell=True`, disabled TLS verification, weak hashes/random/ECB, broad except, stubs, dead code, tautological asserts, placeholders, insecure defaults |
| manifest scan | `TG-D12`: suspicious dependencies in `pyproject.toml` and `requirements*.txt` |
| L2 dynamic | runs pytest in a Docker sandbox for the single-file flow |
| L3 mutation | generates AST mutants and checks whether the tests kill them; works both in the single-file flow and in the repo flow via `--project-mutation` |
| repo scan | checks git/project files, dependency manifests, optional project tests, policy gates, SARIF/HTML/JSON/GitHub annotations |

The analyzed code is never executed; to inspect attributes and signatures
(TG-D02, TG-D13) only stdlib modules from a fixed allowlist are imported. If
tests are executed, that happens explicitly only: single-file tests through the
Docker sandbox, or project tests through a trusted CI command.

The verdict is deterministic: TG-D01/TG-D12 are checked against a committed
snapshot of the top-15000 PyPI packages and the repository's first-party
modules, not against whatever happens to be installed on the machine. Taking
the local environment into account is an opt-in flag, `--trust-local-env`.

Verdict honesty guarantee: a partial analysis is never sold as a PASS. If the
project tests or the mutation layer did not run, the result is downgraded to
REVIEW - an incomplete check must not look like a complete one.

## Installation And Usage

```bash
pip install -e ".[dev]"

trustgate check solution.py --tests test_solution.py --json report.json
trustgate check solution.py --no-sandbox --html report.html

trustgate scan . --json project-report.json
trustgate scan . --changed --base origin/main
trustgate scan . --project-tests "python -m pytest -q"
trustgate scan . --project-tests "python -m pytest -q" --project-mutation
trustgate scan . --sarif trustgate.sarif --github-annotations annotations.json --html trustgate.html
trustgate scan . --policy trustgate.policy.toml --user edna

trustgate history --db trustgate-history.sqlite
trustgate dashboard --db trustgate-history.sqlite --html trustgate-dashboard.html
trustgate report report.json
```

Exit codes: `0 PASS`, `1 REVIEW`, `2 BLOCK`, `3 bad input`, `4 internal error`.

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
    user: edna
    sarif: trustgate.sarif
    github-annotations: annotations.json
    html: trustgate-report.html
```

The repository also ships a ready-made workflow:
`.github/workflows/trustgate.yml`. It generates SARIF, HTML and JSON reports
and uploads the SARIF to GitHub code scanning.

## Verification And Demo

```bash
make test
make scan
make benchmark
make demo-report
```

The examples live in `examples/`. The files are named `*.py.example` so that a
plain `trustgate scan .` does not treat the demonstration vulnerabilities as
code of the project itself.

## Status

- [x] 14 static detectors (`TG-D01..TG-D11`, `TG-D13..TG-D15`)
  + manifest scan `TG-D12`;
- [x] deterministic verdict: top-15000 PyPI snapshot + first-party modules;
- [x] Docker sandbox for single-file pytest;
- [x] mutation testing for the single-file flow;
- [x] project/git scan: `trustgate scan .`, `--changed`;
- [x] dependency manifest scan for `pyproject.toml` and `requirements*.txt`;
- [x] optional project tests: `--project-tests`;
- [x] project-level mutation testing: `--project-mutation`;
- [x] policy management: merge gates and roles in TOML;
- [x] JSON, HTML and SARIF reports;
- [x] GitHub Checks annotations JSON;
- [x] SQLite persistence: project -> scan runs -> findings -> detector trends;
- [x] history dashboard: `trustgate dashboard`;
- [x] GitHub Action and SARIF upload workflow;
- [x] reproducible smoke benchmark;
- [x] external benchmark on 245 samples: comparison against `ruff`, `flake8`,
  `bandit`, `semgrep`, per-slice recall, ablation, FP analysis
  (`experiment/benchmark-result.json`);
- [x] Trust Score threshold calibration on the corpus
  (`experiment/calibration-result.json`, `docs/scoring_rationale.md`).

## Documentation

- `docs/architecture.md` - architecture;
- `docs/benchmark.md` - benchmark and corpus extension plan;
- `docs/scoring_rationale.md` - score rationale;
- `docs/threat_model.md` - threat model;
- `docs/defense_questions.md` - defense Q&A;
- `docs/overview.md` - project overview.

## Limitations

- Full support currently exists for Python only.
- Corpus v1 is 245 samples; its composition and known label noise are described
  in `docs/benchmark.md`. This is a working calibration, not a final study.
- On classic CWE vulnerabilities (SecurityEval) the static layer's recall is
  0.20 - below bandit/semgrep (0.28-0.29): broad classes such as XSS, open
  redirect and path traversal require taint analysis, which TrustGate
  deliberately does not have. TrustGate is an additional layer next to them,
  not a replacement.
- Zero false positives on corpus v1 is a result on 74 clean samples, not a
  guarantee: the detectors are heuristic, on other code FPs are possible and
  are suppressed with `# trustgate: ignore TG-DXX`.
