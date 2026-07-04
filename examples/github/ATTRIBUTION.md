# Атрибуция GitHub-примеров

Файлы в этой папке нужны для демонстрации TrustGate на реалистичных паттернах
из открытых репозиториев. Они специально имеют расширение `.py.example`, чтобы
`trustgate scan .` не считал их кодом самого проекта.

## PyGoat

- Репозиторий: https://github.com/adeyosemanputra/pygoat
- Лицензия: MIT License
- Использование: `pygoat_minimized.py.example` содержит минимизированное
  воспроизведение паттернов уязвимого учебного приложения. Это не полная копия
  исходного файла.

## TheAlgorithms/Python

- Репозиторий: https://github.com/TheAlgorithms/Python
- Лицензия: MIT License
- Использование: `thealgorithms_style_clean.py.example` содержит короткий
  самостоятельный пример алгоритмического кода в стиле репозитория. Это не
  дословная копия исходного файла.

## Как проверять

```bash
trustgate check examples/github/pygoat_minimized.py.example --no-sandbox
trustgate check examples/github/thealgorithms_style_clean.py.example --no-sandbox
```
