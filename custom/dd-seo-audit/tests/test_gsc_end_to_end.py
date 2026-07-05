# custom/dd-seo-audit/tests/test_gsc_end_to_end.py
import io
import zipfile
import generate_report as r


def _make_zip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Queries.csv",
                   "Top queries,Clicks,Impressions,CTR,Position\n"
                   "web design,2,4200,0.8%,12.0\n")
        z.writestr("Pages.csv",
                   "Top pages,Clicks,Impressions,CTR,Position\n"
                   "https://example.com/x,2,4200,0.8%,12.0\n")
    p = tmp_path / "gsc.zip"
    p.write_bytes(buf.getvalue())
    return str(p)


def test_gsc_issues_flow_into_tasks(tmp_path):
    gsc_path = _make_zip(tmp_path)
    # Run only the gsc analysis via the same runner generate_report uses.
    gsc_result = r.run_script("gsc_import.py",
                              [gsc_path, "--url", "https://example.com", "--min-impressions", "50"])
    data = {"url": "https://example.com", "domain": "example.com",
            "sections": {"gsc": gsc_result}, "environment_fixes": []}
    rows = r.build_seo_tasks(data)
    findings = " ".join(row["finding"] for row in rows)
    assert "Striking-distance" in findings         # GSC issue reached the task list
    assert any(row["category"] == "gsc" for row in rows)


def test_render_section_appears(tmp_path):
    gsc_path = _make_zip(tmp_path)
    gsc_result = r.run_script("gsc_import.py", [gsc_path, "--url", "https://example.com"])
    html = r.render_gsc_section(gsc_result)
    assert "Striking-distance queries" in html
