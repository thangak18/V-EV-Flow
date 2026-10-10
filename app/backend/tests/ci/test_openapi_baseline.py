"""Tests for the CI OpenAPI baseline preparation helper."""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(".github/scripts/prepare-openapi-baseline.sh").resolve()
OPENAPI_PATH = "app/backend/contracts/openapi.yaml"


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _repository(tmp_path: Path, include_openapi: bool) -> Path:
    _run("git", "init", "--initial-branch=main", cwd=tmp_path)
    _run("git", "config", "user.email", "ci@example.test", cwd=tmp_path)
    _run("git", "config", "user.name", "CI Test", cwd=tmp_path)
    (tmp_path / "README.md").write_text("fixture\n", encoding="utf-8")
    if include_openapi:
        artifact = tmp_path / OPENAPI_PATH
        artifact.parent.mkdir(parents=True)
        artifact.write_text("openapi: 3.1.0\n", encoding="utf-8")
    _run("git", "add", ".", cwd=tmp_path)
    _run("git", "commit", "-m", "fixture", cwd=tmp_path)
    return tmp_path


def _prepare(repo: Path) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    output = repo / "github-output.txt"
    baseline = repo / ".openapi-main.yaml"
    result = subprocess.run(
        ["bash", str(SCRIPT), "main", str(baseline)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GITHUB_OUTPUT": str(output)},
    )
    return result, baseline, output


def test_baseline_helper_materializes_committed_openapi(tmp_path: Path) -> None:
    result, baseline, output = _prepare(_repository(tmp_path, include_openapi=True))

    assert baseline.read_text(encoding="utf-8") == "openapi: 3.1.0\n"
    assert output.read_text(encoding="utf-8") == "present=true\n"
    assert "will run" in result.stdout


def test_baseline_helper_allows_initial_openapi_artifact(tmp_path: Path) -> None:
    repo = _repository(tmp_path, include_openapi=False)
    stale_baseline = repo / ".openapi-main.yaml"
    stale_baseline.write_text("stale\n", encoding="utf-8")

    result, baseline, output = _prepare(repo)

    assert not baseline.exists()
    assert output.read_text(encoding="utf-8") == "present=false\n"
    assert "first committed OpenAPI artifact" in result.stdout
