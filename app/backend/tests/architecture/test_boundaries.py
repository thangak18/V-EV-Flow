"""Static checks for the dependency boundaries shared by all modules."""

import ast
from pathlib import Path

import pytest

FORBIDDEN_CONTRACT_DEPENDENCIES = (
    "app.backend.api",
    "app.backend.infrastructure",
    "app.backend.modules",
)


def _string_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _string_value(node.left)
        right = _string_value(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    import_module_names = {"import_module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
            import_module_names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "importlib"
            )
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
            if node.module == "importlib":
                import_module_names.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "import_module"
                )
        elif (
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id in import_module_names)
                or (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in import_module_names
                    and node.func.attr == "import_module"
                )
                or (isinstance(node.func, ast.Name) and node.func.id == "__import__")
            )
            and node.args
        ):
            module = _string_value(node.args[0])
            if module is not None:
                modules.add(module)
    return modules


def _forbidden_modules(modules: set[str]) -> list[str]:
    return sorted(
        module
        for module in modules
        if module in FORBIDDEN_CONTRACT_DEPENDENCIES
        or module.startswith(tuple(f"{name}." for name in FORBIDDEN_CONTRACT_DEPENDENCIES))
    )


def test_contracts_do_not_import_application_modules() -> None:
    for path in Path("app/backend/contracts").rglob("*.py"):
        modules = _imported_modules(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        forbidden = _forbidden_modules(modules)
        assert not forbidden, f"{path} imports forbidden modules: {', '.join(forbidden)}"


@pytest.mark.parametrize(
    "source",
    [
        "from app.backend.api import main",
        "import app.backend.api.main",
        "from app.backend.infrastructure import repositories",
        'import importlib\nimportlib.import_module("app.backend." + "modules.prediction")',
        'from importlib import import_module as load\nload("app.backend.api.main")',
        '__import__("app.backend.infrastructure.state")',
    ],
)
def test_import_parser_resolves_direct_and_dynamic_imports(source: str) -> None:
    modules = _imported_modules(ast.parse(source))
    assert _forbidden_modules(modules)
