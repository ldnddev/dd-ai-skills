# custom/dd-seo-audit/tests/test_gsc_insights_core.py
import gsc_import as g


def _row(q=None, p=None, clicks=0, impr=0, ctr=0.0, pos=0.0):
    return {"query": q, "page": p, "clicks": clicks, "impressions": impr, "ctr": ctr, "position": pos}


def test_expected_ctr_monotonic():
    assert g._expected_ctr(1) > g._expected_ctr(5) > g._expected_ctr(15)


def test_striking_distance_selects_pos_11_to_20():
    rows = [_row(q="a", impr=500, pos=12.0), _row(q="b", impr=500, pos=8.0),
            _row(q="c", impr=10, pos=15.0), _row(q="d", impr=500, pos=20.0)]
    out = g.striking_distance(rows, min_impressions=50)
    got = {r["query"] for r in out}
    assert got == {"a", "d"}          # b too high a rank, c too few impressions


def test_low_ctr_flags_below_half_expected():
    # position 3 expected ~11%; 1% actual is well under half
    rows = [_row(q="under", impr=1000, ctr=1.0, pos=3.0),
            _row(q="fine", impr=1000, ctr=12.0, pos=3.0)]
    out = g.low_ctr(rows, min_impressions=50)
    got = {r["query"] for r in out}
    assert got == {"under"}


def test_core_issues_have_task_fields():
    rows = [_row(q="a", p="https://x/a", impr=4200, ctr=0.8, pos=12.0)]
    issues = g.core_issues(g.striking_distance(rows, 50), g.low_ctr(rows, 50))
    assert issues and all({"severity", "finding", "evidence", "fix"} <= set(i) for i in issues)
