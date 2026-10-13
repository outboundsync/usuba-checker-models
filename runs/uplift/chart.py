"""Two charts from runs/uplift/<model>/rows.jsonl + handcheck.json ({model: {"<i>": {"r0": bool, "final": bool, "note": str}}}).
Outcome of each prompt (final answer = first passing attempt, else the last attempt):
  works right away  : the first answer passes the Checker AND passed the hand-check
  fixed by Checker  : the first answer did not count, a later answer (after Checker feedback) passes the Checker AND passed the hand-check
  fully broken      : the final answer does not load at all - no files, manifest/entry invalid, QML syntax/import/unknown type,
                      or the shell failed to load/instantiate it (LOAD_FAIL categories below), or it was cut off / looped with no usable files
  still buggy       : everything else - it loads but the Checker still reports errors, or it passed the Checker but failed the hand-check
Truncated and looping answers never count as passes."""
import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__))
FRONTIER = {"gpt-5.6-sol": "GPT-5.6 Sol", "claude-opus-5.5": "Claude Opus 5.5", "claude-sonnet-5.5": "Claude Sonnet 5.5", "gemini-3.1-pro": "Gemini 3.1 Pro", "grok-4.3": "Grok 4.3", "grok-4.7": "Grok 4.7", "gemini-4-argon": "Gemini 4 Argon", "muse-wonder": "Muse Wonder *"}
NOZDR_NOTE = "* Muse Wonder ran without zero data retention (its only provider, Meta, is not ZDR). All other models ran with ZDR."
OPEN = {"qwen3.6-27b": "Qwen3.6 27B", "qwen3-coder": "Qwen3-Coder", "kimi-k3": "Kimi K3", "deepseek-v4-pro": "DeepSeek V4 Pro"}
LOAD_FAIL = {"no-files-parsed", "manifest", "entry-not-qml", "no-qml", "not-shell-surface", "bad-import", "qt5-api", "qml-syntax",
             "usuba-USB-T01", "usuba-USB-T02", "usuba-USB-Q01", "usuba-USB-A03",
             "rt-load-failed", "rt-unresolved-type/import", "rt-not-instantiated", "rt-manifest-rejected", "rt-qml-syntax", "rt-shell-broken"}
import csv, collections
ROWS = list(csv.DictReader(open(os.path.join(H, "results.csv"))))
missing = []; MISS = []
def outcomes(m):
    R = [r for r in ROWS if r["model"] == m]
    if len(R) < 49: missing.append(f"{FRONTIER.get(m) or OPEN.get(m)} ({len(R)}/49 finished)"); MISS.append(("Frontier models" if m in FRONTIER else "Open models", FRONTIER.get(m) or OPEN.get(m), len(R))); return None
    o = collections.Counter(r["category"] for r in R)
    assert not o.get("unchecked"), (m, "hand check incomplete")
    first = o["works right away"]; after = first + o["fixed by Checker"]
    return {k: o[k] for k in ("works right away", "fixed by Checker", "still buggy", "fully broken")}, first, after, sum(float(r["fix_cost_usd"]) for r in R)
data = []
for grp, D in (("Frontier models", FRONTIER), ("Open models", OPEN)):
    for m, lab in D.items():
        x = outcomes(m)
        if x: data.append((grp, lab, *x))
BG, INK, MUTE = "#fbfaf7", "#222", "#666"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
def frame(ax):
    ax.set_facecolor(BG)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#bbb"); ax.tick_params(axis="y", length=0)
def rows_by_group(key):
    out = []
    for grp in ("Open models", "Frontier models"):
        g = sorted([d for d in data if d[0] == grp], key=key) + [(grp, lab, None, n, None, None) for gg, lab, n in MISS if gg == grp]
        if g: out.append((grp, g))
    return out
# (1) dot chart
fig, ax = plt.subplots(figsize=(8.4, 0.45 * (len(data) + len(MISS) + 3) + 1.6)); fig.patch.set_facecolor(BG); frame(ax)
y = 0; ticks, labs = [], []
for grp, g in rows_by_group(lambda d: (d[4], d[3])):
    col = "#3b6ea8" if grp.startswith("Frontier") else "#c2703d"
    for _, lab, o, first, after, cost in g:
        if o is None:
            ax.text(0.5, y, f"missing: finished {first}/49 prompts", va="center", fontsize=9, color="#999", style="italic")
            ticks.append(y); labs.append(lab); y += 1; continue
        ax.plot([first, after], [y, y], color=col, alpha=0.4, lw=2.5, zorder=1)
        ax.scatter([first], [y], s=50, facecolor=BG, edgecolor=col, lw=1.6, zorder=2); ax.scatter([after], [y], s=50, color=col, zorder=3)
        ax.text(max(first, after) + 0.9, y, f"{first} → {after}", va="center", fontsize=9, color="#444")
        ticks.append(y); labs.append(lab); y += 1
    ax.text(0, y - 0.25, grp, fontsize=9, color=col, weight="bold"); y += 1.2
ax.set_yticks(ticks); ax.set_yticklabels(labs); ax.set_xlim(0, 49); ax.set_ylim(-0.8, y - 0.7)
# reference markers. REF_HUMAN comes from runs/rescore404/SCOREBOARD_USUBA.md ("human reference (ceiling) | 27"): Checker passes, not hand-checked.
REF_HUMAN = 27
ax.axvline(REF_HUMAN, color="#555", ls="--", lw=1, zorder=0)
ax.text(REF_HUMAN + 0.3, y - 0.9, f"person-written reference: {REF_HUMAN}/49", fontsize=8, color="#555", va="top")
ff = [d[3] for d in data if d[0] == "Frontier models"]          # frontier first tries, only from models that finished all 49
if ff:
    ax.axvspan(min(ff), max(ff), color="#3b6ea8", alpha=0.08, zorder=0)
    ax.text(min(ff) + 0.3, -0.55, f"frontier first tries: {min(ff)}-{max(ff)}/49", fontsize=8, color="#3b6ea8", va="top")
else: missing_ref = "frontier first-try marker omitted: no frontier model finished all 49"
ax.grid(axis="x", color="#e6e3dc", lw=0.8); ax.set_axisbelow(True)
ax.set_xlabel("working plugins out of 49 prompts (checked by hand)", color="#555")
ax.scatter([], [], s=50, facecolor=BG, edgecolor="#777", label="first try"); ax.scatter([], [], s=50, color="#777", label="after Checker fixes")
ax.legend(loc="lower right", frameon=False)
fig.suptitle("How many plugins work: first try vs after Checker fixes", x=0.02, ha="left", fontsize=13, weight="bold", color=INK)
ax.set_title("Up to 3 fix attempts using only the Usuba Checker's feedback · Omarchy 4.0.4", loc="left", fontsize=9, color=MUTE)
fig.text(0.02, 0.005, NOZDR_NOTE + ("  " + missing_ref if not ff else ""), fontsize=8, color=MUTE)
plt.tight_layout(rect=(0, 0.03, 1, 1)); plt.savefig(os.path.join(H, "uplift.png"), dpi=150, facecolor=BG); plt.close(fig)
# (2) stacked 100% bars
CATS = [("works right away", "#2f7d4f"), ("fixed by Checker", "#8cc79f"), ("still buggy", "#e7b75f"), ("fully broken", "#c8553d")]
fig, ax = plt.subplots(figsize=(9, 0.45 * (len(data) + len(MISS) + 3) + 1.8)); fig.patch.set_facecolor(BG); frame(ax)
y = 0; ticks, labs = [], []
for grp, g in rows_by_group(lambda d: (d[2]["works right away"] + d[2]["fixed by Checker"], d[2]["works right away"])):
    for _, lab, o, n, *_ in g:
        if o is None:
            ax.text(1, y, f"missing: finished {n}/49 prompts", va="center", fontsize=9, color="#999", style="italic")
            ticks.append(y); labs.append(lab); y += 1; continue
        left = 0
        for c, col in CATS:
            w = 100 * o[c] / 49
            ax.barh(y, w, left=left, color=col, height=0.68, edgecolor=BG, lw=1)
            if o[c] >= 3: ax.text(left + w / 2, y, str(o[c]), ha="center", va="center", fontsize=8, color="white" if c in ("works right away", "fully broken") else INK)
            left += w
        ticks.append(y); labs.append(lab); y += 1
    ax.text(0, y - 0.3, grp, fontsize=9, color=MUTE, weight="bold"); y += 1.2
ax.set_yticks(ticks); ax.set_yticklabels(labs); ax.set_xlim(0, 100); ax.set_ylim(-0.8, y - 0.7)
ax.set_xlabel("share of the 49 prompts (%)  ·  numbers in bars are prompt counts", color="#555")
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=col) for _, col in CATS], labels=[c for c, _ in CATS], ncol=4, frameon=False,
          loc="upper left", bbox_to_anchor=(0, -0.09), fontsize=9)
fig.suptitle("What happens to each plugin", x=0.02, ha="left", fontsize=13, weight="bold", color=INK)
ax.set_title("Working = passes the Usuba Checker and a hand check · fully broken = does not load at all", loc="left", fontsize=9, color=MUTE)
fig.text(0.02, 0.005, NOZDR_NOTE, fontsize=8, color=MUTE)
plt.tight_layout(rect=(0, 0.03, 1, 1)); plt.savefig(os.path.join(H, "outcomes.png"), dpi=150, facecolor=BG); plt.close(fig)
md = ["| group | model | first try /49 | after Checker fixes /49 | works right away | fixed by Checker | still buggy | fully broken | spend (fixes) |", "|---|---|---|---|---|---|---|---|---|"]
for grp, lab, o, first, after, cost in sorted(data, key=lambda d: (d[0], -d[4])):
    md.append(f"| {grp} | {lab} | {first} | {after} | {o['works right away']} | {o['fixed by Checker']} | {o['still buggy']} | {o['fully broken']} | ${cost:.2f} |")
md += [f"| missing | {x} | | | | | | | |" for x in missing]
open(os.path.join(H, "TABLE.md"), "w").write("Source: runs/uplift/results.csv (categories defined in runs/uplift/export.py)\n\n" + "\n".join(md) + "\n\n" + NOZDR_NOTE + "\n"); print("\n".join(md))
