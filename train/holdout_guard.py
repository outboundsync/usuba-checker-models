#!/usr/bin/env python3
"""Holdout / Dell-key guard (audit A12): ONE module imported by every builder, by train_lora.py at load, and by midcheck.

A row is rejected when ANY of these holds:
  * repo      its provenance names a sealed-holdout repo (public id list eval/hancore_holdout/plugin_ids.txt)
  * id        its manifest id equals a holdout manifest id or a Dell-key plugin id (case-insensitive)
  * content   >= 50% of its non-trivial shown files are exact (whitespace-normalised) or near (bottom-k shingle Jaccard >= 0.5) matches of files of ONE holdout plugin
              or ONE Dell-key plugin. Content is compared on what the model actually sees (the code blob in the row's last user message, line-number prefixes stripped),
              so renamed forks/copies, one-character edits and truncated files are caught.
  * file      ANY single non-trivial shown file with shingle Jaccard >= 0.5 against a file of a holdout / Dell-key plugin (scaffolds shared by > BOILERPLATE plugins excepted)
  * same_name the row's repo name or manifest-id name equals a holdout / Dell-key plugin name (normalised, >= MIN_NAME chars), unless the pair is on the reviewed
              allow-list guard_data/SAME_NAME_ALLOW.json (different code under one name, checked by content)
  * same_author  the row's repo owner / manifest author equals the author of a holdout / Dell-key plugin AND any file has Jaccard >= AUTHOR_JACCARD (0.3) with that author's plugin
  * unknown   it names no repo and no recognised provenance kind (FAILS CLOSED: unknown provenance is an error, not a pass)
Fingerprints are hashes only (guard_data/fingerprints.json.gz, built by build_guard_fingerprints.py from the private holdout code + the Dell-key trees; the
plaintext never enters the training repo's data path).

    python3 train/holdout_guard.py train.jsonl[.gz] val.jsonl[.gz] ...      # exit 1 on any hit
    from holdout_guard import Guard; g = Guard(); g.assert_clean(rows)        # builders, train_lora
"""
import gzip, json, os, re, sys, hashlib, zlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
IDS = os.environ.get("HOLDOUT_IDS") or os.path.join(HERE, "..", "eval", "hancore_holdout", "plugin_ids.txt")
FP = os.environ.get("USUBA_GUARD_FP") or os.path.join(HERE, "guard_data", "fingerprints.json.gz")
_GH = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?\"'\s]|$)", re.I)
K = 128; JACCARD = 0.5; FILE_SHARE = 0.5; BOILERPLATE = 4
AUTHOR_JACCARD = 0.3     # a plugin by the SAME AUTHOR as a holdout/Dell-key plugin is rejected at this lower per-file similarity (authors copy their own code between plugins)
MIN_NAME = 6             # shorter normalised plugin names (bar, clock, notes) are too generic for a same-name rule
KNOWN_KINDS = ("synthetic", "winners-mit", "upstream-fix", "dell-sweep", "dell-sweep+checker-agree", "hancore-concrete-verified", "version-history-fix",
               "jankeesvw-history-fixed", "jankeesvw-history-broken", "jankeesvw-history", "clean-registry")


def norm(url):
    m = _GH.search(url if url.endswith("/") else url + "/")
    return (m.group(1) + "/" + m.group(2)).lower() if m else None


def load_ids(path=IDS):
    ids = {norm(l.strip()) for l in open(path) if l.strip()}
    ids.discard(None)
    if len(ids) < 300:
        raise SystemExit(f"holdout id list looks wrong ({len(ids)} ids) at {path}")
    return ids


# ---------------------------------------------------------------- content fingerprints
def ws_hash(text): return hashlib.sha1(re.sub(r"\s+", "", text).encode()).hexdigest()


def sketch(text, k=K):
    """bottom-k sketch of 5-token shingles (sorted list of 32-bit hashes), exact set for short files"""
    toks = re.findall(r"\w+|[^\w\s]", text)
    if len(toks) < 5: toks = toks + ["\0"] * (5 - len(toks))
    hs = {zlib.crc32(" ".join(toks[i:i + 5]).encode()) for i in range(len(toks) - 4)}
    return sorted(hs)[:k]


def jaccard(a, b, k=K):
    if not a or not b: return 0.0
    if len(a) < k and len(b) < k:
        sa, sb = set(a), set(b); return len(sa & sb) / len(sa | sb)
    u = sorted(set(a) | set(b))[:k]; sa, sb = set(a), set(b)
    return sum(1 for x in u if x in sa and x in sb) / len(u)


def trivial(path, text):
    """files that carry no plugin identity: README/LICENSE, tiny files, manifest.json (boilerplate; its id is compared separately)"""
    return path.lower().startswith(("readme", "license", "copying")) or path == "manifest.json" or len(text.strip()) < 200


_NUM = re.compile(r"^ *\d+\| ?", re.M)
_HEAD = re.compile(r"(?:^|\n\n)### ([^\n]+)\n")


def parse_blob(user_content):
    """{path: text} from the 'Plugin source' part of a row's last user message (numbered v4 blobs and plain v2/v3 blobs; omitted files are skipped)."""
    i = user_content.find("## Plugin source\n")
    body = user_content[i + len("## Plugin source\n"):] if i >= 0 else user_content
    heads = list(_HEAD.finditer(body)); out = {}
    for k, m in enumerate(heads):
        seg = body[m.end(): heads[k + 1].start() if k + 1 < len(heads) else len(body)]
        if not seg.startswith("```\n"): continue                       # (omitted: ...) placeholder
        seg = seg[4:]
        end = seg.rfind("\n```")
        if end < 0: continue
        t = seg[:end]
        out[m.group(1)] = _NUM.sub("", t) if re.match(r" *\d+\| ?", t) else t
    return out


def file_fp(text):
    return dict(h=ws_hash(text), s=sketch(text))


def tree_fp(files):
    return [file_fp(t) for p, t in sorted(files.items()) if not trivial(p, t)]


def norm_name(x):
    x = re.sub(r"[^a-z0-9]", "", str(x).lower())
    return x[len("omarchy"):] if x.startswith("omarchy") and len(x) > len("omarchy") + 3 else x


def _mid_parts(mid):
    parts = [q for q in str(mid or "").split(".") if q]
    if len(parts) >= 3 and parts[0] == "io" and parts[1] == "github": return parts[2], ".".join(parts[3:])
    return (parts[0], ".".join(parts[1:])) if len(parts) >= 2 else ("", parts[0] if parts else "")


def plugin_names(m):
    out = {norm_name(m["repo"].split("/")[-1])} if m.get("repo") else set()
    nm = _mid_parts(m.get("mid") or m.get("id"))[1]
    if nm: out.add(norm_name(nm))
    return {n for n in out if len(n) >= MIN_NAME}


def plugin_authors(m):
    out = {m["repo"].split("/")[0].lower()} if m.get("repo") else set()
    au = _mid_parts(m.get("mid") or m.get("id"))[0].lower()
    if au: out.add(au)
    return {a for a in out if len(a) >= 4}


ALLOW = os.environ.get("USUBA_SAME_NAME_ALLOW") or os.path.join(HERE, "guard_data", "SAME_NAME_ALLOW.json")


def load_allow(path=ALLOW):
    """reviewed same-name pairs: {"pairs": [{"repo": "owner/name", "holdout_repo": "owner/name"}]} -> set of (repo, holdout_repo)"""
    if not os.path.exists(path): return set()
    return {(x["repo"].lower(), x["holdout_repo"].lower()) for x in json.load(open(path)).get("pairs", [])}


class Guard:
    def __init__(self, fp_path=FP, ids_path=IDS):
        self.repos = load_ids(ids_path)
        if not os.path.exists(fp_path):
            raise SystemExit(f"HOLDOUT GUARD: fingerprint file missing: {fp_path} (build_guard_fingerprints.py); the guard fails closed")
        d = json.load(gzip.open(fp_path, "rt"))
        if len(d["holdout"]) < 300: raise SystemExit(f"HOLDOUT GUARD: fingerprint file has {len(d['holdout'])} holdout plugins")
        self.fp_sha = hashlib.sha256(open(fp_path, "rb").read()).hexdigest()
        self.mids = {x.lower() for x in d["manifest_ids"]}
        self.dell_ids = {x.lower() for x in d["dell_ids"]}
        self.repos |= {r.lower() for r in d.get("repos", [])}
        self.plugins = [("holdout", i, p) for i, p in enumerate(d["holdout"])] + [("dell", i, p) for i, p in enumerate(d["dell_trees"])]
        self.meta = [dict(kind="holdout", **m) for m in (d.get("holdout_meta") or [{}] * len(d["holdout"]))] + [dict(kind="dell", **m) for m in (d.get("dell_meta") or [{}] * len(d["dell_trees"]))]
        self.names, self.authors = collections.defaultdict(set), collections.defaultdict(set)
        for pi, m in enumerate(self.meta):
            for nm in plugin_names(m): self.names[nm].add(pi)
            for au in plugin_authors(m): self.authors[au].add(pi)
        self.allow = load_allow()
        self.exact = collections.defaultdict(set); self.inv = collections.defaultdict(set); self.files = {}
        for pi, (_, _, files) in enumerate(self.plugins):
            for fi, f in enumerate(files):
                self.exact[f["h"]].add(pi); self.files[(pi, fi)] = f["s"]
                for v in f["s"]: self.inv[v].add((pi, fi))

    # --- one file against the index -> set of plugin indexes it matches
    def match_file(self, text, thr=None):
        thr = JACCARD if thr is None else thr
        h = ws_hash(text); hit = set(self.exact.get(h, ()))
        s = sketch(text); cand = collections.Counter()
        for v in s:
            for key in self.inv.get(v, ()): cand[key] += 1
        for key, c in cand.items():
            if key[0] in hit or c < max(2, 0.6 * thr * min(len(s), K)): continue   # J>=thr implies ~>=0.67*thr of the bottom-k values are shared
            if jaccard(s, self.files[key]) >= thr: hit.add(key[0])
        return hit

    def row_files(self, row):
        m = row["messages"][-2] if row["messages"][-1]["role"] == "assistant" else row["messages"][-1]
        return parse_blob(m["content"])

    def content_hits(self, files):
        """[(set, plugin_index)] plugins matched by >= FILE_SHARE of the files; returns list of (kind, idx)"""
        fs = {p: t for p, t in files.items() if not trivial(p, t)}
        if not fs: return []
        per = collections.Counter()
        for p, t in fs.items():
            m = self.match_file(t)
            if len(m) > BOILERPLATE: continue          # a scaffold shared by many holdout/Dell plugins carries no identity
            for pi in m: per[pi] += 1
        return [(self.plugins[pi][0], self.plugins[pi][1]) for pi, c in per.items() if c / len(fs) >= FILE_SHARE]

    def check_row(self, row, files=None):
        """-> None if clean, else a short reason string"""
        r = row_repos(row)
        if r & self.repos: return "repo:" + sorted(r & self.repos)[0]
        pv = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        kind = pv.get("kind") or meta.get("kind") or ""
        if not r and not str(kind).startswith(KNOWN_KINDS): return "unknown_provenance"
        files = files if files is not None else self.row_files(row)
        mf = files.get("manifest.json")
        if mf:
            try: mid = (json.loads(mf) or {}).get("id")
            except Exception: mid = None
            if isinstance(mid, str) and mid.lower() in self.mids | self.dell_ids: return "manifest_id:" + mid
        ch = self.content_hits(files)
        if ch: return "content:" + ",".join(f"{k}{i}" for k, i in ch[:2])
        fs = {p: t for p, t in files.items() if not trivial(p, t)}
        fh = self.file_hits(fs)
        if fh: return "file:" + ",".join(f"{k}{i}" for k, i in fh[:2])
        sn = self.same_name(r, files)
        if sn: return "same_name:" + sn
        sa = self.same_author(r, files, fs)
        if sa: return "same_author:" + sa
        return None

    def file_hits(self, fs, thr=None):
        """plugins that ANY single file matches at Jaccard >= thr (scaffold files that match > BOILERPLATE plugins are skipped)"""
        out = collections.OrderedDict()
        for p, t in fs.items():
            m = self.match_file(t, thr)
            if not m or len(m) > BOILERPLATE: continue
            for pi in sorted(m): out[pi] = 1
        return [(self.plugins[pi][0], self.plugins[pi][1]) for pi in out]

    def _row_idents(self, repos, files):
        names, authors = set(), set()
        for rp in repos:
            names.add(norm_name(rp.split("/")[-1])); authors.add(rp.split("/")[0].lower())
        mf = files.get("manifest.json")
        if mf:
            try: mid = (json.loads(mf) or {}).get("id")
            except Exception: mid = None
            if isinstance(mid, str):
                au, nm = _mid_parts(mid); names.add(norm_name(nm)); authors.add(au.lower())
        return {n for n in names if len(n) >= MIN_NAME}, {a for a in authors if len(a) >= 4}

    def same_name(self, repos, files):
        names, _ = self._row_idents(repos, files)
        for n in sorted(names):
            for pi in sorted(self.names.get(n, ())):
                hr = (self.meta[pi].get("repo") or "").lower()
                if any((rp, hr) in self.allow for rp in repos): continue
                return f"{n}~{self.plugins[pi][0]}{self.plugins[pi][1]}"
        return None

    def same_author(self, repos, files, fs):
        _, authors = self._row_idents(repos, files)
        pis = {pi for a in authors for pi in self.authors.get(a, ())}
        if not pis: return None
        for p, t in fs.items():
            m = self.match_file(t, AUTHOR_JACCARD)
            if m & pis: return f"{sorted(authors)[0]}~{self.plugins[min(m & pis)][0]}{self.plugins[min(m & pis)][1]}:{p}"
        return None

    def max_file_similarity(self, files):
        """diagnostic: the highest per-file shingle Jaccard of this tree against any holdout / Dell-key file (0 if none above 0.2)"""
        best = 0.0
        for p, t in files.items():
            if trivial(p, t): continue
            s = sketch(t); cand = collections.Counter()
            for v in s:
                for key in self.inv.get(v, ()): cand[key] += 1
            for key, c in cand.items():
                if c >= 2: best = max(best, jaccard(s, self.files[key]))
        return best

    def check(self, rows):
        return {r.get("id", "?"): w for r in rows if (w := self.check_row(r))}

    def assert_clean(self, rows):
        bad = self.check(list(rows))
        if bad:
            raise SystemExit(f"HOLDOUT GUARD: {len(bad)} row(s) rejected, e.g. {list(bad.items())[:5]}")


def row_repos(row):
    """Every repository a row claims to come from (meta/provenance fields, row id, not free text)."""
    out = set()
    for d in (row, row.get("meta"), row.get("provenance")):
        if not isinstance(d, dict): continue
        for k in ("repo", "repo_url", "plugin", "source_repo"):
            v = d.get(k)
            if isinstance(v, str):
                n = norm(v) or (v.lower() if re.fullmatch(r"[\w.-]+/[\w.-]+", v) else None)
                if n: out.add(n)
    prov = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
    for u in (prov.get("comment_urls") or []):
        if isinstance(u, str) and "/issues/" not in u:
            n = norm(u)
            if n: out.add(n)
    # ids look like  source:owner/name:rest  (dell_*, hancore_concrete, version_history, fix_upstream); keep as a repo claim
    m = re.match(r"^[\w-]+:([\w.-]+/[\w.-]+):", str(row.get("id", "")))
    if m: out.add(m.group(1).lower())
    return out


def overlap(rows, ids=None):
    """repo-only check (kept for callers/tests that have no fingerprints); prefer Guard.check"""
    ids = ids or load_ids()
    return [r.get("id", "?") for r in rows if row_repos(r) & ids]


def assert_clean(rows, ids=None):
    bad = overlap(list(rows), ids)
    if bad: raise SystemExit(f"HOLDOUT GUARD: {len(bad)} row(s) come from sealed-holdout repos, e.g. {bad[:5]}")


def read(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


if __name__ == "__main__":
    g = Guard(); bad = 0
    for p in sys.argv[1:]:
        o = g.check(read(p)); bad += len(o)
        print(f"{p}: {len(o)} rejected row(s)" + (f" e.g. {list(o.items())[:3]}" if o else ""))
    sys.exit(1 if bad else 0)
