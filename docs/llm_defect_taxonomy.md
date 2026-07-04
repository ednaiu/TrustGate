# LLM defect taxonomy

This document explains why TrustGate detectors exist. The goal is not to
replace linters, but to cover mistakes that often appear in generated code.

| id | defect class | why it matters |
|----|--------------|----------------|
| TG-D01 | Hallucinated or typo import | LLMs can invent plausible package names or misspell popular ones. |
| TG-D02 | Non-existent stdlib attribute | Generated code often calls an API that looks real but does not exist. |
| TG-D03 | Dangerous execution | `eval`, `exec`, and `pickle.loads` are common unsafe shortcuts. |
| TG-D04 | SQL string building | LLMs frequently use f-strings for SQL examples. |
| TG-D05 | `shell=True` | Shell execution is risky when command text is dynamic. |
| TG-D06 | `verify=False` | Disabling TLS validation is a typical "make it work" patch. |
| TG-D07 | Weak hash for secrets | MD5/SHA1 may be acceptable for checksums, not for passwords or tokens. |
| TG-D08 | Broad swallowed exception | Generated code may hide failures instead of handling them. |
| TG-D09 | Stub left as implementation | LLM output sometimes contains `pass`, TODOs, or `NotImplementedError`. |
| TG-D10 | Dead code | A sign of low-quality or mechanically stitched code. |
| TG-D11 | Tautological assert | Tests can look present while proving nothing. |
| TG-D12 | Suspicious dependency | LLMs can invent package names in `pyproject.toml` or `requirements.txt`. |

## What TrustGate intentionally does not claim

- It does not prove semantic correctness.
- It does not perform full dataflow or taint analysis yet.
- It does not know every third-party package.
- It does not replace human review for security-sensitive code.

## Why a separate tool is still useful

Classic tools are strong, but they optimize for broad style, syntax and
security checks. TrustGate is narrower: it asks whether a generated patch looks
trustworthy enough to merge or whether it needs review.
