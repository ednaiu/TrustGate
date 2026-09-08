# Task: retry_call

Write a function `retry_call(fn, attempts=3)` that calls `fn()` and on an
exception repeats the call, but no more than `attempts` times in total.
If all attempts fail, the last exception must propagate outwards.
