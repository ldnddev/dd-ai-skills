# custom/dd-seo-audit/tests/test_gsc_insights_top.py
import gsc_import as g


def test_brand_token_from_url():
    assert g.brand_tokens_from_url("https://www.ldnddev.com/x") == ["ldnddev"]
    assert g.brand_tokens_from_url("") == []


def test_top_performers_branded_split():
    reports = {
        "queries": [
            {"query": "ldnddev pricing", "page": None, "clicks": 30, "impressions": 100, "ctr": 30.0, "position": 1.0},
            {"query": "web design", "page": None, "clicks": 10, "impressions": 900, "ctr": 1.1, "position": 8.0},
        ],
        "pages": [
            {"query": None, "page": "https://x/a", "clicks": 40, "impressions": 1000, "ctr": 4.0, "position": 3.0},
        ],
    }
    out = g.top_performers(reports, brand_tokens=["ldnddev"], top_n=10)
    assert out["top_queries"][0]["query"] == "ldnddev pricing"
    assert out["top_pages"][0]["page"] == "https://x/a"
    assert out["branded"]["branded_clicks"] == 30
    assert out["branded"]["nonbranded_clicks"] == 10
    assert out["branded"]["branded_share_pct"] == 75.0
