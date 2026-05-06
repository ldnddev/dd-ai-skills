#!/usr/bin/env python3
"""
Validate dd-skills marketplace + plugin manifests.

Checks:
- Root .claude-plugin/marketplace.json exists, parses, has required fields
- Each plugins[].source resolves to a directory with .claude-plugin/plugin.json
- Each plugin.json parses + has required fields (name, version, description, skills)
- Plugin name in marketplace == name in plugin.json
- All plugin names are unique
- All plugin names follow dd-<short> convention
- Each skill path resolves to a directory containing SKILL.md
- Each SKILL.md has YAML frontmatter with `name:` and `description:`
- Skill `name:` matches expected dd-<short> convention
- hooks reference (plugin.json `hooks`) resolves and is valid JSON if present
- package.json (if present) parses + name matches plugin name + deps pinned exact
- package-lock.json (if present) parses + name matches package.json name
- install.sh (if present) has valid bash syntax (best-effort via `bash -n`)
- hooks/*.sh (if present) have valid bash syntax

Exits 0 on success, 1 on any finding. Prints a single line per finding:
    [LEVEL] <path>: <message>

LEVEL = ERROR | WARN. WARN does not fail the build.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_FILE = REPO_ROOT / ".claude-plugin" / "marketplace.json"

PLUGIN_NAME_RE = re.compile(r"^dd-[a-z][a-z0-9-]*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
EXACT_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
REQUIRED_LICENSE = "MIT"

errors: list[str] = []
warnings: list[str] = []


def err(path: Path | str, msg: str) -> None:
    errors.append(f"[ERROR] {path}: {msg}")


def warn(path: Path | str, msg: str) -> None:
    warnings.append(f"[WARN]  {path}: {msg}")


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        err(path, "file not found")
    except json.JSONDecodeError as e:
        err(path, f"invalid JSON: {e}")
    return None


def parse_frontmatter(skill_md: Path) -> dict[str, str] | None:
    """Minimal YAML frontmatter parser — keys + scalar string values only."""
    text = skill_md.read_text()
    if not text.startswith("---"):
        err(skill_md, "missing YAML frontmatter (no leading ---)")
        return None
    end = text.find("\n---", 3)
    if end == -1:
        err(skill_md, "unterminated YAML frontmatter (no closing ---)")
        return None
    block = text[3:end].strip("\n")
    out: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []
    for raw in block.splitlines():
        if not raw.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", raw)
        if m and not raw.startswith(" "):
            if current_key is not None:
                out[current_key] = " ".join(buf).strip()
                buf = []
            current_key = m.group(1)
            value = m.group(2).strip()
            if value in ("", ">", "|", ">-", "|-"):
                continue
            out[current_key] = value
            current_key = None
        elif current_key is not None and raw.startswith((" ", "\t")):
            buf.append(raw.strip())
    if current_key is not None and buf:
        out[current_key] = " ".join(buf).strip()
    return out


def bash_syntax_check(script: Path) -> None:
    if not shutil.which("bash"):
        return
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err(script, f"bash syntax error: {result.stderr.strip()}")


def validate_skill(plugin_dir: Path, plugin_name: str, skill_ref: str) -> None:
    skill_dir = (plugin_dir / skill_ref).resolve()
    if not skill_dir.is_dir():
        err(plugin_dir, f"skill path does not resolve to a directory: {skill_ref}")
        return
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        err(skill_dir, "missing SKILL.md")
        return
    fm = parse_frontmatter(skill_md)
    if fm is None:
        return
    if "name" not in fm:
        err(skill_md, "frontmatter missing `name`")
    else:
        name = fm["name"]
        if not PLUGIN_NAME_RE.match(name):
            err(skill_md, f"skill name `{name}` does not match dd-<short> convention")
        if name != plugin_name:
            err(
                skill_md,
                f"skill name `{name}` does not match plugin name `{plugin_name}`",
            )
    if "description" not in fm or not fm["description"].strip():
        err(skill_md, "frontmatter missing or empty `description`")
    if "license" in fm and fm["license"] != REQUIRED_LICENSE:
        err(
            skill_md,
            f"frontmatter license `{fm['license']}` must be `{REQUIRED_LICENSE}`",
        )


def validate_hooks(plugin_dir: Path, hooks_ref: str) -> None:
    hooks_path = (plugin_dir / hooks_ref).resolve()
    if not hooks_path.is_file():
        err(plugin_dir, f"hooks file does not exist: {hooks_ref}")
        return
    data = load_json(hooks_path)
    if data is None:
        return
    if not isinstance(data, dict):
        err(hooks_path, "hooks.json must be an object")
        return
    valid_events = {
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "Stop",
        "SubagentStop",
        "Notification",
        "PreCompact",
    }
    for event, groups in data.items():
        if event not in valid_events:
            warn(hooks_path, f"unknown hook event `{event}`")
        if not isinstance(groups, list):
            err(hooks_path, f"event `{event}` must be a list")
            continue
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                if not cmd:
                    err(hooks_path, f"event `{event}` has hook with empty command")
                    continue
                if "${CLAUDE_PLUGIN_ROOT}" not in cmd and not cmd.startswith("/"):
                    warn(
                        hooks_path,
                        f"hook command should use ${{CLAUDE_PLUGIN_ROOT}} for portability: {cmd}",
                    )
                # Resolve hook script for syntax-check if local
                if "${CLAUDE_PLUGIN_ROOT}" in cmd:
                    rel = cmd.replace("${CLAUDE_PLUGIN_ROOT}", "").lstrip("/")
                    script = plugin_dir / rel
                    if script.is_file() and script.suffix == ".sh":
                        bash_syntax_check(script)
                    elif script.suffix == ".sh":
                        err(hooks_path, f"hook script not found: {script}")


def validate_package_json(plugin_dir: Path, plugin_name: str) -> None:
    pkg_path = plugin_dir / "package.json"
    if not pkg_path.is_file():
        return
    pkg = load_json(pkg_path)
    if pkg is None:
        return
    if pkg.get("name") != plugin_name:
        err(
            pkg_path,
            f"package.json name `{pkg.get('name')}` does not match plugin name `{plugin_name}`",
        )
    pkg_license = pkg.get("license")
    if pkg_license is None:
        warn(pkg_path, f"missing `license` field (expected `{REQUIRED_LICENSE}`)")
    elif pkg_license != REQUIRED_LICENSE:
        err(pkg_path, f"license `{pkg_license}` must be `{REQUIRED_LICENSE}`")
    for dep_field in ("dependencies", "devDependencies"):
        for dep, ver in (pkg.get(dep_field) or {}).items():
            if not EXACT_VERSION_RE.match(str(ver)):
                warn(pkg_path, f"{dep_field}.{dep} version `{ver}` is not pinned exact")
    lock_path = plugin_dir / "package-lock.json"
    if lock_path.is_file():
        lock = load_json(lock_path)
        if lock is not None and lock.get("name") != pkg.get("name"):
            err(
                lock_path,
                f"package-lock.json name `{lock.get('name')}` does not match package.json name `{pkg.get('name')}`",
            )


def validate_plugin(plugin_entry: dict[str, Any]) -> None:
    plugin_name = plugin_entry.get("name", "")
    source = plugin_entry.get("source", "")
    if not plugin_name or not source:
        err(MARKETPLACE_FILE, f"plugin entry missing name or source: {plugin_entry}")
        return
    if not PLUGIN_NAME_RE.match(plugin_name):
        err(MARKETPLACE_FILE, f"plugin name `{plugin_name}` does not match dd-<short> convention")
    plugin_dir = (REPO_ROOT / source).resolve()
    if not plugin_dir.is_dir():
        err(MARKETPLACE_FILE, f"plugin source `{source}` does not resolve to a directory")
        return

    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    pj = load_json(manifest)
    if pj is None:
        return
    for required in ("name", "version", "description"):
        if required not in pj:
            err(manifest, f"missing required field `{required}`")
    if pj.get("name") != plugin_name:
        err(
            manifest,
            f"plugin name `{pj.get('name')}` does not match marketplace entry `{plugin_name}`",
        )
    if "version" in pj and not SEMVER_RE.match(str(pj["version"])):
        err(manifest, f"version `{pj['version']}` is not semver")
    pj_license = pj.get("license")
    if pj_license is None:
        err(manifest, f"missing `license` field (expected `{REQUIRED_LICENSE}`)")
    elif pj_license != REQUIRED_LICENSE:
        err(manifest, f"license `{pj_license}` must be `{REQUIRED_LICENSE}`")

    skills = pj.get("skills") or []
    if not skills:
        warn(manifest, "no `skills` declared")
    for s in skills:
        validate_skill(plugin_dir, plugin_name, s)

    hooks_ref = pj.get("hooks")
    if hooks_ref:
        validate_hooks(plugin_dir, hooks_ref)

    install_sh = plugin_dir / "install.sh"
    if install_sh.is_file():
        bash_syntax_check(install_sh)
    else:
        warn(plugin_dir, "no install.sh — Codex install path missing")

    readme = plugin_dir / "README.md"
    if not readme.is_file():
        warn(plugin_dir, "no README.md")

    validate_package_json(plugin_dir, plugin_name)


def main() -> int:
    if not MARKETPLACE_FILE.is_file():
        err(MARKETPLACE_FILE, "marketplace file not found")
        print("\n".join(errors))
        return 1

    market = load_json(MARKETPLACE_FILE)
    if market is None:
        print("\n".join(errors))
        return 1

    for required in ("name", "owner", "plugins"):
        if required not in market:
            err(MARKETPLACE_FILE, f"missing required field `{required}`")

    plugins = market.get("plugins") or []
    seen = set()
    for entry in plugins:
        name = entry.get("name", "")
        if name in seen:
            err(MARKETPLACE_FILE, f"duplicate plugin name `{name}`")
        seen.add(name)
        validate_plugin(entry)

    for line in warnings:
        print(line)
    for line in errors:
        print(line)

    print(
        f"\nSummary: {len(plugins)} plugins · "
        f"{len(errors)} errors · {len(warnings)} warnings"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
