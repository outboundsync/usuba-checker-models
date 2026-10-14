#!/usr/bin/env python3
"""Step 3: filter teacher outputs and write the v2 train/val JSONL.
Keep a teacher output only if: valid JSON; verdict matches the label (works->approve, broken->changes_requested); no invented SHAs or plugin
names (eval/dellkey/reason_grade.py style: hex runs / reverse-domain ids not in the prompt input); and for broken rows a blocker matches a
gold reason (Dell/Checker templated finding) by a deterministic rubric in the eval/dellkey/reason_rubric.json style
(file mention AND cause pattern AND line within 15 when both cite one). HANCORE rows: blocker category (normalised) or category cause pattern.
Teacher misses on broken rows fall back to the templated target (SHAs and 'security review' boilerplate stripped).
Works rows whose teacher output is rejected fall back to the Dell/grader-verified templated approve target.
Outputs $DISTILL_WORK/final/{train,val}.jsonl, report.json, spot_check.json."""
import collections, hashlib, json, os, random, re, sys
from common import *
import run_eval as E, prompt_v2 as P, build_train_set as B
from candidates import qwen_tokens
TOL = 15
HEX = re.compile(r"(?<![0-9a-zA-Z])[0-9a-f]{7,40}(?![0-9a-zA-Z])")
PID = re.compile(r"\b(?:[a-z][a-z0-9-]*\.){2,}[a-z0-9][a-z0-9-]*\b")
FILE_EXT = (".tmp", ".bak", ".log", ".lock", ".cache", ".yaml", ".yml", ".ini", ".html", ".xml", ".so", ".desktop", ".service", ".qml", ".js", ".json", ".sh", ".py", ".md", ".txt", ".conf", ".lua", ".toml", ".css", ".svg", ".png", ".mjs")
CODE_OBJ = {"root", "os", "self", "this", "parent", "shell", "json", "math", "qt", "quickshell", "sys", "subprocess", "window", "model", "modeldata", "console", "process", "proc", "settings", "config", "manifest", "plugin", "item", "data", "path", "str", "re"}
def hallucinations(c, out):
    inp = "\n".join(m["content"] for m in c["messages"] if m["role"] == "user")   # incl. few-shot inputs, as reason_grade does for the prompt
    own = {str(c.get("manifest_id") or "").lower(), str(c.get("manifest_name") or "").lower()}
    txt = json.dumps(out)
    shas = sorted({h for h in HEX.findall(txt) if re.search(r"\d", h) and (re.search(r"[a-f]", h) or len(h) >= 12) and h not in inp}
                  | {h for h in re.findall(r"commit\W{0,3}([0-9a-f]{6,40})\b", txt, re.I) if h not in inp})
    names = set()
    for m in PID.findall(txt):
        ml = m.lower()
        if ml.split(".")[0] in CODE_OBJ or ml.endswith(FILE_EXT) or ml in own or m in inp or re.match(r"^(qs|quickshell|qt|org\.kde|io\.qt)\.", ml): continue
        if re.search(r"\.(com|org|net|io|dev|app|ai|co|gov|edu|me)$", ml) and not re.match(r"^(io|com|org|dev|me|net)\.", ml): continue
        names.add(m)
    for m in re.findall(r"(?:plugin|Plugin)(?: widget| service| overlay| panel| bar)?\s+`?([a-z0-9][\w-]*\.[\w.-]*[\w-])", txt):
        if not m.lower().endswith(FILE_EXT) and m.lower() not in own and m not in inp: names.add(m)
    for m in re.findall(r"(?:plugin|Plugin)\s+[\"'`]([^\"'`]{3,40})[\"'`]", txt):
        if m.lower() not in own and m not in inp: names.add(m)
    return shas, sorted(names)
# ---- gold-reason rubric ----
FAMILY = {"Q01": r"unknown|not a (known |valid |real )?(qml )?type|no such type|does not exist|not provided|not (defined|available)|missing import",
          "A01": r"does not exist|not (a member|part)|undefined|no such|not exist", "A04": r"no (such )?method|has no|not a (method|function)|does not exist|undefined|is not a function",
          "A07": r"not part of|undefined|does not exist|not (exposed|provided)|no such", "J01": r"never declared|not declared|undeclared|undefined|ReferenceError|not defined",
          "B01": r"not installed|missing|not shipped|not (on|available|present)|not found|absent|isn't installed", "D04": r"not installed|missing|not shipped|not (on|available)",
          "F01": r"not ship|missing|does not exist|not (included|present|shipped|found)|absent|no such file", "S03": r"rm -rf|delet|destructive|remov",
          "H07": r"placeholder|fake|canned|example\.com|hard-?coded|dummy|not real", "H01": r"placeholder|fake|canned|hard-?coded|proxy|simulat|not real|random",
          "A02": r"not a signal|never fires|handler|no (such )?signal", "J04": r"file://|resolvedUrl|url|scheme|path", "A03": r"\bnew\b|instantiat|constructor",
          "B02": r"x11|xclip|xdotool|wayland", "B03": r"dispatch", "Q05": r"default property|QtObject|child"}
GENERIC = r"missing|not installed|does not exist|undefined|syntax|expected token|unbalanced|unknown|not a type|fails? to load|not created|error|placeholder|fake|random"
INUSE = {"in-use:toggle-opens-nothing": r"opens? nothing|no (new )?(surface|window|panel|overlay)|never (appears|shows|opens|becomes visible)|does nothing|not (shown|visible)|invisible|nothing (appears|happens|is shown)|toggle",
         "in-use:memory-growth": r"memory|leak|grow|allocat|rss", "in-use:panel-cannot-close": r"centerHoverRevealSuppressed|read-?only|cannot (be )?(close|dismiss)|can't close|close\(\)"}
HC = {"unbounded-input-resource": r"unbounded|size cap|no (size )?(cap|limit)|without (a )?(size )?(cap|limit)|entire|large (output|file|input)|memory",
      "install-deps-packaging": r"install|depend|packag|not (installed|shipped)|missing (binary|dependency)", "file-safety-symlink-perms": r"symlink|permission|predictable|world-?(read|writ)|/tmp|race|atomic",
      "secrets-credentials": r"secret|credential|token|password|api key", "privileged-system": r"sudo|root|privileg|system(d| file| config)|pkexec|/etc",
      "process-lifecycle-timeouts": r"timeout|hang|never (exit|terminat)|orphan|kill|lifecycle|zombie", "remote-code-pinning": r"pin|curl .*\| *(ba)?sh|remote (code|script)|download|unverified|checksum",
      "url-scheme-network": r"url|scheme|http|network|xdg-open", "rich-text-markup-injection": r"rich ?text|markup|html|textFormat|inject", "shell-lua-injection": r"inject|sh -c|quot|escap|interpolat|eval",
      "user-config-modification": r"config|overwrit|modif|~/\.config|dotfile", "scope-policy-duplicate": r"scope|policy|duplicate", "listing-metadata-docs": r"manifest|readme|metadata|listing|docs?"}
def gold_rules(c):
    R = []
    for g in c["target"]["findings"]:
        if g["severity"] != "blocker": continue
        cat, txt = g["category"], g["finding"]
        if c["source"] == "hancore":
            R.append(dict(kind="hc", cat=cat, cause=[HC.get(cat, re.escape(cat.split("-")[0]))])); continue
        if cat in INUSE: R.append(dict(kind="re", files=[g["file"]] if g.get("file") else [], cause=[INUSE[cat]], line=None)); continue
        if cat == "in-use:missing-binary":
            bins = re.findall(r"Runs (.+?) at runtime", txt); bins = [b.strip() for b in (bins[0].split(",") if bins else []) if b.strip() and b.strip() != "a binary listed in the code"]
            R.append(dict(kind="re", files=[], cause=[r"(?<![\w-])" + re.escape(b) + r"(?![\w-])" for b in bins] or [r"not installed|missing binary|not shipped"], line=None)); continue
        m = re.match(r"\s*([\w./@+-]+\.(?:qml|js|mjs|sh|py|lua|json|bash|conf|toml|css))\s*:", txt)
        f = g.get("file") or (m.group(1) if m else None)
        ln = re.search(r"line (\d+)", txt); toks = [t for t in re.findall(r"`([^`]{2,60})`", txt) if not t.lower().endswith(FILE_EXT)]
        toks += [t for t in re.findall(r"\b[A-Z]\w+\.\w+\b", txt) if not t.lower().endswith(FILE_EXT)]
        rule = cat.split(":")[-1].split("-")[-1] if cat.startswith("checker:USB") else None
        cause = [re.escape(t) for t in toks[:6]] + ([FAMILY[rule]] if rule in FAMILY else []) + ([GENERIC] if not toks and rule not in FAMILY else [])
        R.append(dict(kind="re", files=[os.path.basename(f)] if f else [], cause=cause, line=int(ln.group(1)) if ln else None))
    return R
# Dell spot-run 2026-10-14 (v2conf-run2): these grader-passed fixes still failed on real Omarchy 4.0.4
DELL_CONTRADICTED = {"bottelet/omarchy-cve-watcher", "alanone/omarchy-plugin-cameras"}
def fix_incomplete(c):
    """upstream fix dirs come from hancore/fetch.py, which keeps only extension-listed files, so extensionless helpers (bin/veil) are
    missing from the prompt. A fix whose QML/JS references a plugin-relative helper path not shown would teach 'approve a missing helper'."""
    fs = set(c["files"])
    for f in fs:
        if not f.endswith((".qml", ".js")): continue
        t = open(os.path.join(c["dir"], f), errors="replace").read()
        for m in re.findall(r"[\"'/]((?:bin|scripts|backend|libexec|tools|helpers)/[\w.-]+)[\"']", t):
            if m not in fs and not any(x.endswith("/" + m) for x in fs): return True
    return False
def file_lines(c):
    u = c["messages"][-1]["content"]
    return {m.group(1): m.group(2).count("\n") + 1 for m in re.finditer(r"^### (.+?)\n```\n(.*?)\n```$", u, re.S | re.M)}
def cites_exist(c, out):
    """every blocker's file must be a file shown in the prompt; its line (if given) must be within that file"""
    FL = file_lines(c)
    for f in out.get("findings") or []:
        if not isinstance(f, dict) or str(f.get("severity")).lower() != "blocker": continue
        fn = f.get("file")
        if not fn: continue
        hit = [p for p in FL if p == fn or p.endswith("/" + fn)]
        if not hit: return False
        if isinstance(f.get("line"), int) and f["line"] > max(FL[p] for p in hit): return False
    return True
def ftext(f): return " ".join(str(f.get(k) or "") for k in ("category", "file", "finding"))
def matches(c, out):
    T = [f for f in (out.get("findings") or []) if isinstance(f, dict) and str(f.get("severity", "")).lower() == "blocker"]
    for r in gold_rules(c):
        for f in T:
            t = ftext(f)
            if r["kind"] == "hc":
                if E.norm_cat(f.get("category")) == r["cat"] or any(re.search(x, t, re.I) for x in r["cause"]): return True
                continue
            if r["files"] and not any(x.lower() in t.lower() for x in r["files"]): continue
            if not any(re.search(x, t, re.I) for x in r["cause"]): continue
            if r["line"]:
                nums = [int(n) for n in re.findall(r"(?::|line\s*|L)(\d{1,5})\b", t, re.I)] + ([int(f["line"])] if isinstance(f.get("line"), int) else [])
                if nums and not any(abs(n - r["line"]) <= TOL for n in nums): continue
            return True
    return False
SECREV = re.compile(r"(?i)[^.]*\b(security|supply-chain)(/supply-chain)? (re-)?review\b[^.]*\.\s*")
def template(c):
    t = json.loads(json.dumps(c["target"]))
    if t.get("load") is None: t["load"] = "broken" if t["verdict"] == "changes_requested" and c["source"] != "hancore" else ("unsure" if t["verdict"] == "changes_requested" else "works")
    fl = []
    for f in t["findings"]:
        s = B.clean_finding(f["finding"]); s2 = SECREV.sub("", s).strip()
        s = s2 if len(s2) > 20 else s
        fl.append(dict(category=f["category"], severity=f["severity"], file=f.get("file"), line=f.get("line"), finding=s))
    t["findings"] = fl; return t
def judge(c, guided, r, want, nudged=False):
    why = None; out = None
    if r is None: why = "no_teacher_result"
    elif r["type"] != "succeeded": why = "teacher_errored"
    else:
        m = r["message"]; raw = "".join(b.get("text", "") for b in m.get("content", []) if b.get("type") == "text"); out = E.parse(raw)
        if m.get("stop_reason") == "max_tokens": why = "truncated"
        elif out is None or out.get("verdict") not in ("approve", "changes_requested"): why = "invalid_json"
        elif out["verdict"] != want: why = "verdict_mismatch"
        else:
            shas, names = hallucinations(c, out)
            if shas: why = "invented_sha"
            elif names: why = "invented_plugin_name"
            elif c["label"] == "broken" and not matches(c, out): why = "blocker_reason_mismatch"
            elif guided and re.search(r"maintainer|\bnote\b|\bhint\b|\bDell\b|verified failure", json.dumps(out), re.I): why = "mentions_hint"
            elif not cites_exist(c, out): why = "cited_file_or_line_missing"
            elif nudged and re.search(r"verif|hardware|\btest(ed|ing)\b|\bnote\b|told|stock omarchy 4\.x system", json.dumps(out), re.I): why = "mentions_nudge"
    return why, out
TEACHER = os.environ.get("TEACHER", "qwen/qwen3.5-397b-a17b")
def load_results(model=None, tag=""):
    res = {}
    p = os.path.join(WORK, "teacher", (model or TEACHER).replace("/", "__"), f"results{'.' + tag if tag else ''}.jsonl")
    if os.path.exists(p):
        for l in open(p):
            if l.strip():
                r = json.loads(l)
                if r["custom_id"] not in res or r["result"]["type"] == "succeeded": res[r["custom_id"]] = r["result"]
    return res
def main():
    cands = jl(os.path.join(WORK, "candidates.jsonl")); res = load_results()
    STAGES = [("first", res, False), ("retry", load_results(tag="retry1"), False), ("retry", load_results(tag="retry2"), False), ("nudged", load_results(tag="nudge"), True)]
    TD = os.path.join(WORK, "teacher", TEACHER.replace("/", "__")); st = json.load(open(os.path.join(TD, "state.json")))
    import guided as GD
    G = {g["orig"]: g for g in jl(os.path.join(WORK, "guided.jsonl"))}
    rows, R = [], collections.Counter(); per = []
    for c in cands:
        guided = None
        if c["source"] == "fix_model": R[f"dropped_fix_model_proprietary:{c['split']}"] += 1; continue   # written by proprietary models -> never training data
        if c["source"].startswith("fix_") and fix_incomplete(c): R[f"dropped_fix_helper_missing_from_prompt:{c['split']}:{c['source']}"] += 1; continue
        if c["source"].startswith("fix_") and c["repo"] in DELL_CONTRADICTED: R[f"dropped_fix_dell_contradicted:{c['split']}"] += 1; continue
        if c["label"] == "broken" and c["source"] != "hancore":
            if c["cid"] not in G: R[f"dropped_runtime_only:{c['split']}:{c['source']}"] += 1; continue
            guided = G[c["cid"]]; c = dict(c, target=dict(c["target"], findings=guided["vis"]))   # gold = code-visible failures only
        if c["source"] == "hancore": res.pop(c["cid"], None)                                       # HANCORE: cleaned templated targets only
        want = "approve" if c["label"] == "works" else "changes_requested"; key = guided["cid"] if guided else c["cid"]
        # first try, then up to 2 blind retries (works rows), then one nudged pass (works: told it is verified working; guided: told to name the known bug)
        why, out = judge(c, guided, res.get(key) if c["source"] != "hancore" else None, want); stage = "first"
        if why not in (None, "no_teacher_result") and c["source"] != "hancore":
            for stg, RS, nd in STAGES[1:]:
                if key not in RS: continue
                w2, o2 = judge(c, guided, RS[key], want, nudged=nd)
                if w2 is None: why, out, stage = None, o2, stg; break
                why = w2
        cs = c["source"]
        if why is None:
            tgt = dict(verdict=out["verdict"], load=out.get("load"), findings=[{k: f.get(k) for k in ("category", "severity", "file", "line", "finding")} for f in out.get("findings") or [] if isinstance(f, dict)])
            kind = ("teacher_guided" if guided else "teacher") + ("" if stage == "first" else "_" + stage)
            if stage == "nudged" and not guided: cs = "nudged_approve"
            R[f"stage_kept:{'guided' if guided else 'blind'}:{stage}"] += 1
        else:
            tgt = template(c); kind = ("template_no_teacher" if why == "no_teacher_result" else "template_fallback") + ("_guided" if guided else "")
        R[f"teacher_{'kept' if why is None else ('not_sent' if why == 'no_teacher_result' else 'rejected:' + why)}:{c['source']}:{c['label']}"] += 1
        msgs = P.messages(*_unpack(c), target=tgt)
        tok = qwen_tokens(msgs)
        if tok > ROW_TOKEN_CAP: R["dropped_over_32k_after_target"] += 1; continue
        rows.append(dict(id=f"{c['source']}:{c['repo']}:{c['cid']}", split=c["split"], source=cs, orig_source=c["source"], label=c["label"], verdict=tgt["verdict"], target_kind=kind,
                         reject_reason=why, is_pair_parent=bool(c.get("is_pair_parent")), pair=c.get("pair"), tokens=tok, provenance=c["provenance"], messages=msgs))
    # approve share target 40-50% (train): trim dell_works_verified if above 50%
    tr = [r for r in rows if r["split"] == "train"]; app = sum(r["verdict"] == "approve" for r in tr)
    if app / len(tr) > 0.50:
        k = int(app - 0.48 * len(tr)) // 1; dw = sorted([r for r in tr if r["source"] == "dell_works_verified"], key=lambda r: (r["target_kind"].startswith("teacher"), hashlib.sha1(r["id"].encode()).hexdigest()))
        drop = {r["id"] for r in dw[:int((app - 0.48 * len(tr)) / 0.52)]}; rows = [r for r in rows if r["id"] not in drop]; R["trimmed_works_for_approve_share"] = len(drop)
    # nudged approve rows <= 25% of approve rows per split: convert the excess back to the grader-verified templated approve target
    CB = {c["cid"]: c for c in cands}
    for spn in ("train", "val"):
        S = [r for r in rows if r["split"] == spn]; ap = sum(r["verdict"] == "approve" for r in S); nd = sorted([r for r in S if r["source"] == "nudged_approve"], key=lambda r: hashlib.sha1(r["id"].encode()).hexdigest())
        for r in nd[:max(0, len(nd) - int(0.25 * ap))]:
            c = CB[r["id"].rsplit(":", 1)[1]]; tgt = template(c); r["messages"] = P.messages(*_unpack(c), target=tgt); r["tokens"] = qwen_tokens(r["messages"])
            r["source"] = r["orig_source"]; r["target_kind"] = "template_fallback_nudge_cap"; R[f"nudged_over_cap_to_template:{spn}"] += 1
    os.makedirs(os.path.join(WORK, "final"), exist_ok=True)
    rnd = random.Random(1337); rnd.shuffle(rows)
    for sp in ("train", "val"): wjl(os.path.join(WORK, "final", f"{sp}.jsonl"), [r for r in rows if r["split"] == sp])
    rep = dict(counts={}, reasons=dict(sorted(R.items())))
    for sp in ("train", "val"):
        S = [r for r in rows if r["split"] == sp]; toks = sorted(r["tokens"] for r in S)
        rep["counts"][sp] = dict(total=len(S), by_label=dict(collections.Counter(r["label"] for r in S)), by_verdict=dict(collections.Counter(r["verdict"] for r in S)),
                                 approve_share=round(sum(r["verdict"] == "approve" for r in S) / max(1, len(S)), 3),
                                 by_source=dict(collections.Counter(r["source"] for r in S)), by_target_kind=dict(collections.Counter(f"{r['source']}:{r['target_kind']}" for r in S)),
                                 tokens=dict(min=toks[0], p50=toks[len(toks) // 2], p90=toks[int(len(toks) * .9)], p99=toks[int(len(toks) * .99)], max=toks[-1], mean=round(sum(toks) / len(toks)), total=sum(toks)) if toks else None)
    import glob
    allsp = {os.path.basename(p): round(json.load(open(p))["spend_usd"], 4) for p in glob.glob(os.path.join(WORK, "teacher", "*", "state*.json"))}
    rep["spend"] = dict(teacher=TEACHER, usd=round(sum(allsp.values()), 4), by_state=allsp, rows=len(st["done"]), note="OpenRouter usage.cost; open-weights teacher only")
    rep["sha256"] = {f: hashlib.sha256(open(os.path.join(WORK, "final", f), "rb").read()).hexdigest() for f in ("train.jsonl", "val.jsonl")}
    wjson(os.path.join(WORK, "final", "report.json"), rep)
    kept = [r for r in rows if r["target_kind"].startswith("teacher")]; sp = random.Random(20261014).sample(kept, min(20, len(kept)))
    wjson(os.path.join(WORK, "final", "spot_check.json"), [dict(id=r["id"], split=r["split"], label=r["label"], tokens=r["tokens"], files=[l[4:] for l in r["messages"][-2]["content"].splitlines() if l.startswith("### ")][:12],
                                                               checker=r["messages"][-2]["content"].split("## Plugin source")[0][:600], target=json.loads(r["messages"][-1]["content"])) for r in sp])
    print(json.dumps(rep, indent=1))
def _unpack(c):
    u = c["messages"][-1]["content"]; rep_s, code = u.split("\n\n## Plugin source\n", 1); rep_s = rep_s.removeprefix("## Checker report\n")
    rep = None if rep_s == "(Checker report unavailable)" else [] if rep_s == "(no Checker findings)" else rep_s.split("\n")
    assert P.messages(code, rep)[-1]["content"] == u
    return code, rep
if __name__ == "__main__": main()
