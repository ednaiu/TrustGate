"""Inject known defect classes into clean solutions (ground truth, FR-EXP-3).

Deterministic by seed: same corpus in, same labeled dataset out.
"""
import argparse
import ast
import json
import random
from pathlib import Path

HERE = Path(__file__).parent


def inject_hallucinated_import(source, rng):
    fake = rng.choice(["requsets", "numppy", "pandsa", "flaskk", "beautifulsoup"])
    return f"import {fake}\n" + source, "TG-D01"


def inject_eval(source, rng):
    return source + "\n\ndef parse_input(raw):\n    return eval(raw)\n", "TG-D03"


def inject_broad_except(source, rng):
    tree = ast.parse(source)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return None
    f = rng.choice(funcs)
    body = ast.unparse(ast.Module(body=f.body, type_ignores=[]))
    indented = "\n".join("        " + line for line in body.splitlines())
    wrapped = (f"def {f.name}({ast.unparse(f.args)}):\n"
               f"    try:\n{indented}\n    except Exception:\n        pass\n")
    start, end = f.lineno - 1, f.end_lineno
    lines = source.splitlines()
    return "\n".join(lines[:start] + wrapped.splitlines() + lines[end:]) + "\n", "TG-D08"


def inject_off_by_one(source, rng):
    class Flip(ast.NodeTransformer):
        def __init__(self):
            self.done = False

        def visit_Compare(self, node):
            if not self.done and isinstance(node.ops[0], (ast.Lt, ast.Gt)):
                node.ops[0] = ast.LtE() if isinstance(node.ops[0], ast.Lt) else ast.GtE()
                self.done = True
            return node

    tree = ast.parse(source)
    flip = Flip()
    tree = flip.visit(tree)
    if not flip.done:
        return None
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n", "logic"


def inject_stub(source, rng):
    return source + "\n\ndef validate(data):\n    # TODO\n    pass\n", "TG-D09"


def inject_hallucinated_kwarg(source, rng):
    snippet = rng.choice([
        "\n\ndef backup_file(src, dst):\n    import shutil\n"
        "    return shutil.copy(src, dst, overwrite=True)\n",
        "\n\ndef normalize_text(text):\n    import textwrap\n"
        "    return textwrap.dedent(text, strip=True)\n",
    ])
    return source + snippet, "TG-D13"


def inject_placeholder(source, rng):
    fake = rng.choice([
        '"YOUR_API_KEY_HERE"',  # trustgate: ignore TG-D14
        '"your-secret-token"',  # trustgate: ignore TG-D14
        '"<your password>"',  # trustgate: ignore TG-D14
    ])
    return source + f"\n\nAPI_KEY = {fake}\n", "TG-D14"


INJECTIONS = [inject_hallucinated_import, inject_eval, inject_broad_except,
              inject_off_by_one, inject_stub, inject_hallucinated_kwarg,
              inject_placeholder]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-class", type=int, default=10)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    clean_dir = HERE / "labeled" / "clean"
    out_dir = HERE / "labeled" / "injected"
    out_dir.mkdir(parents=True, exist_ok=True)
    clean = sorted(clean_dir.glob("*.py"))
    if not clean:
        raise SystemExit("no clean solutions in labeled/clean/ "
                         "(run run_experiment.py --label first)")

    manifest = []
    for inject in INJECTIONS:
        made = 0
        for path in rng.sample(clean, len(clean)):
            if made >= args.per_class:
                break
            result = inject(path.read_text(encoding="utf-8"), rng)
            if result is None:
                continue
            mutated, defect = result
            name = f"{path.stem}__{inject.__name__}.py"
            (out_dir / name).write_text(mutated, encoding="utf-8")
            manifest.append({"file": name, "source": path.name, "defect": defect})
            made += 1

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"injected {len(manifest)} defective samples -> {out_dir}")


if __name__ == "__main__":
    main()
