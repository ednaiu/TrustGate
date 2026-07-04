# Threat model

TrustGate analyzes code that may be wrong or intentionally unsafe. The design
keeps parsing, execution and reporting separated.

## Assets

- Developer workstation or CI runner.
- Source code in the checked repository.
- Network credentials available to CI.
- TrustGate report integrity.

## Main risks

1. The analyzed code tries to access the network.
2. The analyzed code tries to read or modify files outside the working area.
3. The analyzed code consumes too much CPU, memory or process count.
4. A failing test run is misclassified as a build error or success.
5. A partial report is mistaken for a complete verdict.
6. A dependency manifest contains a hallucinated or typo-squatted package name.

## Current controls

- Static layer parses AST only and never imports analyzed code.
- Project scan checks `pyproject.toml` and `requirements*.txt` for suspicious
  dependency names.
- Dynamic layer runs in Docker with `--network none`.
- Project scan runs repository tests only when the caller explicitly provides a
  trusted `--project-tests` command.
- The mounted work directory is read-only.
- CPU, memory and PID limits are set for the container.
- Timeouts kill the running container.
- Missing Docker degrades to `partial: true`.
- Mutation analysis is disabled without sandbox execution.

## Known limitations

- Docker isolation depends on the host Docker daemon configuration.
- Project test commands run in the caller's CI/workstation context, not in the
  single-file Docker sandbox.
- Project-level mutation testing is not implemented yet.
- There is no seccomp profile or rootless Docker setup in the repository yet.

## Planned hardening

- Add `--security-opt no-new-privileges`.
- Add a stricter seccomp profile.
- Support project-level sandbox runs in a temporary copy.
- Add project-level mutation testing.
- Add GitHub Checks annotations on top of SARIF.
