"""Search Crossref (DOI registry) and arXiv for a review topic; keep only records whose TITLE
matches the topic regex. Crossref gives authentic DOI metadata (journals, ACM/IEEE/Springer
proceedings); arXiv covers venues without DOIs (NeurIPS, ICML, ICLR) through their preprints.

Usage:
  python tools/search/crossref_arxiv_search.py <review_dir> <title_regex> "<query 1>" "<query 2>" ...
Output:
  <review_dir>/search/crossref_hits.json, <review_dir>/search/arxiv_hits.json
"""
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

S = requests.Session()
S.headers["User-Agent"] = "review-toolkit/1.0 (academic literature review)"


def crossref(query, rx, max_pages=3):
    """Relevance-ranked Crossref results; scan at most max_pages x 1000 records per query."""
    out, pages = [], 0
    sel = "DOI,title,container-title,is-referenced-by-count,type,published,author,event,page,volume,issue,publisher"
    while pages < max_pages:
        offset = pages * 1000
        pages += 1
        url = (f"https://api.crossref.org/works?query.bibliographic={urllib.parse.quote(query)}"
               f"&filter=from-pub-date:1999,until-pub-date:2026-12-31&rows=1000&offset={offset}&sort=score&order=desc&select={sel}")
        for attempt in range(5):
            try:
                r = S.get(url, timeout=120)
                r.raise_for_status()
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else:
            break
        msg = r.json()["message"]
        items = msg.get("items", [])
        if not items:
            break
        for it in items:
            title = re.sub(r"<[^>]+>|\s+", " ", (it.get("title") or [""])[0]).strip()
            if not rx.search(title):
                continue
            year = ((it.get("published") or {}).get("date-parts") or [[None]])[0][0]
            out.append({
                "doi": it["DOI"].lower(), "title": title, "year": year,
                "venue": (it.get("container-title") or [""])[0], "type": it.get("type"),
                "cited_by": it.get("is-referenced-by-count", 0), "publisher": it.get("publisher", ""),
                "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in (it.get("author") or [])][:12],
                "queries": [query],
            })
        page_hits = sum(1 for it in items if rx.search(re.sub(r"<[^>]+>|\s+", " ", (it.get("title") or [""])[0])))
        if len(items) < 1000 or page_hits < 20:  # end of results or relevance exhausted
            break
        time.sleep(1)
    return out


def arxiv(query, rx, max_results=1500):
    q = urllib.parse.quote(f'ti:"{query}" OR abs:"{query}"')
    url = f"https://export.arxiv.org/api/query?search_query={q}&start=0&max_results={max_results}&sortBy=relevance"
    for attempt in range(4):
        try:
            xml = S.get(url, timeout=240).text
            break
        except Exception:
            time.sleep(10)
    else:
        return []
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        title = re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip()
        if not rx.search(title):
            continue
        aid = re.search(r"<id>http://arxiv.org/abs/([^<]+)</id>", e).group(1)
        out.append({
            "arxiv_id": re.sub(r"v\d+$", "", aid), "title": title,
            "year": int(re.search(r"<published>(\d{4})", e).group(1)),
            "abstract": re.sub(r"\s+", " ", re.search(r"<summary>(.*?)</summary>", e, re.S).group(1)).strip(),
            "authors": re.findall(r"<name>(.*?)</name>", e)[:12],
            "journal_ref": (re.search(r"<arxiv:journal_ref[^>]*>(.*?)</arxiv:journal_ref>", e, re.S) or [None, ""])[1],
            "arxiv_doi": (re.search(r"<arxiv:doi[^>]*>(.*?)</arxiv:doi>", e) or [None, ""])[1],
            "comment": (re.search(r"<arxiv:comment[^>]*>(.*?)</arxiv:comment>", e, re.S) or [None, ""])[1],
            "queries": [query],
        })
    return out


def merge(path, new, key):
    old = {h[key]: h for h in json.load(open(path))} if path.exists() else {}
    for h in new:
        if h[key] in old:
            old[h[key]]["queries"] = sorted(set(old[h[key]]["queries"]) | set(h["queries"]))
        else:
            old[h[key]] = h
    json.dump(list(old.values()), open(path, "w"), indent=1, ensure_ascii=False)
    return len(old)


def main():
    only_crossref = "--crossref-only" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--crossref-only"]
    rdir, rx, queries = Path(args[0]), re.compile(args[1], re.I), args[2:]
    (rdir / "search").mkdir(parents=True, exist_ok=True)
    for q in queries:
        c = crossref(q, rx)
        nc = merge(rdir / "search" / "crossref_hits.json", c, "doi")
        a = [] if only_crossref else arxiv(q, rx)
        na = merge(rdir / "search" / "arxiv_hits.json", a, "arxiv_id")
        print(f"{q!r}: crossref {len(c)} (total {nc}) | arXiv {len(a)} (total {na})", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
