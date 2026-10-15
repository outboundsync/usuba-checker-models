#!/usr/bin/env python3
"""Keep NOTICE complete for everything that ships (audit F1).

The shipped set is the union of repos in the in-repo manifests (legacy/clean/train_final, pool_registry (kept), pool_chunked (not excluded),
legacy/qwen25-coder-v3/train_v3 (not excluded)) and in any `--rows FILE.jsonl[.gz]` you pass for dataset files that live only on Hugging Face (rows carry meta.repo / meta.license).
Modes:
  --check   exit 1 if a shipped repo has no NOTICE line, if a NOTICE line carries Apache boilerplate or a truncated copyright, or if NOTICE still claims "all are MIT".
            Known unresolved copyright lines are listed in sources/notice_known_gaps.txt (a ratchet: it may only shrink).
  --write   regenerate: fix the header, repair boilerplate lines, and rewrite the GENERATED section (repos missing from the hand-written part).
A copyright line that cannot be recovered from the manifests or legacy/clean/registry/scan.jsonl is written as "copyright line not extracted; see LICENSE at repo@commit"
instead of being cut off. This does not replace counsel review of the attribution approach before upload.
"""
import collections
import gzip
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTICE = os.path.join(ROOT, "NOTICE")
GAPS = os.path.join(ROOT, "sources", "notice_known_gaps.txt")
G_BEGIN = "## GENERATED: repos present in shipped data and not listed above (tools/gen_notice.py; do not edit by hand)"
UNRESOLVED = "copyright line not extracted; see LICENSE at repo@commit"
LINE = re.compile(r"(?m)^(\s*)-\s+([\w.\-]+/[\w.\-]+) @ (\w+) — ([\w.\-]+) — (.*?)(?: \((\d+) rows\))?$")


def norm(u):
    return re.sub(r"^https?://github\.com/", "", (u or "").strip().rstrip("/")).removesuffix(".git").lower()


def jload(p):
    with open(os.path.join(ROOT, p)) as f:
        return json.load(f)


def shipped(extra_rows=()):
    """repo(normalised) -> dict(repo, commit, license, copyright)"""
    out = {}
    scan = {}
    p = os.path.join(ROOT, "clean", "registry", "scan.jsonl")
    if os.path.exists(p):
        for line in open(p):
            r = json.loads(line)
            scan[norm(r["repo"])] = r

    def put(repo, commit, lic, cr):
        k = norm(repo)
        if not k:
            return
        e = out.setdefault(k, {"repo": k, "commit": commit, "license": lic, "copyright": None})
        c = cr or (scan.get(k) or {}).get("copyright")
        c = "; ".join(c) if isinstance(c, list) else c
        if c and not e["copyright"]:
            e["copyright"] = c

    for r in jload("legacy/clean/train_final_manifest.json"):
        put(r.get("repo"), r.get("commit"), r.get("license"), None)
    for r in jload("legacy/clean/pool_registry_manifest.json"):
        if r.get("kept"):
            put(r.get("repo"), r.get("commit"), r.get("license"), r.get("copyright"))
    for r in jload("legacy/clean/pool_chunked_manifest.json"):
        if not r.get("excluded"):
            put(r.get("repo"), r.get("commit"), r.get("license"), r.get("copyright"))
    for r in jload("legacy/qwen25-coder-v3/train_v3_manifest.json"):
        if not r.get("excluded"):
            put(r.get("repo"), r.get("commit"), r.get("license"), None)
    for path in extra_rows:
        op = gzip.open if path.endswith(".gz") else open
        with op(path, "rt") as f:
            for line in f:
                m = (json.loads(line).get("meta") or {})
                put(m.get("repo") or m.get("repo_url"), m.get("commit"), m.get("license"), m.get("copyright"))
    return out


def bad_copyright(c):
    c = (c or "").strip()
    return (not c or c.lower().startswith("copyright license") or c.startswith("(c) You") or re.fullmatch(r"Copyright \(c?\)?", c) is not None
            or c.endswith("(c") or c.endswith("(C") or c.lower() in ("copyright", "copyright (c)"))


def split_notice(text):
    return text.split(G_BEGIN)[0].rstrip("\n") + "\n"


def listed(text):
    return {m.group(2).lower(): m for m in LINE.finditer(text)}


def gaps():
    if not os.path.exists(GAPS):
        return set()
    return {ln.strip().lower() for ln in open(GAPS) if ln.strip() and not ln.startswith("#")}


def problems(text, ship):
    head = split_notice(text)
    out = []
    ls = listed(text)
    if re.search(r"all are MIT", head):
        out.append('NOTICE header still says "all are MIT"')
    for repo in sorted(ship):
        if repo not in ls:
            out.append("missing from NOTICE: " + repo)
    bad = [r for r, m in ls.items() if bad_copyright(m.group(5)) and r not in gaps()]
    out += ["unresolved copyright (not in notice_known_gaps.txt): " + r for r in sorted(bad)]
    return out


def write(text, ship):
    head = split_notice(text)
    lic = collections.Counter(e["license"] or "unknown" for e in ship.values())
    summ = "Licences of the third-party plugin sources that ship (by repo): " + ", ".join("%s %d" % kv for kv in sorted(lic.items())) + \
        ". Texts: sources/licenses/ (per repo where kept; Apache-2.0.txt is the standard text that Apache-2.0 sources require us to carry)."
    head = re.sub(r"Every source's LICENSE file was read at the pinned commit; all are MIT\.", "Every source's LICENSE file was read at the pinned commit. " + summ, head)
    ls = listed(head)
    unresolved = set()

    def fix(m):
        if bad_copyright(m.group(5)):
            repo = m.group(2).lower()
            e = ship.get(repo)
            c = (e or {}).get("copyright")
            if bad_copyright(c):
                c = UNRESOLVED
                unresolved.add(repo)
            rows = " (%s rows)" % m.group(6) if m.group(6) else ""
            return "%s- %s @ %s — %s — %s%s" % (m.group(1), m.group(2), m.group(3), m.group(4), c, rows)
        return m.group(0)

    head = LINE.sub(fix, head)
    ls = listed(head)
    missing = sorted(r for r in ship if r not in ls)
    gen = [G_BEGIN, ""]
    for r in missing:
        e = ship[r]
        c = e["copyright"]
        if bad_copyright(c):
            c, _ = UNRESOLVED, unresolved.add(r)
        gen.append("- %s @ %s — %s — %s" % (e["repo"] if "/" in e["repo"] else r, e["commit"] or "unknown", e["license"] or "unknown", c))
    body = head + "\n" + "\n".join(gen) + "\n"
    still = {r for r, m in listed(body).items() if UNRESOLVED in m.group(5) or bad_copyright(m.group(5))}
    return body, sorted(still)


if __name__ == "__main__":
    args = sys.argv[1:]
    extra = [args[i + 1] for i, a in enumerate(args) if a == "--rows"]
    ship = shipped(extra)
    text = open(NOTICE).read()
    if "--write" in args:
        new, still = write(text, ship)
        open(NOTICE, "w").write(new)
        with open(GAPS, "w") as f:
            f.write("# repos whose copyright line could not be recovered from manifests/scan.jsonl; read the LICENSE at the pinned commit. May only shrink.\n")
            f.write("\n".join(still) + "\n")
        print("NOTICE written: %d shipped repos, %d unresolved copyright lines" % (len(ship), len(still)))
    else:
        probs = problems(text, ship)
        for p in probs[:40]:
            print(p)
        if probs:
            sys.exit("NOTICE check failed (%d problems); run python3 tools/gen_notice.py --write" % len(probs))
        print("NOTICE complete for %d shipped repos" % len(ship))
