#!/usr/bin/env python3
"""v3 pool -> refined pool (r3) (no training, no GPU). Stages (all deterministic given the cached open-model replies in r3_cache/llm_cache.jsonl.gz):
 1. HANCORE kind check: 3 independent votes of qwen3.5-397b on the finding prose -> keep (3/3 agree), relabel (3/3 agree on another kind), else drop the finding.
 2. HANCORE text clean-up (stale file:line refs, review framing) + exact-line anchoring (cited line must contain the described construct; blank/comment/range-start lines re-anchored or finding dropped).
 3. Dell-sourced broken/in-use rows: drop findings the open-model audit + deterministic rules call wrong; fix lines.
 4. all rows: warnings in approve rows get the same line check. Rebuild train/val: approve share <=50%, unbounded-only cap, 32k token cap.
usage: refine_r2.py OUTDIR"""
import sys, os, re, json, gzip, random, collections, hashlib
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "r2_helpers"), "/workspace/wt-retrain-v2/train/v3data", "/workspace/wt-retrain-v2/train"]
import exactline as X
from common import load_rows, target
OUT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/r3/refined"; os.makedirs(OUT, exist_ok=True)
QWEN_TOK = os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a/tokenizer.json")
from tokenizers import Tokenizer
_tk = Tokenizer.from_file(QWEN_TOK); ntok = lambda s: len(_tk.encode(s).ids)
MAX_TOK = 32000
HYG = re.compile(r"(?i)remains? (blocked|open)|still (pins|blocked|open|block)|blocked:|retarget|\bthe update\b|re-?review|\bprevious|\bearlier\b|\bblocker remains|\bremaining\b|cannot be approved|\bagain\b|current-tree|\bthe reported\b|\bfixes the\b|\bwas fixed\b|https?://|\(\[|kernel doc|^two .{0,40} boundaries|\bgives three grounds|\bremains?\b|\bnow\b|\bthe new\b|\balready\b|\bnewly\b|\bis created privately\b|\bpremise\b|^(the )?dependency path|^(also|these|those|this|that|both|it|they|then)\b|\bare present\b|\bis present\b|\bnot (a )?(new|regression)\b")
HEDGE = re.compile(r"(?i)checker (flags|reports|treats|is flagging)|\bmay not exist|\bmight not|\bpossibly\b|\bmay (be|not)\b.{0,20}\b(installed|exist)|\bfallback\b|\bif (it|the \w+) (is|are) (not|missing)\b")
ARCH_STOCK = set("""gpasswd useradd usermod userdel groupadd groupdel groupmod newgrp chsh chfn chpasswd passwd su sudo systemd-tmpfiles systemctl loginctl journalctl udevadm modinfo modprobe lsmod insmod
gcc cc g++ c++ make pkg-config pkgconf wayland-scanner ld as ar nm objdump strip patch m4 autoconf automake libtool bison flex awk gawk sed grep egrep find xargs tar gzip bzip2 xz file which diffutils
bash sh dash env cat ls cp mv rm mkdir rmdir ln chmod chown chgrp touch stat date sleep tee tr cut sort uniq wc head tail dirname basename readlink realpath mktemp install df du ps kill pkill pgrep top free uptime
mount umount lsblk blkid findmnt dmesg lscpu nproc id whoami hostname uname logger flock timeout nice nohup printf echo test true false yes seq tty stty od hexdump base64 sha256sum md5sum cksum
python python3 perl curl wget git jq wl-copy wl-paste hyprctl hyprpm notify-send xdg-open less nano vim ip ss ping tput""".split())
import threading
from concurrent.futures import ThreadPoolExecutor
import llm
OUTD = os.environ.get("R_OUT", "/workspace/r3/out"); os.makedirs(OUTD, exist_ok=True)
PREFETCH = False; PAIRS = []
VSYS = """You verify citations in code-review findings for a plugin. You get a finding and the numbered source lines around the CITED line ('>' marks it).
(a) defect_stated: true if the finding describes a concrete defect or risk in this code that a reviewer would ask to have fixed; false if it describes safe or intended behaviour, confirms a fix, states scope, or is not about a defect.
(b) exact: true if the CITED line is the exact statement the finding describes: the line holding the call / assignment / command / declaration whose problem it states (a statement spanning several lines may be cited at its first line). false when the cited line is a function header or a sibling, a log or message string, a different statement, an import, a comment, a closing brace, or only nearby.
(c) better_line: if exact is false and the exact statement is visible in the window, its line number, else null.
Reply JSON only: {"defect_stated": true|false, "exact": true|false, "better_line": null|int, "why": "<one short sentence>"}"""
def vwindow(lines, L, ctx=10):
    a = max(0, L - 1 - ctx); b = min(len(lines), L + ctx)
    return "\n".join(f"{'>' if i + 1 == L else ' '}{i + 1:5d}| {lines[i][:220]}" for i in range(a, b))
def _vcall(txt, lines, L, path, tag):
    return llm.call(VSYS, f"FINDING: {txt}\n\nFILE: {path}\n{vwindow(lines, L)}", tag=tag, max_tokens=300)
def verify(txt, lines, L, path, tag="lineverify"):
    if PREFETCH: PAIRS.append((txt, lines, L, path, tag)); return dict(defect_stated=True, exact=True, better_line=None)
    o = _vcall(txt, lines, L, path, tag)
    if "_error" in o: return dict(defect_stated=True, exact=True, better_line=None, _error=True)
    return o
def accept_line(txt, lines, L, path, need_defect):
    """-> (line or None, reason). Applies the open-model exact-line / defect check; a better line is accepted only if it also passes the mechanical check."""
    v = verify(txt, lines, L, path)
    if need_defect and v.get("defect_stated") is False: return None, "not_a_defect_statement"
    if v.get("exact") is False:
        bl = v.get("better_line")
        if isinstance(bl, int) and 1 <= bl <= len(lines) and bl != L and X.check(txt, lines, bl, path) == "strict":
            v2 = verify(txt, lines, bl, path)
            if v2.get("exact") is not False: return bl, "moved"
        return None, "llm_not_exact_line"
    return L, "ok"
def clean_text(t):
    if t and t[-1] not in ".!?`)\"'…":   # v3 text was cut mid-word at the length cap: cut back to the last full sentence
        ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", t)]
        t = t[:ends[-1]] if ends and ends[-1] >= 60 else None
        if t is None: return None
    t = re.sub(r"(?i)^(additional current-tree finding|additional finding|separately|also|in addition|however|but)\s*[:,]\s*", "", t)
    t = X.strip_line_refs(t)
    t = re.sub(r"(`[^`\n]+`) and \1", r"\1", t)
    t = re.sub(r"\(\s*\)", "", t); t = re.sub(r"\s+([,.;:)])", r"\1", t); t = re.sub(r"\s{2,}", " ", t).strip(" ,;:-")
    if t.endswith("…"):
        cut = t[:-1]; j = max(cut.rfind(". "), cut.rfind("; "))
        t = cut[:j + 1] if j >= 80 else None
        if t is None: return None
    if not t or len(t) < 40 or X.has_artifact(t): return None
    t = t[0].upper() + t[1:]
    return t if t.endswith((".", "!", "?", "`")) else t + "."
def main():
    rows = load_rows(); st = collections.Counter(); drops = collections.Counter(); rnd = random.Random(1337)
    votes = {(v["id"], v["i"]): v for v in json.load(open(OUTD + "/kind_votes_before.json"))}
    audit = json.load(open(OUTD + "/dell_audit.json"))
    anchor_log = []; dell_log = []; refined_findings = []; kind_log = []
    def cited(files, f):
        t = files.get(f["file"]); return t.split("\n") if t is not None else None
    final = []
    for r in rows:
        t = target(r); files = X.parse_files(r["messages"][-2]["content"]); newf = []
        if r["source"] == "hancore_concrete":
            st["hancore_rows_in"] += 1
            for i, f in enumerate(t["findings"]):
                st["hancore_findings_in"] += 1
                v = votes[(r["id"], i)]; vs = v["votes"]; assigned = f["category"]
                if len(set(vs)) == 1 and vs[0] == assigned: kind = assigned; st["kind_keep_unanimous"] += 1
                elif len(set(vs)) == 1 and vs[0] != "ERR": kind = vs[0]; st["kind_relabel_unanimous"] += 1
                else: drops["hancore_finding:kind_disagreement"] += 1; kind_log.append(dict(id=r["id"], i=i, assigned=assigned, votes=vs, action="drop")); continue
                if kind != assigned: kind_log.append(dict(id=r["id"], i=i, assigned=assigned, votes=vs, action="relabel->" + kind))
                txt = clean_text(f["finding"])
                if not txt: drops["hancore_finding:text_unusable_after_cleanup"] += 1; continue
                if HYG.search(txt): drops["hancore_finding:review_framing_or_url"] += 1; continue
                lines = cited(files, f)
                if lines is None: drops["hancore_finding:file_not_in_prompt"] += 1; continue
                before = X.check(txt, lines, f["line"], f["file"]); st["hancore_anchor_before_" + before] += 1
                if before == "nocheck": drops["hancore_finding:no_checkable_construct"] += 1; continue
                if before == "strict": L = f["line"]; how = "kept"
                else:
                    L = X.anchor(txt, lines, f["line"], f["file"]); how = "reanchored"
                    if L is None: drops["hancore_finding:no_exact_line_found"] += 1; anchor_log.append(dict(id=r["id"], file=f["file"], line=f["line"], before=before, action="dropped")); continue
                    st["hancore_findings_reanchored"] += 1; anchor_log.append(dict(id=r["id"], file=f["file"], line=f["line"], before=before, new_line=L, action="reanchored"))
                if how == "kept": st["hancore_findings_line_kept"] += 1
                if X.check(txt, lines, L, f["file"]) != "strict": drops["hancore_finding:anchor_check_failed"] += 1; continue
                L2, why = accept_line(txt, lines, L, f["file"], True)
                if L2 is None: drops["hancore_finding:" + why] += 1; anchor_log.append(dict(id=r["id"], file=f["file"], line=f["line"], action="dropped:" + why)); continue
                if why == "moved": st["hancore_findings_llm_moved"] += 1
                L = L2
                if any(n["file"] == f["file"] and n["line"] == L for n in newf): drops["hancore_finding:duplicate_line"] += 1; continue
                newf.append(dict(category=kind, severity="blocker", file=f["file"], line=L, finding=txt, _i=i, _orig_line=f["line"], _orig_kind=assigned))
        else:
            dellrow = r["source"] in ("dell_broken_verified", "dell_inuse_close", "dell_inuse_missing_binary")
            if dellrow: st["dell_rows_in"] += 1
            for i, f in enumerate(t["findings"]):
                g = dict(f); lines = cited(files, f) if f.get("file") else None
                if dellrow:
                    st["dell_findings_in"] += 1; a = audit.get(f"{r['id']}#{i}", {}); prob = a.get("problem", "ERR")
                    rec = dict(id=r["id"], i=i, category=f["category"], file=f["file"], line=f["line"], audit=prob, why=a.get("why"))
                    if prob != "ok": drops["dell_finding:audit_" + prob] += 1; rec["action"] = "dropped:" + prob; dell_log.append(rec); continue
                    if f["category"].endswith("missing-binary") or f["category"] == "runtime:missing-binary":
                        bins = [sp.split()[0].split("/")[-1] for sp in X.spans(f["finding"])]
                        if any(b in ARCH_STOCK for b in bins): drops["dell_finding:stock_binary_rule"] += 1; rec["action"] = "dropped:stock_rule"; dell_log.append(rec); continue
                    if re.search(r"(?i)\bimport\s+`?Qt\.labs\.\w+", f["finding"]) or re.fullmatch(r"\s*import\s+Qt\.labs\.[\w.]+(\s+as\s+\w+)?\s*", lines[f["line"] - 1] if lines and isinstance(f.get("line"), int) and f["line"] <= len(lines) else ""):
                        drops["dell_finding:qt_labs_import_rule"] += 1; rec["action"] = "dropped:qt_labs_import_rule"; dell_log.append(rec); continue   # Qt.labs.* imports are valid Qt6 modules (functest/static_checks.py QT6_MODULES); the Checker USB-A01 line is a false positive on import statements
                    if HEDGE.search(f["finding"]):
                        rw = a.get("rewritten_finding")
                        if rw and not HEDGE.search(rw) and 40 <= len(rw) <= 300: g["finding"] = rw; st["dell_findings_rewritten"] += 1
                        else: drops["dell_finding:hedged"] += 1; rec["action"] = "dropped:hedged"; dell_log.append(rec); continue
                    rec["action"] = "kept"; dell_log.append(rec)
                if lines is not None and isinstance(f.get("line"), int):
                    c = X.check(g["finding"], lines, g["line"], g["file"])
                    if c in ("fail", "blank_or_comment"):
                        bl = (audit.get(f"{r['id']}#{i}", {}) or {}).get("better_line") if dellrow else None
                        L = bl if isinstance(bl, int) and X.check(g["finding"], lines, bl, g["file"]) == "strict" else X.anchor(g["finding"], lines, g["line"], g["file"])
                        if L is None: drops[("dell" if dellrow else "approve") + "_finding:no_exact_line_found"] += 1; continue
                        g["line"] = L; st[("dell" if dellrow else "approve") + "_findings_reanchored"] += 1
                    L2, why = accept_line(g["finding"], lines, g["line"], g["file"], False)
                    if L2 is None: drops[("dell" if dellrow else "approve") + "_finding:" + why] += 1; continue
                    if why == "moved": st[("dell" if dellrow else "approve") + "_findings_llm_moved"] += 1
                    g["line"] = L2
                newf.append(g)
        if r["source"] == "hancore_concrete" and not newf: drops["hancore_row:no_finding_left"] += 1; continue
        if r["verdict"] == "changes_requested" and not any(f["severity"] == "blocker" for f in newf): drops["row:no_blocker_left:" + r["source"]] += 1; continue
        # rebuild row
        if r["source"] == "hancore_concrete":
            prov = dict(r["provenance"]); pf = prov["findings"]
            def pmatch(f):
                return next((p for p in pf if p["file"] == f["file"] and p["line"] == f["_orig_line"]), None) or {}
            prov["findings"] = [dict(pmatch(f), bug_kind=f["category"], line=f["line"], orig_line=f["_orig_line"], kind_relabeled_r2=f["category"] != f["_orig_kind"], orig_kind_v3=f["_orig_kind"]) for f in newf]
            for f in newf: refined_findings.append([r["id"], len(refined_findings), f["category"], f["finding"]])
            ans = dict(t, findings=[{k: v for k, v in f.items() if not k.startswith("_")} for f in newf]); r = dict(r, provenance=prov)
        else: ans = dict(t, findings=newf)
        msgs = r["messages"][:-1] + [{"role": "assistant", "content": json.dumps(ans, ensure_ascii=False)}]
        r = dict(r, messages=msgs, tokens=ntok(json.dumps(msgs)))
        if r["tokens"] > MAX_TOK: drops["row:over_token_cap"] += 1; continue
        final.append(r)
    # ---- r3: no caps here; dump the refined POOL (caps, val selection and Checker-report regeneration happen in assemble_r3.py) ----
    with gzip.open(os.path.join(OUT, "pool_refined.jsonl.gz"), "wt") as f:
        for r in final: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    out = {"train": final, "val": []}
    # refined_findings file for the 'after' kind pass: (row id, index, kind, text)
    seq = collections.defaultdict(int); rf = []
    for r in final:
        if r["source"] != "hancore_concrete": continue
        for i, f in enumerate(target(r)["findings"]): rf.append([r["id"], i, f["category"], f["finding"]])
    json.dump(rf, open(OUTD + "/refined_findings.json", "w"))
    for name, obj in (("r3_anchor_log", anchor_log), ("r3_dell_audit_log", dell_log), ("r3_kind_log", kind_log)):
        with open(os.path.join(OUT, name + ".jsonl"), "w") as f:
            for x in obj: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    json.dump(dict(stats=dict(st), drops=dict(drops), train=len(out["train"]), val=len(out["val"])), open(os.path.join(OUT, "build_stats.json"), "w"), indent=1)
    print(json.dumps(dict(st), indent=1)); print(json.dumps(dict(drops), indent=1)); print(len(out["train"]), len(out["val"]))
def run():
    global PREFETCH
    PREFETCH = True; PAIRS.clear(); main_quiet()
    seen = {}; 
    for p in PAIRS: seen[(p[0], p[2], p[3])] = p
    print("prefetching", len(seen), "line verifications", flush=True)
    with ThreadPoolExecutor(14) as ex: list(ex.map(lambda p: _vcall(*p), seen.values()))
    PREFETCH = False; main()
def main_quiet():
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()): main()
if __name__ == "__main__": run()
