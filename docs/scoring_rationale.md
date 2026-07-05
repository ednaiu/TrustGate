# Обоснование Trust Score

Trust Score - это не математическое доказательство корректности. Это
объяснимый risk score для CI и code review, и его пороги калиброваны на
внешнем корпусе (см. ниже), а не выбраны на глаз.

Если analysis partial, PASS не должен маскировать неполноту: такой результат
понижается до REVIEW.

## Принцип

Оценка начинается со 100 баллов. За каждую проблему снимается штраф из
`weights.toml`. Затем формируется вердикт:

- `BLOCK`: хотя бы один critical finding, или score <= 39;
- `PASS`: score >= 76 и нет critical findings;
- `REVIEW`: все остальное.

## Калибровка на корпусе (v1, 245 samples)

Пороги проверены скриптом `experiment/calibrate.py` на размеченном корпусе
`experiment/corpus/corpus.json` (171 defective / 74 clean, состав описан в
`docs/benchmark.md`). Перебор сетки порогов `block_threshold x critical_count`
с ограничением FPR на clean-группе <= 10% дал:

| правило BLOCK | precision | recall | FPR на clean |
|---------------|-----------|--------|--------------|
| старое: score<=39 или >=3 criticals | 0.0 | 0.0 | 0.0 |
| текущее: score<=39 или >=1 critical | 1.000 | 0.135 | 0.000 |
| максимум F1 на сетке (score<=75) | 0.967 | 0.170 | 0.014 |

Выводы, зафиксированные в коде:

1. **Старое правило "3 critical" не срабатывало никогда**: медианный дефектный
   файл несет ровно один critical finding. Правило заменено на
   `BLOCK_ON_CRITICAL_COUNT = 1` ([trustgate/scoring.py](../trustgate/scoring.py)).
2. Одиночный critical finding блокирует с precision 1.0 и нулевым FPR на
   clean-группе корпуса - это самый точный сигнал, который у нас есть.
3. Вариант "максимум F1" (score<=75) не принят: он схлопывает зону REVIEW,
   а REVIEW - осознанная часть модели: спорные патчи должен смотреть человек,
   а не автоматика.

Воспроизведение:

```bash
python experiment/calibrate.py --corpus experiment/corpus/corpus.json
```

Результат сохранен в `experiment/calibration-result.json`.

## Почему critical detectors не saturate

Для `TG-D01..TG-D04` и `TG-D13` штрафы не ограничиваются saturation cap:

- hallucinated import;
- non-existent API;
- dangerous execution;
- SQL string building;
- hallucinated keyword argument.

Каждый такой дефект - самостоятельный merge-blocker, поэтому несколько
critical findings не должны "слипаться" в один потолок штрафа.

## Почему часть дефектов дает REVIEW, а не BLOCK

`shell=True`, `verify=False`, broad except, stubs и weak hashes важны, но не
всегда означают немедленный запрет merge. TrustGate отделяет:

- detection - проблема найдена;
- policy - достаточно ли проблемы для `BLOCK`.

Поэтому один major finding может оставить score в `PASS`, но finding все равно
появится в Markdown/HTML/SARIF.

## Ограничения калибровки

Честные оговорки, которые нужно называть самим:

- Корпус v1 - 245 samples; это рабочая калибровка, а не финальная научная
  истина. Схема пересчета зафиксирована и повторяема при росте корпуса.
- Калибровка выполнена по статическому слою (score без dynamic/mutation
  штрафов): в repo-flow именно static определяет большинство вердиктов.
  Порог score<=39 остается как защита для полного пайплайна, где к штрафам
  добавляются проваленные тесты и слабый mutation score.
- Веса отдельных детекторов (`weights.toml`) не перебирались по сетке: при
  правиле "1 critical = BLOCK" их влияние на вердикт вторично; ablation по
  детекторам есть в `experiment/benchmark-result.json`.
