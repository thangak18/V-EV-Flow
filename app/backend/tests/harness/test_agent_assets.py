"""Behavioral tests for cross-tool generation, early guards and one-use diagnostics."""

import importlib.util
import json
import shutil
import subprocess
import time
import tomllib
from pathlib import Path

import pytest

ROOT = Path.cwd()
SPEC = importlib.util.spec_from_file_location(
    "vev_assets_test", ROOT / ".github/scripts/harness_assets.py"
)
assert SPEC and SPEC.loader
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)
CORE_SPEC = importlib.util.spec_from_file_location(
    "vev_core_test", ROOT / ".github/scripts/harness.py"
)
assert CORE_SPEC and CORE_SPEC.loader
core = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(core)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for directory in (".agents", "docs/harness"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    (tmp_path / ".gitignore").write_text(".harness/\n.env\n")
    subprocess.run(
        ["git", "init", "--initial-branch=feat/web-map"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    for key, value in (("user.name", "Asset Test"), ("user.email", "asset@example.test")):
        subprocess.run(["git", "config", key, value], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True
    )
    return tmp_path


def policy(root: Path) -> dict:
    return json.loads((root / "docs/harness/policy.json").read_text())


def payload(root: Path, tool: str, command: str | dict) -> dict:
    value = {"command": command} if isinstance(command, str) and tool == "Bash" else command
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": value,
        "cwd": str(root),
        "session_id": "session-a",
    }


def rules(root: Path, value: dict, branch: str = "feat/web-map", spec: dict | None = None) -> set:
    return {
        item["rule"]
        for item in assets.evaluate(root, assets.normalize(root, value), policy(root), branch, spec)
    }


def test_sync_generates_equal_instructions_for_both_tools(repo: Path) -> None:
    assert assets.synchronize(repo)["result"] == "PASS"
    assert assets.synchronize(repo, check=True)["result"] == "PASS"
    source, source_body = assets.read_frontmatter(repo / ".agents/agents/code-reviewer.md")
    claude, claude_body = assets.read_frontmatter(repo / ".claude/agents/code-reviewer.md")
    codex = tomllib.loads((repo / ".codex/agents/code-reviewer.toml").read_text())
    assert source_body in claude_body
    assert codex["developer_instructions"] == source_body
    assert codex["sandbox_mode"] == "read-only" and claude["model"] == "inherit"
    assert source["name"] == claude["name"] == codex["name"]


def test_claude_settings_preserve_non_hook_fields_and_format(repo: Path) -> None:
    assets.synchronize(repo)
    path = repo / ".claude/settings.json"
    value = json.loads(path.read_text())
    value["permissions"] = {"deny": ["Bash(example:*)"]}
    value["customSetting"] = "keep"
    path.write_text(json.dumps(value, indent=4))
    assert assets.synchronize(repo, check=True)["result"] == "PASS"
    value["hooks"]["Stop"] = []
    path.write_text(json.dumps(value))
    assets.synchronize(repo)
    actual = json.loads(path.read_text())
    assert actual["permissions"] == value["permissions"] and actual["customSetting"] == "keep"
    assert actual["hooks"]["Stop"]


def test_sync_check_is_read_only_and_detects_changed_source(repo: Path) -> None:
    assets.synchronize(repo)
    source = repo / ".agents/skills/task-start/SKILL.md"
    source.write_text(source.read_text() + "\nNew scoped instruction.\n")
    generated = repo / ".claude/skills/task-start/SKILL.md"
    before = generated.read_bytes()
    assert assets.synchronize(repo, check=True)["result"] == "FAIL"
    assert generated.read_bytes() == before


def test_unknown_generated_file_is_preserved(repo: Path) -> None:
    assets.synchronize(repo)
    custom = repo / ".claude/agents/custom.md"
    custom.write_text("unreviewed custom instructions")
    with pytest.raises(ValueError, match="preserved"):
        assets.synchronize(repo)
    assert custom.read_text() == "unreviewed custom instructions"


def test_binary_resources_round_trip(repo: Path) -> None:
    path = repo / ".agents/skills/task-start/assets/icon.png"
    path.parent.mkdir()
    path.write_bytes(b"\x89PNG\r\n\x00\xfffixture")
    assets.synchronize(repo)
    assert (repo / ".claude/skills/task-start/assets/icon.png").read_bytes() == path.read_bytes()


def test_failed_sync_does_not_partially_write_and_does_not_follow_symlinks(repo: Path) -> None:
    assets.synchronize(repo)
    generated = repo / ".claude/skills/task-start/SKILL.md"
    before = generated.read_bytes()
    source = repo / ".agents/skills/task-start/SKILL.md"
    source.write_text(source.read_text() + "\nChange pending.\n")
    settings = repo / ".claude/settings.json"
    custom = repo / "custom-settings.json"
    custom.write_bytes(settings.read_bytes())
    settings.unlink()
    settings.symlink_to(custom)
    with pytest.raises(ValueError, match="symlink"):
        assets.synchronize(repo)
    assert generated.read_bytes() == before


def test_invocation_policy_has_tool_specific_shape(repo: Path) -> None:
    assets.synchronize(repo)
    metadata, _ = assets.read_frontmatter(repo / ".claude/skills/vev-issue/SKILL.md")
    assert metadata["disable-model-invocation"] is True
    stage, _ = assets.read_frontmatter(repo / ".claude/skills/task-verify/SKILL.md")
    assert "disable-model-invocation" not in stage


@pytest.mark.parametrize("tool", ["Edit", "Write", "apply_patch"])
def test_both_tool_edit_shapes_block_generated_outputs(repo: Path, tool: str) -> None:
    relative = "app/frontend/src/types/api.generated.ts"
    raw = {"file_path": relative, "new_string": "manual", "content": "manual"}
    if tool == "apply_patch":
        raw = {
            "patch": "*** Begin Patch\n*** Update File: " + relative + "\n+manual\n*** End Patch"
        }
    assert "GENERATED" in rules(repo, payload(repo, tool, raw))


def test_patch_move_checks_source_and_destination(repo: Path) -> None:
    raw = (
        "*** Begin Patch\n*** Update File: app/frontend/src/x.ts\n"
        "*** Move to: .codex/hooks.json\n+manual\n*** End Patch"
    )
    action = assets.normalize(repo, payload(repo, "apply_patch", {"patch": raw}))
    assert {item["path"] for item in action["edits"]} == {
        "app/frontend/src/x.ts",
        ".codex/hooks.json",
    }
    assert "GENERATED" in {
        item["rule"] for item in assets.evaluate(repo, action, policy(repo), "feat/web-map")
    }


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin HEAD",
        "git push origin +HEAD:feat/web-map",
        "git -c color.ui=false push --force-with-lease origin HEAD",
        "echo done\ngit push --mirror origin",
    ],
)
def test_force_push_shapes_are_blocked(repo: Path, command: str) -> None:
    assert "FORCE_PUSH" in rules(repo, payload(repo, "Bash", command))


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push origin HEAD:refs/heads/main",
        "git push --repo=origin main",
        "git push --repo origin main",
    ],
)
def test_explicit_main_push_shapes_are_blocked(repo: Path, command: str) -> None:
    assert "MAIN_PUSH" in rules(repo, payload(repo, "Bash", command))


def test_git_read_and_regular_branch_push_are_allowed(repo: Path) -> None:
    assert not rules(repo, payload(repo, "Bash", "git log --grep push"), "main")
    assert not rules(repo, payload(repo, "Bash", "git push -u origin HEAD"))
    assert "MAIN_PUSH" in rules(repo, payload(repo, "Bash", "git push"), "main")


def test_shell_write_uses_nested_cwd_and_issue_scope(repo: Path) -> None:
    cwd = repo / "app/frontend"
    cwd.mkdir(parents=True)
    assert "GENERATED" in rules(repo, payload(cwd, "Bash", "echo x > src/types/api.generated.ts"))
    spec = {"lane": "web-map", "issue": 9, "scope": ["app/frontend/src/**"]}
    assert "SCOPE" in rules(
        repo, payload(repo, "Bash", "echo x > app/backend/modules/prediction/x.py"), spec=spec
    )
    assert "SCOPE" in rules(repo, payload(repo, "Bash", "echo x > /tmp/outside-vev.py"), spec=spec)


def test_env_setup_is_allowed_but_staging_and_committing_env_are_not(repo: Path) -> None:
    assert not rules(repo, payload(repo, "Bash", "cp .env.example .env"))
    spec = {"lane": "web-map", "issue": 9, "scope": ["app/frontend/src/**"]}
    assert not rules(repo, payload(repo, "Bash", "cp .env.example .env"), spec=spec)
    assert "ENV_COMMIT" in rules(repo, payload(repo, "Bash", "git add -f .env"))
    (repo / ".env").write_text("DEMO_MODE=true\n")
    subprocess.run(["git", "add", "-f", ".env"], cwd=repo, check=True)
    assert "ENV_COMMIT" in rules(repo, payload(repo, "Bash", "git commit -m checkpoint"))


def test_only_active_issue_handoff_is_allowed(repo: Path) -> None:
    spec = {"lane": "web-map", "issue": 9, "scope": ["app/frontend/src/**"]}
    for tool in ("Write", "Edit"):
        value = {"file_path": "docs/harness/handoffs/9.md", "content": "Checkpoint"}
        assert not rules(repo, payload(repo, tool, value), spec=spec)
        value["file_path"] = "docs/harness/handoffs/10.md"
        assert "SCOPE" in rules(repo, payload(repo, tool, value), spec=spec)


def test_commit_scans_staged_additions_without_echoing_credentials(repo: Path) -> None:
    token = "sk-" + "b" * 40
    path = repo / "source.py"
    path.write_text(f"key = '{token}'\n")
    subprocess.run(["git", "add", "source.py"], cwd=repo, check=True)
    output = assets.evaluate(
        repo,
        assets.normalize(repo, payload(repo, "Bash", "git commit -m checkpoint")),
        policy(repo),
        "feat/web-map",
    )
    assert any(item["rule"] == "SECRET" for item in output)
    assert token not in json.dumps(output)
    subprocess.run(
        ["git", "commit", "-m", "fixture secret"], cwd=repo, check=True, capture_output=True
    )
    path.write_text("key = 'removed'\n")
    subprocess.run(["git", "add", "source.py"], cwd=repo, check=True)
    assert not rules(repo, payload(repo, "Bash", "git commit -m remove-secret"))


def test_secret_diagnostics_never_echo_the_value(repo: Path) -> None:
    token = "sk-" + "a" * 40
    output = assets.evaluate(
        repo,
        assets.normalize(
            repo, payload(repo, "Write", {"file_path": "app/frontend/src/key.ts", "content": token})
        ),
        policy(repo),
        "feat/web-map",
    )
    assert any(item["rule"] == "SECRET" for item in output)
    assert token not in json.dumps(output)


def test_harness_self_edits_require_tooling_lane(repo: Path) -> None:
    data = payload(repo, "Edit", {"file_path": ".agents/hooks.json", "new_string": "{}"})
    assert "HARNESS" in rules(repo, data)
    assert not rules(repo, data, "codex/harness-bootstrap")


def test_canary_is_exact_single_use_and_provider_session_bound(repo: Path) -> None:
    command = "python3 .github/scripts/harness.py canary --provider codex --session session-a"
    action = assets.normalize(repo, payload(repo, "Bash", command))
    assert assets.canary_command(repo, action, "codex")
    assert not assets.canary_command(
        repo, assets.normalize(repo, payload(repo, "Bash", command + " | cat")), "codex"
    )
    assets.stamp_canary(repo, "codex", {"session_id": "session-a"}, "head")
    assert assets.consume_canary(repo, "codex", "head", "session-a", 600)["result"] == "PASS"
    assert assets.consume_canary(repo, "codex", "head", "session-a", 600)["result"] == "BLOCKED"


@pytest.mark.parametrize(
    "value",
    [
        [],
        {"at": "tomorrow"},
        {"at": float("inf")},
        {"at": time.time(), "session": ["wrong-type"]},
        {"at": time.time() + 100, "session": "a"},
    ],
)
def test_malformed_receipts_are_blocked(repo: Path, value: object) -> None:
    path = repo / ".harness/canary/claude.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value))
    assert assets.consume_canary(repo, "claude", "head", None, 600)["result"] == "BLOCKED"


def test_verify_plan_selects_downstream_contract_checks_and_keeps_ac_requirements() -> None:
    spec = {"acceptance": [{"id": "AC-01", "verification": ["frontend-test"]}]}
    selected = core.verification_plan(["app/backend/contracts/stations.py"], spec)
    assert {
        "backend-test-suite",
        "frontend-test-suite",
        "build",
        "smoke",
        "contract-check",
        "frontend-test",
    } <= set(selected)
    assert core.verification_plan([], spec, full=True) == ["ci", "frontend-test"]


def test_backend_only_plan_does_not_run_frontend_checks() -> None:
    spec = {"acceptance": [{"id": "AC-01", "verification": ["backend-test-suite"]}]}
    assert core.verification_plan(["app/backend/modules/prediction/split.py"], spec) == [
        "backend-lint",
        "backend-test-suite",
    ]


@pytest.mark.parametrize("provider", ["codex", "claude"])
def test_pretool_hook_denial_has_native_protocol_and_does_not_run_command(
    repo: Path, provider: str
) -> None:
    value = payload(repo, "Bash", "git push --force origin HEAD")
    result = subprocess.run(
        [
            "python3",
            str(ROOT / ".github/scripts/harness.py"),
            "hook",
            "--provider",
            provider,
            "--event",
            "PreToolUse",
        ],
        input=json.dumps(value),
        capture_output=True,
        text=True,
        cwd=repo,
        timeout=5,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "FORCE_PUSH" in result.stderr


def test_stale_active_state_cannot_disable_common_guard(repo: Path) -> None:
    (repo / ".harness").mkdir()
    (repo / ".harness/active.json").write_text(
        json.dumps({"issue": 9, "snapshot_path": ".harness/missing.json", "branch": "other-branch"})
    )
    output = core.hook(
        repo, "codex", "PreToolUse", payload(repo, "Bash", "git push --force origin HEAD")
    )
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
