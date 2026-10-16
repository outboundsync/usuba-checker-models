"""D7: failures that used to be swallowed by `except Exception` now surface (or are narrowed to the one expected error)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
cr = pytest.importorskip("checker_report")


def _boom(files, **kw): raise RuntimeError("rule bug")


def test_crashing_lifecycle_rule_is_not_an_empty_report(monkeypatch):
    monkeypatch.setattr(cr.LR, "check", _boom)
    with pytest.raises(RuntimeError):
        cr.report_and_warn_rules({"A.qml": "Item {}\n"}, timeout=60)


def test_crashing_hancore_v2_rule_is_not_an_empty_report(monkeypatch):
    monkeypatch.setattr(cr.HV2, "check", _boom)
    with pytest.raises(RuntimeError):
        cr.report_and_warn_rules({"A.qml": "Item {}\n"}, timeout=60)


def test_no_timeout_crash_is_reported_on_stderr(capsys):
    assert cr.run_with_timeout(_boom, ({},), 0) == (False, None)
    assert "rule bug" in capsys.readouterr().err


def test_midcheck_forbidden_ids_refuses_a_corrupt_ground_truth_file(tmp_path, monkeypatch):
    mc = pytest.importorskip("midcheck")
    (tmp_path / "functest").mkdir()
    (tmp_path / "functest" / "dell_ground_truth.jsonl").write_text(json.dumps({"id": "A.B"}) + "\n{not json\n")
    monkeypatch.setattr(mc, "ROOT", str(tmp_path))
    with pytest.raises(ValueError):
        mc._forbidden_ids()


def test_manifest_id_tolerates_only_bad_json():
    bts = pytest.importorskip("build_train_set")
    assert bts.manifest_id({"manifest.json": "{bad"}) is None
    assert bts.manifest_id({"manifest.json": '{"id":"x.y"}'}) == "x.y"
    assert bts.manifest_id({"manifest.json": "[1]"}) is None
