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


# ---- r6: per-file fuzzy (J >= 0.5), same-name and same-author checks
def guard_meta(tmp, holdout_repo="alice/omarchy-glow-widget", mid="alice.glow-widget", allow=None):
    fp = os.path.join(tmp, "fp.json.gz")
    others = [G.tree_fp({'Z.qml': f'Item {{ property string s{i}: "{i}" }}\n' * 30}) for i in range(299)]
    json.dump(dict(holdout=[G.tree_fp(FILES)] + others, manifest_ids=[mid], repos=[], dell_ids=["dell.key-plugin"], dell_trees=[],
                   holdout_meta=[dict(repo=holdout_repo, mid=mid)] + [dict(repo=f"o{i}/r{i}", mid=None) for i in range(299)], dell_meta=[]), gzip.open(fp, "wt"))
    ids = os.path.join(tmp, "ids.txt"); open(ids, "w").write("\n".join(f"https://github.com/o{i}/r{i}" for i in range(329)))
    al = os.path.join(tmp, "allow.json"); json.dump(dict(pairs=allow or []), open(al, "w"))
    old = G.ALLOW; G.ALLOW = al
    try: g = G.Guard(fp, ids); g.allow = G.load_allow(al)
    finally: G.ALLOW = old
    return g


def half_edit(text):
    """a copy that shares about 60% of its 5-token shingles with the original: every 5th line rewritten"""
    return "\n".join(l if i % 5 else l.replace("root.width", f"root.height + {i}").replace("* 3", f"* {i + 7}") for i, l in enumerate(text.split("\n")))


def test_single_file_at_jaccard_half_is_rejected_even_when_other_files_differ():
    with tempfile.TemporaryDirectory() as t:
        g = guard_meta(t)
        big = {"manifest.json": MAN.replace("someone", "x"), "W.qml": half_edit(QML),
               "A.qml": "".join(f"Rectangle {{ id: r{i}; width: {i}; color: \"#{i:06x}\" }}\n" for i in range(80)),
               "B.js": "".join(f"function g{i}(a) {{ return a * {i} + 1; }}\n" for i in range(80))}
        j = G.jaccard(G.sketch(QML), G.sketch(big["W.qml"]))
        assert 0.5 <= j < 0.95, j
        why = g.check_row(row(big, repo="bob/unrelated-thing"))
        assert why and why.startswith(("file:", "content:")), why


def test_unrelated_files_pass():
    with tempfile.TemporaryDirectory() as t:
        g = guard_meta(t)
        f = {"manifest.json": MAN.replace("someone", "x"), "A.qml": "".join(f"Rectangle {{ id: r{i}; width: {i}; color: \"#{i:06x}\" }}\n" for i in range(80))}
        assert g.check_row(row(f, repo="bob/unrelated-thing")) is None


def test_same_name_rejected_unless_allow_listed_and_short_names_ignored():
    f = {"manifest.json": MAN.replace("someone.holdout-plugin", "bob.other"), "A.qml": "".join(f"Rectangle {{ id: r{i}; width: {i} }}\n" for i in range(80))}
    with tempfile.TemporaryDirectory() as t:
        g = guard_meta(t)
        assert g.check_row(row(f, repo="bob/omarchy-glow-widget")).startswith("same_name:")      # same repo name, different owner, different code
        assert g.check_row(row(f, repo="bob/glow-widget")).startswith("same_name:")              # 'omarchy-' prefix is normalised away
        assert g.check_row(row(f, repo="bob/other-thing")) is None
    with tempfile.TemporaryDirectory() as t:
        g = guard_meta(t, allow=[dict(repo="bob/omarchy-glow-widget", holdout_repo="alice/omarchy-glow-widget")])
        assert g.check_row(row(f, repo="bob/omarchy-glow-widget")) is None                        # reviewed pair
    with tempfile.TemporaryDirectory() as t:
        g = guard_meta(t, holdout_repo="alice/bar", mid="alice.bar")
        assert g.check_row(row(f, repo="bob/bar")) is None                                        # generic short name is not an identity


def test_same_author_uses_the_lower_threshold():
    with tempfile.TemporaryDirectory() as t:
        g = guard_meta(t)
        lo = "\n".join(l if i % 2 else l.replace("root.width", f"root.height + {i}").replace("* 3", f"* {i + 7}") for i, l in enumerate(QML.split("\n")))
        j = G.jaccard(G.sketch(QML), G.sketch(lo))
        assert 0.25 < j < 0.5, j                                                                  # below the 0.5 per-file rule, above the same-author 0.3
        f = {"manifest.json": MAN.replace("someone", "x"), "W.qml": lo}
        assert g.check_row(row(f, repo="bob/unrelated-thing")) is None                            # a stranger is fine at this similarity
        why = g.check_row(row(f, repo="alice/some-other-plugin"))                                 # the holdout plugin's own author is not
        assert why and why.startswith("same_author:"), why
