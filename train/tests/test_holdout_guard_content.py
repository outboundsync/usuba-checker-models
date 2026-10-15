"""Content-based holdout guard (audit A12) on synthetic fixtures: renamed fork, one-char edit, truncated copy, id match, unknown provenance."""
import gzip, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import holdout_guard as G, code_blob as C, prompt_v4 as P

QML = "import QtQuick\nItem {\n  id: root\n" + "".join(f"  property int p{i}: {i} * 3 + root.width\n" for i in range(60)) + "}\n"
MAN = json.dumps({"schemaVersion": 1, "id": "someone.holdout-plugin", "name": "H", "version": "1.0.0", "kinds": ["bar-widget"], "entryPoints": {"barWidget": "W.qml"}})
FILES = {"manifest.json": MAN, "W.qml": QML, "Helper.js": "".join(f"function f{i}(x) {{ return x + {i}; }}\n" for i in range(40))}


def guard(tmp):
    fp = os.path.join(tmp, "fp.json.gz")
    json.dump(dict(holdout=[G.tree_fp(FILES)] + [G.tree_fp({'Z.qml': f'Item {{ property string s{i}: "{i}" }}\n' * 30}) for i in range(299)], manifest_ids=["someone.holdout-plugin"], repos=[], dell_ids=["dell.key-plugin"], dell_trees=[]), gzip.open(fp, "wt"))
    ids = os.path.join(tmp, "ids.txt"); open(ids, "w").write("\n".join(f"https://github.com/o{i}/r{i}" for i in range(329)))
    return G.Guard(fp, ids)


def row(files, repo="someone-else/renamed-copy", kind="version-history-fix", rid=None):
    msgs = P.messages(C.code_blob(files), [], dict(verdict="approve", load="works", findings=[]))
    return dict(id=rid or "x", messages=msgs, provenance=dict(kind=kind, repo=repo))


def test_renamed_fork_is_caught_by_content():
    with tempfile.TemporaryDirectory() as t:
        g = guard(t)
        f2 = dict(FILES, **{"manifest.json": MAN.replace("someone.holdout-plugin", "renamed.plugin")})
        assert g.check_row(row(f2)).startswith("content")


def test_one_character_edit_and_truncated_copy_are_caught():
    with tempfile.TemporaryDirectory() as t:
        g = guard(t)
        f2 = dict(FILES, **{"W.qml": QML.replace("p10: 10", "p10: 11"), "manifest.json": MAN.replace("someone", "x")})
        assert g.check_row(row(f2)).startswith("content")
        f3 = dict(FILES, **{"W.qml": QML[:len(QML) * 3 // 4], "manifest.json": MAN.replace("someone", "x")})
        assert g.check_row(row(f3)).startswith("content")


def test_manifest_id_and_dell_id():
    with tempfile.TemporaryDirectory() as t:
        g = guard(t)
        other = {"manifest.json": MAN, "Z.qml": "Rectangle { color: 'red' }\n" * 20}
        assert g.check_row(row(other)).startswith("manifest_id")
        other["manifest.json"] = MAN.replace("someone.holdout-plugin", "Dell.Key-Plugin")
        assert g.check_row(row(other)).startswith("manifest_id")


def test_unknown_provenance_fails_closed():
    with tempfile.TemporaryDirectory() as t:
        g = guard(t)
        r = row({"manifest.json": "{}", "A.qml": "Item { property int zz: 1234 }\n" * 5}, repo=None, kind="")
        r["provenance"] = {}
        assert g.check_row(r) == "unknown_provenance"
        r["provenance"] = {"kind": "synthetic"}
        assert g.check_row(r) is None


def test_unrelated_plugin_passes():
    with tempfile.TemporaryDirectory() as t:
        g = guard(t)
        assert g.check_row(row({"manifest.json": MAN.replace("someone.holdout-plugin", "ok.one"), "Q.qml": "Text { text: 'unrelated' }\n" * 30})) is None


def test_repo_match_in_id_prefix():
    with tempfile.TemporaryDirectory() as t:
        g = guard(t)
        assert g.check_row(row({"manifest.json": "{}"}, repo="a/b", rid="dell_works_verified:o5/r5:r1")) == "repo:o5/r5"


def test_scaffold_shared_by_many_holdout_plugins_is_not_an_identity_signal():
    with tempfile.TemporaryDirectory() as t:
        fp = os.path.join(t, "fp.json.gz")
        scaffold = {"W.qml": QML}
        json.dump(dict(holdout=[G.tree_fp(scaffold)] * 330, manifest_ids=[], repos=[], dell_ids=[], dell_trees=[]), gzip.open(fp, "wt"))
        ids = os.path.join(t, "ids.txt"); open(ids, "w").write("\n".join(f"https://github.com/o{i}/r{i}" for i in range(329)))
        assert G.Guard(fp, ids).check_row(row(scaffold)) is None
