"""One tiny ZDR-constrained call per model: proves the request carries provider zdr/data_collection=deny and that a ZDR endpoint exists."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uplift
for m in sys.argv[1:]:
    out, fin, c, prov = uplift.chat(m, [{"role": "user", "content": "Reply with the single word: ok"}], mt=256)
    print(f"{m:34} finish={fin[:90]} provider={prov} cost=${c:.5f} reply={out.strip()[:20]!r}", flush=True)
