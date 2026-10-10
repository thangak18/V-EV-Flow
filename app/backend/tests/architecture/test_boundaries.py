"""Static checks for the dependency boundaries shared by all modules."""

from pathlib import Path


def test_contracts_do_not_import_application_modules() -> None:
    forbidden = ("app.backend.api", "app.backend.infrastructure", "app.backend.modules")
    for path in Path("app/backend/contracts").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(name in text for name in forbidden), path

