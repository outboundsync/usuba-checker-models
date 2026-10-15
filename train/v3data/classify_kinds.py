#!/usr/bin/env python3
"""Stage 3: independent bug-kind classification of every HANCORE finding from its prose alone (assigned kind never shown), 3 votes with shuffled category order.
usage: classify_kinds.py before|after  (after = re-run on the refined rows with fresh seeds; reads /workspace/r2/out/refined_hancore.json)"""
import sys, json, random, collections, hashlib
from concurrent.futures import ThreadPoolExecutor
sys.path[:0] = ["/workspace/r2", "/workspace/wt-retrain-v2/train/v3data"]
import llm
from common import load_rows, target
KINDS = {
 "unbounded-input-resource": "reads a whole remote response, shared/predictable-path file or process output with no byte/size cap (memory/CPU exhaustion)",
 "process-lifecycle-timeouts": "no deadline/timeout/teardown: hangs, leaked or orphaned child processes, PID reuse, stuck polls",
 "file-safety-symlink-perms": "predictable /tmp or world-writable paths, symlink-following or truncating writes, loose permissions, non-atomic writes, clobbering user files",
 "secrets-credentials": "tokens, passwords, API keys or phrases in argv, logs, world-readable files or otherwise exposed",
 "privileged-system": "sudo/pkexec/polkit/systemd/udev/etc changes or privileged helpers beyond what is documented",
 "remote-code-pinning": "downloads or installs and runs remote code, unpinned dependencies/images/releases, no checksum or signature",
 "rich-text-markup-injection": "untrusted text rendered as rich text / AutoText / StyledText / HTML / markdown",
 "shell-lua-injection": "variables interpolated into sh -c / bash -c / Lua strings / command lines; argument injection",
 "url-scheme-network": "unvalidated URL schemes passed to xdg-open, plain http, redirect/host/SSRF trust problems",
 "install-deps-packaging": "installer/uninstaller scripts, missing or undeclared dependencies, packaging",
 "user-config-modification": "rewrites or modifies the user's own config/dotfiles/settings without consent, backup or safe handling",
 "listing-metadata-docs": "manifest, README, license, listing metadata or documentation problems (including instructions embedded in docs)",
 "runtime-qml-api-compat": "QML/Quickshell API misuse, deprecated or incompatible API, runtime compatibility"}
SYS = "You classify one code-review finding about an Omarchy/Quickshell plugin into exactly one bug kind: the PRIMARY problem the finding describes. Reply JSON only: {\"kind\": \"<one of the listed kinds>\"}"
def classify(text, seed):
    ks = list(KINDS); random.Random(seed).shuffle(ks)
    u = "KINDS:\n" + "\n".join(f"- {k}: {KINDS[k]}" for k in ks) + f"\n\nFINDING:\n{text}"
    o = llm.call(SYS, u, tag=f"kind{seed}", temperature=0.3, max_tokens=60, seed=seed)
    k = o.get("kind"); return k if k in KINDS else "ERR"
def votes(text, base):
    return [classify(text, base + i) for i in range(3)]
def main():
    mode = sys.argv[1]
    if mode == "before":
        items = [(r["id"], i, f["category"], f["finding"]) for r in load_rows() if r["source"] == "hancore_concrete" for i, f in enumerate(target(r)["findings"])]; base = 100
    else:
        items = [tuple(x) for x in json.load(open("/workspace/r2/out/refined_findings.json"))]; base = 900
    with ThreadPoolExecutor(16) as ex: V = list(ex.map(lambda it: votes(it[3], base), items))
    out = [dict(id=it[0], i=it[1], assigned=it[2], votes=v) for it, v in zip(items, V)]
    json.dump(out, open(f"/workspace/r2/out/kind_votes_{mode}.json", "w"), indent=1)
    maj = lambda v: collections.Counter(v).most_common(1)[0]
    ag = sum(maj(o["votes"])[0] == o["assigned"] for o in out); un = sum(len(set(o["votes"])) == 1 and o["votes"][0] == o["assigned"] for o in out)
    print(mode, "n", len(out), "majority==assigned", ag, round(ag / len(out), 3), "unanimous==assigned", un, round(un / len(out), 3), "spend", llm.spent())
if __name__ == "__main__": main()
