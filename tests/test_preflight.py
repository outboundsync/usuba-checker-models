import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import preflight as P  # noqa: E402


def test_detects_the_cancelling_loss_in_code_not_in_docstrings():
    bad = "def f(per, w):\n    return (per * w).sum() / w.sum()\n"
    good = 'def f(per, w, n):\n    """the old (per*w).sum()/w.sum() cancelled"""\n    return (per * w).sum() / n\n'
    assert P._has_cancelling_loss(bad) and not P._has_cancelling_loss(good)


def test_final_answer_is_last_assistant_json():
    row = {"messages": [{"role": "assistant", "content": '{"verdict": "approve"}'}, {"role": "user", "content": "x"},
                        {"role": "assistant", "content": '{"verdict": "changes_requested"}'}]}
    assert P.final_answer(row)["verdict"] == "changes_requested"
    assert P.final_answer({"messages": [{"role": "assistant", "content": "not json"}]}) == {}


def test_all_17_items_registered_and_a_crashing_item_is_a_fail_not_a_skip(tmp_path):
    assert [n for n, _, _ in P.ITEMS] == list(range(1, 18))
    c = P.Ctx()
    c.data, c.scripts, c.min_checker = str(tmp_path / "nope"), str(tmp_path / "nope"), "0000000"
    res = P.run(c)
    assert len(res) == 17 and all(r["status"] in (P.PASS, P.WARN, P.FAIL, P.SKIP) for r in res)
    assert all(r["status"] == P.FAIL for r in res if r["item"] in (1, 2, 3, 4, 5, 6))   # missing data/scripts: never a pass


def test_cli_exit_code_nonzero_when_anything_fails(tmp_path):
    assert P.main(["--data", str(tmp_path / "nope"), "--scripts", str(tmp_path / "nope")]) == 1
