"""Static AST guard for untrusted model code.

This is a guardrail, not a security boundary: it rejects obviously dangerous
constructs fast, before code ever reaches the subprocess sandbox. The sandbox
(timeout + memory cap + separate process) is what contains infinite loops and
resource abuse.
"""

from __future__ import annotations

import ast

MAX_CODE_BYTES = 200_000

ALLOWED_ROOTS = frozenset(
    {
        "math",
        "random",
        "numpy",
        "itertools",
        "functools",
        "collections",
        "dataclasses",
        "statistics",
        "typing",
        "abc",
        "enum",
        "numbers",
        "fractions",
        "decimal",
        "copy",
        "__future__",
        "saboragi",
    }
)

BANNED_NAMES = frozenset(
    {
        "open",
        "exec",
        "eval",
        "__import__",
        "compile",
        "input",
        "breakpoint",
        "exit",
        "quit",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        "memoryview",
    }
)


def check(code: str) -> list[str]:
    """Return a list of problems (empty = code passes the guard)."""
    errors: list[str] = []
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        errors.append(f"code exceeds {MAX_CODE_BYTES} bytes")
        return errors
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error at line {exc.lineno}: {exc.msg}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_ROOTS:
                    errors.append(f"line {node.lineno}: import of {alias.name!r} is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                errors.append(f"line {node.lineno}: relative imports are not allowed")
            elif (node.module or "").split(".")[0] not in ALLOWED_ROOTS:
                errors.append(f"line {node.lineno}: import from {node.module!r} is not allowed")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            errors.append(f"line {node.lineno}: use of {node.id!r} is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                errors.append(
                    f"line {node.lineno}: dunder attribute access ({node.attr!r}) is not allowed"
                )
    return errors


def raise_if_bad(code: str) -> None:
    errors = check(code)
    if errors:
        raise ValueError("guard rejected model code:\n- " + "\n- ".join(errors))
