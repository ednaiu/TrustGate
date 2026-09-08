# Taxonomy Of LLM Code Defects

TrustGate does not replace linters. It covers the error profile that frequently
appears in AI-generated code.

| id | defect class | why it matters |
|----|--------------|----------------|
| TG-D01 | invented or typo import | an LLM can invent a plausible package name |
| TG-D02 | non-existent stdlib/API attribute | the call looks realistic, but the API does not exist |
| TG-D03 | dangerous execution | `eval`, `exec`, `pickle.loads` often appear as a quick shortcut |
| TG-D04 | SQL string building | f-strings in SQL create an injection risk |
| TG-D05 | `shell=True` | a dynamic shell command is dangerous |
| TG-D06 | `verify=False` | disabling TLS validation often slips into "make it work" patches |
| TG-D07 | weak hash for secrets | MD5/SHA1 are unfit for passwords and tokens |
| TG-D08 | broad swallowed exception | the error is hidden instead of handled |
| TG-D09 | stub instead of implementation | `pass`, TODO or `NotImplementedError` stay in the code |
| TG-D10 | dead code | a sign of mechanically assembled or unreviewed code |
| TG-D11 | tautological assert | the test looks like a test but proves nothing |
| TG-D12 | suspicious dependency | an LLM can invent a package in `pyproject.toml` or `requirements.txt` |
| TG-D13 | hallucinated keyword argument | the function exists, the kwarg does not: a classic API hallucination |
| TG-D14 | placeholder value | `"YOUR_API_KEY_HERE"` instead of real configuration reaches the merge |
| TG-D15 | insecure runtime default | `mktemp`, `debug=True`, `extractall()` - patterns from outdated tutorials that LLMs keep reproducing |

## What TrustGate Does Not Promise

- it does not prove semantic correctness;
- it does not perform full taint/dataflow analysis;
- it does not know every PyPI package;
- it does not replace a security review.

## Why A Separate Tool Is Useful

Conventional tools check style, syntax, type hints and a share of security
issues. TrustGate asks something different: "does this AI-generated patch look
reliable enough to pass CI without a manual review?"
