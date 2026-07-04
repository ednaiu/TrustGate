# Демонстрационные Примеры

Файлы имеют расширение `.py.example`, чтобы `trustgate scan .` не принимал
демонстрационные уязвимости за код самого проекта.

## Запуск

```bash
trustgate check examples/pass_solution.py.example --no-sandbox
trustgate check examples/review_solution.py.example --no-sandbox --html review.html
trustgate check examples/block_solution.py.example --no-sandbox --html block.html
trustgate check examples/github/pygoat_minimized.py.example --no-sandbox
trustgate check examples/github/thealgorithms_style_clean.py.example --no-sandbox
```

## Ожидаемый Результат

- `pass_solution.py.example` - чистый пример.
- `review_solution.py.example` - risky pattern, нужен review.
- `block_solution.py.example` - critical LLM-style defects, должен быть `BLOCK`.
- `github/pygoat_minimized.py.example` - реалистичные vulnerable patterns из
  open-source security training проекта.
- `github/thealgorithms_style_clean.py.example` - чистый алгоритмический код.

Атрибуция GitHub-примеров находится в `examples/github/ATTRIBUTION.md`.
