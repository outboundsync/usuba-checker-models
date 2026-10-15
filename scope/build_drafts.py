#!/usr/bin/env python3
"""Candidate S1 / S2 / S4 DRAFT label sets for the Checker model scope, built from data that exists today.

EVERYTHING written here is DRAFT / provisional: machine-derived, not hand-labelled, NOT used for training, and written outside git (default $USUBA_RUNS/scope-v4/drafts)
because it is derived from the sealed Dell key and from mined upstream data. Only this script and aggregate counts are committed.

  python3 -m scope.build_drafts dell    # S1 + S2 drafts from the Dell hardware key vs the Checker scripts report (static stage only)
  python3 -m scope.build_drafts s4      # S4 draft from version-history fix commits (needs network: shallow fetch of public parent commits)

S1 draft (hardware-observable false alarms):  hardware WORKS + a fail-level Checker scripts finding  ->  label false_alarm (the plugin runs on hardware, so "blocks the plugin" is false).
   hardware BROKEN + fail-level finding whose file the key's reason names  ->  label real (draft; the key reason is the only evidence).  Everything else is left unlabelled.
S2 draft:  hardware WORKS + the Checker scripts report has no fail-level finding. ``hand_reviewed`` is false for every row until a human reviews it.
S4 draft:  version-history verified pairs (public MIT/Apache upstream commits); the pre-fix line is quoted from the PARENT commit and checked mechanically (``quote_verified``).
   It is a deterministic repo-disjoint hold-out subset: ``S4_EXCLUDE_REPOS.txt`` lists the repos the training builders must exclude.
Never writes into train/, never touches the sealed Dell key or the HANCORE holdout beyond reading them.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

RUNS = os.environ.get("USUBA_RUNS", "/workspace/usuba-runs")
OUT = os.environ.get("SCOPE_DRAFTS", os.path.join(RUNS, "scope-v4", "drafts"))
DELL_ROOT = os.environ.get("USUBA_DELL_ROOT", "/workspace/wt-retrain-v2")
DELL_KEY = os.environ.get("USUBA_DELL_KEY", os.path.join(DELL_ROOT, "functest", "dell_ground_truth.jsonl"))
VH = os.environ.get("USUBA_VH_DATA", os.path.join(RUNS, "version-history", "data"))
EXCLUDE_ID_PREFIX = ("b3.opus55.",)   # Claude-written plugins are excluded from the key (docs/ANTHROPIC_TERMS_COMPLIANCE.md)


def dump(name, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def build_dell():
    from scope import checker_findings as CF   # puts the Checker's functest dir on sys.path
    import functest as FT
    plugins, s1, s2, cands, stats = [], {}, [], [], dict(plugins=0, missing_dir=0, findings_fail=0, findings_warn=0)
    for line in open(DELL_KEY):
        g = json.loads(line)
        if g["real_verdict"] not in ("WORKS", "BROKEN") or g["id"].startswith(EXCLUDE_ID_PREFIX):
            continue
        d = os.path.join(DELL_ROOT, g["path"])
        if not os.path.isdir(d):
            stats["missing_dir"] += 1
            continue
        files = {p: c for p, c in FT.read_dir(d).items() if p not in ("SOURCE.txt", "checklist.md")}
        fs = CF.findings_for(files)
        hw = "works" if g["real_verdict"] == "WORKS" else "broken"
        plugins.append(dict(plugin=g["id"], set="dell-key", hardware=hw, findings=fs, files=files, key_reason=g["reason"] if hw == "broken" else None))
        stats["plugins"] += 1
        fails = [f for f in (fs or []) if f["level"] == "fail"]
        stats["findings_fail"] += len(fails)
        stats["findings_warn"] += len([f for f in (fs or []) if f["level"] != "fail"])
        if hw == "works":   # warn-level findings are not labelled automatically (a warning can be a real quality issue); they are the queue for the human labelling page
            cands += [dict(key="%s|%s|%s|%s" % (g["id"], f["rule"], f["file"], f["line"]), label=None, basis="unlabelled: hardware-works plugin, warn-level finding")
                      for f in (fs or []) if f["level"] != "fail"]
        for f in fails:
            k = "%s|%s|%s|%s" % (g["id"], f["rule"], f["file"], f["line"])
            if hw == "works":
                s1[k] = dict(label="false_alarm", basis="hardware-works")
            elif os.path.basename(f["file"]) in g["reason"]:
                s1[k] = dict(label="real", basis="key-reason-names-file")
        if hw == "works" and fs is not None and not fails:
            s2.append(dict(plugin=g["id"], hand_reviewed=False, checker_warns=len(fs)))
    dump("dell_plugins.jsonl", plugins)
    dump("S1_draft.jsonl", [dict(key=k, **v) for k, v in sorted(s1.items())])
    dump("S2_draft.jsonl", s2)
    dump("S1_candidates_unlabelled.jsonl", cands)
    stats.update(S1_false_alarm=sum(v["label"] == "false_alarm" for v in s1.values()), S1_real=sum(v["label"] == "real" for v in s1.values()),
                 S2_clean=len(s2), S1_unlabelled_candidates=len(cands), status="DRAFT, provisional, not hand-labelled, not for training")
    return stats


def _git(args, cwd, timeout=120):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False,
                          env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))


def _fetch_tree(url, sha, dest):
    """Shallow-fetch one public commit into ``dest``; returns {path: text} of small text files, or None."""
    if not url.startswith("https://github.com/"):
        return None
    _git(["init", "-q"], dest)
    r = _git(["fetch", "-q", "--depth", "1", url + ".git", sha], dest)
    if r.returncode:
        return None
    ls = _git(["ls-tree", "-r", "-z", "--long", "FETCH_HEAD"], dest).stdout.split("\0")
    files = {}
    for ent in ls:
        if not ent:
            continue
        meta, path = ent.split("\t", 1)
        size = meta.split()[3]
        if size.isdigit() and int(size) < 200_000 and path.endswith((".qml", ".js", ".sh", ".py", ".json", ".md", ".lua", ".toml", ".txt")):
            b = subprocess.run(["git", "show", "FETCH_HEAD:" + path], cwd=dest, capture_output=True, check=False, timeout=60).stdout
            try:
                files[path] = b.decode("utf-8")
            except UnicodeDecodeError:
                continue
    return files


def build_s4(max_n=60):
    pairs = []
    for fn in ("verified_pairs.jsonl", "verified_pairs_2.jsonl"):
        pairs += [json.loads(line) for line in open(os.path.join(VH, fn))]
    cand = [p for p in pairs if p["license"] in ("MIT", "Apache-2.0", "ISC", "BSD") and p["confidence"] >= 0.9 and p["file"].endswith((".qml", ".js", ".sh", ".py"))
            and len(p["pre_fix_line_text"].strip()) >= 12]
    cand.sort(key=lambda p: hashlib.sha256(("s4-draft|" + p["repo"]).encode()).hexdigest())   # deterministic, repo-disjoint selection
    seen, rows, plugins, tried = set(), [], [], 0
    for p in cand:
        if p["repo"] in seen:
            continue
        if len(rows) >= max_n or tried >= max_n * 3:
            break
        seen.add(p["repo"])
        tried += 1
        with tempfile.TemporaryDirectory() as td:
            files = _fetch_tree(p["url"], p["parent"], td)
        if not files or p["file"] not in files or not (1 <= p["pre_fix_line"] <= len(files[p["file"]].split("\n"))):
            continue
        lines = files[p["file"]].split("\n")
        ok = lines[p["pre_fix_line"] - 1].strip() == p["pre_fix_line_text"].strip()
        if not ok:
            continue
        pid = "%s@%s" % (p["repo"], p["parent"][:12])
        rows.append(dict(plugin=pid, file=p["file"], line=p["pre_fix_line"], quote=p["pre_fix_line_text"].strip(), bug_kind=p["bug_kind"], defect=p["defect"],
                         fix_commit=p["commit"], fix_added=p["added"], license=p["license"], quote_verified=True, hand_verified=False))
        plugins.append(dict(plugin=pid, set="s4-draft", hardware=None, files=files))
    dump("S4_draft.jsonl", rows)
    dump("s4_plugins.jsonl", plugins)
    with open(os.path.join(OUT, "S4_EXCLUDE_REPOS.txt"), "w") as f:
        f.write("\n".join(sorted(seen)) + "\n")
    return dict(S4_rows=len(rows), repos_tried=tried, status="DRAFT, provisional: pre-fix line verified in the parent commit, bug NOT hand-verified; repos listed in S4_EXCLUDE_REPOS.txt must not be trained on")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("dell", "s4"):
        sys.exit(__doc__)
    st = build_dell() if sys.argv[1] == "dell" else build_s4()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "stats_%s.json" % sys.argv[1]), "w") as f:
        json.dump(st, f, indent=1)
    print(json.dumps(st, indent=1))


if __name__ == "__main__":
    main()
