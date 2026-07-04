# Benchmark plan and current reproducible smoke test

TrustGate should not rely on claims like "classic linters miss LLM defects"
without data. This page separates the current reproducible smoke benchmark from
the larger research benchmark that still has to be collected.

## Current versioned benchmark

Data: `experiment/static_benchmark_cases.json`  
Runner: `python experiment/static_benchmark.py`

The current corpus is intentionally small and curated. It checks that every
static detector class has at least one reproducible example and that clean
examples stay clean.

Expected current result:

| metric | value |
|--------|-------|
| cases | 12 |
| defective | 10 |
| clean | 2 |
| static detector precision | 1.000 |
| static detector recall | 1.000 |
| static detector F1 | 1.000 |
| expected detector recall | 1.000 |

Important: this measures whether the static layer finds the intended defect. It
does not claim that every finding must block a merge. TrustGate may return
`REVIEW` for lower-severity defects by design.

## Larger benchmark target

The larger benchmark should include at least 100 generated Python solutions:

- multiple tasks from `experiment/tasks/`;
- multiple LLM providers;
- clean/defective labels from reference tests;
- injected defects with known ground truth;
- comparison with `ruff`, `flake8`, `bandit` and `semgrep`.

Minimum report:

| tool | precision | recall | F1 | false positive rate |
|------|-----------|--------|----|---------------------|
| TrustGate | TBD | TBD | TBD | TBD |
| ruff/flake8 | TBD | TBD | TBD | TBD |
| bandit | TBD | TBD | TBD | TBD |
| semgrep | TBD | TBD | TBD | TBD |

This prevents overclaiming. The current repository proves the mechanism and a
small reproducible corpus; the full research claim requires the larger table.
