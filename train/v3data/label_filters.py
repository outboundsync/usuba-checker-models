"""Label-quality filters (audit part E). Pure functions, unit-tested in tests/test_label_filters.py; build_r5.py applies them.

attribution   a HANCORE finding belongs to ONE reviewed commit: the most common reviewed SHA among the plugin's finding comments (strict mode of
              hancore/common.py: a "fixed in <sha>" sentence names the FIXED code, a foreign-repo commit URL is not this plugin's). A row is kept only when
              its recorded commit IS that SHA (so the shown source is the reviewed code). Findings on other SHAs of the same plugin are not this row's evidence.
retractions   findings the reviewer later withdrew (hancore/retraction_check.py output): whole withdrawal = drop the row, partial = drop too (we cannot
              tell which part remains), listed ids come from retraction_list.json (decisions made by an open-weights judge, cached) .
synthetic     generator-made rows carry template tells (manifest id sample./example., row ids syn.*): documented exclusion by default (SYNTHETIC_POLICY)."""
import re, json, collections

SYNTHETIC_POLICY = "exclude"          # "exclude" | "keep": r5 excludes synthetic_lifecycle rows (template-tell artefacts: sample.* manifest ids, 8 rows, label deducible from the id family)
TEMPLATE_ID = re.compile(r'"id"\s*:\s*"(sample|example|syn)[.\-]', re.I)


def plugin_url_key(row_id):
    """hancore_concrete:owner/name:sha10 -> https://github.com/owner/name (lower-case)"""
    repo = row_id.split(":", 1)[1].rsplit(":", 1)[0]
    return "https://github.com/" + repo.lower()


def attribution(strict, row_id, row_commit):
    """-> (ok, reason). strict = hancore.common.load(strict_sha=True) with lower-cased keys."""
    d = strict.get(plugin_url_key(row_id))
    if d is None: return False, "attribution:plugin_not_in_strict_reviews"
    if not d["sha"]: return False, "attribution:no_reviewed_sha"
    if not row_commit or not d["sha"].startswith(row_commit[:10]) and not row_commit.startswith(d["sha"][:10]): return False, "attribution:row_commit_is_not_the_reviewed_sha"
    return True, None


def plurality_table(HC, plugins=None):
    """r6 attribution (Harris 2026-10-15): plurality of the reviewed SHAs that finding comments NAME THEMSELVES (no carry-forward from earlier comments, no back-fill from later
    ones; "fixed in <sha>" and foreign-repo commits are not reviewed SHAs). Plugin -> dict(status, sha, counts).
      ok               one SHA has strictly more explicit mentions than any other (a single mention counts)
      tie              the top two SHAs have equal counts (serial re-reviews at different HEADs): DROP, the choice would be arbitrary
      unresolvable     no finding comment names a reviewed SHA: DROP
      sha_after_review the plurality SHA is first named AFTER a finding comment that names no SHA (the legacy loader back-filled it from the later comment): DROP
    Measured on 4,799 reviewed plugins: ok 2,3xx / tie 1,9xx / unresolvable 4xx (see v3/r6/GATE_REPORT.md)."""
    out = {}
    for p, d in (plugins if plugins is not None else HC.load(strict_sha=True)).items():
        res = []
        for x in sorted(d["items"], key=lambda x: x["date"]):
            if x["item_type"] != "finding" or set(x["categories"]) <= {"clean-review-no-blocker"}: continue
            c = HC.reviewed_shas(x["text"], HC.repo_of(p)); res.append((x["date"], c[0] if c else None))
        cnt = collections.Counter(s for _, s in res if s); top = cnt.most_common(2)
        if not cnt: out[p.lower()] = dict(status="unresolvable", sha=None, counts=dict(cnt)); continue
        if len(top) > 1 and top[0][1] == top[1][1]: out[p.lower()] = dict(status="tie", sha=None, counts=dict(cnt)); continue
        sha = top[0][0]; first = min(dt for dt, s in res if s == sha)
        late = any(s is None and dt < first for dt, s in res)
        out[p.lower()] = dict(status="sha_after_review" if late else "ok", sha=sha, counts=dict(cnt))
    return out


def attribution_v2(table, row_id, row_commit):
    """-> (ok, reason). table = plurality_table(...). A row is kept only when its plugin is `ok` and the row's commit IS the plurality reviewed SHA."""
    d = table.get(plugin_url_key(row_id))
    if d is None: return False, "attribution:plugin_not_in_reviews"
    if d["status"] != "ok": return False, "attribution:" + d["status"]
    if not row_commit or not (d["sha"].startswith(row_commit[:10]) or row_commit.startswith(d["sha"][:10])): return False, "attribution:row_commit_is_not_the_plurality_sha"
    return True, None


def cited_line_exists(files, finding):
    """the finding's file is in the attributed-SHA source and its cited line is inside it (and not blank): a label can only cite code that exists at that SHA"""
    t = files.get(finding.get("file"))
    if t is None or not isinstance(finding.get("line"), int): return False
    lines = t.replace("\r\n", "\n").split("\n")
    return 1 <= finding["line"] <= len(lines) and bool(lines[finding["line"] - 1].strip())


def lower_keys(d): return {k.lower(): v for k, v in d.items()}


def retraction_ids(retraction_list):
    """row ids with a whole or partial retracted finding"""
    return {x["row"] for x in retraction_list if x.get("retracted") or x.get("retracted_partial")}


def synthetic_reason(row):
    """why a row is an artefact of the generator, or None"""
    src = row.get("source") or ""
    if src == "synthetic_lifecycle" or (row.get("provenance") or {}).get("marked") == "SYNTHETIC" or str(row.get("id", "")).startswith("syn."): return "synthetic_row"
    return None


def template_id_fraction(rows):
    """share of rows (by verdict) whose manifest id follows the generator template: a label-correlated tell if it is skewed"""
    c = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        u = r["messages"][-2]["content"]; k = r["verdict"]; c[k][0] += 1; c[k][1] += bool(TEMPLATE_ID.search(u))
    return {k: dict(rows=n, template_id=t, share=round(t / n, 3) if n else 0) for k, (n, t) in c.items()}
