#!/usr/bin/env python3
"""Fetch the third-party plugin source trees listed in sources/plugin_sources.json at their pinned commits.

    python3 sources/fetch_plugin_sources.py [--out sources/repos] [--only ID ...] [--jobs 4]

Each repo is fetched shallowly at the exact commit SHA, the HEAD SHA is verified, and a LICENSE/COPYING file must exist
(the manifest only lists repos that had one at that commit). Nothing here needs credentials; it uses public git clones.
Fetched trees keep their own licences; they are never committed to this repository (see .gitignore).
"""
import argparse, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))


def fetch(p, out):
    d = os.path.join(out, p["id"])
    if os.path.isdir(os.path.join(d, ".git")):
        head = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head == p["commit"]:
            return p["id"], "ok (cached)"
    os.makedirs(d, exist_ok=True)
    run = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=300)
    run("init", "-q")
    run("remote", "remove", "origin")
    run("remote", "add", "origin", p["repo"])
    r = run("fetch", "-q", "--depth", "1", "origin", p["commit"])
    if r.returncode:
        return p["id"], "FAIL fetch: " + r.stderr.strip()[:120]
    run("checkout", "-q", "FETCH_HEAD")
    head = run("rev-parse", "HEAD").stdout.strip()
    if head != p["commit"]:
        return p["id"], "FAIL sha mismatch"
    if not any(os.path.exists(os.path.join(d, n)) for n in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "license")):
        return p["id"], "WARN no LICENSE file at this commit"
    return p["id"], "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(HERE, "plugin_sources.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "repos"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    plugins = json.load(open(a.manifest))["plugins"]
    if a.only:
        plugins = [p for p in plugins if p["id"] in set(a.only)]
    os.makedirs(a.out, exist_ok=True)
    bad = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for pid, st in ex.map(lambda p: fetch(p, a.out), plugins):
            print(f"{pid}: {st}")
            bad += st.startswith("FAIL")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
