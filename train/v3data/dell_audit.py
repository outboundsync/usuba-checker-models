#!/usr/bin/env python3
"""Stage 2: audit Dell-sourced broken / in-use rows. Evidence = plugin source (cited line +-8, other occurrences), the Checker report shown in the row's prompt,
and the Dell sweep run record (qml_errors, missing_bins, listed/toggle) from dell/sweep/results.jsonl. Judge = qwen/qwen3.5-397b-a17b (OpenRouter, open weights).
Never reads functest/dell_ground_truth.jsonl labels; key ids are excluded by the build/leakage check, not looked at here."""
import sys, os, json, re, collections
from concurrent.futures import ThreadPoolExecutor
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "r2_helpers"), "/workspace/wt-retrain-v2/train/v3data", "/workspace/wt-retrain-v2/functest/dell_env"]
OUTD = os.environ.get("R_OUT", "/workspace/r3/out")
import llm, exactline as X
from common import load_rows, target, last_user, dell_res
from binaries import OMARCHY_BINS, SYSTEM_BINS
SYS = """You are a strict auditor of code-review findings for Quickshell/QML plugins that run on a stock Omarchy 4.x system (Arch Linux + Hyprland + Omarchy's own `omarchy-*` commands).
Stock = the Arch `base` and `base-devel` groups (so coreutils, util-linux, shadow tools such as gpasswd/useradd, systemd tools such as systemd-tmpfiles/systemctl/loginctl, kmod tools such as modinfo, gcc, make, pkg-config, wayland-scanner), plus Hyprland tools, wl-clipboard, python3, curl, jq, git, bash, and Omarchy's `omarchy-*` commands. Not stock: third-party apps (anki, cava, zenity, omanote, perf, yt-dlp...) unless the plugin ships or documents them.
You get ONE finding that a reviewer wrote for a plugin that is labelled broken, plus the evidence. Decide whether the finding is a TRUE, correctly stated defect at that line.
Mark it wrong (problem != "ok") when any of these hold:
- not_executable: the quoted "binary/command" is not an executable run at that line: a MIME type, case/glob pattern, regex, usage text, comment, string constant, function name defined in the same script, mpv/IPC property or method name (get_property, set_property, quit), Hyprland dispatcher/option name (gaps_in), or a path fragment (usr/lib).
- stock_binary: the tool is installed on stock Omarchy/Arch (see list above), or is an `omarchy-*` command that really exists on Omarchy.
- optional_fallback: the missing tool is an optional fallback/alternative that is only tried if another works, or its absence is handled, so the plugin does not fail.
- construct_absent: the construct the finding talks about is not on or next to the cited line, or the code contradicts the claim.
- hedged: the finding is hedged or based on what "the checker flags", "may not exist", "could"; a real finding states a fact about this code.
- not_a_defect: harmless as written (e.g. script only documents, or the plugin is correct).
- unverifiable: you cannot confirm from the evidence.
Evidence ranking: (1) the code shown; (2) the Checker report lines, which are produced by static analysis against the real Omarchy shell tree (they know which `qs.Commons`/`qs.Ui` members, imports and QML types really exist, and the Checker's statements of that kind are reliable; its binary-name lines are NOT: it flags MIME types, case patterns, mpv/IPC strings, and stock tools); (3) the Dell run record: non-empty qml_errors/missing_bins are real runtime evidence that CONFIRMS a finding. EMPTY qml_errors or "listed/toggle_ok" prove nothing against a static finding about an undefined property, missing import or unknown type, because panels and overlays are often never opened during the run: never use them to call a finding wrong.
So for load/runtime findings about a missing import/type/property/method, mark "ok" when the code shown is consistent with the claim and (the Checker report states it or the Dell record confirms it); mark wrong only when the code shown contradicts it (for example the call is guarded, the value is converted before use, the identifier is defined in the plugin, or the file the finding says is missing is present).
If the defect is real but the line number or wording is slightly off, set problem "ok", and give better_line (the line of the exact statement) and/or rewritten_finding (1-2 sentences, <=280 chars, states the fact, names the construct in backticks, no mention of the checker or hedging).
Reply JSON only: {"why": "<one sentence>", "problem": "ok|not_executable|stock_binary|optional_fallback|construct_absent|hedged|not_a_defect|unverifiable", "confident": true|false, "better_line": null|int, "rewritten_finding": null|string}"""
def excerpt(files, fn, line, ctx=8):
    t = files.get(fn)
    if t is None: return "(file not in prompt)"
    L = t.split("\n"); a = max(0, (line or 1) - 1 - ctx); b = min(len(L), (line or 1) + ctx)
    return "\n".join(f"{'>' if i + 1 == line else ' '}{i + 1:5d}| {L[i][:200]}" for i in range(a, b))
def other_occurrences(files, f):
    outs = []
    for sp in X.spans(f["finding"])[:3]:
        for c in X.variants(sp)[:1]:
            if isinstance(c, tuple): continue
            for p, t in files.items():
                for i, l in enumerate(t.split("\n")):
                    if c in l and not (p == f["file"] and i + 1 == f["line"]): outs.append(f"{p}:{i+1}| {l.strip()[:140]}")
                    if len(outs) >= 8: return outs
    return outs
def bin_notes(f):
    n = []
    for sp in X.spans(f["finding"]):
        b = sp.split()[0].split("/")[-1]
        if re.fullmatch(r"[\w.+-]+", b): n.append(f"`{b}`: in Omarchy bins list={b in OMARCHY_BINS}, in Dell system list={b in SYSTEM_BINS}")
    return n[:4]
def job(args):
    r, i, res = args
    t = target(r); f = t["findings"][i]; files = X.parse_files(last_user(r)); u = last_user(r)
    rep = u.split("## Plugin source")[0].replace("## Checker report\n", "").strip()[:1500]
    d = res[r["provenance"]["dell_job"]]; dl = d["dell"]
    ev = dict(listed=dl["listed"], toggle_ok=dl["toggle_ok"], died=dl["died"], qml_errors=dl["qml_errors"][:6], missing_bins=dl["missing_bins"], harness_invalid=dl.get("harness_invalid"))
    user = (f"FINDING: [{f['category']}] {f['file']}:{f['line']}: {f['finding']}\n\nCITED CODE ('>' = cited line):\n{excerpt(files, f['file'], f['line'])}\n\n"
            f"OTHER OCCURRENCES OF THE QUOTED CONSTRUCTS IN THE PLUGIN:\n" + ("\n".join(other_occurrences(files, f)) or "(none)") + "\n\nBINARY LOOKUPS:\n" + ("\n".join(bin_notes(f)) or "(n/a)") +
            f"\n\nCHECKER REPORT SHOWN TO THE REVIEWER:\n{rep}\n\nDELL RUN RECORD: {json.dumps(ev)}\nPlugin files: {', '.join(list(files)[:25])}")
    out = llm.call(SYS, user, tag="dellaudit2", max_tokens=700)
    return (r["id"], i), out
def main():
    rows = [r for r in load_rows() if r["source"] in ("dell_broken_verified", "dell_inuse_close", "dell_inuse_missing_binary")]
    res = dell_res(); jobs = [(r, i, res) for r in rows for i in range(len(target(r)["findings"]))]
    print("rows", len(rows), "findings", len(jobs), flush=True)
    out = {}
    with ThreadPoolExecutor(12) as ex:
        for k, v in ex.map(job, jobs): out[f"{k[0]}#{k[1]}"] = v
    json.dump(out, open(OUTD + "/dell_audit.json", "w"), indent=1)
    print(collections.Counter(v.get("problem", "ERR") for v in out.values()), "spend", llm.spent())
if __name__ == "__main__": main()
