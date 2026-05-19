"""Tests for dd_framework_helper.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HELPER = HERE / "dd_framework_helper.py"
ASSETS = HERE.parent / "assets"
MANIFEST = ASSETS / "components.manifest.json"
COMPONENTS = ASSETS / "components"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        capture_output=True,
        text=True,
    )


# ---------- manifest integrity ----------

def test_manifest_is_valid_json():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "components" in data
    assert isinstance(data["components"], dict)


def test_manifest_has_seventeen_components():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(data["components"]) == 17


def test_every_manifest_entry_has_html_and_spec_files():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing: list[str] = []
    for name, comp in data["components"].items():
        if not (COMPONENTS / comp["file"]).exists():
            missing.append(f"{name}: {comp['file']}")
        if not (COMPONENTS / comp["spec"]).exists():
            missing.append(f"{name}: {comp['spec']}")
    assert not missing, "Missing files: " + ", ".join(missing)


def test_every_manifest_entry_has_required_fields():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    required_keys = {"file", "spec", "summary", "root_selector", "wraps_in_section", "required", "variants"}
    for name, comp in data["components"].items():
        missing = required_keys - set(comp.keys())
        assert not missing, f"{name} missing keys: {missing}"


# ---------- list ----------

def test_list_json_default():
    r = run("list")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "components" in out
    assert "dd-hero" in out["components"]
    assert "dd-card" in out["components"]


def test_list_human_output():
    r = run("list", "--human")
    assert r.returncode == 0
    assert "dd-hero" in r.stdout
    assert "summary:" in r.stdout
    assert "required:" in r.stdout


def test_list_includes_all_seventeen():
    r = run("list")
    out = json.loads(r.stdout)
    assert len(out["components"]) == 17


# ---------- get ----------

@pytest.mark.parametrize("name", [
    "dd-accordion", "dd-alert", "dd-alternating", "dd-banner", "dd-blockquote",
    "dd-card", "dd-cookie-consent", "dd-cta", "dd-filmstrip", "dd-hero",
    "dd-milestones", "dd-modal", "dd-section", "dd-slider", "dd-spacer",
    "dd-tabs", "dd-timeline",
])
def test_get_each_component(name: str):
    r = run("get", name)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["name"] == name
    assert "spec_md" in out
    assert "html_example" in out
    assert name in out["spec_md"]


def test_get_section_filter_params_only():
    r = run("get", "dd-hero", "--section", "params")
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert "params" in out
    assert "spec_md" not in out
    assert "html_example" not in out


def test_get_section_filter_html_only():
    r = run("get", "dd-hero", "--section", "html")
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert "html_example" in out
    assert "spec_md" not in out


def test_get_unknown_component_fails():
    r = run("get", "dd-nonexistent")
    assert r.returncode == 2
    assert "Unknown component" in r.stderr


def test_get_human_output():
    r = run("get", "dd-hero", "--human")
    assert r.returncode == 0
    assert "# dd-hero" in r.stdout
    assert "--- SPEC ---" in r.stdout


# ---------- validate ----------

def test_validate_passing_hero(tmp_path: Path):
    f = tmp_path / "ok.html"
    f.write_text("""
    <section class="dd-hero" aria-label="Intro">
      <div class="dd-hero__image"><img src="x.jpg" alt=""></div>
      <div class="dd-hero__content dd-g"><h1>Hello</h1></div>
    </section>
    """)
    r = run("validate", str(f))
    assert r.returncode == 0, r.stdout
    out = json.loads(r.stdout)
    assert "dd-hero" in out["components_detected"]
    assert out["errors"] == 0


def test_validate_hero_without_aria_label_errors(tmp_path: Path):
    f = tmp_path / "bad.html"
    f.write_text("""
    <section class="dd-hero">
      <div class="dd-hero__content"><h1>Hello</h1></div>
    </section>
    """)
    r = run("validate", str(f))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    errs = [x for x in out["findings"] if x["severity"] == "error"]
    assert any("aria-label" in e["message"] for e in errs)


def test_validate_card_image_missing_alt(tmp_path: Path):
    f = tmp_path / "bad.html"
    f.write_text("""
    <div class="dd-card">
      <div class="dd-card__items">
        <div class="dd-card__item"><img src="x.jpg"></div>
      </div>
    </div>
    """)
    r = run("validate", str(f))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    errs = [x for x in out["findings"] if x["severity"] == "error"]
    assert any("alt" in e["message"].lower() for e in errs)


def test_validate_modal_must_be_dialog(tmp_path: Path):
    f = tmp_path / "bad.html"
    f.write_text('<div class="dd-modal"><div class="dd-modal__content">x</div></div>')
    r = run("validate", str(f))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert any("dialog" in e["message"].lower() for e in out["findings"] if e["severity"] == "error")


def test_validate_tabs_anchor_instead_of_button(tmp_path: Path):
    f = tmp_path / "bad.html"
    f.write_text("""
    <div class="dd-tabs">
      <div class="dd-tabs__content"><ul class="dd-tabs__menu" role="tablist">
        <li><a role="tab" aria-selected="true">Tab</a></li>
      </ul></div>
    </div>
    """)
    r = run("validate", str(f))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    errs = [x for x in out["findings"] if x["severity"] == "error"]
    assert any("<button>" in e["message"] for e in errs)


def test_validate_alert_warning_without_role(tmp_path: Path):
    f = tmp_path / "bad.html"
    f.write_text("""
    <div class="dd-alert -error">
      <div class="dd-alert__content"><div class="dd-alert__heading">Oops</div></div>
    </div>
    """)
    r = run("validate", str(f))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert any("role=\"alert\"" in e["message"] for e in out["findings"] if e["severity"] == "error")


def test_validate_cookie_consent_role_dialog_errors(tmp_path: Path):
    f = tmp_path / "bad.html"
    f.write_text('<div id="cookie-consent" class="dd-cookie-consent" role="dialog" aria-modal="false">x</div>')
    r = run("validate", str(f))
    # Note: dd-cookie-consent uses an id-based root, but the class is also present here for detection
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert any("role=\"region\"" in e["message"] for e in out["findings"])


def test_validate_warn_mode_exits_zero_on_errors(tmp_path: Path):
    f = tmp_path / "bad.html"
    f.write_text('<div class="dd-card"><div class="dd-card__items"><img src="x"></div></div>')
    r = run("validate", str(f), "--warn")
    assert r.returncode == 0


def test_validate_missing_file_errors():
    r = run("validate", "/nonexistent/path.html")
    assert r.returncode == 2


def test_validate_human_output(tmp_path: Path):
    f = tmp_path / "ok.html"
    f.write_text('<div class="dd-spacer -xxl" aria-hidden="true"></div>')
    r = run("validate", str(f), "--human")
    assert r.returncode == 0
    assert "dd-spacer" in r.stdout
    assert "Errors:" in r.stdout


def test_validate_empty_html_no_components(tmp_path: Path):
    f = tmp_path / "empty.html"
    f.write_text("<div>plain content, no dd-* classes</div>")
    r = run("validate", str(f))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["components_detected"] == []
    assert out["errors"] == 0
