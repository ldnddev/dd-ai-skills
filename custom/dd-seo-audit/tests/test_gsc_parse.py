# custom/dd-seo-audit/tests/test_gsc_parse.py
import io
import zipfile
import gsc_import as g


def test_parse_ctr_percent_string():
    assert g._parse_ctr("3.4%") == 3.4
    assert g._parse_ctr("0.03") == 3.0      # fraction -> percent
    assert g._parse_ctr("12") == 12.0       # already percent
    assert g._parse_ctr("") is None


def test_detect_report_from_header():
    assert g._report_kind(["Top queries", "Clicks", "Impressions", "CTR", "Position"]) == "queries"
    assert g._report_kind(["Top pages", "Clicks", "Impressions", "CTR", "Position"]) == "pages"
    assert g._report_kind(["Date", "Clicks", "Impressions", "CTR", "Position"]) == "dates"
    assert g._report_kind(["Nonsense", "A"]) is None


def test_parse_queries_csv_rows():
    text = "Top queries,Clicks,Impressions,CTR,Position\nred team,10,500,2%,12.3\nbad,x,y,z,w\n"
    rows, kind, skipped = g._parse_csv_text(text)
    assert kind == "queries"
    assert skipped == 1
    assert rows == [{"query": "red team", "page": None,
                     "clicks": 10, "impressions": 500, "ctr": 2.0, "position": 12.3}]


def test_parse_zip_collects_members():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Queries.csv", "Top queries,Clicks,Impressions,CTR,Position\na,1,2,50%,1.0\n")
        z.writestr("Pages.csv", "Top pages,Clicks,Impressions,CTR,Position\nhttps://x/a,1,2,50%,1.0\n")
    result = g.load_export(buf.getvalue(), kind="zip", input_name="e.zip")
    assert set(result["meta"]["reports"]) == {"queries", "pages"}
    assert result["meta"]["rows_parsed"] == 2


def test_non_gsc_csv_returns_error():
    result = g.load_export(b"foo,bar\n1,2\n", kind="csv", input_name="x.csv")
    assert "error" in result
    assert result["rows"] == []
