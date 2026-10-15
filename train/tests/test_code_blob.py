"""code_blob (audit A1): label-independent rendering, explicit truncation markers, line numbers, visibility info."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import code_blob as C

BIG = "\n".join(f"line {i} = {'x' * 40}" for i in range(1, 1000))   # ~46k chars


def test_order_and_caps_independent_of_which_file_is_buggy():
    files = {"manifest.json": "{}\n", "b.qml": BIG, "a.qml": "Item {}\n", "README.md": "hi\n"}
    # there is no 'cited' argument at all: the same files always give the same blob
    assert C.code_blob(files) == C.code_blob(dict(reversed(list(files.items()))))
    blob, info = C.render(files)
    assert blob.index("### manifest.json") < blob.index("### a.qml") < blob.index("### b.qml") < blob.index("### README.md")


def test_truncation_marker_and_visible_lines():
    blob, info = C.render({"manifest.json": "{}\n", "x.qml": BIG})
    assert info["x.qml"]["truncated"] and 0 < info["x.qml"]["shown"] < info["x.qml"]["lines"]
    n = info["x.qml"]["shown"]
    assert f"(truncated: showing lines 1-{n} of {info['x.qml']['lines']}" in blob
    assert C.line_visible(info, "x.qml", n) and not C.line_visible(info, "x.qml", n + 1)


def test_every_shown_line_is_numbered_from_one():
    blob = C.code_blob({"a.qml": "alpha\nbeta\n"})
    assert "   1| alpha\n   2| beta\n   3| \n" in blob


def test_budget_omits_files_deterministically_not_the_manifest():
    files = {"manifest.json": "{}\n"} | {f"f{i}.qml": "y" * 11000 for i in range(8)}
    blob, info = C.render(files)
    assert not info["manifest.json"]["omitted"]
    assert [p for p, i in info.items() if i["omitted"]] == sorted(p for p in files if p.startswith("f"))[3:]
    assert "(omitted: 11000 chars" in blob


def test_no_truncation_marker_for_short_files():
    blob, info = C.render({"a.qml": "x\n" * 10})
    assert "truncated" not in blob and not info["a.qml"]["truncated"]


def test_crlf_and_lf_render_identically():
    assert C.code_blob({"a.qml": "x\r\ny\r\n"}) == C.code_blob({"a.qml": "x\ny\n"})
