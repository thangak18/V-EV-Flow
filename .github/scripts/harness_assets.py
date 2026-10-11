"""Canonical agent assets and shared tool guards; stdlib, no agent/API calls."""

from __future__ import annotations

import fnmatch
import json
import math
import re
import shlex
import subprocess
import time
import tomllib
from pathlib import Path
from typing import Any

MANAGED = (".claude/skills", ".claude/agents", ".codex/agents")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SKILL_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
SHELL_TOOLS = {"bash", "powershell", "shell", "local_shell", "exec_command", "unified_exec"}
EVENTS = {"SessionStart", "Stop", "PreToolUse"}


def path_in(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"Unsafe asset path: {relative}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Asset path escapes checkout: {relative}")
    return path


def read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing frontmatter: {path.name}")
    raw, body = match.groups()
    if raw.lstrip().startswith("{"):
        value = json.loads(raw)
    else:
        value = {}
        for line in raw.splitlines():
            key, separator, item = line.partition(":")
            if not separator or not re.fullmatch(r"[a-z-]+", key):
                raise ValueError("Use JSON object frontmatter for nested or multiline metadata")
            value[key] = item.strip().strip('"')
    if not isinstance(value, dict) or not body.strip():
        raise ValueError(f"Asset needs metadata and instructions: {path.name}")
    return value, body.strip() + "\n"


def validate_name(value: dict[str, Any], expected: str) -> None:
    if value.get("name") != expected or not NAME.fullmatch(expected) or len(expected) > 64:
        raise ValueError(f"Asset name must match its path: {expected}")
    description = value.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise ValueError(f"Asset description must be 1–1024 characters: {expected}")


def generated_note(source: str) -> str:
    return f"<!-- GENERATED from {source} by harness.py sync; edit the canonical source. -->\n"


def markdown(metadata: dict[str, Any], body: str) -> str:
    return "---\n" + json.dumps(metadata, indent=2, ensure_ascii=False) + "\n---\n\n" + body


def implicit_policy(path: Path) -> bool:
    if not path.is_file():
        return True
    text = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"\s*policy:\s*\n\s+allow_implicit_invocation:\s*(true|false)\s*", text)
    if not match:
        raise ValueError(f"Unsupported invocation metadata: {path}")
    return match[1] == "true"


def local_links(source: str, body: str, root: Path) -> None:
    for target in re.findall(r"\]\(([^\s)]+)\)", body):
        if re.match(r"(?:https?:|mailto:|#)", target):
            continue
        relative = target.split("#")[0]
        if not relative:
            continue
        path = (root / source).parent / relative
        if not path.resolve().is_relative_to(root.resolve()) or not path.exists():
            raise ValueError(f"Broken/outside asset link in {source}: {target}")


def render(root: Path) -> dict[str, str | bytes]:
    """Render tool-specific formats without executing or changing anything."""
    expected: dict[str, str | bytes] = {}
    for directory in sorted(path_in(root, ".agents/skills").iterdir()):
        if not directory.is_dir():
            continue
        source = f".agents/skills/{directory.name}/SKILL.md"
        metadata, body = read_frontmatter(path_in(root, source))
        validate_name(metadata, directory.name)
        if set(metadata) - SKILL_KEYS:
            raise ValueError(f"Nonstandard skill metadata: {source}")
        if len(body.splitlines()) >= 500:
            raise ValueError(f"Skill exceeds 500-line budget: {source}")
        local_links(source, body, root)
        claude_metadata = dict(metadata)
        policy_file = path_in(root, f".agents/skills/{directory.name}/agents/openai.yaml")
        if not implicit_policy(policy_file):
            claude_metadata["disable-model-invocation"] = True
        expected[f".claude/skills/{directory.name}/SKILL.md"] = markdown(
            claude_metadata, generated_note(source) + "\n" + body
        )
        for resource in directory.rglob("*"):
            if resource.is_file() and resource.name != "SKILL.md":
                relative = resource.relative_to(directory).as_posix()
                if resource.is_symlink():
                    raise ValueError(f"Do not synchronize symlinked skill resources: {resource}")
                expected[f".claude/skills/{directory.name}/{relative}"] = resource.read_bytes()
    for source_file in sorted(path_in(root, ".agents/agents").glob("*.md")):
        source = source_file.relative_to(root).as_posix()
        metadata, body = read_frontmatter(path_in(root, source))
        name = source_file.stem
        validate_name(metadata, name)
        if set(metadata) - {"name", "description", "claude", "codex"}:
            raise ValueError(f"Unsupported role metadata: {source}")
        local_links(source, body, root)
        claude = metadata.get("claude", {})
        codex = metadata.get("codex", {})
        tools = claude.get("tools", "Read, Grep, Glob, Bash")
        if isinstance(tools, list):
            tools = ", ".join(tools)
        if not isinstance(tools, str) or set(tools.replace(" ", "").split(",")) - {
            "Read",
            "Grep",
            "Glob",
            "Bash",
        }:
            raise ValueError(f"Reviewer tools must be read-only: {source}")
        if claude.get("model", "inherit") != "inherit" or codex.get("sandbox_mode") != "read-only":
            raise ValueError(
                f"Review/QA roles must inherit model and use read-only sandbox: {source}"
            )
        expected[f".claude/agents/{name}.md"] = markdown(
            {
                "name": name,
                "description": metadata["description"],
                "tools": tools,
                "model": "inherit",
            },
            generated_note(source) + "\n" + body,
        )
        expected[f".codex/agents/{name}.toml"] = (
            f"# GENERATED from {source} by harness.py sync\n"
            f"name = {json.dumps(name)}\n"
            f"description = {json.dumps(metadata['description'], ensure_ascii=False)}\n"
            'sandbox_mode = "read-only"\n'
            f"developer_instructions = {json.dumps(body, ensure_ascii=False)}\n"
        )
        tomllib.loads(expected[f".codex/agents/{name}.toml"])
    source_hooks = json.loads(path_in(root, ".agents/hooks.json").read_text(encoding="utf-8"))
    if source_hooks.get("schema_version") != 1:
        raise ValueError("Unsupported canonical hooks version")
    hooks: dict[str, dict[str, Any]] = {"codex": {}, "claude": {}}
    for entry in source_hooks["hooks"]:
        event = entry["event"]
        if event not in EVENTS or event in hooks["codex"] or entry["timeout"] <= 0:
            raise ValueError(
                "Canonical hooks must have unique supported events and positive timeouts"
            )
        for provider in hooks:
            script = (
                '"${CLAUDE_PROJECT_DIR}/.github/scripts/harness.py"'
                if provider == "claude"
                else '"$(git rev-parse --show-toplevel)/.github/scripts/harness.py"'
            )
            group: dict[str, Any] = {
                "hooks": [
                    {
                        "type": "command",
                        "command": f"python3 {script} hook --provider {provider} --event {event}",
                        "timeout": entry["timeout"],
                    }
                ]
            }
            if entry.get(f"{provider}_matcher"):
                group["matcher"] = entry[f"{provider}_matcher"]
            hooks[provider][event] = [group]
    if set(hooks["codex"]) != EVENTS:
        raise ValueError("Canonical lifecycle/guard hooks are incomplete")
    expected[".codex/hooks.json"] = (
        json.dumps(
            {
                "description": "GENERATED from .agents/hooks.json by harness.py sync",
                "hooks": hooks["codex"],
            },
            indent=2,
        )
        + "\n"
    )
    settings_path = path_in(root, ".claude/settings.json")
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    settings["hooks"] = hooks["claude"]
    expected[".claude/settings.json"] = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    return expected


def synchronize(root: Path, check: bool = False) -> dict[str, Any]:
    expected = render(root)
    drift = []
    actual: set[str] = set()
    for directory in MANAGED:
        for path in path_in(root, directory).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                actual.add(path.relative_to(root).as_posix())
    extra = sorted(actual - set(expected))
    if extra:
        raise ValueError(f"Unmanaged generated assets preserved; review/remove explicitly: {extra}")
    destinations = {}
    for relative, contents in expected.items():
        path = path_in(root, relative)
        if path.is_symlink() or any(
            parent.is_symlink()
            for parent in path.parents
            if parent != root and parent.is_relative_to(root)
        ):
            raise ValueError(f"Refusing generated symlink: {relative}")
        destinations[relative] = path
        if relative == ".claude/settings.json" and path.exists():
            current = json.loads(path.read_text())
            matching = (
                isinstance(current, dict) and current.get("hooks") == json.loads(contents)["hooks"]
            )
        else:
            encoded = contents if isinstance(contents, bytes) else contents.encode("utf-8")
            matching = (
                path.is_file() and path.read_bytes().replace(b"\r\n", b"\n") == encoded
                if isinstance(contents, str)
                else path.is_file() and path.read_bytes() == encoded
            )
        if not matching:
            drift.append(relative)
    if not check:
        for relative in drift:
            path = destinations[relative]
            path.parent.mkdir(parents=True, exist_ok=True)
            content = expected[relative]
            path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return {
        "result": "FAIL" if check and drift else "PASS",
        "generated": len(expected),
        "drift": drift,
        "next": "Run harness.py sync" if drift and check else "Run make harness-check",
    }


def budgets(root: Path) -> None:
    """Keep the full root-to-leaf instruction chain within Codex's default cap."""
    files = [path_in(root, "AGENTS.md"), *path_in(root, "app").rglob("AGENTS.md")]
    for file in files:
        if any(part in ("node_modules", "dist", "__pycache__") for part in file.parts):
            continue
        chain = [
            parent / "AGENTS.md"
            for parent in [file.parent, *file.parent.parents]
            if parent.is_relative_to(root) and (parent / "AGENTS.md").is_file()
        ]
        if sum(len(path.read_bytes()) for path in chain) > 32768:
            raise ValueError(f"Instruction chain exceeds 32 KiB: {file.relative_to(root)}")


def parse_patch(value: str) -> list[dict[str, str]]:
    edits: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in value.splitlines():
        header = re.match(r"\*\*\* (Add|Update|Delete) File: (.+)$", line)
        if header:
            current = {"path": header[2], "op": header[1].lower(), "added": ""}
            edits.append(current)
        elif line.startswith("*** Move to: ") and current:
            current = {
                "path": line.removeprefix("*** Move to: "),
                "op": "move",
                "added": current["added"],
            }
            edits.append(current)
        elif current and line.startswith("+") and not line.startswith("+++"):
            current["added"] += line[1:] + "\n"
    return edits


def normalize(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    tool = str(payload.get("tool_name") or "").rsplit(".", 1)[-1].lower()
    raw = payload.get("tool_input") or {}
    commands = []
    edits = []
    if tool in SHELL_TOOLS and isinstance(raw, dict):
        command = raw.get("command", raw.get("cmd", ""))
        if isinstance(command, list):
            command = (
                command[-1]
                if len(command) > 2 and command[-2] in ("-c", "-lc", "/c")
                else shlex.join(command)
            )
        if isinstance(command, str):
            commands.append(command)
            if "*** Begin Patch" in command:
                edits.extend(parse_patch(command))
    elif tool == "apply_patch":
        patch = (
            raw
            if isinstance(raw, str)
            else raw.get("input", raw.get("patch", raw.get("command", "")))
        )
        if isinstance(patch, str):
            edits = parse_patch(patch)
    elif tool in ("edit", "write", "multiedit", "notebookedit") and isinstance(raw, dict):
        edits = [
            {
                "path": raw.get("file_path", raw.get("notebook_path", "")),
                "op": tool,
                "added": raw.get("new_string", raw.get("content", raw.get("new_source", ""))),
            }
        ]
        if tool == "multiedit":
            edits[0]["added"] = "\n".join(
                edit.get("new_string", "") for edit in raw.get("edits", [])
            )
    cwd = Path(payload.get("cwd", root)).resolve()
    for edit in edits:
        target = (cwd / edit["path"]).resolve()
        edit["path"] = (
            target.relative_to(root).as_posix() if target.is_relative_to(root) else str(target)
        )
    return {"tool": tool, "commands": commands, "edits": edits, "cwd": str(cwd)}


def segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    pieces: list[list[str]] = [[]]
    for token in lexer:
        if token and all(char in ";&|\n" for char in token):
            pieces.append([])
        else:
            pieces[-1].append(token)
    return [piece for piece in pieces if piece]


def secret_present(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b|"
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
            r"postgres(?:ql)?://[^\s:@]+:[^\s@]+@",
            value,
        )
    )


def git_verb(tokens: list[str]) -> tuple[str, list[str]]:
    if not tokens or Path(tokens[0]).name != "git":
        return "", []
    index = 1
    while index < len(tokens) and tokens[index].startswith("-"):
        flag = tokens[index]
        index += 2 if flag in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") else 1
    return (tokens[index], tokens[index + 1 :]) if index < len(tokens) else ("", [])


def evaluate(
    root: Path,
    action: dict[str, Any],
    policy: dict[str, Any],
    branch_name: str,
    spec: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Heuristic early feedback; trusted-base scope/CI remains authoritative."""
    violations: list[dict[str, str]] = []
    lane = (
        spec.get("lane")
        if spec
        else next(
            (
                name
                for name, value in policy["lanes"].items()
                if fnmatch.fnmatchcase(branch_name, value["branch"])
            ),
            None,
        )
    )
    cwd = Path(action.get("cwd", root)).resolve()

    def add(rule: str, reason: str) -> None:
        if not any(item["rule"] == rule and item["reason"] == reason for item in violations):
            violations.append({"rule": rule, "reason": reason})

    def protected(path: str) -> None:
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in policy["generated_paths"]):
            add("GENERATED", f"Use the canonical source/generator for {path}")
        if lane != "tooling" and any(
            fnmatch.fnmatchcase(path, pattern) for pattern in policy["harness_paths"]
        ):
            add("HARNESS", "Harness changes belong in an authorized tooling lane")
        if (
            spec
            and lane not in ("tooling", "contract")
            and any(fnmatch.fnmatchcase(path, pattern) for pattern in policy["protected_paths"])
        ):
            add("SCOPE", "Shared interfaces/tooling require a separate reviewed PR")

    def inspect(path: str) -> None:
        if Path(path).is_absolute():
            add("SCOPE", "File edit escapes the active checkout")
            return
        if spec and path == f"docs/harness/handoffs/{spec.get('issue', '')}.md":
            return
        if re.fullmatch(r"\.env(?:\..+)?", Path(path).name) and not path.endswith(".example"):
            # Local configuration is an authorized setup operation, never a tracked change.
            return
        protected(path)
        if spec and not path.startswith(".harness/"):
            allowed = policy["lanes"].get(lane, {}).get("allowed_paths", [])
            if not any(fnmatch.fnmatchcase(path, item) for item in spec["scope"]) or not any(
                fnmatch.fnmatchcase(path, item) for item in allowed
            ):
                add("SCOPE", "File edit is outside the assigned issue scope/owner paths")

    for edit in action["edits"]:
        inspect(edit["path"])
        if secret_present(edit.get("added", "")):
            add("SECRET", "Credential-looking content belongs outside prompts/code/logs")
    for command in action["commands"]:
        if secret_present(command):
            add("SECRET", "Credential-looking value in shell command")
        for original in segments(command):
            tokens = original
            while tokens and re.fullmatch(r"\w+=.*", tokens[0]):
                tokens = tokens[1:]
            if not tokens:
                continue
            verb, args = git_verb(tokens)
            if verb == "push":
                if any(
                    arg.startswith("--force")
                    or arg in ("--mirror", "--all")
                    or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", arg)
                    or arg.startswith("+")
                    for arg in args
                ):
                    add(
                        "FORCE_PUSH",
                        "Use ordinary issue-branch pushes; force/mirror/all pushes are blocked",
                    )
                explicit_remote = any(arg.startswith("--repo=") for arg in args) or "--repo" in args
                positional = []
                index = 0
                while index < len(args):
                    if args[index] in ("--repo", "--receive-pack", "--exec", "--push-option", "-o"):
                        index += 2
                        continue
                    if not args[index].startswith("-"):
                        positional.append(args[index])
                    index += 1
                targets = positional if explicit_remote else positional[1:]
                if any(
                    re.fullmatch(r"(?:refs/heads/)?(?:main|master)", item.split(":")[-1])
                    for item in targets
                ):
                    add("MAIN_PUSH", "Push an owner/tooling branch and use a reviewed PR")
                if (
                    (not targets or targets == ["HEAD"])
                    and "--tags" not in args
                    and branch_name in ("main", "master")
                ):
                    add("MAIN_PUSH", "Pushing the current main branch is blocked")
            if verb in ("add", "commit"):
                candidates = (
                    args
                    if verb == "add"
                    else subprocess.run(
                        ["git", "diff", "--cached", "--name-only", "-z"],
                        cwd=cwd,
                        check=True,
                        capture_output=True,
                        timeout=2,
                    )
                    .stdout.decode()
                    .split("\0")
                )
                if any(
                    re.fullmatch(r"\.env(?:\..+)?", Path(item).name)
                    and not item.endswith(".example")
                    for item in candidates
                ):
                    add("ENV_COMMIT", "Local environment files must remain untracked")
                if verb == "commit":
                    staged = subprocess.run(
                        ["git", "diff", "--cached", "--no-ext-diff", "--unified=0"],
                        cwd=cwd,
                        check=True,
                        capture_output=True,
                        timeout=2,
                    ).stdout.decode(errors="replace")
                    additions = "\n".join(
                        line[1:]
                        for line in staged.splitlines()
                        if line.startswith("+") and not line.startswith("+++")
                    )
                    if secret_present(additions):
                        add("SECRET", "Credential-looking content in staged changes")
            targets = [
                tokens[index + 1] for index, token in enumerate(tokens[:-1]) if token in (">", ">>")
            ]
            if tokens[0] in ("cp", "mv", "install", "tee") and len(tokens) > 1:
                targets.append(tokens[-1])
            if tokens[0] in ("rm", "touch", "truncate") or tokens[:2] == ["sed", "-i"]:
                targets.extend(item for item in tokens[1:] if not item.startswith("-"))
            for target in targets:
                normalized = (cwd / target).resolve()
                inspect(
                    normalized.relative_to(root).as_posix()
                    if normalized.is_relative_to(root)
                    else str(normalized)
                )
    return violations


def canary_command(root: Path, action: dict[str, Any], provider: str) -> bool:
    if len(action["commands"]) != 1:
        return False
    try:
        tokens = shlex.split(action["commands"][0])
    except ValueError:
        return False
    if len(tokens) not in (5, 7) or Path(tokens[0]).name not in ("python3", "python"):
        return False
    if (root / tokens[1]).resolve() != root / ".github/scripts/harness.py":
        return False
    return tokens[2:5] == ["canary", "--provider", provider] and (
        len(tokens) == 5 or tokens[5] == "--session"
    )


def stamp_canary(root: Path, provider: str, payload: dict[str, Any], head: str) -> None:
    session = payload.get("session_id")
    if not isinstance(session, str) or not session:
        return
    path = path_in(root, f".harness/canary/{provider}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "provider": provider,
                "session": session,
                "head": head,
                "root": str(root),
                "at": time.time(),
            }
        ),
        encoding="utf-8",
    )


def consume_canary(
    root: Path, provider: str, head: str, session: str | None, max_age: int
) -> dict[str, Any]:
    path = path_in(root, f".harness/canary/{provider}.json")
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        value = {}
    if path.exists():
        path.unlink()
    typed = (
        isinstance(value, dict)
        and isinstance(value.get("session"), str)
        and bool(value["session"])
        and isinstance(value.get("at"), (int, float))
        and not isinstance(value["at"], bool)
        and math.isfinite(value["at"])
    )
    if not typed:
        value = {}
    age = time.time() - value.get("at", 0)
    valid = (
        typed
        and value.get("provider") == provider
        and value.get("root") == str(root)
        and value.get("head") == head
        and (session is None or value["session"] == session)
        and 0 <= age <= max_age
    )
    return {
        "result": "PASS" if valid else "BLOCKED",
        "provider": provider,
        "session": value.get("session"),
        "head": head,
        "reason": "PreToolUse observed this one invocation; not a security/adoption guarantee"
        if valid
        else (
            "No matching fresh hook receipt. Review/trust hooks and run through the agent tool; "
            "manual core workflow remains available"
        ),
    }
