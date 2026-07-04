# Обоснование Trust Score

Trust Score - это не математическое доказательство корректности. Это
объяснимый risk score для CI и code review.

## Принцип

Оценка начинается со 100 баллов. За каждую проблему снимается штраф из
`weights.toml`. Затем формируется вердикт:

- `PASS`: score >= 76;
- `REVIEW`: 40..75;
- `BLOCK`: score <= 39 или три и более critical findings.

## Почему critical detectors не saturate

Для `TG-D01..TG-D04` штрафы не ограничиваются saturation cap:

- hallucinated import;
- non-existent API;
- dangerous execution;
- SQL string building.

Один такой дефект может быть ошибкой, но несколько critical findings в одном
патче означают системный риск. Поэтому три critical finding принудительно дают
`BLOCK`.

## Почему часть дефектов дает REVIEW, а не BLOCK

`shell=True`, `verify=False`, broad except, stubs и weak hashes важны, но не
всегда означают немедленный запрет merge. TrustGate отделяет:

- detection - проблема найдена;
- policy - достаточно ли проблемы для `BLOCK`.

Поэтому один major finding может оставить score в `PASS`, но finding все равно
появится в Markdown/HTML/SARIF.

## Как калибровать веса

Веса вынесены в `weights.toml`, а строгую политику можно задавать через
`trustgate.policy.toml`:

```bash
trustgate scan . --config trustgate.policy.toml
```

Для финальной исследовательской версии веса должны калиброваться на корпусе:

1. собрать clean/defective samples;
2. посчитать false positives и false negatives;
3. подобрать penalties и thresholds;
4. зафиксировать результат в `docs/benchmark.md`.

Текущие веса - инженерная baseline-политика, а не окончательная научная
калибровка.
