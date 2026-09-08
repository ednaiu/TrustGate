# Demo Examples

The files use the `.py.example` extension so that `trustgate scan .` does not
mistake the demonstration vulnerabilities for the project's own code.

## Running

```bash
trustgate check examples/pass_solution.py.example --no-sandbox
trustgate check examples/review_solution.py.example --no-sandbox --html review.html
trustgate check examples/block_solution.py.example --no-sandbox --html block.html
trustgate check examples/github/pygoat_minimized.py.example --no-sandbox
trustgate check examples/github/thealgorithms_style_clean.py.example --no-sandbox
```

## Expected Result

- `pass_solution.py.example` - a clean example.
- `review_solution.py.example` - a risky pattern, needs review.
- `block_solution.py.example` - critical LLM-style defects, must be `BLOCK`.
- `github/pygoat_minimized.py.example` - realistic vulnerable patterns from an
  open-source security training project.
- `github/thealgorithms_style_clean.py.example` - clean algorithmic code.

The attribution for the GitHub examples is in
`examples/github/ATTRIBUTION.md`.
