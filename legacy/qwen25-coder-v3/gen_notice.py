"""Append a v3 training-data attribution section to NOTICE: Omarchy (first-party + builtin catalog snapshot) and every
registry repo that has at least one row in v3/train_v3.jsonl, with commit, verified license and copyright line."""
import json, re, collections
R = "/workspace/omarchy-specialist/"
M = [m for m in json.load(open(R + "v3/train_v3_manifest.json")) if not m["excluded"]]
cr = {}
for l in open(R + "clean/registry/scan.jsonl"):
    r = json.loads(l); c = r.get("copyright") or []
    if c: cr[r["repo"].rstrip("/").lower()] = "; ".join(c) if isinstance(c, list) else c
NOTICE_TXT = open(R + "NOTICE").read().split("\n## v3 training set")[0].rstrip("\n") + "\n"; open(R + "NOTICE", "w").write(NOTICE_TXT)
for l in NOTICE_TXT.splitlines():
    m = re.match(r"- (\S+/\S+) @ \S+ — \S+ — (Copyright.*)", l.strip())
    if m: cr.setdefault("https://github.com/" + m.group(1).lower(), m.group(2))
src = collections.OrderedDict(); n = collections.Counter()
for m in M:
    repo = (m["repo"] or "").rstrip("/")
    if "basecamp/omarchy" in repo or "omacom/omarchy" in repo: n["omarchy"] += 1; continue
    p = m["provenance"]; mm = re.search(r"\((Copyright[^)]*)\)", p)
    src.setdefault(repo, [m["commit"], m["license"], mm.group(1) if mm else cr.get(repo.lower(), "")]); n[repo] += 1
miss = [r for r, v in src.items() if not v[2]]
assert not miss, miss
lines = ["", "## v3 training set (v3/train_v3.jsonl, 2026-10-12)", "",
 "Every row's provenance is in v3/train_v3_manifest.json. All code is merged upstream (Omarchy) or from a verified listing",
 "in the official Omarchy plugin registry (plugins.omarchy.org), at the listing's validated commit, LICENSE file read at that commit.", "",
 f"- Omarchy — basecamp/omarchy (now omacom/omarchy) @ 9480d1b6a98156314dbabe6bfef08f39f8b9cd07 — MIT — Copyright (c) David Heinemeier Hansson ({n['omarchy']} rows).",
 "  Built-in plugins (6 Omarchy built-ins, ids re-namespaced acme.*, 2 phrasings each): basecamp/omarchy @ c668141e9c42b13c80c9ca4ea108e11708c5e8a5",
 "  (shell/ byte-identical to the Omarchy 4.0.4-1 package on the reference laptop) — MIT — Copyright (c) David Heinemeier Hansson.",
 "  Built-in list from the plugins.omarchy.org catalog (sourceType=builtin).",
 "- Omarchy plugin registry: https://plugins.omarchy.org (catalog.json snapshot clean/registry/catalog_live.json). Registry repos used:"]
for repo, (c, lic, cp) in sorted(src.items(), key=lambda x: x[0].lower()):
    lines.append(f"  - {repo.replace('https://github.com/', '')} @ {c} — {lic} — {cp} ({n[repo]} rows)")
open(R + "NOTICE", "a").write("\n".join(lines) + "\n")
print(len(src), "registry repos;", n["omarchy"], "omarchy rows")
