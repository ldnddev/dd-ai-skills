# custom/dd-seo-audit/tests/test_gsc_render.py
import generate_report as r


def _gsc():
    return {
        "insights": {
            "striking_distance": [{"query": "web design", "page": None,
                                   "impressions": 900, "ctr": 1.0, "position": 12.0}],
            "low_ctr": [], "cannibalization": [],
            "top_performers": {"top_queries": [], "top_pages": [], "branded": {}},
            "trends": {},
        },
        "meta": {"rows_parsed": 1, "notes": []},
    }


def test_render_gsc_section_has_accessible_table():
    html = r.render_gsc_section(_gsc())
    assert "<table" in html
    assert "<caption" in html
    assert 'scope="col"' in html
    assert "web design" in html


def test_render_gsc_section_empty_on_error():
    assert r.render_gsc_section({"error": "bad file"}) == ""
    assert r.render_gsc_section({}) == ""
