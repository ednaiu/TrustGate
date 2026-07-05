# Бенчмарк И Оценка Качества

TrustGate не опирается на голословное утверждение "обычные линтеры пропускают
дефекты генеративного кода". В проекте два уровня оценки: регрессионный smoke
benchmark и внешний benchmark на корпусе из 245 samples с полным provenance.
Все цифры ниже воспроизводятся из закоммиченных данных и скриптов.

## Внешний Бенчмарк: Результаты (corpus v1, 245 samples)

Запуск:

```bash
python experiment/benchmark_external.py \
  --corpus experiment/corpus/corpus.json \
  --out experiment/benchmark-result.json
```

Критерий: инструмент "пометил" файл, если выдал хотя бы один finding - то есть
как merge-gate он завернул бы этот патч.

| инструмент | precision | recall | F1 | FPR на clean |
|------------|-----------|--------|-----|--------------|
| **TrustGate (static)** | **1.000** | 0.357 | **0.526** | **0.0%** |
| bandit 1.9.4 | 0.962 | 0.298 | 0.455 | 2.7% |
| semgrep 1.168.0 (config auto) | 1.000 | 0.263 | 0.417 | 0.0% |
| ruff 0.15.20 | 0.973 | 0.211 | 0.346 | 1.4% |
| flake8 7.3.0 | 0.841 | 0.801 | 0.820 | **35.1%** |

Как это читать честно:

- Среди инструментов, пригодных как gate (FPR < 5%), TrustGate дает лучший F1
  при нулевых false positives на clean-группе.
- flake8 формально впереди по recall, но помечает **каждый третий чистый
  production-файл** - как merge-gate он непригоден, это style-линтер.
- Ноль FP - результат на 74 clean-сэмплах корпуса v1, а не гарантия для
  любого кода.

## Recall По Срезам: Где Чьи Слепые Зоны

| срез корпуса (defective) | TrustGate | bandit | semgrep | ruff |
|--------------------------|-----------|--------|---------|------|
| SecurityEval, 130 CWE-уязвимостей от Copilot | 0.200 | 0.285 | 0.292 | 0.215 |
| Профиль генеративного кода, 41 (hallucinated imports/kwargs, stubs, placeholders, eval) | **0.854** | 0.341 | 0.171 | 0.195 |

Это главный результат позиционирования:

- На классических CWE-уязвимостях (LDAP/XXE/SSRF и т.п.) bandit и semgrep
  сильнее - TrustGate **не претендует заменить их** и должен работать рядом.
  Широкие классы (XSS, open redirect, path traversal) требуют taint-анализа,
  которого в TrustGate осознанно нет.
- На дефект-профиле генеративного кода TrustGate находит 85% дефектов, а
  лучшие baseline - максимум 34%. Этот класс дефектов - слепая зона
  существующих инструментов, и именно его TrustGate закрывает.
- Оставшиеся 15% на втором срезе - инъекции off-by-one: логические ошибки
  статически не ловятся by design, для них есть L2/L3 (tests + mutation).

## Состав Корпуса (245 samples, 171 defective / 74 clean)

| источник | размер | label | как получен |
|----------|--------|-------|-------------|
| SecurityEval (MSR 2022) | 130 | defective | код, реально сгенерированный GitHub Copilot для security-чувствительных промптов; цитирование: Siddiq & Santos, DOI 10.1145/3549035.3561184 |
| trustgate-tasks | 46 | clean | решения 23 задач из `experiment/tasks/`, сгенерированные claude-haiku и claude-sonnet через CLI; label присвоен прогоном reference-тестов (все 46 прошли) |
| injected-defects | 41 | defective | те же LLM-решения с одной детерминированной инъекцией дефекта (`inject_defects.py`, seed 42) - единственный синтетический срез, покрывает профиль генеративного кода |
| clean-oss | 28 | clean | файлы из requests, flask, click, fastapi и др., пиненные на release-теги (`experiment/corpus/clean_oss/sources.json`) - проба false positives |

Как собрать корпус заново:

```bash
git clone https://github.com/s2e-lab/SecurityEval /tmp/SecurityEval
python experiment/generate_corpus.py           # нужен claude CLI или API-ключи
python experiment/build_corpus.py --securityeval /tmp/SecurityEval
```

Известные ограничения разметки (называем сами):

- Label "defective" для SecurityEval унаследован от конструкции датасета:
  промпты провоцируют уязвимость, но отдельные ответы Copilot могли оказаться
  безопасными. Это шум меток, общий для всех сравниваемых инструментов.
- Срез injected-defects синтетический (мутации реального LLM-кода) - стандартная
  методика ground truth, полностью помечен в provenance.
- 46 из 74 clean-сэмплов - решения простых алгоритмических задач; сложный
  "чистый" LLM-код в корпусе v1 не представлен.

## Ablation По Детекторам

`experiment/benchmark-result.json` содержит ablation: как падает recall при
отключении каждого детектора. Топ вкладов на corpus v1: TG-D03
(eval/exec/os.system/yaml.load, -9.9% recall), TG-D09 (stubs, -5.3%), TG-D08
(broad except, -4.7%), TG-D01 (hallucinated imports, -4.1%), TG-D13 и TG-D14
(по -3.5%). Детекторы LLM-профиля (D01, D02, D09, D13, D14) в сумме дают
около половины recall.

## False Positive Analysis

Блок `false_positive_analysis` в JSON перечисляет каждый ложно помеченный
clean-сэмпл с инструментом и detector ids. У TrustGate на corpus v1 их **0**.
Этот ноль - заработанный: первая версия давала 3 FP, все от сабчека
"TODO/FIXME в комментарии" (зрелый OSS-код полон долгоживущих TODO -
`fastapi/param_functions.py`, `requests/hooks.py`, `urllib3/exceptions.py`).
Сабчек удален: реальные заглушки ловятся по телу функции (TG-D09), строки
"TODO: implement" - через TG-D14, а recall от удаления не изменился. Это
пример рабочего цикла false positive analysis -> правка правил. На коде вне
корпуса FP остаются возможными и подавляются `# trustgate: ignore TG-DXX`.

## Smoke-Бенчмарк (регрессия детекторов)

Данные: `experiment/static_benchmark_cases.json` (15 кейсов, по одному на
детектор + clean-кейсы). Запуск:

```bash
python experiment/static_benchmark.py
```

Он отвечает на один вопрос: каждый детектор имеет воспроизводимый пример и не
разваливается при изменениях кода. Метрики на нем (precision/recall 1.0) - это
регрессионная проверка механики, а не исследовательское утверждение; для
исследовательских цифр см. внешний бенчмарк выше.

## Формат Корпуса

JSON или JSONL, каждый sample: `id`, `label`, `code`, `source` (provenance).
Допустимые defective labels: `defective`, `bad`, `unsafe`, `vulnerable`,
`hallucinated`, `1`, `true`. Все остальные считаются clean.

Если корпус меньше 100 samples, runner возвращает `"status": "needs_corpus"` -
маленькая синтетика не должна выдаваться за полноценное исследование.
