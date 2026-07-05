from trustgate.mutation import MAX_MUTANTS, generate

SRC = """
def clamp(x, lo, hi):
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
"""


def test_generates_mutants():
    mutants = generate(SRC)
    assert mutants
    assert all(src != SRC for _, src in mutants)


def test_mutants_are_valid_python():
    import ast
    for _, src in generate(SRC):
        ast.parse(src)


def test_deterministic_with_seed():
    assert generate(SRC, seed=7) == generate(SRC, seed=7)  # trustgate: ignore TG-D11


def test_respects_budget():
    big = "\n".join(f"x{i} = {i} < {i + 1}" for i in range(200))
    assert len(generate(big)) <= MAX_MUTANTS


def test_compare_mutation_changes_operator():
    mutants = generate("def f(a, b):\n    return a < b\n")
    assert any("a <= b" in src for _, src in mutants)


def test_binop_mutation_changes_operator():
    mutants = generate("def f(a, b):\n    return a + b\n")
    assert any("a - b" in src or "a / b" in src for _, src in mutants)


def test_killed_mutant_detection():
    from trustgate.mutation import evaluate

    def fake_runner(mutated_source, tests):
        # pretend the tests fail on every mutant
        return {"ran": True, "tests_total": 1, "tests_failed": 1}

    result = evaluate(SRC, "def test(): pass", fake_runner)
    assert result["mutation_score"] == 1.0
    assert result["mutants_killed"] == result["mutants_total"]
    assert "coverage_by_type" in result
    assert "compare" in result["coverage_by_type"]
