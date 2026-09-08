# Trust Score Rationale

The Trust Score is not a mathematical proof of correctness. It is an
explainable risk score for CI and code review, and its thresholds are
calibrated on an external corpus (see below), not eyeballed.

If the analysis is partial, a PASS must not mask that incompleteness: such a
result is downgraded to REVIEW.

## Principle

Scoring starts at 100 points. Every problem subtracts a penalty from
`weights.toml`. Then the verdict is formed:

- `BLOCK`: at least one critical finding, or score <= 39;
- `PASS`: score >= 76 and no critical findings;
- `REVIEW`: everything else.

## Calibration On The Corpus (v1, 245 samples)

The thresholds were verified with `experiment/calibrate.py` on the labeled
corpus `experiment/corpus/corpus.json` (171 defective / 74 clean, composition
described in `docs/benchmark.md`). A grid search over
`block_threshold x critical_count` with the FPR on the clean group constrained
to <= 10% produced:

| BLOCK rule | precision | recall | FPR on clean |
|------------|-----------|--------|--------------|
| old: score<=39 or >=3 criticals | 0.0 | 0.0 | 0.0 |
| current: score<=39 or >=1 critical | 1.000 | 0.152 | 0.000 |
| best F1 on the grid (score<=70) | 1.000 | 0.164 | 0.000 |

The conclusions fixed in the code:

1. **The old "3 criticals" rule never fired**: the median defective file
   carries exactly one critical finding. The rule was replaced with
   `BLOCK_ON_CRITICAL_COUNT = 1` ([trustgate/scoring.py](../trustgate/scoring.py)).
2. A single critical finding blocks with precision 1.0 and zero FPR on the
   corpus clean group - the most precise signal available.
3. The "best F1" variant (score<=70) was rejected: it collapses the REVIEW
   zone, and REVIEW is a deliberate part of the model - a human, not automation,
   should look at contentious patches.

Reproduction:

```bash
python experiment/calibrate.py --corpus experiment/corpus/corpus.json
```

The result is stored in `experiment/calibration-result.json`.

## Why Critical Detectors Do Not Saturate

For `TG-D01..TG-D04` and `TG-D13` the penalties are not bounded by the
saturation cap:

- hallucinated import;
- non-existent API;
- dangerous execution;
- SQL string building;
- hallucinated keyword argument.

Each such defect is a merge blocker on its own, so several critical findings
must not collapse into a single penalty ceiling.

## Why Some Defects Yield REVIEW Rather Than BLOCK

`shell=True`, `verify=False`, broad except, stubs and weak hashes matter, but
they do not always mean an immediate merge ban. TrustGate separates:

- detection - the problem was found;
- policy - is the problem enough for a `BLOCK`.

So a single major finding may leave the score in `PASS`, yet the finding still
appears in Markdown/HTML/SARIF.

## Calibration Limitations

Honest caveats that are worth stating outright:

- Corpus v1 is 245 samples; this is a working calibration, not final scientific
  truth. The recomputation scheme is fixed and repeatable as the corpus grows.
- The calibration was performed on the static layer (the score without
  dynamic/mutation penalties): in the repo flow it is the static layer that
  determines most verdicts. The score<=39 threshold remains as a safeguard for
  the full pipeline, where failed tests and a weak mutation score add to the
  penalties.
- The individual detector weights (`weights.toml`) were not grid-searched: under
  the "1 critical = BLOCK" rule their influence on the verdict is secondary; a
  per-detector ablation is in `experiment/benchmark-result.json`.
