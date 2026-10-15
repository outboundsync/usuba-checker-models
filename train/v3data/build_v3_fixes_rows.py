#!/usr/bin/env python3
"""Builds the v3-fixes rows for r3 to fold in (no LLM, no network, no GPU, no Dell; deterministic).
  synthetic_rows.jsonl : rows from synthetic_lifecycle.SPECS; a spec is written only if the Checker agrees (expected rule ids fire / tree is clean) and, with --qs-probe,
                         the real Quickshell 0.3.2 headless probe agrees for the QML-level ones. Marked synthetic=true, source=synthetic_lifecycle.
  winners_rows.jsonl   : real MIT text from the four winners (text sources only): omagotchi before/after (reviewed commit vs HEAD), robzolkos/omarchy-github PR 23 before/after,
                         omapods root files (no daemon/, no AGENTS.md/knowledge), marked synthetic=false, source=winners_mit, license + copyright in provenance.
Rows carry the prompt_v3 prefix (7 shots). r3 can re-wrap with prompt_v3.rebuild(messages). usage: python3 train/v3data/build_v3_fixes_rows.py --out /workspace/usuba-runs/v3-fixes [--qs-probe]"""
import sys, os, re, json, subprocess, argparse, hashlib, tempfile, shutil, time
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
sys.path[:0] = [os.path.join(ROOT, "train"), os.path.join(ROOT, "functest"), os.path.join(ROOT, "functest/usuba"), H]
import prompt_v3 as P, checker_report as C, lifecycle_rules as LR, hancore_rules_v2 as V
from synthetic_lifecycle import SPECS
ANCHOR = {  # id -> (file, regex of the cited line)
 "syn.lifecycle.overlay-toggle-only": ("Overlay.qml", r"^Item \{"), "syn.lifecycle.panel-open-no-close": ("Panel.qml", r"^Item \{"), "syn.lifecycle.menu-close-only": ("Menu.qml", r"^Item \{"),
 "syn.manifest.kind-without-key": ("manifest.json", r'"entryPoints"'), "syn.manifest.kind-used-as-key": ("manifest.json", r'"entryPoints"'), "syn.manifest.no-schema-version": ("manifest.json", r'"id"'),
 "syn.qml.required-injected-property": ("BarWidget.qml", r"required property var shell"), "syn.supply.cargo-git-unpinned": ("install.sh", r"cargo install --git"),
 "syn.supply.sudoers-nopasswd-all": ("setup.sh", r"NOPASSWD: ALL")}
def ntok(s):
    try:
        import build_v3_data as B; return B.ntok(s)
    except Exception: return len(s) // 3
def row(id_, files, tgt, source, synthetic, prov, label=None):
    rep = C.report(files)
    msgs = P.messages(P._code(files), rep, tgt)
    return dict(id=id_, split="train", source=source, orig_source=source, synthetic=synthetic, label=tgt["load"], verdict=tgt["verdict"], target_kind=source, reject_reason=None, is_pair_parent=False, pair=None,
                tokens=ntok(json.dumps(msgs)), provenance=prov, weight=1.0, messages=msgs)
def fires(files):
    s = {f["rule"] for f in LR.check(files, enabled=set(LR.RULES))} | {f["rule"] for f in V.check(files, enabled=set(V.RULES))}
    return s
def qs_probe(specs):
    """real Quickshell 0.3.2 on a headless sway: Loader-load every entry, report status and typeof open/close."""
    tmp = tempfile.mkdtemp(prefix="qsprobe"); os.chmod(tmp, 0o700); env = dict(os.environ, XDG_RUNTIME_DIR=tmp, WLR_BACKENDS="headless", WLR_LIBINPUT_NO_DEVICES="1")
    sw = subprocess.Popen(["sway", "-c", "/dev/null"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(3)
    disp = next((x for x in os.listdir(tmp) if re.fullmatch(r"wayland-\d", x)), None); out = {}
    try:
        for s in specs:
            man = json.loads(s["files"]["manifest.json"]) if s["files"]["manifest.json"].lstrip().startswith("{") else {}
            for k, ep in (man.get("entryPoints") or {}).items():
                if k not in ("panel", "overlay", "menu", "barWidget") or ep not in s["files"] or "import qs." in s["files"][ep] or not (s["id"].startswith(("syn.lifecycle.", "syn.ok.overlay", "syn.ok.panel", "syn.ok.menu", "syn.ok.service", "syn.qml."))): continue
                d = os.path.join(tmp, "p_" + hashlib.md5((s["id"] + k).encode()).hexdigest()[:8]); os.makedirs(d)
                for p, c in s["files"].items():
                    if p.endswith((".qml", ".js")): os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True); open(os.path.join(d, p), "w").write(c)
                open(d + "/shell.qml", "w").write('import QtQuick\nimport Quickshell\nShellRoot {\n Loader { id: l; source: "%s"; onLoaded: console.log("PROBE loaded", typeof item.open, typeof item.close) }\n Timer { interval: 1200; running: true; onTriggered: { console.log("PROBE status", l.status); Qt.quit() } }\n}\n' % ep)
                r = subprocess.run(["quickshell", "-p", d + "/shell.qml"], env=dict(env, WAYLAND_DISPLAY=disp, QT_QPA_PLATFORM="wayland"), capture_output=True, text=True, timeout=30)
                t = r.stdout + r.stderr; m = re.search(r"PROBE loaded (\w+) (\w+)", t); st = re.search(r"PROBE status (\d)", t)
                out[s["id"] + ":" + k] = dict(status=int(st.group(1)) if st else None, open=m.group(1) if m else None, close=m.group(2) if m else None)
    finally: sw.terminate(); shutil.rmtree(tmp, ignore_errors=True)
    return out
def synthetic(a):
    specs = []
    for s in SPECS:
        s = json.loads(json.dumps(s, default=list)); s["expect"] = set(s["expect"]); specs.append(s)
    for s in specs:   # fix cited lines from anchors
        if s["id"] in ANCHOR:
            f, rx = ANCHOR[s["id"]]; ln = next(i for i, l in enumerate(s["files"][f].splitlines(), 1) if re.search(rx, l)); s["findings"][0]["line"] = ln; s["findings"][0]["file"] = f
    bad = []
    for s in specs:
        got = fires(s["files"])
        if not (s["expect"] <= got and (s["expect"] or not got)): bad.append((s["id"], sorted(s["expect"]), sorted(got)))
        if s["expect"] and not (got <= s["expect"] | {"USB-W12"}): bad.append((s["id"], "unexpected extra", sorted(got - s["expect"])))
    probe = qs_probe(specs) if a.qs_probe else {}
    for k, v in probe.items():
        sid, kind = k.rsplit(":", 1); s = next(x for x in specs if x["id"] == sid)
        want_load = s["id"] != "syn.qml.required-injected-property"
        has_both = v["open"] == "function" and v["close"] == "function"
        want_both = not (s["id"].startswith("syn.lifecycle.") or s["id"] == "syn.ok.service-driven-hud")
        if (v["status"] == 1) != want_load: bad.append((sid, "probe load", v))
        elif want_load and kind != "barWidget" and has_both != want_both and s["id"] != "syn.ok.service-driven-hud": bad.append((sid, "probe open/close", v))
    if bad: raise SystemExit("synthetic specs failed verification: " + json.dumps(bad, default=list))
    rows = [row(s["id"], s["files"], dict(verdict=s["verdict"], load=s["load"], findings=s["findings"]), "synthetic_lifecycle", True,
                dict(kind="synthetic", note=s["note"], expected_rules=sorted(s["expect"]), qs_probe=probe.get(s["id"] + ":" + next(iter(json.loads(s["files"]["manifest.json"]).get("entryPoints", {"x": 0})), ""), None) if probe else None,
                     license="own work (this repository)", marked="SYNTHETIC")) for s in specs]
    with open(a.out + "/synthetic_rows.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows, probe
def git(repo, rev, p): return subprocess.run(["git", "-C", repo, "show", f"{rev}:{p}"], capture_output=True, text=True).stdout
def lic(d): return open(d + "/LICENSE").read().split("\n")[2] if os.path.exists(d + "/LICENSE") else ""
def line_of(files, f, needle):
    for i, l in enumerate(files[f].splitlines(), 1):
        if needle in l: return i
    raise SystemExit(f"anchor not found: {f} {needle}")
def winners(a, retr):
    SW = "/workspace/sweep_repos"; rows = []; notes = []
    def pv(repo, commit, files, extra=None): return dict(kind="winners-mit", repo=repo, commit=commit, files=sorted(files), license="MIT", copyright=lic(f"{SW}/" + repo.replace("/", "__").lower()) or "see repo LICENSE", synthetic=False, notice="MIT: keep copyright + permission notice with copies", **(extra or {}))
    # --- omagotchi before (reviewed tree) / after (HEAD): text sources only, no sounds/, CREDITS, tools
    og_before = "/workspace/hancore_cache/SLcode777__omagotchi@9c15d705a201ebbb7f4d4b759d8f214690467ba0"; og_head = SW + "/slcode777__omagotchi"
    pick = ("manifest.json", "Service.qml", "BarWidget.qml", "PetSprite.qml", "RoamWindow.qml", "README.md")
    fb = {p: open(f"{og_before}/{p}").read() for p in pick}; fa = {p: open(f"{og_head}/{p}").read() for p in pick}
    ln = line_of(fb, "Service.qml", "root.loadedSettingsText = text()")
    retracted = retr.get("omagotchi", False)   # retraction_check.py found no withdrawal in the review thread of this commit
    WHY = "kept out of training by default: the blocker is an owner-controlled state/config file the plugin itself writes (the v3 prompt's trusted-and-small exception and the 2026-10-03 disposition make that a warning); the reviewer's thread for this commit has no explicit withdrawal, so the pair is delivered for r3 to decide"
    rows.append(row("winners_mit:omagotchi:before-9c15d705-warning", fb, dict(verdict="approve", load="works", findings=[dict(category="unbounded-input-resource", severity="warning", file="Service.qml", line=ln, finding="`FileView` reads the whole settings file with `text()` and no size cap; the file is the plugin's own state under XDG, so this is a hardening note (the later version reads through `head -c 65536`).")]), "winners_mit", False,
                    pv("SLcode777/omagotchi", "9c15d705a201ebbb7f4d4b759d8f214690467ba0", fb, dict(role="before-calibration", include_in_train=False, why_not="runtime label of this commit was not measured (the Dell sweep ran HEAD); policy calibration variant of the blocker row", pair="winners_mit:omagotchi:after-669ea0b7"))))
    if True:
        rows.append(row("winners_mit:omagotchi:before-9c15d705", fb, dict(verdict="changes_requested", load="unsure", findings=[dict(category="unbounded-input-resource", severity="blocker", file="Service.qml", line=ln, finding="`FileView` in the always-loaded service reads the whole user-writable settings file with `text()` and no size cap (the state file below it too), so an oversized file or a symlink to a large file is pulled completely into the shell.")]), "winners_mit", False,
                        pv("SLcode777/omagotchi", "9c15d705a201ebbb7f4d4b759d8f214690467ba0", fb, dict(role="before", partial_tree="Panel.qml omitted (token cap); sounds/CREDITS excluded", pair="winners_mit:omagotchi:after-669ea0b7", include_in_train=False, why_not=WHY, label_origin="HANCORE marketplace review of this commit (unbounded read of state files); line re-anchored to the exact statement (the review cited 537, the construct is at the FileView onLoaded handler)"))))
    rows.append(row("winners_mit:omagotchi:after-669ea0b7", fa, dict(verdict="approve", load="works", findings=[]), "winners_mit", False,
                    pv("SLcode777/omagotchi", "669ea0b7eac7a78ec408512cb81d8e5082c3c33b", fa, dict(role="after", include_in_train=False, why_not="Dell sweep label for this HEAD is broken (rt-invisible: bar widget draws no ink pixels); an approve/works row would contradict it. Kept as the pair partner only.", pair="winners_mit:omagotchi:before-9c15d705"))))
    # --- robzolkos/omarchy-github PR 23 (merge commit c38e600): before = c38e600^, after = c38e600
    g = SW + "/robzolkos__omarchy-github"; names = ("manifest.json", "Panel.qml", "Service.qml")
    gb = {p: git(g, "c38e600^", p) for p in names}; ga = {p: git(g, "c38e600", p) for p in names + ("UrlLauncher.qml",)}
    ln = line_of(gb, "Panel.qml", 'Util.execArgv(["xdg-open", value])')
    rows.append(row("winners_mit:github-pr23:before", gb, dict(verdict="changes_requested", load="unsure", findings=[dict(category="url-scheme-network", severity="blocker", file="Panel.qml", line=ln, finding="`openUrl` passes any URL string from the fetched GitHub data to `xdg-open` (and `omarchy-launch-webapp`) with no scheme or host check, so a `file:`, `javascript:` or custom-handler link in an item opens as-is.")]), "winners_mit", False,
                    pv("robzolkos/omarchy-github", "c38e600^ (parent of the PR 23 merge)", gb, dict(role="before", pair="winners_mit:github-pr23:after", partial_tree="omarchy-github-fetch helper, tests and README omitted (token cap)", label_origin="the merged security-hardening change itself (openUrl: refuse anything that is not https); finding text written for this row, no review text copied"))))
    rows.append(row("winners_mit:github-pr23:after", ga, dict(verdict="approve", load="works", findings=[]), "winners_mit", False,
                    pv("robzolkos/omarchy-github", "c38e600", ga, dict(role="after", pair="winners_mit:github-pr23:before", partial_tree="omarchy-github-fetch helper, tests and README omitted (token cap)", label_origin="same commit as the PR merge; Dell sweep label of the later HEAD is works"))))
    # --- omapods root files (MIT); daemon/ GPL-3.0, AGENTS.md, knowledge/ excluded
    pd = SW + "/thisisgm__omarchy-pods"; po = {p: open(f"{pd}/{p}").read() for p in ("manifest.json", "Panel.qml", "Service.qml", "Model.js", "AirPodsIcon.qml", "setup", "README.md")}
    rows.append(row("winners_mit:omapods:root-files", po, dict(verdict="approve", load="works", findings=[]), "winners_mit", False,
                    pv("thisisgm/omarchy-pods", "fff7fec600a5b9a61cdb40e93eccbcceb4b8f824", po, dict(role="approve-example", excluded="daemon/ (GPL-3.0), AGENTS.md, .claude/, knowledge/, tests/", label_origin="Dell sweep run6: toggle ok, no QML errors, no missing bins; the sweep's 'broken' label came only from `bad-import` on unreachable daemon/*.qml (label corrected by manifest-scoped import check)"))))
    with open(a.out + "/winners_rows.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows, notes
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="/workspace/usuba-runs/v3-fixes"); ap.add_argument("--qs-probe", action="store_true"); ap.add_argument("--retractions", default="")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    retr = {}
    rf = a.retractions or (a.out + "/retraction_winners.json")
    if os.path.exists(rf): retr = json.load(open(rf))
    s, probe = synthetic(a); w, notes = winners(a, retr)
    summ = dict(synthetic_rows=len(s), synthetic_broken=sum(r["verdict"] != "approve" for r in s), winners_rows=len(w), winners_in_train=sum(r["provenance"].get("include_in_train", True) for r in w), tokens_max=max(r["tokens"] for r in s + w), notes=notes, probe=probe)
    json.dump(summ, open(a.out + "/rows_summary.json", "w"), indent=1); print(json.dumps(summ, indent=1)[:1500])
if __name__ == "__main__": main()
