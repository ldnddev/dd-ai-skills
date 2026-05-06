#!/usr/bin/env python3
"""
axe-core accessibility audit script.
Uses Playwright with axe-core for automated WCAG testing.
"""

import json
import sys
import argparse
import subprocess
import tempfile
import os
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parent.parent
PACKAGE_JSON_PATH = SKILL_DIR / "package.json"

def _node_command():
    """Return the node executable if available."""
    return "node"

def check_dependencies():
    """Check whether the Node-side axe/playwright runtime is usable."""
    missing = []
    install_commands = []

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
        missing.extend(["playwright (Node package)", "@axe-core/playwright"])
        install_commands.append(f"cd {SKILL_DIR} && npm install playwright @axe-core/playwright")
    elif not missing:
        probe = """
const { createRequire } = require('module');
const requireFromSkill = createRequire(process.argv[1]);
try {
  requireFromSkill('playwright');
} catch (error) {
  console.error('missing:playwright');
  process.exit(11);
}
try {
  requireFromSkill('@axe-core/playwright');
} catch (error) {
  console.error('missing:@axe-core/playwright');
  process.exit(12);
}
process.exit(0);
"""
        result = subprocess.run(
            [_node_command(), "-e", probe, str(PACKAGE_JSON_PATH)],
            capture_output=True,
            text=True,
            cwd=SKILL_DIR,
        )
        if result.returncode == 11:
            missing.append("playwright (Node package)")
        elif result.returncode == 12:
            missing.append("@axe-core/playwright")
        elif result.returncode != 0:
            missing.append("Node module resolution")

        if missing:
            install_commands.append(f"cd {SKILL_DIR} && npm install playwright @axe-core/playwright")

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

def run_axe_audit(url, level="AA", rules=None, timeout=30000):
    """
    Run axe-core accessibility audit on a URL.
    
    Args:
        url: URL to test
        level: WCAG level (A, AA, AAA)
        rules: Specific rules to run (comma-separated)
        timeout: Page load timeout in milliseconds
    
    Returns:
        dict: Audit results
    """
    # Create a temporary JavaScript file
    js_content = """
    const { createRequire } = require('module');
    const requireFromSkill = createRequire('""" + str(PACKAGE_JSON_PATH) + """');
    const { chromium } = requireFromSkill('playwright');
    const axePlaywright = requireFromSkill('@axe-core/playwright');
    const AxeBuilder = axePlaywright.default || axePlaywright.AxeBuilder || axePlaywright;
    
    async function runAxeAudit() {
        const browser = await chromium.launch({ headless: true, channel: 'chromium' });
        const context = await browser.newContext();
        const page = await context.newPage();
        
        try {
            await page.goto('""" + url + """', { waitUntil: 'networkidle' });
            
            const builder = new AxeBuilder({ page });
            
            // Configure options
            builder.withTags(['wcag2a', 'wcag2aa', 'wcag2aaa']);
            
            if ('""" + level + """' === 'A') {
                builder.withTags(['wcag2a']);
            } else if ('""" + level + """' === 'AA') {
                builder.withTags(['wcag2a', 'wcag2aa']);
            } else if ('""" + level + """' === 'AAA') {
                builder.withTags(['wcag2a', 'wcag2aa', 'wcag2aaa']);
            }
            
            // Add specific rules if provided
            const rulesStr = '""" + (rules or "") + """';
            if (rulesStr) {
                const ruleList = rulesStr.split(',').map(r => r.trim()).filter(r => r);
                builder.withRules(ruleList);
            }
            
            // Run analysis
            const results = await builder.analyze();
            
            // Close browser
            await browser.close();
            
            // Return results
            console.log(JSON.stringify(results, null, 2));
            
        } catch (error) {
            await browser.close();
            console.error(JSON.stringify({
                error: true,
                message: error.message,
                url: '""" + url + """'
            }));
        }
    }
    
    runAxeAudit().catch(error => {
        console.error(JSON.stringify({
            error: true,
            message: error.message
        }));
    });
    """
    
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
        return format_axe_results(data, url, level)
        
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

def format_axe_results(data, url, level):
    """Format axe-core results into structured output."""
    violations = data.get("violations", [])
    passes = data.get("passes", [])
    incomplete = data.get("incomplete", [])
    inapplicable = data.get("inapplicable", [])
    
    # Calculate scores
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
    
    # Map to WCAG principles
    wcag_mapping = {
        "perceivable": ["color-contrast", "image-alt", "label", "aria-hidden-focus"],
        "operable": ["button-name", "link-name", "keyboard", "focus-order"],
        "understandable": ["page-has-heading-one", "heading-order", "language"],
        "robust": ["aria-valid-attr", "aria-required-attr", "duplicate-id"]
    }
    
    # Count violations by principle
    principle_counts = {principle: 0 for principle in wcag_mapping.keys()}
    for violation in violations:
        rule_id = violation.get("id", "")
        for principle, rules in wcag_mapping.items():
            if rule_id in rules:
                principle_counts[principle] += 1
                break
    
    return {
        "metadata": {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "tool": "axe-core",
            "wcag_level": level,
            "score": round(score, 1)
        },
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
    parser.add_argument("url", help="URL to test")
    parser.add_argument("--level", choices=["A", "AA", "AAA"], default="AA",
                       help="WCAG compliance level (default: AA)")
    parser.add_argument("--rules", help="Specific rules to run (comma-separated)")
    parser.add_argument("--timeout", type=int, default=30000,
                       help="Page load timeout in milliseconds (default: 30000)")
    parser.add_argument("--output", help="Output file path (JSON format)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    # Check dependencies
    dependency_status = check_dependencies()
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
    results = run_axe_audit(args.url, args.level, args.rules, args.timeout)
    
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
    output.append(f"WCAG Level: {meta['wcag_level']}")
    output.append(f"Overall Score: {meta['score']}/100")
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
