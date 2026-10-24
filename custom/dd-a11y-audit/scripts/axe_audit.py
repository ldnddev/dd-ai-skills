#!/usr/bin/env python3
"""
axe-core accessibility audit script.
Uses Playwright with axe-core for automated WCAG testing.
"""

import json
import re
import sys
import argparse
import subprocess
import tempfile
import os
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parent.parent
PACKAGE_JSON_PATH = SKILL_DIR / "package.json"
AXE_RUNTIME_DIR = SKILL_DIR / ".axe-runtime"
AXE_RUNTIME_PACKAGE = AXE_RUNTIME_DIR / "package.json"
AXE_READY_PATH = AXE_RUNTIME_DIR / "ready.json"

# axe-core tags are not cumulative. wcag22aa is only the success criteria
# added in WCAG 2.2 at AA. A 2.2 AA scan is every A and AA tag from 2.0, 2.1,
# and 2.2. Tags with no rules yet (wcag22a today) match nothing and pick up
# new rules when axe adds them. best-practice and wcag2a-obsolete are not
# part of this set: obsolete rules are no longer required for 2.2 conformance.
WCAG_TAGS = {
    "A": ["wcag2a", "wcag21a", "wcag22a"],
    "AA": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"],
    "AAA": [
        "wcag2a", "wcag2aa", "wcag2aaa",
        "wcag21a", "wcag21aa", "wcag21aaa",
        "wcag22a", "wcag22aa", "wcag22aaa",
    ],
}

# Disabled rules with these tags stay off. experimental is not stable enough
# to treat as a conformance result. deprecated and wcag2a-obsolete are not
# required (4.1.1 Parsing was removed in WCAG 2.2). Other disabled rules that
# carry the selected WCAG tags are turned on — axe ships target-size (2.5.8)
# tagged wcag22aa with enabled:false, so a tag-only run would skip it.
SKIP_RULE_TAGS = ["experimental", "deprecated", "wcag2a-obsolete"]

_PRINCIPLES = {
    "1": "perceivable",
    "2": "operable",
    "3": "understandable",
    "4": "robust",
}

# Success-criterion tags (wcag143, wcag2411). Level tags (wcag2aa, wcag22aa) are not all digits.
_SC_TAG = re.compile(r"^wcag\d+$")


def wcag_tags(level):
    """Return the axe tag list for a WCAG 2.2 conformance level."""
    try:
        return list(WCAG_TAGS[level])
    except KeyError as exc:
        raise ValueError(f"Unsupported WCAG level: {level}") from exc


def principles_for_tags(tags):
    """Map axe success-criterion tags (wcag111, wcag1410, wcag2411) to POUR.

    Level tags such as wcag2aa and wcag22aa are not criterion numbers and are
    ignored. A rule can count toward more than one principle.
    """
    found = []
    for tag in tags or []:
        if not isinstance(tag, str) or not tag.startswith("wcag"):
            continue
        rest = tag[4:]
        if not rest.isdigit():
            continue
        principle = _PRINCIPLES.get(rest[0])
        if principle and principle not in found:
            found.append(principle)
    return found


def runtime_manifest(axe_core_version, axe_playwright_version):
    """Package manifest that pins both packages to the versions just resolved.

    The override forces @axe-core/playwright to load this axe-core, not an
    older nested copy from its own dependency range.
    """
    return {
        "name": "dd-a11y-axe-runtime",
        "private": True,
        "description": "Resolved at audit time from the npm latest dist-tags. Do not edit.",
        "dependencies": {
            "@axe-core/playwright": axe_playwright_version,
            "axe-core": axe_core_version,
        },
        "overrides": {
            "axe-core": "$axe-core",
        },
    }


def _npm_latest(package):
    """Return the npm `latest` dist-tag. That tag is the current stable release."""
    result = subprocess.run(
        ["npm", "view", package, "version"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or f"npm view {package} failed")
    lines = [line.strip().strip('"') for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"npm view {package} returned no version")
    return lines[-1]


def _installed_version(package_name, root):
    if package_name.startswith("@"):
        scope, name = package_name.split("/", 1)
        path = root / "node_modules" / scope / name / "package.json"
    else:
        path = root / "node_modules" / package_name / "package.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text()).get("version")
    except (OSError, json.JSONDecodeError):
        return None


def _resolved_axe_version(package_json):
    """Version of axe-core that Node will load from this package.json.

    Require the package itself. axe-core's exports block `axe-core/package.json`,
    and @axe-core/playwright blocks its package.json subpath too.
    """
    script = """
const { createRequire } = require('module');
const requireFromAxe = createRequire(process.argv[1]);
try {
  const axe = requireFromAxe('axe-core');
  const axePlaywright = requireFromAxe('@axe-core/playwright');
  if (!axe || !axe.version || !axePlaywright) {
    throw new Error('axe runtime did not load');
  }
  process.stdout.write(JSON.stringify({ axe_core: axe.version }));
} catch (error) {
  process.stderr.write(error && error.message ? error.message : String(error));
  process.exit(1);
}
"""
    result = subprocess.run(
        [_node_command(), "-e", script, str(package_json)],
        capture_output=True,
        text=True,
        cwd=package_json.parent,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _write_ready(status):
    AXE_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    AXE_READY_PATH.write_text(json.dumps(status, indent=2) + "\n")


def load_ready():
    if not AXE_READY_PATH.is_file():
        return {}
    try:
        return json.loads(AXE_READY_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _fallback_package_json():
    """Prefer the audit-time runtime. Fall back to the skill install."""
    if _installed_version("axe-core", AXE_RUNTIME_DIR) and _installed_version(
        "@axe-core/playwright", AXE_RUNTIME_DIR
    ):
        return AXE_RUNTIME_PACKAGE
    if PACKAGE_JSON_PATH.is_file():
        return PACKAGE_JSON_PATH
    return None


def ensure_latest_axe():
    """Install the npm `latest` axe-core and @axe-core/playwright into `.axe-runtime`.

    Returns a status dict. `usable` means a scan can load axe. `ok` means that
    copy matches the registry latest tags. A registry outage keeps the copy
    already on disk and sets `warning`.
    """
    try:
        latest_core = _npm_latest("axe-core")
        latest_playwright = _npm_latest("@axe-core/playwright")
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        package_json = _fallback_package_json()
        resolved = _resolved_axe_version(package_json) if package_json else None
        playwright_version = _installed_version(
            "@axe-core/playwright", Path(package_json).parent if package_json else AXE_RUNTIME_DIR
        )
        usable = bool(resolved and resolved.get("axe_core"))
        warning = (
            "Could not reach the npm registry to confirm axe-core is the current "
            f"release ({exc}). "
        )
        if usable:
            warning += f"Scanning with installed axe-core {resolved['axe_core']}."
        else:
            warning += "No axe-core is installed, so the scan cannot run."
        status = {
            "ok": False,
            "usable": usable,
            "updated": False,
            "axe_core": (resolved or {}).get("axe_core"),
            "axe_playwright": playwright_version,
            "latest_axe_core": None,
            "latest_axe_playwright": None,
            "package_json": str(package_json) if package_json else None,
            "warning": warning,
        }
        if usable:
            _write_ready(status)
        return status

    resolved_now = (
        _resolved_axe_version(AXE_RUNTIME_PACKAGE) if AXE_RUNTIME_PACKAGE.is_file() else None
    )
    installed_core = (resolved_now or {}).get("axe_core") or _installed_version("axe-core", AXE_RUNTIME_DIR)
    installed_playwright = _installed_version("@axe-core/playwright", AXE_RUNTIME_DIR)
    needs_install = installed_core != latest_core or installed_playwright != latest_playwright
    if needs_install:
        AXE_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        manifest = runtime_manifest(latest_core, latest_playwright)
        AXE_RUNTIME_PACKAGE.write_text(json.dumps(manifest, indent=2) + "\n")
        try:
            subprocess.run(
                ["npm", "install", "--no-audit", "--no-fund", "--ignore-scripts"],
                cwd=AXE_RUNTIME_DIR,
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            detail = ""
            if isinstance(exc, subprocess.CalledProcessError):
                detail = (exc.stderr or exc.stdout or "").strip()
            package_json = _fallback_package_json()
            resolved = _resolved_axe_version(package_json) if package_json else None
            playwright_version = _installed_version(
                "@axe-core/playwright", Path(package_json).parent if package_json else AXE_RUNTIME_DIR
            )
            usable = bool(resolved and resolved.get("axe_core"))
            warning = "Failed to install the latest axe-core. "
            if detail:
                warning += detail[:500] + " "
            if usable:
                warning += f"Scanning with installed axe-core {resolved['axe_core']}."
            else:
                warning += "No usable axe-core is installed."
            status = {
                "ok": False,
                "usable": usable,
                "updated": False,
                "axe_core": (resolved or {}).get("axe_core"),
                "axe_playwright": playwright_version,
                "latest_axe_core": latest_core,
                "latest_axe_playwright": latest_playwright,
                "package_json": str(package_json) if package_json else None,
                "warning": warning,
            }
            if usable:
                _write_ready(status)
            return status

    resolved = _resolved_axe_version(AXE_RUNTIME_PACKAGE)
    actual = (resolved or {}).get("axe_core")
    installed_playwright = _installed_version("@axe-core/playwright", AXE_RUNTIME_DIR) or installed_playwright
    warning = None
    ok = actual == latest_core
    if actual and actual != latest_core:
        warning = (
            f"npm latest axe-core is {latest_core}, but the runtime resolved {actual}."
        )
    elif not actual:
        warning = "axe-core installed, but Node could not resolve it from .axe-runtime."
        ok = False
    status = {
        "ok": ok,
        "usable": bool(actual),
        "updated": needs_install and bool(actual),
        "axe_core": actual,
        "axe_playwright": installed_playwright or latest_playwright,
        "latest_axe_core": latest_core,
        "latest_axe_playwright": latest_playwright,
        "package_json": str(AXE_RUNTIME_PACKAGE) if actual else None,
        "warning": warning,
    }
    if actual:
        _write_ready(status)
    return status

def _node_command():
    """Return the node executable if available."""
    return "node"

def check_dependencies(axe_package_json=None):
    """Check whether the Node-side axe/playwright runtime is usable."""
    missing = []
    install_commands = []
    axe_package = Path(axe_package_json) if axe_package_json else _fallback_package_json()
    if axe_package is None:
        axe_package = PACKAGE_JSON_PATH

    try:
        node_version = subprocess.run(
            [_node_command(), "--version"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        missing.append("Node.js")
        install_commands.append("Install Node.js so the audit can execute the Playwright/axe runtime.")
        node_version = None

    if not PACKAGE_JSON_PATH.exists():
        missing.append("playwright (Node package)")
        install_commands.append(f"cd {SKILL_DIR} && npm ci")
    if not axe_package.exists():
        missing.extend(["@axe-core/playwright", "axe-core"])
        install_commands.append(f"cd {SKILL_DIR} && python3 scripts/axe_audit.py --prepare-axe")
    elif not missing:
        probe = """
const { createRequire } = require('module');
const requireFromSkill = createRequire(process.argv[1]);
const requireFromAxe = createRequire(process.argv[2]);
try {
  requireFromSkill('playwright');
} catch (error) {
  console.error('missing:playwright');
  process.exit(11);
}
try {
  requireFromAxe('@axe-core/playwright');
} catch (error) {
  console.error('missing:@axe-core/playwright');
  process.exit(12);
}
try {
  requireFromAxe('axe-core');
} catch (error) {
  console.error('missing:axe-core');
  process.exit(14);
}
process.exit(0);
"""
        result = subprocess.run(
            [_node_command(), "-e", probe, str(PACKAGE_JSON_PATH), str(axe_package)],
            capture_output=True,
            text=True,
            cwd=SKILL_DIR,
        )
        if result.returncode == 11:
            missing.append("playwright (Node package)")
        elif result.returncode == 12:
            missing.append("@axe-core/playwright")
        elif result.returncode == 14:
            missing.append("axe-core")
        elif result.returncode != 0:
            missing.append("Node module resolution")

        if missing:
            if "playwright (Node package)" in missing:
                install_commands.append(f"cd {SKILL_DIR} && npm ci")
            if "@axe-core/playwright" in missing or "axe-core" in missing:
                install_commands.append(
                    f"cd {SKILL_DIR} && python3 scripts/axe_audit.py --prepare-axe"
                )

    browser_probe = """
const { createRequire } = require('module');
const requireFromSkill = createRequire(process.argv[1]);
const { chromium } = requireFromSkill('playwright');
chromium.launch({ headless: true, channel: 'chromium' }).then(async browser => {
  await browser.close();
  process.exit(0);
}).catch(error => {
  console.error(error && error.message ? error.message : String(error));
  process.exit(13);
});
"""
    if not missing and PACKAGE_JSON_PATH.exists():
        browser_result = subprocess.run(
            [_node_command(), "-e", browser_probe, str(PACKAGE_JSON_PATH)],
            capture_output=True,
            text=True,
            cwd=SKILL_DIR,
        )
        if browser_result.returncode != 0:
            error_text = (browser_result.stderr or browser_result.stdout).strip()
            if "Operation not permitted" in error_text or "sandbox" in error_text.lower():
                missing.append("Browser launch permission in the current sandbox/runtime")
            else:
                missing.append("Playwright Chromium browser runtime")
                install_commands.append(f"cd {SKILL_DIR} && npx playwright install chromium")
            return {
                "ok": False,
                "message": "Playwright is installed, but the browser could not be launched.",
                "missing": missing,
                "install_commands": install_commands,
                "details": {
                    "node_version": node_version,
                    "skill_dir": str(SKILL_DIR),
                    "launch_error": error_text,
                },
            }

    if missing:
        return {
            "ok": False,
            "message": "Missing or unusable dependencies for axe-core audit.",
            "missing": missing,
            "install_commands": install_commands,
            "details": {
                "node_version": node_version,
                "skill_dir": str(SKILL_DIR),
            },
        }

    return {
        "ok": True,
        "details": {
            "node_version": node_version,
            "skill_dir": str(SKILL_DIR),
        },
    }

def dependency_error_result(dependency_status, url):
    """Create a structured error payload for missing dependencies."""
    missing = dependency_status.get("missing", [])
    commands = dependency_status.get("install_commands", [])
    details = dependency_status.get("details", {})

    command_text = "\n".join(f"- {command}" for command in commands) if commands else "- No install commands available."
    missing_text = ", ".join(missing) if missing else "unknown dependencies"
    node_version = details.get("node_version") or "not found"
    launch_error = details.get("launch_error")

    message = (
        f"The audit cannot run because these dependencies are missing or unusable: {missing_text}.\n"
        f"Detected Node.js version: {node_version}\n"
    )

    if launch_error:
        message += (
            "Playwright and axe-core appear to be installed, but browser launch failed in the current environment.\n"
            f"Launch error: {launch_error}\n"
        )

    if commands:
        message += "Install or repair them with:\n" + command_text
    else:
        message += "No install step is required. Re-run the audit in an environment that allows Chromium to launch."

    return {
        "error": True,
        "url": url,
        "message": message,
        "missing_dependencies": missing,
        "install_commands": commands,
    }

def run_axe_audit(url, level="AA", rules=None, timeout=30000, axe_package_json=None, expected_axe_version=None):
    """
    Run axe-core accessibility audit on a URL.

    Args:
        url: URL to test
        level: WCAG 2.2 level (A, AA, AAA). Default AA.
        rules: Specific rules to run (comma-separated). Replaces the WCAG tag set.
        timeout: Page load timeout in milliseconds
        axe_package_json: package.json whose node_modules holds axe-core
        expected_axe_version: npm latest version this run should have loaded

    Returns:
        dict: Audit results
    """
    axe_package = str(axe_package_json or _fallback_package_json() or PACKAGE_JSON_PATH)
    rule_list = [part.strip() for part in (rules or "").split(",") if part.strip()]
    config = {
        "url": url,
        "tags": wcag_tags(level),
        "rules": rule_list,
        "skipRuleTags": SKIP_RULE_TAGS,
        "packageJson": str(PACKAGE_JSON_PATH),
        "axePackageJson": axe_package,
    }
    # Create a temporary JavaScript file. Config is JSON so the URL cannot break out.
    js_content = """
    const { createRequire } = require('module');
    const config = __CONFIG__;
    const requireFromSkill = createRequire(config.packageJson);
    const requireFromAxe = createRequire(config.axePackageJson);
    const { chromium } = requireFromSkill('playwright');
    const axePlaywright = requireFromAxe('@axe-core/playwright');
    const AxeBuilder = axePlaywright.default || axePlaywright.AxeBuilder || axePlaywright;
    const axe = requireFromAxe('axe-core');

    function wcagRuleOptions(tags) {
      const options = {};
      if (typeof axe.getRules !== 'function') {
        return options;
      }
      const skip = new Set(config.skipRuleTags || []);
      for (const rule of axe.getRules(tags)) {
        const ruleTags = rule.tags || [];
        if (ruleTags.some((tag) => skip.has(tag))) {
          options[rule.ruleId] = { enabled: false };
          continue;
        }
        if (rule.enabled === false) {
          options[rule.ruleId] = { enabled: true };
        }
      }
      return options;
    }

    async function runAxeAudit() {
        const browser = await chromium.launch({ headless: true, channel: 'chromium' });
        const context = await browser.newContext();
        const page = await context.newPage();

        try {
            await page.goto(config.url, { waitUntil: 'networkidle' });

            const builder = new AxeBuilder({ page });
            const ruleOptions = wcagRuleOptions(config.tags);
            if (Object.keys(ruleOptions).length) {
              builder.options({ rules: ruleOptions });
            }
            if (config.rules.length) {
              builder.withRules(config.rules);
            } else {
              builder.withTags(config.tags);
            }

            const results = await builder.analyze();

            await browser.close();

            console.log(JSON.stringify(results));

        } catch (error) {
            await browser.close();
            console.error(JSON.stringify({
                error: true,
                message: error.message,
                url: config.url
            }));
        }
    }

    runAxeAudit().catch(error => {
        console.error(JSON.stringify({
            error: true,
            message: error.message
        }));
    });
    """.replace("__CONFIG__", json.dumps(config))
    
    # Write JS to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(js_content)
        js_file = f.name
    
    try:
        # Run the JavaScript with Node.js
        result = subprocess.run(
            ['node', js_file],
            capture_output=True,
            text=True,
            timeout=timeout/1000 + 10,  # Add 10 seconds buffer
            cwd=SKILL_DIR,
        )
        
        # Clean up temp file
        os.unlink(js_file)
        
        if result.returncode != 0:
            return {
                "error": True,
                "message": f"Node.js execution failed: {result.stderr}",
                "url": url
            }
        
        # Parse JSON output
        output = result.stdout.strip()
        if not output:
            return {
                "error": True,
                "message": "No output from axe-core",
                "url": url
            }
        
        data = json.loads(output)
        
        if data.get("error"):
            return data
        
        # Format results
        return format_axe_results(data, url, level, expected_axe_version)
        
    except subprocess.TimeoutExpired:
        if os.path.exists(js_file):
            os.unlink(js_file)
        return {
            "error": True,
            "message": f"Audit timed out after {timeout}ms",
            "url": url
        }
    except json.JSONDecodeError as e:
        return {
            "error": True,
            "message": f"Failed to parse JSON: {e}",
            "output": result.stdout[:500] if result else "No output"
        }
    except Exception as e:
        if os.path.exists(js_file):
            os.unlink(js_file)
        return {
            "error": True,
            "message": f"Unexpected error: {str(e)}",
            "url": url
        }

def collect_sc_tags(*rule_lists):
    """SC tags axe actually executed, including inapplicable rules.

    Collected before passes are truncated. The report subtracts these from the
    scanned level to list criteria that did not run.
    """
    found = set()
    for rules in rule_lists:
        for rule in rules or []:
            for tag in rule.get("tags") or []:
                if _SC_TAG.match(tag):
                    found.add(tag)
    return sorted(found)


def format_axe_results(data, url, level, expected_axe_version=None):
    """Format axe-core results into structured output."""
    violations = data.get("violations", [])
    passes = data.get("passes", [])
    incomplete = data.get("incomplete", [])
    inapplicable = data.get("inapplicable", [])
    sc_checked = collect_sc_tags(violations, passes, incomplete, inapplicable)
    
    # Share of rules that passed. Incomplete rules are not passes.
    # This is not a WCAG conformance percentage.
    total_checks = len(violations) + len(passes) + len(incomplete)
    if total_checks == 0:
        score = 0
    else:
        score = (len(passes) / total_checks) * 100
    
    # Categorize violations by impact
    critical = [v for v in violations if v.get("impact") == "critical"]
    serious = [v for v in violations if v.get("impact") == "serious"]
    moderate = [v for v in violations if v.get("impact") == "moderate"]
    minor = [v for v in violations if v.get("impact") == "minor"]

    principle_counts = {principle: 0 for principle in _PRINCIPLES.values()}
    for violation in violations:
        for principle in principles_for_tags(violation.get("tags") or []):
            principle_counts[principle] += 1

    engine = data.get("testEngine") or {}
    axe_version = engine.get("version")
    metadata = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "tool": engine.get("name") or "axe-core",
        "axe_core_version": axe_version,
        "wcag_version": "2.2",
        "wcag_level": level,
        "wcag_target": f"WCAG 2.2 Level {level}",
        "wcag_tags": wcag_tags(level),
        "score": round(score, 1),
        "score_method": "passed_rules / (passed + violated + incomplete rules)",
        "sc_checked": sc_checked,
    }
    if expected_axe_version and axe_version and axe_version != expected_axe_version:
        metadata["axe_version_warning"] = (
            f"Scan ran axe-core {axe_version}, but npm latest is {expected_axe_version}."
        )

    return {
        "metadata": metadata,
        "summary": {
            "total_violations": len(violations),
            "total_passes": len(passes),
            "total_incomplete": len(incomplete),
            "total_inapplicable": len(inapplicable),
            "critical_violations": len(critical),
            "serious_violations": len(serious),
            "moderate_violations": len(moderate),
            "minor_violations": len(minor)
        },
        "principle_counts": principle_counts,
        "violations": format_violations(violations),
        "passes": format_passes(passes),
        "incomplete": format_incomplete(incomplete),
        "recommendations": generate_recommendations(violations, score)
    }

def format_violations(violations):
    """Format violations for output."""
    formatted = []
    for violation in violations:
        formatted.append({
            "id": violation.get("id"),
            "description": violation.get("description"),
            "impact": violation.get("impact"),
            "help": violation.get("help"),
            "helpUrl": violation.get("helpUrl"),
            "nodes_count": len(violation.get("nodes", [])),
            "wcag_tags": [tag for tag in violation.get("tags", []) if tag.startswith("wcag")],
            "nodes_preview": [{
                "html": node.get("html", "")[:200],
                "target": node.get("target", [])
            } for node in violation.get("nodes", [])[:3]]  # First 3 nodes only
        })
    return formatted

def format_passes(passes):
    """Format passes for output."""
    formatted = []
    for check in passes:
        formatted.append({
            "id": check.get("id"),
            "description": check.get("description"),
            "impact": check.get("impact"),
            "nodes_count": len(check.get("nodes", []))
        })
    return formatted[:20]  # Limit to 20 passes

def format_incomplete(incomplete):
    """Format incomplete checks for output."""
    formatted = []
    for check in incomplete:
        formatted.append({
            "id": check.get("id"),
            "description": check.get("description"),
            "impact": check.get("impact"),
            "message": check.get("message", "")
        })
    return formatted

def generate_recommendations(violations, score):
    """Generate actionable recommendations based on violations."""
    recommendations = []
    
    # Check for common critical issues
    critical_rules = ["color-contrast", "image-alt", "button-name", "link-name"]
    for rule_id in critical_rules:
        rule_violations = [v for v in violations if v.get("id") == rule_id]
        if rule_violations:
            count = len(rule_violations)
            if rule_id == "color-contrast":
                recommendations.append({
                    "priority": "critical",
                    "issue": "Color contrast violations",
                    "count": count,
                    "action": "Fix color contrast ratios to meet WCAG 2.2 1.4.3 (minimum 4.5:1 for normal text)",
                    "impact": "Affects users with low vision or color blindness"
                })
            elif rule_id == "image-alt":
                recommendations.append({
                    "priority": "critical",
                    "issue": "Missing alt text on images",
                    "count": count,
                    "action": "Add descriptive alt text to all informative images, empty alt for decorative images",
                    "impact": "Screen reader users cannot understand image content"
                })
            elif rule_id == "button-name":
                recommendations.append({
                    "priority": "critical",
                    "issue": "Buttons without accessible names",
                    "count": count,
                    "action": "Add aria-label or visible text to all buttons",
                    "impact": "Screen reader users cannot identify button purpose"
                })
    
    # General recommendations based on score
    if score < 50:
        recommendations.append({
            "priority": "critical",
            "issue": "Low overall accessibility score",
            "action": "Conduct comprehensive accessibility review and remediation",
            "impact": "Significant barriers for users with disabilities"
        })
    elif score < 75:
        recommendations.append({
            "priority": "serious",
            "issue": "Moderate accessibility score",
            "action": "Address critical and serious violations first, then moderate issues",
            "impact": "Multiple barriers affecting user experience"
        })
    
    return recommendations

def main():
    parser = argparse.ArgumentParser(description="Run axe-core accessibility audit")
    parser.add_argument("url", nargs="?", help="URL to test")
    parser.add_argument("--level", choices=["A", "AA", "AAA"], default="AA",
                       help="WCAG 2.2 conformance level (default: AA)")
    parser.add_argument("--prepare-axe", action="store_true",
                       help="Install the npm latest axe-core and @axe-core/playwright, then exit")
    parser.add_argument("--rules", help="Specific rules to run (comma-separated)")
    parser.add_argument("--timeout", type=int, default=30000,
                       help="Page load timeout in milliseconds (default: 30000)")
    parser.add_argument("--output", help="Output file path (JSON format)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()

    if args.prepare_axe:
        status = ensure_latest_axe()
        print(json.dumps(status, indent=2))
        sys.exit(0 if status.get("usable") else 1)

    if not args.url:
        parser.error("URL is required unless --prepare-axe is set.")

    if os.environ.get("DD_A11Y_SKIP_AXE_UPDATE") == "1":
        ready = load_ready()
        axe_status = ready or {"package_json": str(_fallback_package_json() or "")}
    else:
        axe_status = ensure_latest_axe()
        if axe_status.get("warning"):
            print(axe_status["warning"], file=sys.stderr)

    axe_package_json = axe_status.get("package_json") or str(_fallback_package_json() or PACKAGE_JSON_PATH)
    expected_axe_version = axe_status.get("latest_axe_core") or axe_status.get("axe_core")

    # Check dependencies
    dependency_status = check_dependencies(axe_package_json)
    if not dependency_status.get("ok"):
        results = dependency_error_result(dependency_status, args.url)
        output = json.dumps(results, indent=2) if args.json else format_human_readable(results)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Results saved to {args.output}", file=sys.stderr)
        else:
            print(output)
        sys.exit(1)
    
    # Run audit
    print(f"Running axe-core audit on {args.url}...", file=sys.stderr)
    results = run_axe_audit(
        args.url,
        args.level,
        args.rules,
        args.timeout,
        axe_package_json=axe_package_json,
        expected_axe_version=expected_axe_version,
    )
    
    # Output results
    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = format_human_readable(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results saved to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    # Exit code based on critical violations
    if results.get("error"):
        sys.exit(1)
    elif results.get("summary", {}).get("critical_violations", 0) > 0:
        sys.exit(2)
    elif results.get("summary", {}).get("serious_violations", 0) > 5:
        sys.exit(3)
    else:
        sys.exit(0)

def format_human_readable(results):
    """Format results for human-readable output."""
    if results.get("error"):
        return f"Error: {results.get('message')}"
    
    meta = results["metadata"]
    summary = results["summary"]
    
    output = []
    output.append("=" * 60)
    output.append(f"axe-core Accessibility Audit")
    output.append("=" * 60)
    output.append(f"URL: {meta['url']}")
    output.append(f"Timestamp: {meta['timestamp']}")
    output.append(f"WCAG Target: {meta.get('wcag_target') or meta['wcag_level']}")
    if meta.get("axe_core_version"):
        output.append(f"axe-core: {meta['axe_core_version']}")
    if meta.get("axe_version_warning"):
        output.append(f"Warning: {meta['axe_version_warning']}")
    output.append(f"Overall Score: {meta['score']}/100 (rule pass rate, not conformance)")
    output.append("")
    
    output.append("Summary:")
    output.append(f"  Critical Violations: {summary['critical_violations']}")
    output.append(f"  Serious Violations: {summary['serious_violations']}")
    output.append(f"  Moderate Violations: {summary['moderate_violations']}")
    output.append(f"  Minor Violations: {summary['minor_violations']}")
    output.append(f"  Passed Checks: {summary['total_passes']}")
    output.append("")
    
    output.append("WCAG Principle Distribution:")
    for principle, count in results.get("principle_counts", {}).items():
        output.append(f"  {principle.title()}: {count} violations")
    output.append("")
    
    if results.get("violations"):
        output.append("Top Violations:")
        for i, violation in enumerate(results["violations"][:5], 1):
            output.append(f"{i}. {violation['description']}")
            output.append(f"   Impact: {violation['impact'].title()}")
            output.append(f"   Elements: {violation['nodes_count']}")
            if violation.get('wcag_tags'):
                output.append(f"   WCAG: {', '.join(violation['wcag_tags'])}")
            output.append("")
    
    if results.get("recommendations"):
        output.append("Recommendations:")
        for rec in results["recommendations"]:
            output.append(f"  [{rec['priority'].upper()}] {rec['issue']}")
            if rec.get('count'):
                output.append(f"     Count: {rec['count']} occurrences")
            output.append(f"     Action: {rec['action']}")
            output.append("")
    
    return "\n".join(output)

if __name__ == "__main__":
    main()
