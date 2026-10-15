"""One place for machine-specific locations (audit H). Every path is read from a documented environment variable,
with a repo-relative default; nothing here touches the disk at import time.

  USUBA_CHECKER_ROOT  checkout of usuba-checker-scripts (provides functest/, the Checker). Default: ../usuba-checker-scripts next to this repo.
  USUBA_RUNS          directory with run outputs and data (default /workspace/usuba-runs)
  USUBA_WORK          scratch directory for builders (default /workspace)
  USUBA_HOLDOUT_DIR   private holdout dir with manifest.jsonl + code/ (default <checker root>/eval/hancore_holdout, else this repo's eval/hancore_holdout)
  FT_OMARCHY          reference Omarchy tree for the Checker's API table (default <checker root>/dell-ref/omarchy-4.0.4)
  HF_HOME / USUBA_BASE_REVISION   Hugging Face cache; base model revision (default: BASE_REVISION below)
"""
import os, subprocess, hashlib, glob

TRAIN = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TRAIN)
BASE_MODEL = "Qwen/Qwen3.5-9B"
BASE_REVISION = "c202236235762e1c871ad0ccb60c8ee5ba337b9a"   # the snapshot every builder counted tokens with; train_lora, builders and eval load exactly this


def runs_dir(): return os.environ.get("USUBA_RUNS", "/workspace/usuba-runs")
def work_dir(): return os.environ.get("USUBA_WORK", "/workspace")


def checker_root():
    """Root that contains functest/ (the Usuba Checker). Raises if missing: a silent fallback changes every Checker report."""
    cands = [os.environ.get("USUBA_CHECKER_ROOT"), os.path.join(os.path.dirname(REPO), "usuba-checker-scripts"), REPO]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "functest", "usuba")): return os.path.abspath(c)
    raise FileNotFoundError("Usuba Checker not found: set USUBA_CHECKER_ROOT to a usuba-checker-scripts checkout")


def reference_tree():
    r = os.environ.get("FT_OMARCHY") or os.path.join(checker_root(), "dell-ref", "omarchy-4.0.4")
    if not os.path.isdir(os.path.join(r, "shell")): raise FileNotFoundError(f"Omarchy reference tree missing: {r} (set FT_OMARCHY)")
    return r


def holdout_dir():
    for c in (os.environ.get("USUBA_HOLDOUT_DIR"), os.path.join(checker_root(), "eval", "hancore_holdout"), os.path.join(REPO, "eval", "hancore_holdout")):
        if c and os.path.isdir(c): return c
    raise FileNotFoundError("holdout dir not found")


def tokenizer_json(revision=None):
    rev = revision or os.environ.get("USUBA_BASE_REVISION") or BASE_REVISION
    hf = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    p = os.path.join(hf, "hub", "models--" + BASE_MODEL.replace("/", "--"), "snapshots", rev, "tokenizer.json")
    if not os.path.exists(p): raise FileNotFoundError(f"tokenizer for {BASE_MODEL}@{rev} not in the HF cache: {p}")
    return p


def git_info(path):
    """{sha, dirty} of a checkout, or {sha: None} when it is not a git repo."""
    try:
        sha = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", path, "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
        return dict(sha=sha, dirty=dirty)
    except Exception:
        return dict(sha=None, dirty=None)


def rules_hash(root=None):
    """sha256 over every Checker rule/config file that can change a report (code + json data + binary lists + reference-tree API table inputs)."""
    root = root or checker_root(); fs = []
    for pat in ("functest/usuba/*.py", "functest/usuba/*.json", "functest/dell_env/*.py", "functest/dell_env/*.txt", "functest/*.py"):
        fs += glob.glob(os.path.join(root, pat))
    h = hashlib.sha256()
    for f in sorted(set(fs)):
        h.update(os.path.relpath(f, root).encode()); h.update(b"\0"); h.update(open(f, "rb").read()); h.update(b"\0")
    return h.hexdigest()


def sha256_file(fn):
    h = hashlib.sha256()
    with open(fn, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
