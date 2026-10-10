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


def _imported_modules(tree: ast.AST, package: str | None = None) -> set[str]:
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
            imported = node.module
            if node.level and package:
                base = package.split(".")[: -node.level]
                imported = ".".join(base + [node.module])
            if imported.startswith("app.backend.modules"):
                modules.add(imported)
                modules.update(f"{imported}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level and package:
            base = package.split(".")[: -node.level]
            imported = ".".join(base + ([node.module] if node.module else []))
            if imported.startswith("app.backend.modules"):
                modules.add(imported)
                modules.update(f"{imported}.{alias.name}" for alias in node.names)
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


def _private_or_cross_domain_imports(
    modules: set[str], source_domain: str | None = None
) -> list[str]:
    domains = ("station_data", "simulation", "prediction", "recommendation")
    violations: list[str] = []
    for module in modules:
        parts = module.split(".")
        if len(parts) < 4 or parts[:3] != ["app", "backend", "modules"]:
            continue
        if parts[3] not in domains:
            continue
        if any(part.startswith("_") for part in parts[4:]):
            violations.append(module)
        if source_domain is not None and parts[3] != source_domain:
            violations.append(module)
    return sorted(set(violations))


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


@pytest.mark.parametrize(
    "source,source_domain",
    [
        ("from app.backend.modules.prediction._internal import model", "prediction"),
        ("from app.backend.modules.station_data import generator", "prediction"),
        ("from ..station_data import generator", "prediction"),
        ("from app.backend.modules import station_data", "prediction"),
    ],
)
def test_domain_import_parser_rejects_private_and_cross_domain_imports(
    source: str, source_domain: str
) -> None:
    modules = _imported_modules(
        ast.parse(source), package=f"app.backend.modules.{source_domain}.fixture"
    )
    assert _private_or_cross_domain_imports(modules, source_domain)


def test_domain_files_have_no_private_or_cross_domain_imports() -> None:
    for path in Path("app/backend/modules").rglob("*.py"):
        modules = _imported_modules(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        source_domain = path.parts[path.parts.index("modules") + 1]
        violations = _private_or_cross_domain_imports(modules, source_domain)
        assert not violations, (
            f"{path} imports private/cross-domain modules: {', '.join(violations)}"
        )
