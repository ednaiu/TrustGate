# Бенчмарк И План Оценки

TrustGate не должен опираться на голословное утверждение “обычные линтеры
пропускают LLM-дефекты”. Поэтому в проекте есть воспроизводимый smoke benchmark
и план большого benchmark.

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

## Большой Бенчмарк

Следующий уровень - минимум 100 Python-решений:

- задачи из `experiment/tasks/`;
- несколько LLM-провайдеров;
- clean/defective labels по reference tests;
- injected defects с ground truth;
- сравнение с `ruff`, `flake8`, `bandit`, `semgrep`.

Минимальная таблица:

| инструмент | precision | recall | F1 | false positive rate |
|------------|-----------|--------|----|---------------------|
| TrustGate | TBD | TBD | TBD | TBD |
| ruff/flake8 | TBD | TBD | TBD | TBD |
| bandit | TBD | TBD | TBD | TBD |
| semgrep | TBD | TBD | TBD | TBD |

Такое разделение не позволяет завышать claims: текущий benchmark доказывает
механизм и регрессионную проверку, а сильное исследовательское утверждение
потребует большого корпуса.
