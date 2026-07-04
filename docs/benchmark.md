# Бенчмарк И Оценка Качества

TrustGate не должен опираться на голословное утверждение “обычные линтеры
пропускают LLM-дефекты”. Поэтому в проекте есть два уровня оценки:
регрессионный smoke benchmark и внешний benchmark на реальном корпусе.

## Текущий Smoke-Бенчмарк

Данные: `experiment/static_benchmark_cases.json`
Запуск:

```bash
python experiment/static_benchmark.py
```

Корпус маленький и специально подобранный. Его задача - проверить, что каждый
статический detector имеет воспроизводимый пример, а чистые примеры остаются
чистыми.

Текущий ожидаемый результат:

| метрика | значение |
|---------|----------|
| cases | 12 |
| defective | 10 |
| clean | 2 |
| static detector precision | 1.000 |
| static detector recall | 1.000 |
| static detector F1 | 1.000 |
| expected detector recall | 1.000 |

Важно: benchmark измеряет, нашел ли статический слой нужный дефект. Это не
означает, что каждый finding обязан давать `BLOCK`: часть findings по design
дают `REVIEW` или остаются в `PASS` как предупреждение.

## Внешний Бенчмарк На 100+ LLM Samples

Runner уже реализован: `experiment/benchmark_external.py`.

Формат корпуса: JSON или JSONL, минимум 100 записей:

```json
[
  {
    "id": "sample_001",
    "label": "clean",
    "code": "def add(a, b):\n    return a + b\n"
  },
  {
    "id": "sample_002",
    "label": "defective",
    "code": "def parse(raw):\n    return eval(raw)\n"
  }
]
```

Допустимые defective labels: `defective`, `bad`, `unsafe`, `vulnerable`,
`hallucinated`, `1`, `true`. Все остальные labels считаются clean.

Запуск:

```bash
python experiment/benchmark_external.py \
  --corpus data/llm_samples_100.json \
  --out benchmark-result.json
```

Если корпус содержит меньше 100 samples, runner честно вернет
`"status": "needs_corpus"`. Это сделано специально, чтобы проект не выдавал
маленькую синтетику за полноценное исследование.

## Сравнение С Ruff, Flake8, Bandit, Semgrep

Runner автоматически пробует запустить:

- `ruff check --output-format json`;
- `flake8`;
- `bandit -q -f json`;
- `semgrep --quiet --json --config auto`.

Если инструмент не установлен, в JSON будет:

```json
{ "available": false, "reason": "tool_not_installed" }
```

То есть benchmark не падает из-за отсутствия optional baseline, но явно
показывает, какие сравнения реально были выполнены.

Минимальная таблица:

| инструмент | precision | recall | F1 | false positive rate |
|------------|-----------|--------|----|---------------------|
| TrustGate | TBD | TBD | TBD | TBD |
| ruff/flake8 | TBD | TBD | TBD | TBD |
| bandit | TBD | TBD | TBD | TBD |
| semgrep | TBD | TBD | TBD | TBD |

## Confusion Matrix И False Positive Analysis

Для TrustGate и каждого доступного baseline runner считает:

- `tp` - defective sample найден;
- `tn` - clean sample не найден как дефектный;
- `fp` - clean sample ошибочно помечен;
- `fn` - defective sample пропущен;
- `precision`, `recall`, `f1`.

Отдельный блок `false_positive_analysis` содержит список clean samples, которые
были помечены как проблемные, с указанием инструмента и detector ids для
TrustGate. Этот список нужен для ручного разбора нормальных проектов: какие
правила слишком агрессивны и где стоит снижать severity.

## Как Подготовить Честный Корпус

1. Взять 100+ Python-фрагментов или небольших решений, реально созданных LLM.
2. Для каждого sample сохранить исходный prompt или ссылку на задачу отдельно
   от benchmark JSON.
3. Разметить `clean`/`defective` по reference tests, review и known defects.
4. Добавить отдельную группу нормальных open-source файлов без искусственных
   дефектов для false positive analysis.
5. Запустить runner и сохранить `benchmark-result.json` как artifact.

Такое разделение не позволяет завышать claims: smoke benchmark доказывает
механизм и регрессионную проверку, а сильное исследовательское утверждение
появляется только после подключения внешнего корпуса.
