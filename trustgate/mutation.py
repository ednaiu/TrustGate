"""Mutation (L3) layer: our own AST mutator, three operators (TZ NS-15).

Surviving mutants mean the provided tests don't really test the code.
Requires the sandbox: no Docker -> no mutation run (TZ NS-9).
"""
import ast
import copy
import random

MAX_MUTANTS = 50

COMPARE_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
                ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}


def _mutations(tree):
    """Yield (description, walk_index, kind) for every mutable site."""
    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare) and type(node.ops[0]) in COMPARE_SWAP:
            yield f"compare@{node.lineno}", i, "compare"
        elif isinstance(node, ast.BoolOp):
            yield f"boolop@{node.lineno}", i, "boolop"
        elif isinstance(node, ast.Constant) and isinstance(node.value, int) \
                and not isinstance(node.value, bool):
            yield f"const@{getattr(node, 'lineno', 0)}", i, "const"


def _apply(tree, index, kind, offset):
    tree = copy.deepcopy(tree)
    for i, node in enumerate(ast.walk(tree)):
        if i != index:
            continue
        if kind == "compare":
            node.ops[0] = COMPARE_SWAP[type(node.ops[0])]()
        elif kind == "boolop":
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        elif kind == "const":
            node.value += offset
        break
    return tree


def generate(source: str, seed: int = 0) -> list[tuple[str, str]]:
    """Returns [(description, mutated_source)], at most MAX_MUTANTS."""
    tree = ast.parse(source)
    sites = list(_mutations(tree))
    rng = random.Random(seed)
    if len(sites) > MAX_MUTANTS:
        sites = rng.sample(sites, MAX_MUTANTS)
        sites.sort(key=lambda s: s[1])

    mutants = []
    for desc, index, kind in sites:
        offset = rng.choice([1, -1]) if kind == "const" else 0
        mutated = _apply(tree, index, kind, offset)
        try:
            mutants.append((desc, ast.unparse(ast.fix_missing_locations(mutated))))
        except (ValueError, RecursionError):
            continue
    return mutants


def evaluate(source: str, tests: str, run_tests, seed: int = 0) -> dict:
    """run_tests is injected (the sandbox runner) so this module stays import-safe."""
    mutants = generate(source, seed)
    if not mutants:
        return {"ran": True, "mutants_total": 0, "mutants_killed": 0, "mutation_score": 1.0}

    killed = 0
    for _, mutated_source in mutants:
        result = run_tests(mutated_source, tests)
        if result.get("tests_failed", 0) > 0 or result.get("build_error") or result.get("timeout"):
            killed += 1
    return {
        "ran": True,
        "mutants_total": len(mutants),
        "mutants_killed": killed,
        "mutation_score": killed / len(mutants),
    }
