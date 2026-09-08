# Attribution Of The GitHub Examples

The files in this folder exist to demonstrate TrustGate on realistic patterns
from open repositories. They deliberately use the `.py.example` extension so
that `trustgate scan .` does not treat them as the project's own code.

## PyGoat

- Repository: https://github.com/adeyosemanputra/pygoat
- License: MIT License
- Usage: `pygoat_minimized.py.example` contains a minimized reproduction of the
  patterns of the vulnerable training application. It is not a full copy of the
  source file.

## TheAlgorithms/Python

- Repository: https://github.com/TheAlgorithms/Python
- License: MIT License
- Usage: `thealgorithms_style_clean.py.example` contains a short self-contained
  example of algorithmic code in the repository's style. It is not a verbatim
  copy of the source file.

## How To Check

```bash
trustgate check examples/github/pygoat_minimized.py.example --no-sandbox
trustgate check examples/github/thealgorithms_style_clean.py.example --no-sandbox
```
