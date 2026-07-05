"""Static (L1) detectors. Each takes the parsed tree and source, returns findings.

Analyzed code is never executed here (only parsed) -- see NFR-3 in the spec.
"""
import ast
import io
import re
import tokenize
from dataclasses import dataclass

from .findings import Finding
from .known_packages import closest_popular, is_known


@dataclass(frozen=True)
class ScanContext:
    """Extra knowledge for detectors that need more than the source itself."""
    known_modules: frozenset[str] = frozenset()  # first-party modules of the scanned repo
    trust_local_env: bool = False  # opt-in: accept packages installed locally

# stdlib modules we dare to import ourselves to verify attribute access (TG-D02)
ATTR_CHECK_MODULES = {
    "os", "os.path", "sys", "json", "re", "math", "random", "string",
    "time", "datetime", "itertools", "functools", "collections",
    "pathlib", "hashlib", "shutil", "subprocess", "base64", "textwrap",
}

SECRET_WORDS = ("password", "passwd", "token", "secret", "api_key", "apikey")
IGNORE_RE = re.compile(r"\bTG-D\d{2}\b", re.IGNORECASE)


def _dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _comments(source):
    try:
        yield from (
            tok for tok in tokenize.generate_tokens(io.StringIO(source).readline)
            if tok.type == tokenize.COMMENT
        )
    except tokenize.TokenError:
        return


def _ignored_detectors(source):
    ignores = {}
    marker = "trustgate: ignore"
    for tok in _comments(source):
        text = tok.string.lstrip("#").strip()
        lower = text.lower()
        if marker not in lower:
            continue
        after = text[lower.index(marker) + len(marker):]
        detectors = {m.group(0).upper() for m in IGNORE_RE.finditer(after)}
        ignores.setdefault(tok.start[0], set()).update(detectors or {"*"})
    return ignores


def check_imports(tree, source, ctx):  # TG-D01
    out = []
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules = [(node.module, node.lineno)]
        for mod, line in modules:
            if is_known(mod, extra_known=ctx.known_modules,
                        trust_local_env=ctx.trust_local_env):
                continue
            similar = closest_popular(mod)
            if similar:
                out.append(Finding(
                    "TG-D01", "critical", line,
                    f"import '{mod}' looks like a typo/hallucination of '{similar}'"))
            else:
                out.append(Finding(
                    "TG-D01", "major", line,
                    f"import '{mod}': unknown package, verify it exists"))
    return out


def _version_guarded_lines(tree):
    """Lines inside `if sys.version_info...` / `hexversion` blocks.

    Code there intentionally differs per interpreter, so validating it against
    the interpreter running TrustGate (TG-D02/TG-D13) would be a coin flip.
    """
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_src = ast.dump(node.test)
            if "version_info" in test_src or "hexversion" in test_src:
                lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def check_attributes(tree, source, ctx):  # TG-D02
    import importlib

    guarded = _version_guarded_lines(tree)
    out = []
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                # plain `import os.path` still binds the name `os`
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    top = a.name.split(".")[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.level == 0 \
                and node.module in ATTR_CHECK_MODULES:
            mod = importlib.import_module(node.module)
            for a in node.names:
                if a.name != "*" and not hasattr(mod, a.name):
                    out.append(Finding("TG-D02", "critical", node.lineno,
                                       f"'{node.module}' has no attribute '{a.name}'"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        dotted = _dotted_name(node)
        if not dotted:
            continue
        parts = dotted.split(".")
        real_root = aliases.get(parts[0])
        if real_root is None:
            continue
        full = [real_root] + parts[1:]
        # longest whitelisted prefix, then verify the next attribute exists
        for cut in range(len(full) - 1, 0, -1):
            prefix = ".".join(full[:cut])
            if prefix in ATTR_CHECK_MODULES:
                mod = importlib.import_module(prefix)
                if not hasattr(mod, full[cut]):
                    out.append(Finding("TG-D02", "critical", node.lineno,
                                       f"'{prefix}' has no attribute '{full[cut]}'"))
                break

    seen = set()
    unique = []
    for f in out:  # ast.walk visits nested Attribute nodes repeatedly
        if f.line not in guarded and (f.line, f.message) not in seen:
            seen.add((f.line, f.message))
            unique.append(f)
    return unique


def check_dangerous_exec(tree, source, ctx):  # TG-D03
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            literal = node.args and isinstance(node.args[0], ast.Constant)
            out.append(Finding(
                "TG-D03", "minor" if literal else "critical", node.lineno,
                f"{node.func.id}() {'on a literal' if literal else 'on non-literal data'}"))
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "loads":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
                out.append(Finding("TG-D03", "critical", node.lineno,
                                   "pickle.loads() on untrusted data allows code execution"))
    return out


def _static_string(node):
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return _static_string(node.left) and _static_string(node.right)
    return False


def _has_dynamic_string(node):
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return not _static_string(node)
    return False


def check_sql_injection(tree, source, ctx):  # TG-D04
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("execute", "executemany") and node.args):
            if _has_dynamic_string(node.args[0]):
                out.append(Finding("TG-D04", "critical", node.lineno,
                                   "SQL query built by string interpolation, use parameters"))
    return out


def check_shell_true(tree, source, ctx):  # TG-D05
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                literal = node.args and isinstance(node.args[0], ast.Constant)
                out.append(Finding(
                    "TG-D05", "minor" if literal else "major", node.lineno,
                    "shell=True" + ("" if literal else " with a non-literal command")))
    return out


def check_tls_verify(tree, source, ctx):  # TG-D06
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                out.append(Finding("TG-D06", "major", node.lineno,
                                   "TLS certificate verification disabled (verify=False)"))
    return out


def _contains_weak_hash(node):
    for sub in ast.walk(node):
        if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                and sub.func.attr in ("md5", "sha1")):
            return sub.lineno
    return None


def check_weak_hash(tree, source, ctx):  # TG-D07
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id.lower() for t in node.targets if isinstance(t, ast.Name)]
        if any(w in n for n in names for w in SECRET_WORDS):
            line = _contains_weak_hash(node.value)
            if line:
                out.append(Finding("TG-D07", "major", line,
                                   "md5/sha1 used for a secret, use a KDF (bcrypt/argon2)"))
    return out


def check_broad_except(tree, source, ctx):  # TG-D08
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        bare = node.type is None
        broad = (isinstance(node.type, ast.Name)
                 and node.type.id in ("Exception", "BaseException"))
        if not (bare or broad):
            continue
        swallows = all(
            isinstance(s, ast.Pass)
            or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
            for s in node.body
        )
        has_raise = any(isinstance(s, ast.Raise) for s in ast.walk(node))
        if (bare or swallows) and not has_raise:
            out.append(Finding("TG-D08", "major", node.lineno,
                               "broad except silently swallows errors"))
    return out


def _is_abstract(func):
    for d in func.decorator_list:
        name = d.attr if isinstance(d, ast.Attribute) else getattr(d, "id", "")
        if name in ("abstractmethod", "overload"):
            return True
    return False


def check_stubs(tree, source, ctx):  # TG-D09
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or _is_abstract(node):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            body = body[1:]  # skip docstring
        if not body:
            continue

        def is_stub_stmt(s):
            if isinstance(s, ast.Pass):
                return True
            if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is ...:
                return True
            if isinstance(s, ast.Raise) and s.exc is not None:
                name = s.exc.func.id if isinstance(s.exc, ast.Call) and isinstance(s.exc.func, ast.Name) \
                    else getattr(s.exc, "id", "")
                return name == "NotImplementedError"
            return False

        if all(is_stub_stmt(s) for s in body):
            out.append(Finding("TG-D09", "major", node.lineno,
                               f"function '{node.name}' is a stub, not an implementation"))
    for tok in _comments(source):
        if any(m in tok.string for m in ("TODO", "FIXME")):
            out.append(Finding("TG-D09", "minor", tok.start[0], "TODO/FIXME marker left in code"))
    return out


def check_dead_code(tree, source, ctx):  # TG-D10
    out = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if not isinstance(block, list):
                continue
            terminated = False
            for stmt in block:
                if terminated:
                    out.append(Finding("TG-D10", "minor", stmt.lineno,
                                       "unreachable code after return/raise"))
                    break
                if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                    terminated = True
        if isinstance(node, ast.If) and isinstance(node.test, ast.Constant):
            dead = node.orelse if node.test.value else node.body
            if dead:
                out.append(Finding("TG-D10", "minor", dead[0].lineno,
                                   "branch is dead: condition is a constant"))
    return out


def _import_bindings(tree):
    """Names bound by imports: alias -> module, plus from-imports -> (module, attr)."""
    aliases = {}
    from_imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    top = a.name.split(".")[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.level == 0 \
                and node.module in ATTR_CHECK_MODULES:
            for a in node.names:
                if a.name != "*":
                    from_imports[a.asname or a.name] = (node.module, a.name)
    return aliases, from_imports


def _resolve_stdlib_callable(node, aliases, from_imports):
    """Return the actual stdlib object a call targets, or None."""
    import importlib

    if isinstance(node.func, ast.Name):
        binding = from_imports.get(node.func.id)
        if binding is None:
            return None
        mod = importlib.import_module(binding[0])
        return getattr(mod, binding[1], None)
    if not isinstance(node.func, ast.Attribute):
        return None
    dotted = _dotted_name(node.func)
    if not dotted:
        return None
    parts = dotted.split(".")
    real_root = aliases.get(parts[0])
    if real_root is None:
        return None
    full = [real_root] + parts[1:]
    for cut in range(len(full) - 1, 0, -1):
        prefix = ".".join(full[:cut])
        if prefix in ATTR_CHECK_MODULES:
            obj = importlib.import_module(prefix)
            for attr in full[cut:]:
                obj = getattr(obj, attr, None)
                if obj is None:
                    return None  # TG-D02's job, not ours
            return obj
    return None


def check_kwargs(tree, source, ctx):  # TG-D13
    """Keyword arguments that the called stdlib function does not accept.

    A classic LLM hallucination: the function exists, the kwarg does not
    (e.g. shutil.copy(src, dst, overwrite=True)). Only whitelisted stdlib
    modules are checked, so the verdict stays deterministic.
    """
    import inspect

    out = []
    guarded = _version_guarded_lines(tree)
    aliases, from_imports = _import_bindings(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.keywords \
                or node.lineno in guarded:
            continue
        func = _resolve_stdlib_callable(node, aliases, from_imports)
        if func is None or not callable(func):
            continue
        try:
            params = inspect.signature(func).parameters
        except (ValueError, TypeError):
            continue  # C function without introspectable signature
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            continue
        valid = {
            name for name, p in params.items()
            if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                          inspect.Parameter.KEYWORD_ONLY)
        }
        for kw in node.keywords:
            if kw.arg is not None and kw.arg not in valid:
                name = getattr(func, "__qualname__", getattr(func, "__name__", "?"))
                out.append(Finding(
                    "TG-D13", "critical", node.lineno,
                    f"'{name}()' has no keyword argument '{kw.arg}'"))
    return out


PLACEHOLDER_RES = (
    re.compile(r"your[-_ ]?(api[-_ ]?key|token|secret|password|username|email|domain)",
               re.IGNORECASE),
    re.compile(r"<\s*your\b[^>]*>", re.IGNORECASE),
    re.compile(r"\bYOUR_[A-Z][A-Z0-9_]+\b"),
    re.compile(r"\bchange[-_ ]?me\b", re.IGNORECASE),
    re.compile(r"\binsert[-_ ](your|api|key|token)\b", re.IGNORECASE),
)


def check_placeholders(tree, source, ctx):  # TG-D14
    """Template placeholder values left in string literals (fake keys, tokens).

    LLMs routinely ship them instead of wiring real configuration; merged
    as-is they become runtime failures or fake credentials.
    """
    out = []
    seen = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        for pattern in PLACEHOLDER_RES:
            match = pattern.search(node.value)
            if match and (node.lineno, match.group(0)) not in seen:
                seen.add((node.lineno, match.group(0)))
                out.append(Finding(
                    "TG-D14", "major", node.lineno,
                    f"placeholder value '{match.group(0)}' left in code"))
                break
    return out


def check_tautological_asserts(tree, source, ctx):  # TG-D11
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        if isinstance(node.test, ast.Constant):
            out.append(Finding("TG-D11", "major", node.lineno,
                               "assert on a constant proves nothing"))
        elif isinstance(node.test, ast.Compare) and len(node.test.comparators) == 1:
            if ast.dump(node.test.left) == ast.dump(node.test.comparators[0]):
                out.append(Finding("TG-D11", "major", node.lineno,
                                   "assert compares an expression with itself"))
    return out


DETECTORS = [
    check_imports,
    check_attributes,
    check_dangerous_exec,
    check_sql_injection,
    check_shell_true,
    check_tls_verify,
    check_weak_hash,
    check_broad_except,
    check_stubs,
    check_dead_code,
    check_tautological_asserts,
    check_kwargs,
    check_placeholders,
]

# TG-D12 (dependency manifests) lives in scan.py: it needs manifest files,
# not a Python AST. Together: 13 static detectors + 1 manifest detector.
DETECTOR_CODES = (
    "TG-D01", "TG-D02", "TG-D03", "TG-D04", "TG-D05",
    "TG-D06", "TG-D07", "TG-D08", "TG-D09", "TG-D10", "TG-D11",
    "TG-D13", "TG-D14",
)

# Detectors targeting the defect profile characteristic of generated code
# (hallucinated names, stubs, placeholders) vs. general code-quality rules.
LLM_SPECIFIC_DETECTORS = frozenset(
    {"TG-D01", "TG-D02", "TG-D09", "TG-D12", "TG-D13", "TG-D14"})


def run_static(
    source: str,
    disabled_detectors: set[str] | None = None,
    ctx: ScanContext | None = None,
) -> list[Finding]:
    tree = ast.parse(source)
    ctx = ctx or ScanContext()
    disabled = set(disabled_detectors or ())
    ignored = _ignored_detectors(source)
    findings = []
    for det in DETECTORS:
        findings.extend(det(tree, source, ctx))
    findings = [
        f for f in findings
        if "*" not in ignored.get(f.line, set())
        and f.detector not in ignored.get(f.line, set())
        and f.detector not in disabled
    ]
    findings.sort(key=lambda f: (f.line, f.detector))
    return findings
