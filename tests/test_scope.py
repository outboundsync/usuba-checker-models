"""Tests for the Checker model scope code (scope/): schema, post-filter, scorer, prompt, label page. CPU only, no network, no model."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scope import postfilter, prompt_scope, schema  # noqa: E402
from scope import scoring as SC  # noqa: E402
from scope.labelpage import make_label_page as LP  # noqa: E402

FILES = {"Panel.qml": "import QtQuick\nItem {\n  property string k: \"EXAMPLE_VALUE_123\"\n  Process { command: [\"curl\", \"http://x.test/a\"] }\n}\n",
         "manifest.json": "{\"id\": \"acme.panel\"}\n"}
FIND = [dict(rule="USB-Q01", file="Panel.qml", line=2, message="m", stage="static", level="fail"),
        dict(rule="USB-R02", file="Panel.qml", line=0, message="TypeError", stage="runtime", level="fail"),
        dict(rule="USB-W01", file="manifest.json", line=0, message="w", stage="static", level="warn")]


def tri(rule, file, line, decision="confirm", quote="import QtQuick"):
    return dict(rule=rule, file=file, line=line, decision=decision, reason="because", quote=quote)


def add(**kw):
    d = dict(category="url-scheme-network", severity="warning", file="Panel.qml", line=4, quote="http://x.test/a", finding="plain http", fix="use https://x.test/a")
    d.update(kw)
    return d


def good(**kw):
    out = dict(scripts_triage=[tri("USB-Q01", "Panel.qml", 2), tri("USB-R02", "Panel.qml", 0), tri("USB-W01", "manifest.json", 0, quote="acme.panel")],
               added_findings=[add()], verdict="changes_requested")
    out.update(kw)
    return out


# ---- schema ------------------------------------------------------------------------------------------------------------------------------------
def test_valid_answer_passes():
    assert schema.validate(good(), FIND) == []


@pytest.mark.parametrize("mut", [
    lambda o: o.pop("verdict"),
    lambda o: o.update(verdict="maybe"),
    lambda o: o.update(extra=1),
    lambda o: o["added_findings"][0].update(category="load:unknown-type"),
    lambda o: o["added_findings"][0].update(severity="critical"),
    lambda o: o["added_findings"][0].update(line=0),
    lambda o: o["added_findings"][0].pop("fix"),
    lambda o: o["scripts_triage"][0].update(decision="maybe"),
    lambda o: o["scripts_triage"][0].update(reason="two\nlines"),
    lambda o: o["scripts_triage"][0].update(line="2"),
    lambda o: o["scripts_triage"].pop(),
    lambda o: o["scripts_triage"].append(dict(o["scripts_triage"][0])),
    lambda o: o.update(added_findings=[add() for _ in range(9)]),
])
def test_invalid_answers_are_rejected(mut):
    o = good()
    mut(o)
    assert schema.validate(o, FIND)


def test_parse_answer_classifies_invalid_reasons():
    assert schema.parse_answer("ERROR boom")[1] == "error"
    assert schema.parse_answer("SKIPPED max-cost")[1] == "skipped"
    assert schema.parse_answer(json.dumps(good()), FIND, "length")[1] == "truncated"
    assert schema.parse_answer("no json here", FIND)[1] == "unparseable"
    assert schema.parse_answer(json.dumps(good(verdict="x")), FIND)[1].startswith("schema")
    out, why = schema.parse_answer("<think>x</think>```json\n" + json.dumps(good()) + "\n```", FIND)
    assert why is None and out["verdict"] == "changes_requested"


def test_empty_report_requires_empty_triage():
    o = dict(scripts_triage=[], added_findings=[], verdict="approve")
    assert schema.validate(o, []) == []
    assert schema.validate(dict(o, scripts_triage=[tri("X", "a", 1)]), [])


# ---- post-filter -------------------------------------------------------------------------------------------------------------------------------
def test_dismissal_with_ungrounded_quote_reverts_to_confirm():
    o = good()
    o["scripts_triage"][0] = tri("USB-Q01", "Panel.qml", 2, "dismiss", quote="not in the file at all")
    f, st = postfilter.apply(o, FILES, FIND)
    assert f["scripts_triage"][0]["decision"] == "confirm" and st["dismissals_dropped"] == 1


def test_grounded_dismissal_of_static_finding_is_kept():
    o = good()
    o["scripts_triage"][0] = tri("USB-Q01", "Panel.qml", 2, "dismiss", quote="import QtQuick")
    f, st = postfilter.apply(o, FILES, FIND)
    assert f["scripts_triage"][0]["decision"] == "dismiss" and st["dismissals_kept"] == 1


def test_runtime_fail_cannot_be_dismissed_even_with_good_quote():
    o = good()
    o["scripts_triage"][1] = tri("USB-R02", "Panel.qml", 0, "dismiss", quote="import QtQuick")
    f, st = postfilter.apply(o, FILES, FIND)
    assert f["scripts_triage"][1]["decision"] == "confirm" and st["runtime_dismissal_blocked"] == 1


def test_added_finding_filters():
    o = good(added_findings=[
        add(),                                              # kept
        add(quote="this text is not there", line=3),        # ungrounded
        add(file="Missing.qml"),                            # unknown file
        add(line=2, quote="import QtQuick"),                # same (file, line) as a Checker scripts finding
        add(quote="}", line=5),                             # too short to ground anything
        add(),                                              # duplicate of the first added finding
    ])
    f, st = postfilter.apply(o, FILES, FIND)
    assert len(f["added_findings"]) == 1
    assert (st["added_dropped_quote"], st["added_dropped_file"], st["added_dropped_duplicate"]) == (2, 1, 2)


def test_quote_may_carry_line_number_prefix_and_crlf():
    assert postfilter.quote_in_file("   4| http://x.test/a", FILES["Panel.qml"])
    assert postfilter.quote_in_file("import QtQuick", "import QtQuick\r\nItem {}\r\n")


def test_system_verdict_is_the_checker_scripts_verdict():
    f, _ = postfilter.apply(good(verdict="approve"), FILES, FIND)
    assert f["verdict"] == "changes_requested" and f["model_verdict"] == "approve"   # the model cannot flip the System verdict
    f2, _ = postfilter.apply(dict(scripts_triage=[], added_findings=[], verdict="changes_requested"), FILES, [])
    assert f2["verdict"] == "approve"


# ---- scoring -----------------------------------------------------------------------------------------------------------------------------------
def row(plugin, out=None, findings=None, hardware=None, valid=True, invalid_reason=None, secs=1.0):
    findings = FIND if findings is None else findings
    if out is None and valid:
        out = good()
    flt, st = postfilter.apply(out, FILES, findings) if out is not None and valid else (None, None)
    return dict(plugin=plugin, findings=findings, valid=valid and out is not None, invalid_reason=invalid_reason, raw_out=out if valid else None, out=flt, stats=st,
                secs=secs, hardware=hardware)


def test_triage_metrics_invalid_is_wrong_and_never_a_dismissal():
    f1 = [dict(rule="A", file="Panel.qml", line=2, stage="static", level="fail")]
    ok = row("p1", dict(scripts_triage=[tri("A", "Panel.qml", 2, "dismiss")], added_findings=[], verdict="approve"), f1)
    bad = row("p2", valid=False, invalid_reason="unparseable", findings=f1)
    s1 = {"p1|A|Panel.qml|2": "false_alarm", "p2|A|Panel.qml|2": "real"}
    m = SC.triage_metrics([ok, bad], s1)
    assert m["n"] == 2 and m["triage_accuracy"] == 0.5 and m["dismiss_of_real"] == 0.0 and m["n_no_decision"] == 1


def test_m3_counts_dismissal_of_real_after_postfilter():
    f1 = [dict(rule="A", file="Panel.qml", line=2, stage="static", level="fail")]
    r1 = row("p1", dict(scripts_triage=[tri("A", "Panel.qml", 2, "dismiss", quote="import QtQuick")], added_findings=[], verdict="approve"), f1)
    r2 = row("p2", dict(scripts_triage=[tri("A", "Panel.qml", 2, "dismiss", quote="nope nope nope")], added_findings=[], verdict="approve"), f1)
    s1 = {"p1|A|Panel.qml|2": "real", "p2|A|Panel.qml|2": "real"}
    m = SC.triage_metrics([r1, r2], s1)
    assert m["dismiss_of_real"] == 0.5 and m["dismiss_of_real_before_postfilter"] == 1.0


def test_clean_metrics_counts_invalid_as_blocker():
    clean_ok = row("c1", dict(scripts_triage=[], added_findings=[], verdict="approve"), [])
    clean_blk = row("c2", dict(scripts_triage=[], added_findings=[add(severity="blocker")], verdict="changes_requested"), [])
    clean_bad = row("c3", valid=False, invalid_reason="truncated", findings=[])
    m = SC.clean_metrics([clean_ok, clean_blk, clean_bad, row("other")], {"c1", "c2", "c3"})
    assert m["n_clean"] == 3 and m["clean_with_blocker"] == 2 and m["added_per_clean"] == round(2 / 3, 3)


def test_added_precision_excludes_unsure_and_reports_it():
    rows = [row("p%d" % i, dict(scripts_triage=[], added_findings=[add()], verdict="changes_requested"), []) for i in range(4)]
    s3 = {"p0|Panel.qml|4|url-scheme-network": "real", "p1|Panel.qml|4|url-scheme-network": "real", "p2|Panel.qml|4|url-scheme-network": "not_real",
          "p3|Panel.qml|4|url-scheme-network": "unsure"}
    m = SC.added_precision(rows, s3)
    assert (m["real"], m["not_real"], m["unsure"], m["precision"]) == (2, 1, 1, 0.667)
    assert m["precision_wilson"][0] < 0.667 < m["precision_wilson"][1]


def test_wilson_known_value():
    lo, hi = SC.wilson(60, 100)
    assert abs(lo - 0.502) < 0.002 and abs(hi - 0.691) < 0.002


def test_gate_report_never_passes_below_minimum_set_size():
    a = dict(precision=0.9, precision_ci95=[0.8, 0.95], n_adjudicated=20)
    g = SC.gate_report(dict(added=a), dict(S3=20))
    assert g["M1"]["status"] == "provisional-pass"
    g2 = SC.gate_report(dict(added=a), dict(S3=100))
    assert g2["M1"]["status"] == "pass"
    g3 = SC.gate_report(dict(added=dict(a, precision_ci95=[0.4, 0.95])), dict(S3=100))
    assert g3["M1"]["status"] == "fail"
    assert SC.gate_report({}, {})["M2"]["status"] == "not measurable"


def test_tracked_and_practical_run():
    rows = [row("p1"), row("p2", valid=False, invalid_reason="schema: x")]
    t = SC.tracked(rows)
    assert t["T1_n_added_raw"] == 1 and t["T2_line_accuracy_of_kept"] == 1.0
    p = SC.practical(rows)
    assert p["schema_valid"] == 0.5 and p["invalid_reasons"] == {"schema": 1}


def test_verdict_metrics_use_shared_scorer():
    try:
        SC.load_shared()
    except FileNotFoundError:
        pytest.skip("usuba-checker-scripts sibling checkout not available")
    rows = [row("w", hardware="works"), row("b", hardware="broken"), row("x", valid=False, hardware="works", invalid_reason="error")]
    m = SC.verdict_metrics(rows)
    assert m["n"] == 3 and m["n_invalid"] == 1 and m["negative_correct_approve"] == 0.0   # model said changes_requested on the clean plugin; invalid is not an approval


def test_paired_cluster_diff_detects_a_difference():
    f1 = [dict(rule="A", file="Panel.qml", line=2, stage="static", level="fail")]
    good_rows = [row("p%d" % i, dict(scripts_triage=[tri("A", "Panel.qml", 2)], added_findings=[], verdict="changes_requested"), f1) for i in range(20)]
    bad_rows = [row("p%d" % i, valid=False, invalid_reason="error", findings=f1) for i in range(20)]
    s1 = {"p%d|A|Panel.qml|2" % i: "real" for i in range(20)}
    d = SC.paired_triage_diff(good_rows, bad_rows, s1, n_boot=200)
    assert d["diff"] == 1.0 and d["excludes_zero"]


# ---- prompt ------------------------------------------------------------------------------------------------------------------------------------
def _need_renderer():
    try:
        prompt_scope.code_blob_module()
    except (ImportError, FileNotFoundError):
        pytest.skip("usuba-checker-scripts (code_blob renderer) not available")


def test_prompt_uses_exact_terms_and_schema_and_is_stable():
    _need_renderer()
    s = prompt_scope.SYSTEM
    assert "Checker scripts" in s and "scripts_triage" in s and "added_findings" in s
    for c in schema.ADDED_CATEGORIES:
        assert c in s
    m = prompt_scope.messages(prompt_scope.render_files(FILES), FIND)
    assert [x["role"] for x in m] == ["system", "user"]
    assert "   2| Item {" in m[1]["content"] or "2| Item {" in m[1]["content"]
    assert "rule=USB-R02 stage=runtime level=fail" in m[1]["content"]
    assert prompt_scope.messages("c", [])[1]["content"].startswith("## Checker scripts report\n(no Checker scripts findings)")
    assert len(prompt_scope.PROMPT_SHA256) == 64


# ---- label page --------------------------------------------------------------------------------------------------------------------------------
def test_sample_batches_build_offline_pages():
    d = os.path.join(ROOT, "scope", "labelpage")
    for fn in ("sample_batch.json", "sample_batch_added.json"):
        b = json.load(open(os.path.join(d, fn)))
        html = LP.build(b)
        assert "<script src" not in html and "<link" not in html and "fetch(" not in html and "XMLHttpRequest" not in html
        assert b["items"][0]["id"] in html


def test_label_page_rejects_bad_batches_and_escapes_script_end():
    item = dict(id="a", plugin="p", file="f", line=2, explanation="e </script><b>x", claim="c", snippet=dict(start=1, lines=["a", "b", "c"]))
    html = LP.build(dict(batch_id="b", set="S1", kind="checker", items=[item]))
    assert html.count("</script>") == 2   # the data block and the code block only; the injected one is escaped
    with pytest.raises(ValueError):
        LP.build(dict(batch_id="b", set="S1", kind="checker", items=[dict(item, line=9)]))
    with pytest.raises(ValueError):
        LP.build(dict(batch_id="b", set="S1", kind="checker", items=[item, item]))
