"""Regression tests for the non-mutating tracked-file secret gate."""

import subprocess
from pathlib import Path


def test_detect_secrets_hook_rejects_injected_secret(tmp_path: Path) -> None:
    candidate = tmp_path / "injected.py"
    candidate.write_text('token = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
    baseline = Path(".secrets.baseline")
    result = subprocess.run(
        ["uv", "run", "detect-secrets-hook", "--baseline", str(baseline), str(candidate)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
