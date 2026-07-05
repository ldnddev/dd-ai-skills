# custom/dd-seo-audit/tests/test_generate_report_wiring.py
import inspect
import generate_report as r


def test_collect_data_accepts_gsc_params():
    sig = inspect.signature(r.collect_data)
    assert "gsc_path" in sig.parameters
    assert "brand" in sig.parameters
    assert "min_impressions" in sig.parameters


def test_main_defines_gsc_flag():
    src = inspect.getsource(r.main)
    assert "--gsc" in src
    assert "gsc_path" in src
