"""Print reading excerpts (with bibliographic header and full-text provenance) for a list of keys.
Usage: python show.py <review_dir> key1 key2 ...   |  python show.py <review_dir> --next N  (next N unread)
"""
import json
import sys
from pathlib import Path

rdir = Path(sys.argv[1])
queue = {q["key"]: q for q in json.load(open(rdir / "search" / "fulltext_queue.json"))}
man = json.load(open(rdir / "fulltext" / "manifest.json"))
if sys.argv[2] == "--next":
    n = int(sys.argv[3])
    done = {p.stem for p in (rdir / "evidence").glob("*.json")}
    skip_p = rdir / "search" / "fulltext_decisions.json"
    skip = set(json.load(open(skip_p))) if skip_p.exists() else set()
    keys = [k for k in sorted(queue) if (rdir / "excerpts" / f"{k}.md").exists() and k not in done and k not in skip][:n]
else:
    keys = sys.argv[2:]
for k in keys:
    q, m = queue[k], man.get(k, {})
    print(f"\n######## {k} | cid {q['cid']} | {q.get('corpus_id','')} | stratum {q['stratum']}")
    print(f"VENUE: {q['venue']} {q['year']} | DOI {q['doi']} | arXiv {q.get('arxiv_id','')} | READ: {m.get('source')} {m.get('version')} {m.get('url')}")
    print((rdir / "excerpts" / f"{k}.md").read_text())
