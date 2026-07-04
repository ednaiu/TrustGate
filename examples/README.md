# Demo examples

These files are intentionally named `*.py.example` so project scans do not
accidentally treat the bad examples as repository code.

Run:

```bash
trustgate check examples/pass_solution.py.example --no-sandbox
trustgate check examples/review_solution.py.example --no-sandbox --html review.html
trustgate check examples/block_solution.py.example --no-sandbox --html block.html
```

Expected behavior:

- `pass_solution.py.example` should pass in static-only mode.
- `review_solution.py.example` should require review because it has risky but
  not immediately blocking code.
- `block_solution.py.example` should block because it contains critical
  LLM-style defects.
