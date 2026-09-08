# Task: safe_get

Write a function `safe_get(data, path, default=None)` that extracts a value from
nested dictionaries by the list of keys `path`. If some key is missing or an
intermediate value is not a dictionary, return `default`.
