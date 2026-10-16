"""Build search/fulltext_queue.json (records sought for retrieval) from the screening decisions.
Keys follow tools/review/keys.py (<surname><year><first content word>); keys of earlier runs are kept stable.
Usage: python tools/make_queue.py <review_dir>"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "review"))
from keys import make_key  # noqa: E402

rdir = Path(sys.argv[1])
cands = {r["cid"]: r for r in json.load(open(rdir / "search" / "candidates.json"))}
scr = json.load(open(rdir / "search" / "screening.json"))
pool = {r["id"]: r for r in json.load(open(ROOT / "corpus_2025_2026" / "pool.json"))}
qp = rdir / "search" / "fulltext_queue.json"
old = {r["cid"]: r["key"] for r in json.load(open(qp))} if qp.exists() else {}
taken = set(old.values())
queue = []
for s in scr:
    if s["decision"] != "include":
        continue
    c = cands[s["cid"]]
    key = old.get(s["cid"]) or make_key(c.get("authors") or [], c.get("year"), c["title"], taken)
    taken.add(key)
    rec = {"key": key, "cid": s["cid"], "title": c["title"], "authors": c.get("authors", []), "year": c.get("year"),
           "venue": c.get("venue", ""), "doi": c.get("doi", ""), "arxiv_id": c.get("arxiv_id", ""),
           "acl_url": c.get("acl_url", ""), "corpus_id": c.get("corpus_id", ""), "landing_url": c.get("landing_url", ""),
           "code": s["code"], "tier": s["tier"]}
    if c.get("corpus_id"):
        p = pool[c["corpus_id"]]
        rec.update(oa_pdf=p.get("oa_pdf", ""), pdf_url=p.get("pdf_url", ""), landing_url=p.get("landing_url", "") or rec["landing_url"])
    queue.append(rec)
json.dump(queue, open(qp, "w"), indent=1, ensure_ascii=False)
print(len(queue), "records in the full-text queue")
