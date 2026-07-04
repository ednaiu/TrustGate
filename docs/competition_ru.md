# TrustGate для ITMO STARS

Автор: Юсупова Ева ([iusupovaeva-debug](https://github.com/iusupovaeva-debug))
Репозиторий: `github.com/ednaiu/TrustGate`
Направление: 09.03.02 "Информационные системы и технологии"

## Коротко

TrustGate - это учебный, но уже рабочий инструмент для проверки Python-кода,
который мог быть написан с помощью LLM. Он запускается в репозитории или CI и
выдает понятный вердикт: `PASS`, `REVIEW` или `BLOCK`.

Главная идея: обычные линтеры хорошо ловят стиль и часть security-проблем, но
хуже работают с типичными ошибками LLM: выдуманные библиотеки, похожие на
настоящие API, опасные quick fixes, заглушки вместо решения и слабые тесты.

## Почему это информационная система

В проекте есть не только алгоритм анализа, но и полный поток обработки данных:

1. Источник данных - git-репозиторий, PR-diff или отдельный Python-файл.
2. Обработка - статические детекторы, sandboxed pytest, mutation testing.
3. Хранение результата - JSON-отчет по схеме.
4. Представление - Markdown для CI и HTML для демонстрации.
5. Интеграция - CLI и GitHub Action.

Это делает TrustGate небольшим quality-gate для процесса разработки, а не
разовым скриптом.

## Что уже сделано

- 11 AST-детекторов `TG-D01..TG-D11`.
- Безопасный запуск тестов в Docker: без сети, с лимитами CPU/RAM/PID.
- Mutation testing с фиксированным seed и лимитом мутантов.
- Объяснимый Trust Score 0-100.
- CLI: `check`, `scan`, `report`.
- Git workflow: `trustgate scan .` и `trustgate scan . --changed`.
- GitHub Action для PR.
- JSON schema и HTML reports.
- Набор тестов для детекторов, scoring, sandbox, CLI и project scan.

## Личный вклад

Я проектировала TrustGate как понятную систему из небольших модулей:

- `detectors.py` - правила поиска дефектов;
- `sandbox.py` - безопасный запуск тестов;
- `mutation.py` - генерация мутантов;
- `scoring.py` - расчет баллов;
- `scan.py` - работа с git/project workflow;
- `action.yml` - запуск в CI.

Код специально оставлен простым: без тяжелого фреймворка и без "магии", чтобы
можно было объяснить каждое решение на собеседовании.

## Что можно показать на демо

1. Проверка отдельного решения:

```bash
trustgate check examples/block_solution.py.example --no-sandbox --html report.html
```

2. Проверка всего проекта:

```bash
trustgate scan . --json project-report.json --html project-report.html
```

3. Проверка только измененных файлов:

```bash
trustgate scan . --changed --base HEAD
```

4. GitHub Action в pull request: `BLOCK` падает, `REVIEW` оставляет summary,
   `PASS` проходит.

## Слабые места, которые я понимаю

- Сейчас полноценный dynamic/mutation слой работает для одного файла с pytest,
  а project scan в v1.0 статический.
- Поддерживается только Python.
- Часть проверок эвристическая: например, import hallucination зависит от
  списка популярных пакетов и локального окружения.
- Для сильной защиты нужен законченный benchmark с метриками против
  `ruff`, `flake8`, `bandit` и `semgrep`.

## План развития

Ближайший практический план:

1. Довести benchmark до готовой таблицы: precision, recall, F1, false positive
   rate.
2. Добавить project sandbox runner, который запускает тесты всего репозитория,
   а не только пары `solution.py + test_solution.py`.
3. Сохранять историю проверок в SQLite.
4. Добавить SARIF export для GitHub code scanning.
5. Расширить поддержку языков: JavaScript/TypeScript как следующий кандидат.

Главная цель развития - сделать TrustGate не заменой линтеров, а отдельным
слоем контроля доверия к AI-generated коду.
