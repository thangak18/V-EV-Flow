"""Exercise the portable harness against disposable Git repositories and real subprocesses."""

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(".github/scripts/harness.py").resolve()
SPEC = importlib.util.spec_from_file_location("vev_harness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


def command(root: Path, *argv: str) -> str:
    return subprocess.check_output(argv, cwd=root, text=True).strip()


def commit(root: Path, message: str = "fixture") -> str:
    command(root, "git", "add", ".")
    command(root, "git", "commit", "-m", message)
    return command(root, "git", "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    command(tmp_path, "git", "init", "--initial-branch=main")
    command(tmp_path, "git", "config", "user.email", "harness@example.test")
    command(tmp_path, "git", "config", "user.name", "Harness Test")
    command(tmp_path, "git", "remote", "add", "origin", "https://github.com/example/fixture.git")
    (tmp_path / ".gitignore").write_text(".harness/\n")
    foundation_sha = commit(tmp_path, "foundation fixture")
    policy = json.loads(Path(harness.POLICY_PATH).read_text())
    policy["foundation"]["sha"] = foundation_sha
    policy["foundation"]["review_status"] = "PASS"
    policy["foundation"]["review_url"] = "https://github.com/example/fixture/pull/1"
    for relative in (harness.POLICY_PATH, harness.SCHEMA_PATH):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, target)
    (tmp_path / harness.POLICY_PATH).write_text(json.dumps(policy))
    source = tmp_path / "app/frontend/src/feature.ts"
    source.parent.mkdir(parents=True)
    source.write_text("export const feature = 1;\n")
    generated = tmp_path / "app/frontend/src/types/api.generated.ts"
    generated.parent.mkdir()
    generated.write_text("// generated fixture\n")
    (tmp_path / "Makefile").write_text("test ci:\n\t@echo verified\n")
    sha = commit(tmp_path)
    command(tmp_path, "git", "update-ref", "refs/remotes/origin/main", sha)
    command(tmp_path, "git", "switch", "-c", "feat/web-map")
    return tmp_path


def issue(root: Path, verification: str = "test") -> dict:
    spec = {
        "lane": "web-map",
        "reviewer": "reviewer",
        "scope": ["app/frontend/src/**"],
        "acceptance": [
            {"id": "AC-01", "description": "observable fixture", "verification": [verification]}
        ],
        "dependencies": [],
        "contract_impact": "none",
        "data_origin": "mock",
        "rollback": "revert",
    }
    return {
        "number": 9,
        "url": "https://github.com/example/fixture/issues/9",
        "title": "fixture",
        "body": "Goal\n```json\n" + json.dumps(spec) + "\n```",
        "assignees": [{"login": "owner"}],
        "updatedAt": "2026-10-11T00:00:00Z",
        "state": "OPEN",
    }


def activate(root: Path, verification: str = "test") -> dict:
    snapshot = root / ".harness/input.json"
    snapshot.parent.mkdir(exist_ok=True)
    snapshot.write_text(json.dumps(issue(root, verification)))
    return harness.start(
        root,
        argparse.Namespace(
            issue="9",
            snapshot=str(snapshot),
            base="origin/main",
            bootstrap=False,
            tool="manual",
            surface="cli",
        ),
    )


def finish_handoff(root: Path) -> None:
    harness.handoff(root, 9)
    path = root / "docs/harness/handoffs/9.md"
    text = path.read_text()
    text = text.replace('"completed": []', '"completed": ["AC-01"]')
    text = text.replace('"remaining": [\n    "AC-01"\n  ]', '"remaining": []')
    text = text.replace(
        "Describe the next concrete action before handing off", "Request independent review"
    )
    path.write_text(text)
    commit(root, "checkpoint with portable handoff")


def run(root: Path, check: str = "test", ac: bool = True) -> dict:
    return harness.run_check(
        root,
        argparse.Namespace(
            issue="9", check=check, path=None, ac=["AC-01"] if ac else [], timeout=10
        ),
    )


def scoped(root: Path, policy: dict | None = None) -> dict:
    return harness.scope_check(
        root,
        policy or harness.load_policy(root, "origin/main"),
        harness.task_spec(issue(root)),
        9,
        "origin/main",
    )


def test_scope_includes_committed_staged_unstaged_and_untracked(repo: Path) -> None:
    source = repo / "app/frontend/src/feature.ts"
    source.write_text("committed\n")
    commit(repo)
    source.write_text("staged\n")
    command(repo, "git", "add", str(source))
    source.write_text("unstaged\n")
    filename = "app/frontend/src/tên with space\nline.ts"
    (repo / filename).write_text("new\n")
    assert set(scoped(repo)["paths"]) == {"app/frontend/src/feature.ts", filename}
    (repo / "README.md").write_text("unrelated existing work\n")
    with pytest.raises(harness.HarnessError, match="README"):
        scoped(repo)
    assert (repo / "README.md").read_text() == "unrelated existing work\n"


@pytest.mark.parametrize("operation", ["edit", "delete", "rename-out", "rename-in"])
def test_protected_paths_override_parent_allowlist(repo: Path, operation: str) -> None:
    generated = repo / "app/frontend/src/types/api.generated.ts"
    if operation == "edit":
        generated.write_text("modified\n")
    elif operation == "delete":
        generated.unlink()
    elif operation == "rename-out":
        generated.rename(repo / "app/frontend/src/other.ts")
    else:
        generated.unlink()
        (repo / "app/frontend/src/feature.ts").rename(generated)
    with pytest.raises(harness.HarnessError, match="api.generated"):
        scoped(repo)


def test_policy_cannot_authorize_its_own_feature_diff(repo: Path) -> None:
    current = json.loads((repo / harness.POLICY_PATH).read_text())
    current["protected_paths"] = []
    current["lanes"]["web-map"]["allowed_paths"] = ["**"]
    (repo / harness.POLICY_PATH).write_text(json.dumps(current))
    (repo / "app/frontend/src/types/api.generated.ts").write_text("changed\n")
    with pytest.raises(harness.HarnessError, match="Scope violation"):
        scoped(repo)


def test_unknown_base_is_blocked(repo: Path) -> None:
    with pytest.raises(harness.HarnessError) as error:
        harness.load_policy(repo, "missing-base")
    assert error.value.result == "BLOCKED"


def test_other_issue_handoff_is_not_allowed(repo: Path) -> None:
    path = repo / "docs/harness/handoffs/10.md"
    path.parent.mkdir(parents=True)
    path.write_text("another issue\n")
    with pytest.raises(harness.HarnessError, match="10.md"):
        scoped(repo)


def test_symlink_cannot_escape_checkout(repo: Path, tmp_path: Path) -> None:
    target = tmp_path.parent / "outside-harness-fixture"
    target.write_text("preserve")
    (repo / ".harness").symlink_to(target.parent, target_is_directory=True)
    with pytest.raises(harness.HarnessError, match="escapes"):
        harness.write_json(repo, ".harness/probe.json", {"must_not_write": True})
    assert target.read_text() == "preserve"


def test_snapshot_wrong_repo_and_duplicate_ac_are_rejected(repo: Path) -> None:
    data = issue(repo)
    data["url"] = "https://github.com/other/repo/issues/9"
    with pytest.raises(harness.HarnessError):
        harness.normalize_issue(repo, data, 9)
    data = issue(repo)
    spec = harness.task_spec(data)
    spec["acceptance"].append(spec["acceptance"][0])
    data["body"] = "```json\n" + json.dumps(spec) + "\n```"
    with pytest.raises(harness.HarnessError, match="unique"):
        harness.normalize_issue(repo, data, 9)


def test_pending_foundation_blocks_feature_start(repo: Path) -> None:
    policy = harness.load_policy(repo)
    policy["foundation"]["review_status"] = "BLOCKED"
    (repo / harness.POLICY_PATH).write_text(json.dumps(policy))
    sha = commit(repo)
    command(repo, "git", "update-ref", "refs/remotes/origin/main", sha)
    with pytest.raises(harness.HarnessError, match="Foundation"):
        activate(repo)


def test_real_failed_subprocess_cannot_produce_pass(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo)
    monkeypatch.setattr(
        harness,
        "check_command",
        lambda *args: ["python3", "-c", "print('failure');raise SystemExit(7)"],
    )
    record = run(repo)
    assert record["result"] == "FAIL" and record["exit_code"] == 7
    assert "failure" in (repo / record["log_path"]).read_text()


def test_missing_executable_records_blocked(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    activate(repo)
    monkeypatch.setattr(harness, "check_command", lambda *args: ["missing-vev-command"])
    record = run(repo)
    assert record["result"] == "BLOCKED" and record["exit_code"] is None


def test_ready_uses_clean_commit_and_external_evidence_without_recursive_sha(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    assert run(repo)["result"] == "PASS"
    assert run(repo, "ci", ac=False)["result"] == "PASS"
    assert harness.ready(repo, 9, refresh=False)["state"] == "verified"
    assert command(repo, "git", "status", "--porcelain") == ""


def test_failed_evidence_metadata_cannot_be_changed_to_pass(repo: Path) -> None:
    (repo / "Makefile").write_text("test ci:\n\t@echo failed-fixture\n\t@exit 7\n")
    base = commit(repo, "failing gates fixture")
    command(repo, "git", "update-ref", "refs/remotes/origin/main", base)
    activate(repo)
    finish_handoff(repo)
    for check, ac in (("test", True), ("ci", False)):
        record = run(repo, check, ac=ac)
        assert record["result"] == "FAIL" and record["exit_code"] != 0
    active, _ = harness.active_task(repo)
    for path in (repo / active["directory"]).glob("*.evidence.json"):
        record = json.loads(path.read_text())
        record.update(result="PASS", exit_code=0)
        path.write_text(json.dumps(record))
    with pytest.raises(harness.HarnessError, match="integrity"):
        harness.ready(repo, 9, refresh=False)


@pytest.mark.parametrize("field", ["argv", "finished_at", "integrity"])
def test_evidence_seal_covers_command_and_ordering_metadata(repo: Path, field: str) -> None:
    activate(repo)
    finish_handoff(repo)
    run(repo)
    run(repo, "ci", ac=False)
    active, _ = harness.active_task(repo)
    path = next((repo / active["directory"]).glob("*.evidence.json"))
    record = json.loads(path.read_text())
    assert record["schema_version"] == 2
    if field == "integrity":
        record.pop(field)
    else:
        record[field] = ["make", "setup"] if field == "argv" else "2099-01-01T00:00:00Z"
    path.write_text(json.dumps(record))
    with pytest.raises(harness.HarnessError, match="integrity"):
        harness.ready(repo, 9, refresh=False)


def test_legacy_unsealed_proof_requires_fresh_run_but_preserves_history(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    run(repo)
    run(repo, "ci", ac=False)
    active, _ = harness.active_task(repo)
    legacy = []
    for path in (repo / active["directory"]).glob("*.evidence.json"):
        record = json.loads(path.read_text())
        record["schema_version"] = 1
        record.pop("integrity")
        path.write_text(json.dumps(record))
        original = path.with_name(path.name.replace(".v2.evidence.json", ".evidence.json"))
        path.rename(original)
        legacy.append(original)
    with pytest.raises(harness.HarnessError, match="Legacy unsealed"):
        harness.ready(repo, 9, refresh=False)
    run(repo)
    run(repo, "ci", ac=False)
    output = harness.ready(repo, 9, refresh=False)
    assert output["result"] == "PASS" and output["evidence_trust"] == "self-reported"
    assert output["review_ready"] is False
    assert all(path.exists() for path in legacy)


def test_evidence_key_is_local_private_and_required_for_validation(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    run(repo)
    run(repo, "ci", ac=False)
    key = repo / ".harness/evidence.key"
    assert key.stat().st_mode & 0o777 == 0o600
    assert len(key.read_bytes()) == 32
    assert command(repo, "git", "status", "--porcelain") == ""
    key.unlink()
    with pytest.raises(harness.HarnessError, match="integrity key missing"):
        harness.ready(repo, 9, refresh=False)
    assert not key.exists()


@pytest.mark.parametrize("mutation", ["identity", "downgrade"])
def test_modified_identity_or_version_cannot_hide_latest_failed_evidence(
    repo: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    activate(repo)
    finish_handoff(repo)
    run(repo)
    run(repo, "ci", ac=False)
    monkeypatch.setattr(
        harness, "check_command", lambda *args: ["python3", "-c", "raise SystemExit(1)"]
    )
    failed = run(repo)
    active, _ = harness.active_task(repo)
    for path in (repo / active["directory"]).glob("*.evidence.json"):
        record = json.loads(path.read_text())
        if record["log_path"] == failed["log_path"]:
            if mutation == "identity":
                record["identity"]["head"] = "f" * 40
            else:
                record["schema_version"] = 1
                record.pop("integrity")
            path.write_text(json.dumps(record))
    with pytest.raises(harness.HarnessError, match="integrity"):
        harness.ready(repo, 9, refresh=False)


def test_scope_cli_rejects_head_that_hides_committed_protected_change(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    activate(repo)
    (repo / "app/frontend/src/types/api.generated.ts").write_text("protected change\n")
    commit(repo, "scope violation fixture")
    with pytest.raises(harness.HarnessError, match="Scope violation"):
        scoped(repo)
    assert harness.main(["--root", str(repo), "scope", "--issue", "9", "--base", "HEAD"]) == 1
    assert "integration base" in json.loads(capsys.readouterr().out)["reason"]


@pytest.mark.parametrize("base", [None, "origin/main", "sha-alias"])
def test_scope_uses_saved_base_and_accepts_only_matching_sha_assertions(
    repo: Path, base: str | None, capsys: pytest.CaptureFixture[str]
) -> None:
    activate(repo)
    source = repo / "app/frontend/src/feature.ts"
    source.write_text("scoped committed change\n")
    commit(repo)
    argv = ["--root", str(repo), "scope", "--issue", "9"]
    if base:
        argv.extend(
            ["--base", harness.resolve(repo, "origin/main") if base == "sha-alias" else base]
        )
    assert harness.main(argv) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["paths"] == ["app/frontend/src/feature.ts"]
    assert output["base"] == harness.active_task(repo)[0]["base"]


def test_scope_default_blocks_protected_change_and_cannot_enable_bootstrap(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    activate(repo)
    argv = ["--root", str(repo), "scope", "--issue", "9"]
    assert harness.main([*argv, "--bootstrap"]) == 1
    assert "cannot enable bootstrap" in json.loads(capsys.readouterr().out)["reason"]
    (repo / "app/frontend/src/types/api.generated.ts").write_text("protected change\n")
    commit(repo)
    assert harness.main(argv) == 1
    assert "Scope violation" in json.loads(capsys.readouterr().out)["reason"]


def test_scope_blocks_advanced_saved_base_ref(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    activate(repo)
    (repo / "app/frontend/src/feature.ts").write_text("new base\n")
    new_base = commit(repo)
    command(repo, "git", "update-ref", "refs/remotes/origin/main", new_base)
    assert harness.main(["--root", str(repo), "scope", "--issue", "9"]) == 2
    assert "Integration base changed" in json.loads(capsys.readouterr().out)["reason"]


def test_bootstrap_ci_reports_blocked_manual_acceptance_not_overall_pass(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    command(repo, "git", "switch", "-c", "codex/harness-bootstrap")
    base = harness.load_policy(repo)["foundation"]["sha"]
    head = command(repo, "git", "rev-parse", "HEAD")
    event = repo / ".harness/event.json"
    event.parent.mkdir(exist_ok=True)
    event.write_text(
        json.dumps(
            {
                "pull_request": {
                    "base": {"sha": base},
                    "head": {"sha": head, "ref": "codex/harness-bootstrap"},
                }
            }
        )
    )
    monkeypatch.setattr(harness, "self_check", lambda root: {"result": "PASS"})
    assert harness.main(["--root", str(repo), "ci", "--event-file", str(event)]) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["result"] == output["scope"] == output["manual_acceptance"] == "BLOCKED"
    assert output["checks"] == "PASS" and output["mode"] == "bootstrap"
    assert output["review_ready"] is False
    assert output["head"] == head and output["base"] == base


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "old-pass",
        "wrong-head",
        "wrong-branch",
        "failed-checks",
        "wrong-exit",
        "normal-pass",
        "push-pass",
        "blocked-normal",
    ],
)
def test_ci_workflow_classifies_manual_gate_without_masking_failures(
    repo: Path, mutation: str | None
) -> None:
    workflow = Path(".github/workflows/ci.yml").read_text()
    block = workflow.split('export HARNESS_SCOPE_EXIT="$scope_exit"', 1)[1]
    script = textwrap.dedent(block.split("python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0])
    head, base = harness.resolve(repo, "HEAD"), harness.resolve(repo, "origin/main")
    output = {
        "result": "BLOCKED",
        "checks": "PASS",
        "mode": "bootstrap",
        "scope": "BLOCKED",
        "foundation_review": "BLOCKED",
        "manual_acceptance": "BLOCKED",
        "review_ready": False,
        "head": head,
        "base": base,
    }
    status, branch = 2, "codex/harness-bootstrap"
    if mutation == "old-pass":
        output["result"], status = "PASS", 0
    elif mutation == "wrong-head":
        output["head"] = "f" * 40
    elif mutation == "wrong-branch":
        branch = "feat/web-map"
    elif mutation == "failed-checks":
        output["checks"] = "FAIL"
    elif mutation == "wrong-exit":
        status = 1
    elif mutation in ("normal-pass", "blocked-normal"):
        output = {"result": "PASS", "head": head, "base": base}
        status, branch = 0, "feat/web-map"
        if mutation == "blocked-normal":
            output["manual_acceptance"] = "BLOCKED"
    elif mutation == "push-pass":
        output = {"result": "PASS", "scope": "NOT RUN"}
        status, branch, base = 0, "", ""
    path = repo / ".harness/ci/scope.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(output))
    summary = repo / ".harness/summary.md"
    process = subprocess.run(
        ["python3", "-c", script],
        cwd=repo,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "HARNESS_SCOPE_EXIT": str(status),
            "CHECKED_HEAD": head,
            "BASE_SHA": base,
            "HEAD_BRANCH": branch,
            "GITHUB_STEP_SUMMARY": str(summary),
        },
        timeout=5,
    )
    if mutation in (None, "normal-pass", "push-pass"):
        assert process.returncode == 0, process.stderr
        if mutation is None:
            assert "::warning" in process.stdout
            assert "manual acceptance BLOCKED" in summary.read_text()
            assert head in summary.read_text() and base in summary.read_text()
        else:
            assert "not established by CI" in summary.read_text()
    else:
        assert process.returncode != 0


@pytest.mark.parametrize("mutation", ["new-commit", "dirty", "log", "missing-log", "not-run"])
def test_stale_or_unexecuted_evidence_never_satisfies_ready(repo: Path, mutation: str) -> None:
    activate(repo)
    finish_handoff(repo)
    record = run(repo)
    run(repo, "ci", ac=False)
    if mutation in ("new-commit", "dirty"):
        (repo / "app/frontend/src/feature.ts").write_text("changed\n")
        if mutation == "new-commit":
            commit(repo)
    elif mutation == "log":
        (repo / record["log_path"]).write_text("tampered\n")
    elif mutation == "missing-log":
        (repo / record["log_path"]).unlink()
    else:
        active, _ = harness.active_task(repo)
        target = next((repo / active["directory"]).glob("*.evidence.json"))
        value = json.loads(target.read_text())
        value.update(result="NOT RUN", exit_code=None, log_path=None, log_sha256=None)
        target.write_text(json.dumps(value))
    with pytest.raises(harness.HarnessError):
        harness.ready(repo, 9, refresh=False)


def test_live_issue_change_invalidates_snapshot(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo)
    changed = issue(repo)
    changed["title"] = "new requirement"
    monkeypatch.setattr(harness, "fetch_issue", lambda *args: changed)
    with pytest.raises(harness.HarnessError, match="Issue changed"):
        harness.ready(repo, 9)


def test_ac_mapping_rejects_undeclared_check(repo: Path) -> None:
    activate(repo)
    with pytest.raises(harness.HarnessError, match="AC mapping"):
        run(repo, "ci")


def test_current_base_change_invalidates_readiness(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    run(repo)
    run(repo, "ci", ac=False)
    command(repo, "git", "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(harness.HarnessError, match="base"):
        harness.ready(repo, 9, refresh=False)


def test_handoff_does_not_overwrite_decisions(repo: Path) -> None:
    activate(repo)
    harness.handoff(repo, 9)
    path = repo / "docs/harness/handoffs/9.md"
    original = path.read_text()
    with pytest.raises(harness.HarnessError, match="already exists"):
        harness.handoff(repo, 9)
    assert path.read_text() == original


def test_later_failure_without_ac_mapping_invalidates_earlier_pass(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo)
    finish_handoff(repo)
    run(repo)
    run(repo, "ci", ac=False)
    monkeypatch.setattr(
        harness, "check_command", lambda *args: ["python3", "-c", "raise SystemExit(1)"]
    )
    run(repo, "test", ac=False)
    with pytest.raises(harness.HarnessError, match="failed"):
        harness.ready(repo, 9, refresh=False)


def test_handoff_requires_all_acceptance_ids_completed(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    path = repo / "docs/harness/handoffs/9.md"
    path.write_text(path.read_text().replace('"completed": ["AC-01"]', '"completed": []'))
    commit(repo, "incorrect handoff")
    run(repo)
    run(repo, "ci", ac=False)
    with pytest.raises(harness.HarnessError, match="completed"):
        harness.ready(repo, 9, refresh=False)


@pytest.mark.parametrize("provider", ["codex", "claude"])
@pytest.mark.parametrize("event", ["SessionStart", "Stop"])
def test_hooks_are_read_only_and_do_not_call_network_or_run_checks(
    repo: Path, provider: str, event: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo)
    before = command(repo, "git", "status", "--porcelain")
    monkeypatch.setattr(harness, "github_json", lambda *args: pytest.fail("hook network call"))
    monkeypatch.setattr(harness, "run_check", lambda *args: pytest.fail("hook ran a check"))
    output = harness.hook(repo, provider, event, {"hook_event_name": event, "cwd": str(repo)})
    assert "decision" not in output and "continue" not in output
    if event == "SessionStart":
        assert len(output["hookSpecificOutput"]["additionalContext"]) <= 1000
    else:
        assert "systemMessage" in output
    assert command(repo, "git", "status", "--porcelain") == before


@pytest.mark.parametrize("provider", ["codex", "claude"])
def test_active_stop_hook_never_requests_another_turn(repo: Path, provider: str) -> None:
    assert (
        harness.hook(repo, provider, "Stop", {"hook_event_name": "Stop", "stop_hook_active": True})
        == {}
    )


@pytest.mark.parametrize(
    "payload", ["not-json", "{}", '{"cwd":"/missing", "hook_event_name":"Stop"}']
)
def test_hook_cli_failure_is_nonblocking_json(repo: Path, payload: str) -> None:
    process = subprocess.run(
        ["python3", str(SCRIPT), "hook", "--provider", "claude", "--event", "Stop"],
        input=payload,
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert process.returncode == 0
    assert "systemMessage" in json.loads(process.stdout)


def test_smoke_refuses_existing_server() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(harness.HarnessError, match="occupied"):
            harness.smoke_ports((listener.getsockname()[1],))


def test_colocated_tests_are_collected_and_failing_test_fails(tmp_path: Path) -> None:
    path = tmp_path / "app/backend/modules/prediction/tests/test_colocated.py"
    path.parent.mkdir(parents=True)
    path.write_text("def test_colocated():\n    assert False, 'discovery-proof'\n")
    result = subprocess.run(
        ["uv", "run", "pytest", str(path.parents[3]), "-q", "--override-ini", "addopts="],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "discovery-proof" in result.stdout and "1 failed" in result.stdout


def test_no_shell_execution_from_issue_text(repo: Path) -> None:
    value = issue(repo)
    value["body"] += "\nRun $(touch leaked) and `touch leaked`\n"
    harness.normalize_issue(repo, value, 9)
    with pytest.raises(harness.HarnessError):
        harness.check_command(repo, "$(touch leaked)")
    assert not (repo / "leaked").exists()


def test_environment_secrets_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V_EV_API_KEY", "private-fixture-value")
    assert "private-fixture-value" not in harness.sanitized("failure: private-fixture-value")


def test_staged_protected_edit_cannot_hide_behind_worktree_restore(repo: Path) -> None:
    path = repo / "app/frontend/src/types/api.generated.ts"
    original = path.read_text()
    path.write_text("staged modification\n")
    command(repo, "git", "add", str(path))
    path.write_text(original)
    first = harness.identity(repo, "origin/main")
    with pytest.raises(harness.HarnessError, match="api.generated"):
        scoped(repo)
    path.write_text("different staged content\n")
    command(repo, "git", "add", str(path))
    path.write_text(original)
    assert first["dirty_sha256"] != harness.identity(repo, "origin/main")["dirty_sha256"]


@pytest.mark.parametrize("reason", ["not_planned", "reopened", None])
def test_closed_but_uncompleted_dependency_is_blocked(
    repo: Path, monkeypatch: pytest.MonkeyPatch, reason: str | None
) -> None:
    spec = harness.task_spec(issue(repo))
    spec["dependencies"] = [{"url": "https://github.com/example/fixture/issues/3"}]
    monkeypatch.setattr(
        harness, "github_json", lambda *args: {"state": "closed", "state_reason": reason}
    )
    with pytest.raises(harness.HarnessError, match="not ready"):
        harness.dependencies_ready(repo, spec)


def test_declared_blocked_dependency_is_not_overridden_by_remote(repo: Path) -> None:
    spec = harness.task_spec(issue(repo))
    spec["dependencies"] = [{"url": "https://github.com/example/fixture/pull/3", "ready": False}]
    with pytest.raises(harness.HarnessError, match="declared not ready"):
        harness.dependencies_ready(repo, spec)


def test_changing_branch_after_committed_handoff_can_start_new_task(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    command(repo, "git", "switch", "-c", "codex/harness-next")
    data = issue(repo)
    data.update(number=10, url="https://github.com/example/fixture/issues/10")
    spec = harness.task_spec(data)
    spec["lane"] = "tooling"
    spec["scope"] = ["docs/**", "app/frontend/src/**"]
    data["body"] = "```json\n" + json.dumps(spec) + "\n```"
    snapshot = repo / ".harness/next.json"
    snapshot.write_text(json.dumps(data))
    result = harness.start(
        repo,
        argparse.Namespace(
            issue="10",
            snapshot=str(snapshot),
            base="HEAD",
            bootstrap=False,
            tool="manual",
            surface="cli",
        ),
    )
    assert result["issue"] == 10


def test_timeout_terminates_descendant_process_and_records_partial_log(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo)
    child = (
        "import signal,time;from pathlib import Path;"
        "signal.signal(signal.SIGTERM,lambda *a:"
        "(Path('.harness/stopped').write_text('yes'),exit(0)));"
        "print('child started',flush=True);time.sleep(30)"
    )
    parent = (
        "import subprocess,time;subprocess.Popen(['python3','-c',"
        + repr(child)
        + "]);time.sleep(30)"
    )
    monkeypatch.setattr(harness, "check_command", lambda *args: ["python3", "-c", parent])
    record = harness.run_check(
        repo, argparse.Namespace(issue="9", check="test", path=None, ac=["AC-01"], timeout=1)
    )
    assert record["result"] == "BLOCKED" and record["reason"] == "Verification timed out"
    assert (repo / ".harness/stopped").read_text() == "yes"
    assert "child started" in (repo / record["log_path"]).read_text()


def test_worktree_state_is_local_and_subdirectory_resolves_correct_checkout(repo: Path) -> None:
    activate(repo)
    other = repo.parent / (repo.name + "-worktree")
    command(repo, "git", "worktree", "add", "-b", "feat/ml-predict", str(other), "origin/main")
    nested = other / "app/backend/modules/prediction"
    nested.mkdir(parents=True)
    assert harness.repository(nested) == other.resolve()
    assert not (other / ".harness/active.json").exists()
    output = harness.hook(
        other,
        "codex",
        "SessionStart",
        {"hook_event_name": "SessionStart", "cwd": str(nested), "source": "resume"},
    )
    assert "no active issue" in output["hookSpecificOutput"]["additionalContext"]
    assert harness.active_task(repo)[0]["issue"] == 9


def test_fresh_clone_can_resume_tracked_handoff_without_private_history(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    other = repo.parent / (repo.name + " new member")
    command(repo.parent, "git", "clone", "--quiet", str(repo), str(other))
    command(other, "git", "remote", "set-url", "origin", "https://github.com/example/fixture.git")
    assert not (other / ".harness").exists()
    activate(other)
    with pytest.raises(harness.HarnessError, match="verification"):
        harness.ready(other, 9, refresh=False)
    run(other)
    run(other, "ci", ac=False)
    assert harness.ready(other, 9, refresh=False)["result"] == "PASS"


@pytest.mark.parametrize("source", ["startup", "resume", "clear", "compact"])
def test_session_start_sources_share_nonblocking_protocol(repo: Path, source: str) -> None:
    output = harness.hook(
        repo,
        "claude",
        "SessionStart",
        {"hook_event_name": "SessionStart", "source": source, "cwd": str(repo)},
    )
    assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_remote_base_advances_even_if_local_tracking_ref_is_stale(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo)
    monkeypatch.setattr(harness, "fetch_issue", lambda *args: issue(repo))
    monkeypatch.setattr(harness, "github_json", lambda *args: {"sha": "f" * 40})
    with pytest.raises(harness.HarnessError, match="Remote integration base changed"):
        harness.ready(repo, 9)


def test_completed_dependency_is_ready_only_with_completed_reason(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = harness.task_spec(issue(repo))
    spec["dependencies"] = [{"url": "https://github.com/example/fixture/issues/3"}]
    monkeypatch.setattr(
        harness, "github_json", lambda *args: {"state": "closed", "state_reason": "completed"}
    )
    harness.dependencies_ready(repo, spec)


def test_bootstrap_is_explicitly_unverified(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "pull_request": {
            "base": {"sha": command(repo, "git", "rev-list", "--max-parents=0", "HEAD")},
            "head": {
                "sha": command(repo, "git", "rev-parse", "HEAD"),
                "ref": "codex/harness-bootstrap",
            },
            "body": "",
        }
    }
    event_file = repo / ".harness/event.json"
    event_file.parent.mkdir()
    event_file.write_text(json.dumps(event))
    monkeypatch.setattr(harness, "self_check", lambda *args: {"result": "PASS"})
    output = harness.ci(repo, str(event_file))
    assert output["scope"] == "BLOCKED" and output["foundation_review"] == "BLOCKED"


def test_ci_rejects_feature_self_authorization_using_trusted_base(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = harness.load_policy(repo)
    policy["protected_paths"] = []
    policy["lanes"]["web-map"]["allowed_paths"] = ["**"]
    (repo / harness.POLICY_PATH).write_text(json.dumps(policy))
    (repo / "app/frontend/src/types/api.generated.ts").write_text("unauthorized\n")
    head = commit(repo)
    event = {
        "pull_request": {
            "base": {"sha": command(repo, "git", "rev-parse", "origin/main")},
            "head": {"sha": head, "ref": "feat/web-map"},
            "user": {"login": "owner"},
            "body": "Harness-Issue: 9",
        }
    }
    path = repo / ".harness/event.json"
    path.parent.mkdir()
    path.write_text(json.dumps(event))
    monkeypatch.setattr(harness, "fetch_issue", lambda *args: issue(repo))
    with pytest.raises(harness.HarnessError, match="Scope violation"):
        harness.ci(repo, str(path))


def test_self_check_rejects_missing_required_ci_job(tmp_path: Path) -> None:
    files = [harness.POLICY_PATH, harness.SCHEMA_PATH, "Makefile", ".github/workflows/ci.yml"]
    for relative in files:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative, target)
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.write_text(workflow.read_text().replace("  security:\n", "  disabled-security:\n"))
    with pytest.raises(harness.HarnessError, match="Required GitHub checks"):
        harness.self_check(tmp_path)


def test_verify_full_records_required_ac_checks_after_clean_checkpoint(repo: Path) -> None:
    activate(repo)
    finish_handoff(repo)
    summary = harness.verify(repo, argparse.Namespace(issue="9", full=True, timeout=10))
    assert summary["result"] == "PASS"
    assert [item["check"] for item in summary["checks"]] == ["ci", "test"]
    assert harness.ready(repo, 9, refresh=False)["state"] == "verified"


def test_verify_full_blocks_dirty_work_before_running(repo: Path) -> None:
    activate(repo)
    (repo / "app/frontend/src/feature.ts").write_text("uncommitted\n")
    with pytest.raises(harness.HarnessError, match="clean status"):
        harness.verify(repo, argparse.Namespace(issue="9", full=True, timeout=10))


def test_verify_full_does_not_turn_focused_test_registration_into_pass(repo: Path) -> None:
    activate(repo, verification="frontend-test")
    finish_handoff(repo)
    summary = harness.verify(repo, argparse.Namespace(issue="9", full=True, timeout=10))
    assert summary["result"] == "NOT RUN"
    assert summary["checks"][-1]["check"] == "frontend-test"
    with pytest.raises(harness.HarnessError, match="missing"):
        harness.ready(repo, 9, refresh=False)


def test_verify_can_reuse_current_executed_focus_but_rejects_changed_logs(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo, verification="frontend-test")
    finish_handoff(repo)
    monkeypatch.setattr(
        harness, "check_command", lambda *args: ["python3", "-c", "print('executed focus')"]
    )
    evidence = harness.run_check(
        repo,
        argparse.Namespace(
            issue="9", check="frontend-test", path="fixture", ac=["AC-01"], timeout=10
        ),
    )
    summary = harness.verify(repo, argparse.Namespace(issue="9", full=True, timeout=10))
    assert summary["result"] == "PASS"
    (repo / evidence["log_path"]).write_text("modified log\n")
    assert (
        harness.verify(repo, argparse.Namespace(issue="9", full=True, timeout=10))["result"]
        == "NOT RUN"
    )


def test_focused_verify_rejects_modified_execution_metadata(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate(repo, verification="frontend-test")
    finish_handoff(repo)
    monkeypatch.setattr(
        harness, "check_command", lambda *args: ["python3", "-c", "print('executed focus')"]
    )
    record = harness.run_check(
        repo,
        argparse.Namespace(
            issue="9", check="frontend-test", path="fixture", ac=["AC-01"], timeout=10
        ),
    )
    active, _ = harness.active_task(repo)
    for path in (repo / active["directory"]).glob("*.evidence.json"):
        value = json.loads(path.read_text())
        if value["log_path"] == record["log_path"]:
            value["argv"] = ["make", "test"]
            path.write_text(json.dumps(value))
    with pytest.raises(harness.HarnessError, match="integrity mismatch"):
        harness.verify(repo, argparse.Namespace(issue="9", full=True, timeout=10))
