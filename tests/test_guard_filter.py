import json
import os

HF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hf", "GUARD_FILTER.json")


def test_guard_filter_has_r4_public_entries():
    d = json.load(open(HF))
    for k, kept in (("v3_r4_public/train.jsonl.gz", 464), ("v3_r4_public/val.jsonl.gz", 55)):
        assert d[k]["kept"] == kept and d[k]["dropped_holdout_overlap"] == 0 and len(d[k]["sha256"]) == 64


def test_pool_chunked_arithmetic():
    e = json.load(open(HF))["clean/pool_chunked.jsonl"]
    assert e["kept"] + e["dropped_holdout_overlap"] == 334   # rows built; README's old "328" was stale
