# Модель Угроз

TrustGate анализирует код, который может быть ошибочным или небезопасным.
Поэтому parsing, execution и reporting разделены.

## Активы

- CI runner или рабочая машина разработчика.
- Исходный код репозитория.
- Secrets и credentials в CI.
- Целостность TrustGate-отчета.

## Риски

1. Проверяемый код пытается выйти в сеть.
2. Проверяемый код пытается читать или менять файлы вне рабочей области.
3. Проверяемый код потребляет слишком много CPU/RAM/processes.
4. Ошибка тестов неверно классифицируется.
5. Partial report принимается за полный verdict.
6. Dependency manifest содержит hallucinated или typo-squatted package.

## Текущие Контроли

- Static layer только парсит AST и не импортирует проверяемый код; для
  TG-D02/TG-D13 импортируются исключительно stdlib-модули из фиксированного
  белого списка (`ATTR_CHECK_MODULES`).
- Вердикт TG-D01/TG-D12 детерминирован: снапшот PyPI в репозитории, локальное
  окружение учитывается только по явному `--trust-local-env`.
- Project scan проверяет `pyproject.toml` и `requirements*.txt`.
- Single-file dynamic layer запускается в Docker без сети.
- Docker runner использует CPU/RAM/PID limits.
- Docker runner использует `--cap-drop ALL`, `no-new-privileges`,
  `--read-only` и tmpfs для `/tmp`.
- Project tests запускаются только явно через доверенный `--project-tests`.
- Missing Docker дает `partial: true`.
- Mutation отключается без sandbox.

## Ограничения

- Docker isolation зависит от host Docker daemon.
- Project test command задается владельцем CI и выполняется в Docker sandbox
  над временной копией репозитория.
- Seccomp profile и rootless Docker остаются roadmap.

## Roadmap Hardening

- rootless Docker;
- custom seccomp profile.
