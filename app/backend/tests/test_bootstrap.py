from pathlib import Path


def test_required_repository_commands_are_declared() -> None:
    makefile = Path("Makefile").read_text()
    for target in ("setup:", "format:", "lint:", "test:", "contract-check:", "smoke:", "ci:"):
        assert target in makefile
