# Threat Model

TrustGate analyzes code that may be faulty or unsafe. That is why parsing,
execution and reporting are separated.

## Assets

- The CI runner or the developer's machine.
- The repository source code.
- Secrets and credentials in CI.
- The integrity of the TrustGate report.

## Risks

1. The analyzed code tries to reach the network.
2. The analyzed code tries to read or modify files outside the workspace.
3. The analyzed code consumes too much CPU/RAM/processes.
4. A test failure is misclassified.
5. A partial report is taken for a complete verdict.
6. A dependency manifest contains a hallucinated or typo-squatted package.

## Current Controls

- The static layer only parses the AST and never imports the analyzed code; for
  TG-D02/TG-D13 exclusively stdlib modules from a fixed allowlist
  (`ATTR_CHECK_MODULES`) are imported.
- The TG-D01/TG-D12 verdict is deterministic: a PyPI snapshot lives in the
  repository, and the local environment is taken into account only with an
  explicit `--trust-local-env`.
- The project scan checks `pyproject.toml` and `requirements*.txt`.
- The single-file dynamic layer runs in Docker without network access.
- The Docker runner applies CPU/RAM/PID limits.
- The Docker runner uses `--cap-drop ALL`, `no-new-privileges`,
  `--read-only` and tmpfs for `/tmp`.
- Project tests run only explicitly, via a trusted `--project-tests`.
- Missing Docker yields `partial: true`.
- Mutation is disabled without a sandbox.

## Limitations

- Docker isolation depends on the host Docker daemon.
- The project test command is defined by the CI owner and is executed in a
  Docker sandbox over a temporary copy of the repository.
- A seccomp profile and rootless Docker remain on the roadmap.

## Roadmap Hardening

- rootless Docker;
- a custom seccomp profile.
