"""Record a manual screening decision (title/abstract or full-text level) in search/manual_decisions.json.

Usage: python manual.py <review_dir> <cid|corpus_id> <decision> <code> "<note>"
  decision: eligible | exclude
"""
import json
import sys
from pathlib import Path

rdir, ident, decision, code, note = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
cands = json.load(open(rdir / "search" / "candidates.json"))
cid = next((r["cid"] for r in cands if ident in (r["cid"], r.get("corpus_id"))), None)
if cid is None:
    sys.exit(f"unknown id {ident}")
p = rdir / "search" / "manual_decisions.json"
m = json.load(open(p)) if p.exists() else {}
m[cid] = {"decision": decision, "code": "" if code == "-" else code, "note": note, "id": ident}
json.dump(m, open(p, "w"), indent=1, ensure_ascii=False)
print(cid, m[cid])
