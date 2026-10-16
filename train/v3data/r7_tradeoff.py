#!/usr/bin/env python3
"""r7 tradeoff table: load every candidate row once (no caps), re-run r7_merge.pipeline over a grid of settings, print markdown (rows, per-category verified/provisional + file-and-line share, approve share, source mix).
usage: r7_tradeoff.py OUT.md DIR [DIR ...]"""
import sys, os, json, itertools, collections, tempfile
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import r7_merge as RM


def stats(rows):
    n = len(rows) or 1; kinds = collections.defaultdict(lambda: [0, 0, 0, 0])      # n findings, verified rows, provisional rows, with line
    for r in rows:
        for a in RM.tgt(r)["added_findings"]:
            k = kinds[a["category"]]; k[0] += 1; k[1 if not r["meta"]["provisional"] else 2] += 1; k[3] += 1 if a.get("line", 0) > 0 and a.get("file") else 0
    src = collections.Counter(r["source"] for r in rows); tri = [t for r in rows for t in RM.tgt(r)["scripts_triage"]]
    return dict(rows=len(rows), verified=sum(1 for r in rows if not r["meta"]["provisional"]), prov=sum(1 for r in rows if r["meta"]["provisional"]), approve=sum(map(RM.is_approve, rows)) / n,
                kinds={k: tuple(v) for k, v in kinds.items()}, src={k: round(v / n, 2) for k, v in src.most_common()}, dismiss=(sum(1 for t in tri if t["decision"] == "dismiss") / len(tri)) if tri else 0,
                types=dict(collections.Counter(r["row_type"] for r in rows)), plugins=len({r["meta"]["repo"] for r in rows}))


def grid():
    for hist, dis, floor, dell, amin in itertools.product((0.55, 0.70, 0.85), (0.35, 0.50), (15, 10), (0.30, 0.40), (0.0, 0.45)):
        yield dict(hist=hist, dismiss=dis, floor=floor, dell=dell, amin=amin)


def main(out, dirs):
    sys.argv = ["x", tempfile.mkdtemp(), tempfile.mkdtemp()]; import build_scope as B
    rows = RM.load_rows(dirs); base = stats(rows); L = ["# r7 tradeoff table\n", f"candidate pool before any cap/floor: {json.dumps(base)}\n",
        "| hist cap | dismiss max | floor | Dell cap | approve>= | rows | train+val plugins | verified/prov | approve | dismiss share | row types | sources | per-category n (ver/prov rows, file+line%) |", "|" + "---|" * 13]
    for p in grid():
        ver, st = RM.pipeline(rows, B, floor=p["floor"], dell=p["dell"], dismiss=p["dismiss"], src=0.40, hist=p["hist"], amax=0.50, amin=p["amin"]); s = stats(ver)
        kk = "; ".join(f"{k} {v[0]} ({v[1]}/{v[2]}, {100 * v[3] // max(1, v[0])}%)" for k, v in sorted(s["kinds"].items())) or "-"
        L.append(f"| {int(p['hist'] * 100)}% | {int(p['dismiss'] * 100)}% | {p['floor']} | {int(p['dell'] * 100)}% | {p['amin'] or '-'} | {s['rows']} | {s['plugins']} | {s['verified']}/{s['prov']} | {s['approve']:.0%} | {s['dismiss']:.0%} | {s['types']} | {s['src']} | {kk} |")
        print(L[-1][:200], flush=True)
    open(out, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
