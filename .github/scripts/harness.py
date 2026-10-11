#!/usr/bin/env python3
"""Portable, human-started V-EV Flow issue workflow. Python 3.11+ stdlib only."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import hmac
import importlib.util
import json
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

POLICY_PATH = "docs/harness/policy.json"
SCHEMA_PATH = "docs/harness/schemas/evidence.schema.json"
CHECKS = (
    "setup",
    "lint",
    "test",
    "build",
    "contract-check",
    "smoke",
    "security",
    "harness-check",
    "ci",
    "backend-lint",
    "backend-test-suite",
    "frontend-lint",
    "frontend-test-suite",
    "backend-test",
    "frontend-test",
    "e2e-test",
)
RESULTS = ("PASS", "FAIL", "BLOCKED", "NOT RUN")


class HarnessError(Exception):
    def __init__(self, message: str, result: str = "BLOCKED") -> None:
        super().__init__(message)
        self.result = result


def agent_assets() -> Any:
    """Lazy load: the trusted CI scope validator remains standalone."""
    module_path = Path(__file__).with_name("harness_assets.py")
    spec = importlib.util.spec_from_file_location("vev_agent_assets", module_path)
    if spec is None or spec.loader is None:
        raise HarnessError("Agent assets module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def now() -> str:
    return datetime.now(UTC).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True).encode()


def execute(root: Path, argv: list[str], timeout: int = 15) -> bytes:
    try:
        process = subprocess.run(argv, cwd=root, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessError(f"Cannot execute {argv[0]}: {exc}") from exc
    if process.returncode:
        raise HarnessError(f"{argv[0]} failed: {process.stderr.decode(errors='replace')[:500]}")
    return process.stdout


def git(root: Path, *args: str) -> bytes:
    return execute(root, ["git", *args])


def repository(cwd: str | Path = ".") -> Path:
    path = Path(cwd).resolve()
    return Path(git(path, "rev-parse", "--show-toplevel").decode().strip()).resolve()


def inside(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or "\\" in relative:
        raise HarnessError(f"Unsafe repository path: {relative}", "FAIL")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise HarnessError(f"Path escapes checkout: {relative}", "FAIL")
    return path


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HarnessError(f"Cannot read JSON {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessError(f"Expected JSON object: {path.name}", "FAIL")
    return value


def write_json(root: Path, relative: str, value: Any, exclusive: bool = False) -> None:
    path = inside(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")


def evidence_key(root: Path, create: bool = False) -> bytes:
    """Local tamper detection only; the checkout owner can read/recreate this key."""
    path = inside(root, ".harness/evidence.key")
    if path.is_symlink():
        raise HarnessError("Evidence integrity key must not be a symlink", "FAIL")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(os.urandom(32))
    if not path.is_file():
        raise HarnessError("Evidence integrity key missing; restore it or use a fresh checkout")
    key = path.read_bytes()
    if len(key) != 32:
        raise HarnessError(
            "Evidence integrity key invalid; restore it or use a fresh checkout", "FAIL"
        )
    return key


def evidence_signature(root: Path, record: dict[str, Any], create: bool = False) -> str:
    unsigned = {name: value for name, value in record.items() if name != "integrity"}
    return hmac.new(evidence_key(root, create), canonical(unsigned), hashlib.sha256).hexdigest()


def resolve(root: Path, ref: str) -> str:
    return (
        git(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").decode().strip()
    )


def branch(root: Path) -> str:
    return git(root, "symbolic-ref", "--quiet", "--short", "HEAD").decode().strip()


def load_policy(root: Path, base: str | None = None, bootstrap: bool = False) -> dict[str, Any]:
    if base:
        try:
            value = json.loads(git(root, "show", f"{resolve(root, base)}:{POLICY_PATH}"))
        except (HarnessError, ValueError) as exc:
            if not bootstrap:
                raise HarnessError(
                    "Trusted base has no harness policy; bootstrap review required"
                ) from exc
            if git(root, "ls-tree", "--name-only", resolve(root, base), "--", POLICY_PATH):
                raise HarnessError(
                    "Trusted base policy exists but is invalid; bootstrap cannot bypass it"
                ) from exc
            if branch(root) != "codex/harness-bootstrap":
                raise HarnessError(
                    "Bootstrap exception is limited to codex/harness-bootstrap"
                ) from exc
            value = read_json(inside(root, POLICY_PATH))
    else:
        value = read_json(inside(root, POLICY_PATH))
    if value.get("schema_version") != 1 or not isinstance(value.get("lanes"), dict):
        raise HarnessError("Unsupported or malformed policy", "FAIL")
    return value


def origin(root: Path) -> str:
    remote = git(root, "remote", "get-url", "origin").decode().strip()
    match = re.fullmatch(
        r"(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?/?", remote
    )
    if not match:
        raise HarnessError("origin must identify a GitHub repository")
    return match[1]


def issue_number(root: Path, value: str | int) -> int:
    raw = str(value)
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    match = re.fullmatch(r"https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)", raw)
    if match and match[1] == origin(root) and int(match[2]) > 0:
        return int(match[2])
    raise HarnessError("Issue must be a positive ID or an issue URL for origin", "FAIL")


def github_json(root: Path, argv: list[str]) -> Any:
    try:
        return json.loads(execute(root, ["gh", *argv], timeout=30))
    except ValueError as exc:
        raise HarnessError("GitHub returned invalid JSON") from exc


def fetch_issue(root: Path, number: int) -> dict[str, Any]:
    return github_json(
        root,
        [
            "issue",
            "view",
            str(number),
            "--repo",
            origin(root),
            "--json",
            "number,url,title,body,assignees,updatedAt,state",
        ],
    )


def task_spec(issue: dict[str, Any]) -> dict[str, Any]:
    blocks = re.findall(r"```json\s*\n(.*?)\n```", issue.get("body", ""), re.DOTALL)
    candidates = []
    for block in blocks:
        try:
            item = json.loads(block)
        except ValueError:
            continue
        if isinstance(item, dict) and "lane" in item:
            candidates.append(item)
    if len(candidates) != 1:
        raise HarnessError("Issue needs exactly one JSON task specification with lane")
    spec = candidates[0]
    for name in ("lane", "reviewer", "contract_impact", "data_origin", "rollback"):
        if not isinstance(spec.get(name), str) or not spec[name].strip():
            raise HarnessError(f"Issue specification missing {name}")
    scope = spec.get("scope")
    if not isinstance(scope, list) or not scope or any(not isinstance(p, str) for p in scope):
        raise HarnessError("Issue scope must be a nonempty list of repository paths")
    for path in scope:
        if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts or "\\" in path:
            raise HarnessError("Issue scope contains unsafe path", "FAIL")
    criteria = spec.get("acceptance")
    if not isinstance(criteria, list) or not criteria:
        raise HarnessError("Issue needs acceptance criteria")
    seen = set()
    for item in criteria:
        if not isinstance(item, dict) or not re.fullmatch(r"AC-\d{2,}", item.get("id", "")):
            raise HarnessError("Acceptance IDs must have form AC-01")
        if (
            item["id"] in seen
            or not isinstance(item.get("description"), str)
            or not item["description"]
        ):
            raise HarnessError("Acceptance criteria need unique IDs and descriptions")
        seen.add(item["id"])
        verification = item.get("verification")
        if (
            not isinstance(verification, list)
            or not verification
            or any(v not in CHECKS for v in verification)
        ):
            raise HarnessError("AC verification must name supported checks")
    dependencies = spec.get("dependencies")
    if not isinstance(dependencies, list):
        raise HarnessError("Dependencies must be explicit, including an empty list")
    for dependency in dependencies:
        if not isinstance(dependency, dict) or not isinstance(dependency.get("url"), str):
            raise HarnessError("Each dependency needs a GitHub issue/PR URL")
        if "ready" in dependency and not isinstance(dependency["ready"], bool):
            raise HarnessError("Dependency ready flag must be boolean")
    return spec


def normalize_issue(root: Path, issue: dict[str, Any], number: int) -> dict[str, Any]:
    if issue.get("number") != number or issue_number(root, issue.get("url", "")) != number:
        raise HarnessError("Snapshot issue identity does not match origin", "FAIL")
    if issue.get("state") != "OPEN" or not issue.get("title") or not issue.get("updatedAt"):
        raise HarnessError("Issue must be open with title and updatedAt")
    assignees = issue.get("assignees", [])
    if len(assignees) != 1 or not assignees[0].get("login"):
        raise HarnessError("Issue must have exactly one assignee")
    spec = task_spec(issue)
    if spec["reviewer"].lstrip("@") == assignees[0]["login"]:
        raise HarnessError("Reviewer must differ from assignee")
    result = {
        key: issue[key]
        for key in ("number", "url", "title", "body", "assignees", "updatedAt", "state")
    }
    result["spec"] = spec
    result["issue_hash"] = digest(canonical(result))
    result["fetched_at"] = now()
    return result


def dependencies_ready(root: Path, spec: dict[str, Any]) -> None:
    for dependency in spec["dependencies"]:
        if dependency.get("ready") is False:
            raise HarnessError(f"Dependency declared not ready: {dependency['url']}")
        match = re.fullmatch(
            r"https://github\.com/([\w.-]+/[\w.-]+)/(issues|pull)/(\d+)", dependency["url"]
        )
        if not match or match[1] != origin(root):
            raise HarnessError("Dependency must reference an issue/PR in origin")
        if match[2] == "issues":
            data = github_json(root, ["api", f"repos/{match[1]}/issues/{match[3]}"])
            complete = (
                data.get("state") == "closed"
                and data.get("state_reason") == "completed"
                and "pull_request" not in data
            )
        else:
            data = github_json(
                root, ["pr", "view", match[3], "--repo", match[1], "--json", "state"]
            )
            complete = data.get("state") == "MERGED"
        if not complete:
            raise HarnessError(f"Dependency not ready: {dependency['url']}")


def paths(root: Path, base: str, head: str = "HEAD", local: bool = True) -> list[str]:
    ancestor = git(root, "merge-base", resolve(root, base), resolve(root, head)).decode().strip()
    output = git(root, "diff", "--name-only", "--no-renames", "-z", ancestor, resolve(root, head))
    if local:
        output += git(root, "diff", "--cached", "--name-only", "--no-renames", "-z")
        output += git(root, "diff", "--name-only", "--no-renames", "-z")
        output += git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted({p.decode("utf-8", errors="surrogateescape") for p in output.split(b"\0") if p})


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def scope_check(
    root: Path,
    policy: dict[str, Any],
    spec: dict[str, Any],
    number: int,
    base: str,
    head: str = "HEAD",
    local: bool = True,
    branch_name: str | None = None,
) -> dict[str, Any]:
    lane = policy["lanes"].get(spec["lane"])
    if lane is None:
        raise HarnessError("Unknown owner lane")
    active_branch = branch_name if branch_name is not None else branch(root)
    if not fnmatch.fnmatchcase(active_branch, lane["branch"]):
        raise HarnessError(f"Branch {active_branch} does not match lane {spec['lane']}", "FAIL")
    handoff = f"docs/harness/handoffs/{number}.md"
    denied = []
    changed = paths(root, base, head, local)
    for path in changed:
        if path == handoff:
            continue
        protected = spec["lane"] not in ("tooling", "contract") and matches(
            path, policy["protected_paths"]
        )
        if (
            protected
            or not matches(path, lane["allowed_paths"])
            or not matches(path, spec["scope"])
        ):
            denied.append(path)
    if denied:
        raise HarnessError("Scope violation: " + json.dumps(denied, ensure_ascii=True), "FAIL")
    return {"result": "PASS", "lane": spec["lane"], "paths": changed, "base": resolve(root, base)}


def identity(root: Path, base: str) -> dict[str, Any]:
    status = git(root, "status", "--porcelain=v1", "-z")
    content = git(root, "diff", "--cached", "--binary") + git(root, "diff", "--binary") + status
    for raw in git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if raw:
            path = inside(root, raw.decode("utf-8", errors="surrogateescape"))
            content += raw + (
                os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            )
    return {
        "head": resolve(root, "HEAD"),
        "base": resolve(root, base),
        "branch": branch(root),
        "dirty_sha256": digest(content),
        "clean": not status,
    }


def active_task(root: Path, number: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    active = read_json(inside(root, ".harness/active.json"))
    if number is not None and active.get("issue") != number:
        raise HarnessError(
            "Different issue is active in this checkout; hand off before starting another"
        )
    snapshot = read_json(inside(root, active["snapshot_path"]))
    normalized = normalize_issue(root, snapshot, active["issue"])
    if normalized["issue_hash"] != snapshot.get("issue_hash"):
        raise HarnessError("Issue snapshot was modified; refresh before continuing", "FAIL")
    if active.get("branch") != branch(root):
        raise HarnessError("Active task branch differs from current branch")
    resolve(root, active["base"])
    return active, snapshot


def task_scope(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    number = issue_number(root, args.issue)
    active, snapshot = active_task(root, number)
    if resolve(root, active.get("base_ref", active["base"])) != active["base"]:
        raise HarnessError("Integration base changed; restart and reverify")
    if args.base and resolve(root, args.base) != active["base"]:
        raise HarnessError("Scope --base differs from the recorded integration base", "FAIL")
    if args.bootstrap and not active["bootstrap"]:
        raise HarnessError("Scope cannot enable bootstrap for an existing feature task", "FAIL")
    if args.lane and args.lane != snapshot["spec"]["lane"]:
        raise HarnessError("Lane does not match active issue", "FAIL")
    return scope_check(
        root,
        load_policy(root, active["base"], active["bootstrap"]),
        snapshot["spec"],
        number,
        active["base"],
    )


def version(root: Path, argv: list[str]) -> str:
    try:
        return execute(root, argv, timeout=3).decode(errors="replace").strip().splitlines()[0]
    except (HarnessError, IndexError):
        return "unavailable"


def doctor(root: Path) -> dict[str, Any]:
    tools = {
        name: version(root, [name, "--version"])
        for name in ("git", "gh", "uv", "node", "npm", "codex", "claude")
    }
    missing = [name for name in ("git", "gh", "uv", "node", "npm") if tools[name] == "unavailable"]
    if tools["node"] != "unavailable" and not tools["node"].startswith("v22."):
        missing.append("Node 22")
    if sys.version_info < (3, 11):  # noqa: UP036 - doctor also diagnoses an older interpreter
        missing.append("Python 3.11+")
    return {
        "result": "BLOCKED" if missing else "PASS",
        "root": str(root),
        "head": resolve(root, "HEAD"),
        "branch": branch(root),
        "clean": not git(root, "status", "--porcelain"),
        "tools": tools,
        "python": platform.python_version(),
        "missing": missing,
        "env_file": (root / ".env").is_file(),
        "agent_runtime": "NOT RUN",
    }


def start(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    number = issue_number(root, args.issue)
    if (root / ".harness/active.json").exists():
        previous = read_json(inside(root, ".harness/active.json"))
        if previous["issue"] != number or previous["branch"] != branch(root):
            handoff_path = f"docs/harness/handoffs/{previous['issue']}.md"
            try:
                git(root, "show", f"{resolve(root, previous['branch'])}:{handoff_path}")
            except HarnessError as exc:
                raise HarnessError("Previous branch needs a committed handoff") from exc
            if not identity(root, previous["base"])["clean"]:
                raise HarnessError(
                    "Previous issue needs a committed handoff before replacing active task"
                )
    issue = read_json(Path(args.snapshot)) if args.snapshot else fetch_issue(root, number)
    snapshot = normalize_issue(root, issue, number)
    spec = snapshot["spec"]
    base = resolve(root, args.base)
    policy = load_policy(root, base, args.bootstrap)
    if spec["lane"] not in ("tooling", "contract"):
        foundation = policy["foundation"]
        if foundation["review_status"] != "PASS" or not foundation.get("review_url"):
            raise HarnessError("Foundation independent review is pending; feature start is BLOCKED")
        git(root, "merge-base", "--is-ancestor", foundation["sha"], "HEAD")
    if not args.snapshot:
        actor = github_json(root, ["api", "user"])["login"]
        if actor != snapshot["assignees"][0]["login"]:
            raise HarnessError("Issue is assigned to another GitHub user")
        dependencies_ready(root, spec)
    elif spec["dependencies"]:
        raise HarnessError("Offline snapshots cannot prove dependency readiness")
    scope_check(root, policy, spec, number, base)
    session = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    directory = f".harness/issues/{number}/sessions/{session}"
    snapshot["source"] = "offline" if args.snapshot else "github"
    write_json(root, f"{directory}/issue.json", snapshot, exclusive=True)
    cli_version = (
        version(root, [args.tool, "--version"]) if args.tool in ("codex", "claude") else "manual"
    )
    active = {
        "schema_version": 1,
        "issue": number,
        "session": session,
        "snapshot_path": f"{directory}/issue.json",
        "directory": directory,
        "branch": branch(root),
        "base": base,
        "base_ref": args.base,
        "bootstrap": args.bootstrap,
        "started_at": now(),
        "initial_identity": identity(root, base),
        "tool": {
            "name": args.tool,
            "surface": args.surface,
            "version": cli_version if args.surface == "cli" else "NOT VERIFIED",
            "cli_version": cli_version,
        },
    }
    write_json(root, ".harness/active.json", active)
    return {
        "result": "PASS",
        "issue": number,
        "session": session,
        "base": base,
        "snapshot_source": snapshot["source"],
        "next": "Read scoped instructions and map ACs before editing",
    }


def check_command(root: Path, check: str, test_path: str | None = None) -> list[str]:
    if check not in CHECKS:
        raise HarnessError("Unsupported check", "FAIL")
    if check not in ("backend-test", "frontend-test", "e2e-test"):
        if test_path:
            raise HarnessError("--path is only accepted for focused tests", "FAIL")
        return ["make", check]
    if not test_path or not inside(root, test_path).is_file():
        raise HarnessError("Focused test requires an existing repository test file")
    if (
        check == "backend-test"
        and test_path.startswith("app/backend/")
        and Path(test_path).name.startswith("test_")
        and test_path.endswith(".py")
    ):
        return ["uv", "run", "pytest", test_path, "-v"]
    if (
        check == "frontend-test"
        and test_path.startswith("app/frontend/src/")
        and re.search(r"\.test\.tsx?$", test_path)
    ):
        return [
            "npm",
            "--prefix",
            "app/frontend",
            "run",
            "test",
            "--",
            test_path.removeprefix("app/frontend/"),
        ]
    if (
        check == "e2e-test"
        and test_path.startswith("app/frontend/e2e/")
        and test_path.endswith(".spec.ts")
    ):
        return [
            "npm",
            "--prefix",
            "app/frontend",
            "run",
            "test:e2e",
            "--",
            test_path.removeprefix("app/frontend/"),
        ]
    raise HarnessError("Focused test path does not match selected check", "FAIL")


def smoke_ports(ports: tuple[int, ...] = (8000, 4173)) -> None:
    for port in ports:
        with socket.socket() as probe:
            probe.settimeout(0.25)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise HarnessError(
                    f"Smoke port {port} is occupied; stop the owned server or use a separate host"
                )


def sanitized(text: str) -> str:
    for key, value in os.environ.items():
        if re.search(r"token|secret|password|api.?key", key, re.I) and len(value) >= 4:
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+", r"\1[REDACTED]", text)
    return re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b", "[REDACTED]", text)


def verification_process(root: Path, argv: list[str], timeout: int) -> tuple[int, bytes, str]:
    """Stop the whole verification process group on timeout or interruption."""
    if timeout <= 0:
        raise HarnessError("Verification timeout must be positive", "FAIL")
    process = subprocess.Popen(
        argv,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env={
            **os.environ,
            "DATA_BACKEND": "mock",
            "PREDICTOR_BACKEND": "fake",
            "ROUTE_BACKEND": "fake",
        },
    )
    reason = ""
    try:
        output, _ = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        reason = (
            "Verification timed out"
            if isinstance(exc, subprocess.TimeoutExpired)
            else "Interrupted"
        )
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
    return process.returncode, output, reason


def run_check(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    number = issue_number(root, args.issue)
    active, snapshot = active_task(root, number)
    policy = load_policy(root, active["base"], active["bootstrap"])
    scope_check(root, policy, snapshot["spec"], number, active["base"])
    known = {ac["id"]: ac for ac in snapshot["spec"]["acceptance"]}
    if any(ac not in known or args.check not in known[ac]["verification"] for ac in args.ac):
        raise HarnessError("AC mapping must use the check declared in the issue", "FAIL")
    argv = check_command(root, args.check, args.path)
    before = identity(root, active["base"])
    result: dict[str, Any] = {
        "schema_version": 2,
        "issue": number,
        "issue_hash": snapshot["issue_hash"],
        "check": args.check,
        "ac_ids": sorted(set(args.ac)),
        "argv": argv,
        "cwd": str(root),
        "started_at": now(),
        "identity": before,
        "tool": active["tool"],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "node": version(root, ["node", "--version"]),
            "uv": version(root, ["uv", "--version"]),
        },
        "result": "NOT RUN",
        "exit_code": None,
        "log_path": None,
        "log_sha256": None,
    }
    content = ""
    try:
        if args.check in ("smoke", "ci", "e2e-test"):
            smoke_ports()
        if not shutil.which(argv[0]):
            raise HarnessError(f"Missing executable: {argv[0]}")
        exit_code, output, reason = verification_process(root, argv, args.timeout)
        content = sanitized(output.decode(errors="replace"))
        result.update(exit_code=exit_code, result="PASS" if exit_code == 0 else "FAIL")
        if reason:
            result.update(result="BLOCKED", reason=reason)
    except (OSError, subprocess.TimeoutExpired, HarnessError) as exc:
        result.update(result="BLOCKED", reason=str(exc))
        if isinstance(exc, subprocess.TimeoutExpired):
            content = sanitized(
                ((exc.stdout or b"") + (exc.stderr or b"")).decode(errors="replace")
            )
    after = identity(root, active["base"])
    if before != after and result["result"] == "PASS":
        result.update(
            result="FAIL", reason="Verification changed code identity; commit changes and rerun"
        )
    stamp = uuid.uuid4().hex
    if result["exit_code"] is not None or content:
        log_path = f"{active['directory']}/{stamp}.log"
        log = inside(root, log_path)
        log.write_text(content, encoding="utf-8")
        result.update(log_path=log_path, log_sha256=digest(log.read_bytes()))
    result["finished_at"] = now()
    result["integrity"] = {
        "algorithm": "hmac-sha256",
        "value": evidence_signature(root, result, create=True),
    }
    write_json(root, f"{active['directory']}/{stamp}.v2.evidence.json", result, exclusive=True)
    return result


def validate_schema(value: Any, schema: dict[str, Any], location: str = "evidence") -> None:
    types = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    expected = schema.get("type")
    if expected:
        names = expected if isinstance(expected, list) else [expected]
        if not any(
            isinstance(value, types[name]) and not (name == "integer" and isinstance(value, bool))
            for name in names
        ):
            raise HarnessError(f"{location}: incorrect type", "FAIL")
    if "const" in schema and value != schema["const"]:
        raise HarnessError(f"{location}: incorrect version", "FAIL")
    if "enum" in schema and value not in schema["enum"]:
        raise HarnessError(f"{location}: unsupported value", "FAIL")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        raise HarnessError(f"{location}: invalid format", "FAIL")
    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        raise HarnessError(f"{location}: below minimum", "FAIL")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise HarnessError(f"{location}: missing {key}", "FAIL")
        for key, child in schema.get("properties", {}).items():
            if key in value:
                validate_schema(value[key], child, f"{location}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise HarnessError(f"{location}: empty list", "FAIL")
        if schema.get("uniqueItems") and len({canonical(item) for item in value}) != len(value):
            raise HarnessError(f"{location}: duplicate values", "FAIL")
        for item in value:
            validate_schema(item, schema.get("items", {}), location)


def current_evidence(
    root: Path, number: int, snapshot: dict[str, Any], code: dict[str, Any]
) -> list[dict[str, Any]]:
    schema = read_json(inside(root, SCHEMA_PATH))
    records = []
    legacy = False
    for path in inside(root, f".harness/issues/{number}/sessions").glob("*/*.evidence.json"):
        item = read_json(path)
        if path.name.endswith(".v2.evidence.json") and item.get("schema_version") != 2:
            raise HarnessError(
                "Evidence integrity version mismatch; sealed record downgraded", "FAIL"
            )
        current = (
            item.get("issue") == number
            and item.get("issue_hash") == snapshot["issue_hash"]
            and item.get("identity") == code
        )
        if item.get("schema_version") == 1 and "integrity" not in item:
            legacy |= current
            continue
        validate_schema(item, schema)
        if not hmac.compare_digest(item["integrity"]["value"], evidence_signature(root, item)):
            raise HarnessError(
                "Evidence integrity mismatch; restore/archive the altered record and rerun", "FAIL"
            )
        if current:
            records.append(item)
    if legacy and not records:
        raise HarnessError("Legacy unsealed evidence has no integrity seal; rerun checks")
    return records


def handoff(root: Path, number: int) -> dict[str, Any]:
    active, snapshot = active_task(root, number)
    path = inside(root, f"docs/harness/handoffs/{number}.md")
    if path.exists():
        raise HarnessError(
            "Handoff already exists; update its decisions/remaining work without overwriting",
            "FAIL",
        )
    checkpoint = {
        "schema_version": 1,
        "issue": number,
        "url": snapshot["url"],
        "issue_hash": snapshot["issue_hash"],
        "branch": branch(root),
        "head": resolve(root, "HEAD"),
        "base": active["base"],
        "state": "implemented",
        "completed": [],
        "remaining": [ac["id"] for ac in snapshot["spec"]["acceptance"]],
        "decisions": [],
        "blockers": [],
        "next_step": "Describe the next concrete action before handing off",
        "retries": 0,
        "dirty_at_checkpoint": not identity(root, active["base"])["clean"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Handoff — issue #{number}\n\n```json\n{json.dumps(checkpoint, indent=2)}\n```\n\n"
        "## Mục tiêu và phạm vi\n\nTham chiếu issue; ghi quyết định và công việc còn lại.\n\n"
        "## Bằng chứng\n\nFinal checks pending. PR/CI evidence records the final tested HEAD; "
        "this checkpoint HEAD is not the commit containing this file.\n",
        encoding="utf-8",
    )
    return {
        "result": "PASS",
        "path": str(path),
        "next": "Complete handoff prose and commit before final verification",
    }


def read_handoff(
    root: Path, number: int, active: dict[str, Any], snapshot: dict[str, Any]
) -> dict[str, Any]:
    path = inside(root, f"docs/harness/handoffs/{number}.md")
    try:
        blocks = re.findall(r"```json\s*\n(.*?)\n```", path.read_text(encoding="utf-8"), re.DOTALL)
        item = json.loads(blocks[0])
    except (OSError, ValueError, IndexError) as exc:
        raise HarnessError("Missing or malformed per-issue handoff") from exc
    for key in (
        "issue",
        "issue_hash",
        "branch",
        "head",
        "base",
        "state",
        "completed",
        "remaining",
        "decisions",
        "blockers",
        "next_step",
        "retries",
    ):
        if key not in item:
            raise HarnessError(f"Handoff missing {key}")
    if (
        item["issue"] != number
        or item["issue_hash"] != snapshot["issue_hash"]
        or item["branch"] != active["branch"]
        or item["base"] != active["base"]
    ):
        raise HarnessError("Handoff does not match active issue/branch/base")
    if item["state"] not in ("implemented", "verified", "review-ready", "blocked"):
        raise HarnessError("Merged state is reserved for GitHub/integrator")
    if item.get("schema_version") != 1:
        raise HarnessError("Unsupported handoff version")
    for key in ("completed", "remaining", "decisions", "blockers"):
        if not isinstance(item[key], list):
            raise HarnessError(f"Handoff {key} must be a list")
    if set(item["completed"]) != {ac["id"] for ac in snapshot["spec"]["acceptance"]}:
        raise HarnessError("Handoff completed IDs must cover every acceptance criterion")
    git(root, "merge-base", "--is-ancestor", resolve(root, item["head"]), "HEAD")
    if item["remaining"] or item["blockers"] or not item["next_step"] or item["state"] == "blocked":
        raise HarnessError("Handoff has remaining work or blockers")
    return item


def ready(root: Path, number: int, refresh: bool = True) -> dict[str, Any]:
    active, snapshot = active_task(root, number)
    if resolve(root, active.get("base_ref", active["base"])) != active["base"]:
        raise HarnessError("Integration base changed; restart and reverify")
    if refresh:
        current = normalize_issue(root, fetch_issue(root, number), number)
        if current["issue_hash"] != snapshot["issue_hash"]:
            raise HarnessError("Issue changed; refresh snapshot and reassess ACs")
        if active.get("base_ref") == "origin/main":
            remote_base = github_json(root, ["api", f"repos/{origin(root)}/commits/main"])["sha"]
            if remote_base != active["base"]:
                raise HarnessError("Remote integration base changed; fetch, integrate and reverify")
        dependencies_ready(root, snapshot["spec"])
    policy = load_policy(root, active["base"], active["bootstrap"])
    scope_check(root, policy, snapshot["spec"], number, active["base"])
    current_identity = identity(root, active["base"])
    if not current_identity["clean"]:
        raise HarnessError("Ready requires committed work and clean git status", "FAIL")
    read_handoff(root, number, active, snapshot)
    records = current_evidence(root, number, snapshot, current_identity)
    for item in records:
        if item["result"] in ("PASS", "FAIL") and item["exit_code"] is None:
            raise HarnessError("Executed result requires exit code", "FAIL")
        if item["result"] == "PASS" and item["exit_code"] != 0:
            raise HarnessError("PASS requires exit zero", "FAIL")
        if item["result"] in ("PASS", "FAIL"):
            if not item["log_path"] or not item["log_sha256"]:
                raise HarnessError("Executed evidence requires a log", "FAIL")
            log = inside(root, item["log_path"])
            if not log.is_file() or digest(log.read_bytes()) != item["log_sha256"]:
                raise HarnessError("Evidence log missing or modified", "FAIL")
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for item in sorted(records, key=lambda record: record["finished_at"]):
        latest[(item["check"], "gate")] = item
        for ac in item["ac_ids"]:
            latest[(item["check"], ac)] = item
    missing = [
        check
        for check in policy["required_local_checks"]
        if latest.get((check, "gate"), {}).get("result") != "PASS"
    ]
    for ac in snapshot["spec"]["acceptance"]:
        for check in ac["verification"]:
            if (
                latest.get((check, ac["id"]), {}).get("result") != "PASS"
                or latest.get((check, "gate"), {}).get("result") != "PASS"
            ):
                missing.append(f"{ac['id']}:{check}")
    if missing:
        raise HarnessError("Current verification missing/failed: " + ", ".join(missing), "FAIL")
    return {
        "result": "PASS",
        "state": "verified",
        "evidence_trust": "self-reported",
        "review_ready": False,
        "head": current_identity["head"],
        "next": "Attach evidence to PR; independent CI and human review still required",
        "merge": "NOT RUN",
    }


def verification_plan(changed: list[str], spec: dict[str, Any], full: bool = False) -> list[str]:
    if full:
        declared = {check for ac in spec["acceptance"] for check in ac["verification"]}
        return ["ci", *[check for check in CHECKS if check in declared and check != "ci"]]
    selected: set[str] = set()
    backend = any(path.startswith("app/backend/") for path in changed)
    frontend = any(path.startswith("app/frontend/") for path in changed)
    contracts = any(
        path.startswith("app/backend/contracts/")
        or path == "app/frontend/src/types/api.generated.ts"
        for path in changed
    )
    automation = any(
        path.startswith((".agents/", ".claude/", ".codex/", ".github/", "docs/harness/"))
        or Path(path).name in ("AGENTS.md", "CLAUDE.md", "Makefile", "pyproject.toml")
        for path in changed
    )
    if backend or contracts:
        selected.update(("backend-lint", "backend-test-suite"))
    if frontend or contracts:
        selected.update(("frontend-lint", "frontend-test-suite", "build", "smoke"))
    if contracts:
        selected.add("contract-check")
    if automation:
        selected.add("harness-check")
        if any(path.endswith(".py") for path in changed):
            selected.add("backend-lint")
    for ac in spec["acceptance"]:
        selected.update(ac["verification"])
    if "ci" in selected:
        return ["ci", *[item for item in CHECKS[-3:] if item in selected]]
    if "lint" in selected:
        selected.difference_update(("backend-lint", "frontend-lint"))
    if "test" in selected:
        selected.difference_update(("backend-test-suite", "frontend-test-suite"))
    return [check for check in CHECKS if check in selected]


def verify(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    number = issue_number(root, args.issue)
    active, snapshot = active_task(root, number)
    policy = load_policy(root, active["base"], active["bootstrap"])
    scope = scope_check(root, policy, snapshot["spec"], number, active["base"])
    code = identity(root, active["base"])
    if args.full and not code["clean"]:
        raise HarnessError("Full verification requires a committed checkpoint and clean status")
    checks = verification_plan(scope["paths"], snapshot["spec"], args.full)
    records = []
    for check in checks:
        if check in CHECKS[-3:]:
            current = [
                record
                for record in current_evidence(root, number, snapshot, code)
                if record["check"] == check
            ]
            required_ids = {
                ac["id"] for ac in snapshot["spec"]["acceptance"] if check in ac["verification"]
            }
            ordered = sorted(current, key=lambda item: item["finished_at"])
            covered = set()
            for record in ordered:
                valid = (
                    record["result"] == "PASS" and record["exit_code"] == 0 and record["log_path"]
                )
                if valid:
                    log = inside(root, record["log_path"])
                    valid = log.is_file() and digest(log.read_bytes()) == record["log_sha256"]
                if valid:
                    covered.update(record["ac_ids"])
                else:
                    covered.clear()
            if ordered and required_ids <= covered:
                records.append(
                    {
                        "check": check,
                        "result": "PASS",
                        "ac_ids": sorted(covered),
                        "reason": "Reused sealed local evidence with matching revision and logs",
                    }
                )
                continue
            records.append(
                {
                    "check": check,
                    "result": "NOT RUN",
                    "reason": "Use focused --path/--ac; registry presence is not execution proof",
                }
            )
            continue
        ac_ids = [ac["id"] for ac in snapshot["spec"]["acceptance"] if check in ac["verification"]]
        record = run_check(
            root,
            argparse.Namespace(
                issue=str(number), check=check, path=None, ac=ac_ids, timeout=args.timeout
            ),
        )
        records.append(
            {key: record[key] for key in ("check", "result", "exit_code", "ac_ids", "log_path")}
        )
        if record["result"] != "PASS":
            break
    results = [record["result"] for record in records]
    result = (
        "FAIL"
        if "FAIL" in results
        else "BLOCKED"
        if "BLOCKED" in results
        else ("NOT RUN" if not results or "NOT RUN" in results else "PASS")
    )
    summary = {
        "result": result,
        "evidence_trust": "self-reported",
        "issue": number,
        "identity": code,
        "full": args.full,
        "checks": records,
        "state": "implemented",
        "next": "Run ready with current AC/full-gate evidence; CI/review still required",
    }
    write_json(
        root, f"{active['directory']}/{uuid.uuid4().hex}.verify.json", summary, exclusive=True
    )
    return summary


def hook(root: Path, provider: str, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    if provider not in ("codex", "claude") or payload.get("hook_event_name") != event:
        return {"systemMessage": "V-EV harness: unsupported hook payload; run doctor manually"}
    if event == "PreToolUse":
        assets = agent_assets()
        policy = load_policy(root)
        spec = None
        if inside(root, ".harness/active.json").is_file():
            try:
                active, snapshot = active_task(root)
                policy = {**policy, **load_policy(root, active["base"], active["bootstrap"])}
                spec = {**snapshot["spec"], "issue": active["issue"]}
            except HarnessError:
                # A stale task cannot disable common push/generated/secret guards.
                pass
        action = assets.normalize(root, payload)
        violations = assets.evaluate(root, action, policy, branch(root), spec)
        if violations:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "; ".join(
                        f"{item['rule']}: {item['reason']}" for item in violations
                    ),
                }
            }
        if assets.canary_command(root, action, provider):
            assets.stamp_canary(root, provider, payload, resolve(root, "HEAD"))
        return {}
    if event == "Stop" and payload.get("stop_hook_active"):
        return {}
    if not inside(root, ".harness/active.json").is_file():
        if event == "Stop":
            return {}
        summary = (
            "V-EV harness: no active issue. Read docs/harness/workflow.md; "
            "start an assigned issue explicitly."
        )
    else:
        try:
            active, snapshot = active_task(root)
            state = identity(root, active["base"])
            summary = (
                f"V-EV issue #{active['issue']}; branch {state['branch']}; "
                f"HEAD {state['head'][:12]}; clean={state['clean']}. "
            )
            summary += (
                f"Read docs/harness/handoffs/{active['issue']}.md and docs/harness/workflow.md. "
            )
            summary += "Recheck Git, issue and evidence before editing."
            if event == "Stop":
                read_handoff(root, active["issue"], active, snapshot)
                if not state["clean"]:
                    raise HarnessError("Dirty checkpoint: complete handoff before transfer")
                ready(root, active["issue"], refresh=False)
                summary += "Run ready explicitly with fresh GitHub data; this hook ran no checks."
        except HarnessError as exc:
            summary = f"V-EV harness: {exc}; run doctor and complete the per-issue handoff."
    if event == "SessionStart":
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": summary[:1000],
            }
        }
    return {"systemMessage": summary[:1000]}


def self_check(root: Path) -> dict[str, Any]:
    policy = load_policy(root)
    schema = read_json(inside(root, SCHEMA_PATH))
    workflow = inside(root, ".github/workflows/ci.yml").read_text(encoding="utf-8")
    jobs = set(re.findall(r"(?m)^  ([a-z][a-z-]+):\s*$", workflow.split("\njobs:\n", 1)[1]))
    if jobs != set(policy["required_github_checks"]):
        raise HarnessError("Required GitHub checks differ from policy", "FAIL")
    makefile = inside(root, "Makefile").read_text(encoding="utf-8")
    make_targets = set(re.findall(r"(?m)^([a-z][a-z-]*):", makefile))
    if set(CHECKS[:-3]) - make_targets:
        raise HarnessError("Runner checks differ from Makefile", "FAIL")
    if schema["properties"]["check"]["enum"] != list(CHECKS):
        raise HarnessError("Evidence check vocabulary drift", "FAIL")
    if schema["properties"]["result"]["enum"] != list(RESULTS):
        raise HarnessError("Evidence result vocabulary drift", "FAIL")
    for directory in ("", "app/", "app/backend/", "app/frontend/"):
        importer = inside(root, f"{directory}CLAUDE.md")
        if importer.read_text(encoding="utf-8").strip() != "@AGENTS.md":
            raise HarnessError(f"Importer must only reference AGENTS: {importer}", "FAIL")
    for tool in (".agents", ".claude"):
        skill = inside(root, f"{tool}/skills/vev-issue/SKILL.md").read_text(encoding="utf-8")
        if "docs/harness/workflow.md" not in skill or "harness.py" not in skill:
            raise HarnessError(f"Workflow adapter drift: {tool}", "FAIL")
    assets = agent_assets()
    assets.budgets(root)
    synchronized = assets.synchronize(root, check=True)
    if synchronized["result"] != "PASS":
        raise HarnessError("Generated assets drift: " + ", ".join(synchronized["drift"]), "FAIL")
    for filename in git(root, "ls-files", "-z").split(b"\0"):
        basename = Path(filename.decode()).name
        if re.fullmatch(r"\.env(?:\..+)?", basename) and not basename.endswith(".example"):
            raise HarnessError("Real environment files must remain untracked", "FAIL")
    for config in (".codex/hooks.json", ".claude/settings.json"):
        settings = read_json(inside(root, config))
        if set(settings["hooks"]) != {"SessionStart", "Stop", "PreToolUse"}:
            raise HarnessError(f"Unexpected hook events: {config}", "FAIL")
        for groups in settings["hooks"].values():
            for group in groups:
                for handler in group["hooks"]:
                    if (
                        handler.get("type") != "command"
                        or handler.get("timeout") != policy["limits"]["hook_timeout_seconds"]
                    ):
                        raise HarnessError(f"Hook protocol drift: {config}", "FAIL")
    for path in (root / "docs/superpowers/plans").glob("*.md"):
        if re.search(
            r"REQUIRED SUB-SKILL|must use `superpowers:", path.read_text(encoding="utf-8")
        ):
            raise HarnessError(f"Unshared mandatory skill: {path.name}", "FAIL")
    return {"result": "PASS", "schema_version": 1, "runtime_pilot": "NOT RUN"}


def ci(root: Path, event_path: str) -> dict[str, Any]:
    event = read_json(Path(event_path))
    pr = event.get("pull_request")
    if not pr:
        return {
            **self_check(root),
            "scope": "NOT RUN",
            "reason": "Push checks structure; PR event checks task scope",
        }
    base = resolve(root, pr["base"]["sha"])
    head = resolve(root, pr["head"]["sha"])
    if resolve(root, "HEAD") != head:
        raise HarnessError("CI checkout does not match PR head")
    branch_name = pr["head"]["ref"]
    try:
        policy = load_policy(root, base)
    except HarnessError:
        if branch_name != "codex/harness-bootstrap" or git(
            root, "ls-tree", "--name-only", base, "--", POLICY_PATH
        ):
            raise
        return {
            **self_check(root),
            "result": "BLOCKED",
            "checks": "PASS",
            "mode": "bootstrap",
            "scope": "BLOCKED",
            "foundation_review": "BLOCKED",
            "manual_acceptance": "BLOCKED",
            "review_ready": False,
            "head": head,
            "base": base,
            "reason": (
                "First harness bootstrap requires manual scope/policy review; "
                "base has no trusted validator"
            ),
        }
    match = re.search(r"(?m)^Harness-Issue:\s*(\d+)\s*$", pr.get("body") or "")
    if not match:
        raise HarnessError("PR body must include Harness-Issue: N", "FAIL")
    number = int(match[1])
    snapshot = normalize_issue(root, fetch_issue(root, number), number)
    if pr.get("user", {}).get("login") != snapshot["assignees"][0]["login"]:
        raise HarnessError("PR author must be the issue assignee", "FAIL")
    dependencies_ready(root, snapshot["spec"])
    result = scope_check(root, policy, snapshot["spec"], number, base, head, False, branch_name)
    if snapshot["spec"]["lane"] not in ("tooling", "contract"):
        foundation = policy["foundation"]
        if foundation["review_status"] != "PASS" or not foundation.get("review_url"):
            raise HarnessError("Foundation review pending")
    return {**result, "head": head, "issue": number, "review": "NOT RUN", "merge": "NOT RUN"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", default=".", help="Path inside checkout")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("self-check")
    commands.add_parser("smoke-preflight")
    sync_parser = commands.add_parser("sync")
    sync_parser.add_argument("--check", action="store_true")
    canary_parser = commands.add_parser("canary")
    canary_parser.add_argument("--provider", choices=("codex", "claude"), required=True)
    canary_parser.add_argument("--session")
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--issue", required=True)
    verify_parser.add_argument("--full", action="store_true")
    verify_parser.add_argument("--timeout", type=int, default=900)
    for name in ("start", "scope", "run", "handoff", "ready"):
        command = commands.add_parser(name)
        command.add_argument("--issue", required=True)
        if name in ("start", "scope"):
            command.add_argument(
                "--base",
                default="origin/main" if name == "start" else None,
                help="Integration base at start; scope only accepts the recorded base SHA",
            )
            command.add_argument("--bootstrap", action="store_true")
        if name == "start":
            command.add_argument(
                "--snapshot", help="Offline issue replay, not proof of GitHub readiness"
            )
            command.add_argument("--tool", choices=("codex", "claude", "manual"), default="manual")
            command.add_argument("--surface", default="cli")
        if name == "scope":
            command.add_argument("--lane", help="Must match snapshot lane")
        if name == "run":
            command.add_argument("--check", choices=CHECKS, required=True)
            command.add_argument("--path")
            command.add_argument("--ac", action="append", default=[])
            command.add_argument("--timeout", type=int, default=900)
    hooks = commands.add_parser("hook")
    hooks.add_argument("--provider", choices=("codex", "claude"), required=True)
    hooks.add_argument("--event", choices=("SessionStart", "Stop", "PreToolUse"), required=True)
    ci_parser = commands.add_parser("ci")
    ci_parser.add_argument("--event-file", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "hook":
            payload = json.loads(sys.stdin.buffer.read(65536))
            if not isinstance(payload, dict) or not isinstance(payload.get("cwd"), str):
                raise HarnessError("Hook needs cwd")
            root = repository(payload["cwd"])
            output = hook(root, args.provider, args.event, payload)
            if (
                args.event == "PreToolUse"
                and output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
            ):
                print(output["hookSpecificOutput"]["permissionDecisionReason"], file=sys.stderr)
                print(json.dumps(output))
                return 2
        else:
            root = repository(args.root)
            if args.command == "doctor":
                output = doctor(root)
            elif args.command == "start":
                output = start(root, args)
            elif args.command == "self-check":
                output = self_check(root)
            elif args.command == "sync":
                output = agent_assets().synchronize(root, check=args.check)
            elif args.command == "canary":
                output = agent_assets().consume_canary(
                    root,
                    args.provider,
                    resolve(root, "HEAD"),
                    args.session,
                    load_policy(root)["limits"]["canary_ttl_seconds"],
                )
            elif args.command == "smoke-preflight":
                smoke_ports()
                output = {"result": "PASS", "ports": [8000, 4173]}
            elif args.command == "ci":
                output = ci(root, args.event_file)
            else:
                number = issue_number(root, args.issue)
                if args.command == "run":
                    output = run_check(root, args)
                elif args.command == "handoff":
                    output = handoff(root, number)
                elif args.command == "ready":
                    output = ready(root, number)
                elif args.command == "verify":
                    output = verify(root, args)
                else:
                    output = task_scope(root, args)
        print(json.dumps(output, ensure_ascii=True))
        if args.command == "hook":
            return 0
        return {"PASS": 0, "FAIL": 1, "BLOCKED": 2, "NOT RUN": 2}[output["result"]]
    except (HarnessError, OSError, ValueError, KeyError, TypeError) as exc:
        if args.command == "hook":
            print(
                json.dumps(
                    {
                        "systemMessage": (
                            f"V-EV harness validation unavailable: {exc}; run doctor manually"
                        )
                    }
                )
            )
            return 0
        status = exc.result if isinstance(exc, HarnessError) else "BLOCKED"
        print(json.dumps({"result": status, "reason": str(exc)}, ensure_ascii=True))
        return 1 if status == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
