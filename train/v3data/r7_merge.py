#!/usr/bin/env python3
"""r7: merge scope-v4 row sets (r6 scope build + below-floor rows + security subset + history-mining output), dedupe by plugin+version, then (in this order)
per-slug floor (>=15 added findings else the slug's rows are dropped), Dell share cap, provisional-dismiss cap (dismiss items <= DISMISS_MAX of all triage items),
per-source cap (<= SRC_MAX of any source; version_history <= HIST_MAX), approve cap, floor again, plugin-level split (all rows of a plugin in one split).
usage: r7_merge.py OUTDIR DIR [DIR ...]   (env R7_SRC_MAX 0.40, R7_HIST_MAX 0.55, R7_DISMISS_MAX 0.35, R6S_APPROVE_MAX 0.50, R6S_DELL_SHARE 0.30)"""
import sys, os, json, gzip, random, collections, tempfile
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
E_ = os.environ.get
SRC_MAX = float(E_("R7_SRC_MAX", "0.40")); HIST_MAX = float(E_("R7_HIST_MAX", "0.55")); DISMISS_MAX = float(E_("R7_DISMISS_MAX", "0.35")); APPROVE_MAX = float(E_("R6S_APPROVE_MAX", "0.50"))


def tgt(r): return json.loads(r["messages"][-1]["content"])
def is_approve(r): return tgt(r)["verdict"] == "approve"
def n_dismiss(r): return sum(1 for t in tgt(r)["scripts_triage"] if t["decision"] == "dismiss")
def n_triage(r): return len(tgt(r)["scripts_triage"])
def prio(r): return ({"extend": 0, "triage": 1, "clean": 2}[r["row_type"]], r["meta"]["provisional"], r["id"])      # larger = dropped first


def load_rows(dirs):
    rows, seen = [], set()
    for d in dirs:
        for fn in ("train", "val", "below_floor"):
            p = os.path.join(d, fn + ".jsonl.gz")
            if not os.path.exists(p): continue
            for l in gzip.open(p, "rt"):
                r = json.loads(l); k = (r["meta"]["repo"], r["meta"]["commit"], r["row_type"])
                if r["id"] in seen or k in seen: continue
                seen.add(r["id"]); seen.add(k); r["_repo"] = r["meta"]["repo"]; r["_fh"] = frozenset(); r.pop("split", None); rows.append(r)
    return rows


def cap_dismiss(rows, dmax=None):
    """drop provisional rows (most dismiss items first; rows with an extend finding or a confirm last) until dismiss items <= dmax of all triage items. Verified-tier rows are never dropped here."""
    dmax = DISMISS_MAX if dmax is None else dmax; rows = list(rows)
    def share(rs):
        t = sum(map(n_triage, rs)); return (sum(map(n_dismiss, rs)) / t) if t else 0.0
    cand = sorted([r for r in rows if r["meta"]["provisional"] and n_dismiss(r)], key=lambda r: (-(n_dismiss(r) / max(1, n_triage(r))), r["row_type"] == "extend", r["id"]))
    dropped = 0
    for r in cand:
        if share(rows) <= dmax: break
        rows.remove(r); dropped += 1
    return rows, dropped


def cap_sources(rows, src_max=None, hist_max=None):
    src_max = SRC_MAX if src_max is None else src_max; hist_max = HIST_MAX if hist_max is None else hist_max; rows = list(rows)
    for _ in range(200):
        n = len(rows); cnt = collections.Counter(r["source"] for r in rows)
        over = [(s, c) for s, c in cnt.items() if c / n > (hist_max if s == "version_history" else src_max)]
        if not over: break
        s, c = max(over, key=lambda x: x[1] / n); lim = hist_max if s == "version_history" else src_max
        k = max(1, c - int(lim * (n - 1))); ids = {r["id"] for r in sorted([r for r in rows if r["source"] == s], key=prio, reverse=True)[:k]}
        rows = [r for r in rows if r["id"] not in ids]
    return rows


def cap_approve(rows, amax=None):
    amax = APPROVE_MAX if amax is None else amax; rows = list(rows)
    while rows and sum(map(is_approve, rows)) / len(rows) > amax:
        c_ = [r for r in rows if is_approve(r) and r["row_type"] == "clean"] or [r for r in rows if is_approve(r)]
        rows.remove(sorted(c_, key=prio, reverse=True)[0])
    return rows


def split_rows(rows, seed=7):
    rnd = random.Random(seed); plugins = sorted({r["_repo"] for r in rows}); rnd.shuffle(plugins); val = set(plugins[:max(1, len(plugins) // 10)]); tr, va = [], []
    for r in rows:
        r = {k: v for k, v in r.items() if not k.startswith("_")}; r["split"] = "val" if r["meta"]["repo"] in val else "train"; (va if r["split"] == "val" else tr).append(r)
    return tr, va, plugins


def lift_approve(rows, lo):
    """approve share below `lo`: drop the lowest-priority NON-approve rows (provisional first) until it reaches `lo`; never drops an approve row"""
    rows = list(rows)
    while rows and sum(map(is_approve, rows)) / len(rows) < lo:
        c_ = [r for r in rows if not is_approve(r)]
        if not c_: break
        rows.remove(sorted(c_, key=prio, reverse=True)[0])
    return rows


def pipeline(rows, B, floor=15, dell=0.30, dismiss=0.35, src=0.40, hist=0.55, amax=0.50, amin=0.0):
    """-> (rows, stats). Order: floor, Dell cap, dismiss cap, source caps, approve cap (<= amax), approve lift (>= amin), floor again. B = build_scope (module globals FLOOR / DELL_SHARE are set here)."""
    B.FLOOR = floor; B.DELL_SHARE = dell; B.BELOW.clear(); st = {}
    ver, c, low = B.enforce_floor(list(rows)); st["floor_dropped_slugs"] = low
    ver = B.cap_dell(ver); ver, st["dismiss_rows_dropped"] = cap_dismiss(ver, dismiss); ver = cap_sources(ver, src, hist); ver = cap_approve(ver, amax)
    if amin: ver = lift_approve(ver, amin)
    ver, c, low2 = B.enforce_floor(ver); st["floor_dropped_slugs_2"] = low2; st["slug_counts"] = dict(c)
    return ver, st


def main(out, dirs):
    os.makedirs(out, exist_ok=True); sys.argv = ["x", tempfile.mkdtemp(), out]
    import build_scope as B
    rows = load_rows(dirs); st = dict(input_rows=len(rows), by_source_in=dict(collections.Counter(r["source"] for r in rows)))
    ver, s2 = pipeline(rows, B, floor=int(E_("R6S_FLOOR", "15")), dell=float(E_("R6S_DELL_SHARE", "0.30")), dismiss=DISMISS_MAX, src=SRC_MAX, hist=HIST_MAX, amax=APPROVE_MAX, amin=float(E_("R7_APPROVE_MIN", "0")))
    st.update(s2); tr, va, plugins = split_rows(ver)
    for name, rs in (("train", tr), ("val", va)):
        with gzip.open(os.path.join(out, name + ".jsonl.gz"), "wt") as f:
            for r in rs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    st.update(rows=len(tr) + len(va), train=len(tr), val=len(va), plugins=len(plugins))
    json.dump(st, open(os.path.join(out, "merge_stats.json"), "w"), indent=1); print(st)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
