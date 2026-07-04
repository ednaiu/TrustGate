
# Architecture

```
solution.py (+ tests)  -->  trustgate check
        |
        |-- L1  detectors.run_static      AST only, code is never imported
        |-- L2  sandbox.run_tests         docker: no net, 1 cpu, 512M, 64 pids, ro-mount
        |-- L3  mutation.evaluate         own AST mutator, needs green L2 baseline
        |
        '-- scoring.aggregate  ->  report.build  ->  markdown + report.json

git repo / project dir  -->  trustgate scan
        |
        |-- discover Python files from git ls-files / git diff / directory walk
        |-- run L1 static analysis per file
        |-- inspect dependency manifests (pyproject.toml, requirements*.txt)
        |-- optionally run a trusted project test command
        |-- aggregate findings once for the whole project
        '-- markdown + JSON + optional HTML/SARIF project report
```

## Modules

- `detectors.py` — 11 static checks (TG-D01..TG-D11). Pure functions
  `(tree, source) -> [Finding]`, registered in the `DETECTORS` list.
- `known_packages.py` — TG-D01 backend: stdlib names, local environment,
  bundled top-packages snapshot, Levenshtein for typosquat detection.
- `sandbox.py` — Docker runner. Classification relies on pytest exit codes,
  not output grepping. A timed-out container is explicitly killed.
- `mutation.py` — three mutation operators (compare, and/or, int constants),
  deterministic by seed, budget of 50 mutants. Mutants execute only through
  the sandbox runner injected by the caller.
- `scoring.py` — penalties from `weights.toml`; critical detectors
  (TG-D01..04) never saturate, three criticals force BLOCK.
- `cli.py` — wiring plus the degradation policy: no Docker means static-only
  analysis, `partial: true`, and mutation disabled (it executes code).
- `engine.py` — shared single-file analysis pipeline used by `check` and
  project scan internals.
- `scan.py` — repository/project workflow: discover Python files, scan all or
  changed files, inspect dependency manifests, optionally run a trusted project
  test command, emit SARIF, aggregate a project-level verdict.

## Invariants worth keeping

1. Analyzed code runs **only** inside the sandbox (L1 parses, never imports).
2. Disabling a layer can never *increase* the score (uniform missing-mutation
   penalty).
3. Two runs on the same input produce identical reports (fixed seeds).
4. Exit codes: 0 PASS, 1 REVIEW, 2 BLOCK, 3 bad input, 4 internal —
   argparse usage errors are remapped from 2 to 3.
5. Project scan executes tests only when the caller explicitly supplies a
   trusted command via `--project-tests`.
6. Project mutation is not implied by project tests; mutation remains scoped to
   the single-file sandbox flow until a project-level mutator exists.
