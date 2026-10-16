"""Resolve bibliographic metadata for titles found by citation searching.

Lookup order: ACL Anthology dump (exact normalised title) -> Crossref (fuzzy >= 93) -> arXiv API (fuzzy >= 93).
Output is appended to search/citation_hits.json (source "citation_search" in build_candidates.py).

Usage: python resolve_titles.py <review_dir> <titles.txt>
"""
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[3]
S = requests.Session()
S.headers["User-Agent"] = "review-toolkit/1.0 (academic literature review)"


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def acl_index():
    idx = {}
    for line in open(ROOT / "sources" / "acl_anthology.jsonl"):
        r = json.loads(line)
        idx.setdefault(norm(r["title"]), r)
    return idx


def crossref(title):
    url = ("https://api.crossref.org/works?rows=8&select=DOI,title,container-title,published,author,type,is-referenced-by-count"
           "&query.bibliographic=" + urllib.parse.quote(title))
    try:
        items = S.get(url, timeout=60).json()["message"]["items"]
    except Exception:
        return None
    best = None
    for it in items:
        t = re.sub(r"<[^>]+>|\s+", " ", (it.get("title") or [""])[0]).strip()
        sc = fuzz.ratio(norm(t), norm(title))
        if sc >= 93 and it.get("type") in ("proceedings-article", "journal-article", "book-chapter"):
            if best is None or (it.get("is-referenced-by-count", 0) > best.get("is-referenced-by-count", 0)):
                best = dict(it, _title=t)
    if not best:
        return None
    return {"title": best["_title"], "doi": best["DOI"].lower(), "venue": (best.get("container-title") or [""])[0],
            "year": ((best.get("published") or {}).get("date-parts") or [[None]])[0][0],
            "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in best.get("author") or []][:12],
            "cited_by": best.get("is-referenced-by-count", 0)}


def arxiv(title):
    clean = re.sub(r"[^A-Za-z0-9 ]", " ", title)
    q = urllib.parse.quote(f'ti:"{clean}"')
    try:
        xml = S.get(f"https://export.arxiv.org/api/query?search_query={q}&max_results=5", timeout=90).text
    except Exception:
        return None
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        t = re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip()
        if fuzz.ratio(norm(t), norm(title)) >= 93:
            aid = re.sub(r"v\d+$", "", re.search(r"<id>http://arxiv.org/abs/([^<]+)</id>", e).group(1))
            return {"title": t, "arxiv_id": aid, "doi": f"10.48550/arxiv.{aid}", "venue": "arXiv",
                    "year": int(re.search(r"<published>(\d{4})", e).group(1)),
                    "authors": re.findall(r"<name>(.*?)</name>", e)[:12],
                    "abstract": re.sub(r"\s+", " ", re.search(r"<summary>(.*?)</summary>", e, re.S).group(1)).strip(),
                    "venue_hint": " ".join(x for x in (
                        (re.search(r"<arxiv:journal_ref[^>]*>(.*?)</arxiv:journal_ref>", e, re.S) or [None, ""])[1],
                        (re.search(r"<arxiv:comment[^>]*>(.*?)</arxiv:comment>", e, re.S) or [None, ""])[1]) if x)}
    return None


def main():
    rdir, tfile = Path(sys.argv[1]), Path(sys.argv[2])
    out_p = rdir / "search" / "citation_hits.json"
    hits = json.load(open(out_p)) if out_p.exists() else []
    have = {norm(h["seed_title"]) for h in hits}
    idx = acl_index()
    for title in [l.strip() for l in open(tfile) if l.strip() and not l.startswith("#")]:
        if norm(title) in have:
            continue
        rec = None
        a = idx.get(norm(title))
        if a:
            rec = {"title": a["title"], "authors": a["authors"], "year": a["year"], "venue": a["venue"], "doi": a["doi"],
                   "acl_key": a["acl_key"], "acl_url": a["url"], "abstract": a["abstract"], "pages": a["pages"]}
        if not rec:
            rec = crossref(title)
            time.sleep(1)
        ax = arxiv(title)
        time.sleep(3)
        if rec and ax:
            rec["arxiv_id"] = ax["arxiv_id"]
            rec.setdefault("abstract", ax["abstract"])
            if not rec.get("abstract"):
                rec["abstract"] = ax["abstract"]
            rec["venue_hint"] = ax.get("venue_hint", "")
        rec = rec or ax
        if rec:
            rec["seed_title"] = title
            hits.append(rec)
            print("OK ", title[:70], "->", rec.get("venue", "")[:50], rec.get("doi", ""), flush=True)
        else:
            print("MISS", title[:70], flush=True)
        json.dump(hits, open(out_p, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
