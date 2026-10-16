"""Evidence ingestion for this review (same contract as tools/review/ingest_evidence.py).

Fills bibliographic/provenance fields from search/fulltext_queue.json and fulltext/manifest.json
(title, venue label, year, doi, cid, corpus_id, read_from) when a record omits them, sets
source_id = key (full texts are stored as fulltext/txt/<key>.txt), checks the required fields, writes
evidence/<key>.json and runs the verifier (tools/verify_evidence.py).

Usage: python ingest.py <review_dir> <batch.json>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RDIR, BATCH = Path(sys.argv[1]), Path(sys.argv[2])

ACL_TRACKS = {"long": "", "short": " (short)", "industry": " (Industry Track)", "main": "", "demo": " (demo)"}


def venue_label(q):
    doi = (q.get("doi") or "").lower()
    m = re.match(r"10\.18653/v1/(\d{4})\.([a-z]+)-([a-z]+)\.", doi)
    if m:
        y, a, b = m.groups()
        if a == "findings":
            return f"Findings of {b.upper()} {y}"
        return f"{a.upper()} {y}{ACL_TRACKS.get(b, '')}"
    m = re.match(r"10\.18653/v1/(\d{4})\.([a-z]+)\.", doi)
    if m:
        return f"{m.group(2).upper()} {m.group(1)}"
    m = re.match(r"10\.1162/tacl", doi)
    if m:
        return f"TACL {q.get('year')}"
    m = re.match(r"10\.1609/aaai\.v(\d+)", doi)
    if m:
        return f"AAAI {int(m.group(1)) + 1986}"
    return f"{q.get('venue', '')} {q.get('year', '')}".strip()


def read_from(m):
    src, ver = m.get("source", ""), m.get("version", "")
    if src == "acl-anthology":
        return "ACL Anthology published PDF"
    if src == "aaai-ojs":
        return "AAAI OJS published PDF"
    if src == "openreview":
        return "OpenReview camera-ready PDF"
    if src in ("arxiv", "arxiv-title-search"):
        return f"arXiv preprint {m.get('arxiv_id', '')} (open-access copy; citation uses the published version)"
    if src == "oa-link":
        return f"open-access copy ({m.get('url', '')})"
    if src == "corpus-copy":
        return f"author corpus copy ({ver}, {m.get('url', '')})"
    return f"{src} {ver}".strip()


def main():
    queue = {q["key"]: q for q in json.load(open(RDIR / "search" / "fulltext_queue.json"))}
    man = json.load(open(RDIR / "fulltext" / "manifest.json"))
    recs = json.load(open(BATCH))
    for r in recs:
        q, m = queue[r["key"]], man.get(r["key"], {})
        r.setdefault("source_id", r["key"])
        r.setdefault("cid", q["cid"])
        r.setdefault("corpus_id", q.get("corpus_id", ""))
        r.setdefault("title", q["title"])
        r.setdefault("venue", venue_label(q))
        r.setdefault("year", q["year"])
        r.setdefault("doi", q.get("doi", ""))
        r.setdefault("read_from", read_from(m))
        r.setdefault("evidence_level", "full-text")
    required = ["key", "source_id", "title", "category", "task", "problem", "architecture", "datasets", "metrics",
                "baselines", "key_results", "strengths", "limitations", "code", "evidence_level",
                "retriever", "generator", "knowledge_source"]
    for r in recs:
        miss = [f for f in required if f not in r]
        if miss:
            sys.exit(f"{r['key']}: missing fields {miss}")
    for r in recs:
        p = RDIR / "fulltext" / "txt" / f"{r['source_id']}.txt"
        r["fulltext_txt"] = str(p.resolve()) if p.exists() else ""
        json.dump(r, open(RDIR / "evidence" / f"{r['key']}.json", "w"), indent=1, ensure_ascii=False)
    print(f"wrote {len(recs)} evidence records")
    BATCH.unlink()
    subprocess.run([sys.executable, str(Path(__file__).parent / "verify_evidence.py"), str(RDIR)])


if __name__ == "__main__":
    main()
