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
BINOP_SWAP = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.Div,
    ast.Div: ast.Mult,
    ast.FloorDiv: ast.Mod,
    ast.Mod: ast.FloorDiv,
}
MUTATION_TYPES = ("compare", "boolop", "binop", "const")


def _mutations(tree):
    """Yield (description, walk_index, kind) for every mutable site."""
    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare) and type(node.ops[0]) in COMPARE_SWAP:
            yield f"compare@{node.lineno}", i, "compare"
        elif isinstance(node, ast.BoolOp):
            yield f"boolop@{node.lineno}", i, "boolop"
        elif isinstance(node, ast.BinOp) and type(node.op) in BINOP_SWAP:
            op_name = type(node.op).__name__.lower()
            yield f"binop:{op_name}@{getattr(node, 'lineno', 0)}", i, "binop"
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
        elif kind == "binop":
            node.op = BINOP_SWAP[type(node.op)]()
        elif kind == "const":
            node.value += offset
        break
    return tree


def _generate_with_kinds(source: str, seed: int = 0) -> list[tuple[str, str, str]]:
    """Returns [(description, kind, mutated_source)], at most MAX_MUTANTS."""
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
            mutants.append((desc, kind, ast.unparse(ast.fix_missing_locations(mutated))))
        except (ValueError, RecursionError):
            continue
    return mutants


def generate(source: str, seed: int = 0) -> list[tuple[str, str]]:
    """Returns [(description, mutated_source)], at most MAX_MUTANTS."""
    return [(desc, mutated_source) for desc, _, mutated_source in _generate_with_kinds(source, seed)]


def _summary_template() -> dict[str, dict[str, float | int]]:
    return {
        kind: {
            "sites": 0,
            "generated": 0,
            "killed": 0,
            "coverage": 0.0,
            "kill_rate": 0.0,
        }
        for kind in MUTATION_TYPES
    }


def evaluate(source: str, tests: str, run_tests, seed: int = 0) -> dict:
    """run_tests is injected (the sandbox runner) so this module stays import-safe."""
    tree = ast.parse(source)
    sites = list(_mutations(tree))
    mutants = _generate_with_kinds(source, seed)
    if not mutants:
        return {
            "ran": True,
            "mutants_total": 0,
            "mutants_killed": 0,
            "mutation_score": 1.0,
            "coverage_by_type": _summary_template(),
        }

    killed = 0
    stats = _summary_template()
    for _, kind, _ in mutants:
        stats[kind]["generated"] += 1
    for _, kind, mutated_source in mutants:
        result = run_tests(mutated_source, tests)
        if result.get("tests_failed", 0) > 0 or result.get("build_error") or result.get("timeout"):
            killed += 1
            stats[kind]["killed"] += 1
    total_sites = len(sites)
    for kind, item in stats.items():
        kind_sites = sum(1 for _, _, site_kind in sites if site_kind == kind)
        item["sites"] = kind_sites
        item["coverage"] = round(item["generated"] / kind_sites, 4) if kind_sites else 0.0
        item["kill_rate"] = round(item["killed"] / item["generated"], 4) if item["generated"] else 0.0
    return {
        "ran": True,
        "mutants_total": len(mutants),
        "mutants_killed": killed,
        "mutation_score": killed / len(mutants),
        "mutant_sites_total": total_sites,
        "coverage_by_type": stats,
    }
