# Таксономия Дефектов LLM-Кода

TrustGate не заменяет линтеры. Он закрывает профиль ошибок, который часто
появляется в AI-generated коде.

| id | класс дефекта | почему важно |
|----|---------------|--------------|
| TG-D01 | выдуманный или typo import | LLM может придумать правдоподобное имя пакета |
| TG-D02 | несуществующий stdlib/API attribute | вызов выглядит реалистично, но API нет |
| TG-D03 | dangerous execution | `eval`, `exec`, `pickle.loads` часто появляются как быстрый shortcut |
| TG-D04 | SQL string building | f-strings в SQL создают injection risk |
| TG-D05 | `shell=True` | динамическая shell-команда опасна |
| TG-D06 | `verify=False` | отключение TLS validation часто попадает в “make it work” patches |
| TG-D07 | weak hash для secrets | MD5/SHA1 не подходят для паролей и токенов |
| TG-D08 | broad swallowed exception | ошибка скрывается вместо обработки |
| TG-D09 | stub вместо реализации | `pass`, TODO или `NotImplementedError` остаются в коде |
| TG-D10 | dead code | признак механически собранного или невычитанного кода |
| TG-D11 | tautological assert | тест выглядит как тест, но ничего не доказывает |
| TG-D12 | suspicious dependency | LLM может придумать пакет в `pyproject.toml` или `requirements.txt` |
| TG-D13 | hallucinated keyword argument | функция существует, а kwarg - нет: классическая галлюцинация API |
| TG-D14 | placeholder value | `"YOUR_API_KEY_HERE"` вместо реальной конфигурации доезжает до merge |
| TG-D15 | insecure runtime default | `mktemp`, `debug=True`, `extractall()` - паттерны из устаревших туториалов, которые LLM продолжает воспроизводить |

## Чего TrustGate Не Обещает

- не доказывает semantic correctness;
- не делает полный taint/dataflow analysis;
- не знает все пакеты PyPI;
- не заменяет security review.

## Почему Отдельный Инструмент Полезен

Обычные инструменты проверяют стиль, syntax, type hints и часть security issues.
TrustGate спрашивает другое: “выглядит ли AI-generated patch достаточно
надежным, чтобы пройти CI без ручного review?”
