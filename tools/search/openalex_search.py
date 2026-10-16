"""Search OpenAlex with a list of query phrases (title + abstract) and save the raw hits.

Usage:
  python tools/search/openalex_search.py <review_dir> <years> <max_per_query> "<phrase 1>" "<phrase 2>" ...
Example:
  python tools/search/openalex_search.py reviews/01_topic_modeling 2003-2026 300 "topic model" "neural topic model"

Output: <review_dir>/search/openalex_hits.json  (merged, de-duplicated by OpenAlex id, with the
        query phrases that found each record)
"""
import json
import sys
import time
import urllib.parse
from pathlib import Path

import requests

S = requests.Session()
S.headers["User-Agent"] = "review-toolkit/1.0 (academic literature review)"
FIELDS = ("id,doi,title,display_name,publication_year,type,cited_by_count,primary_location,locations,"
          "open_access,best_oa_location,authorships,abstract_inverted_index,biblio")


def abstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, idx in inv.items():
        for i in idx:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def run(phrase, years, limit):
    flt = f'title_and_abstract.search:"{phrase}",publication_year:{years}'
    out, cursor = [], "*"
    while cursor and len(out) < limit:
        url = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(flt, safe=":,")
               + f"&sort=cited_by_count:desc&per-page=200&cursor={cursor}&select={FIELDS}")
        for attempt in range(5):
            try:
                r = S.get(url, timeout=90)
                r.raise_for_status()
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else:
            break
        js = r.json()
        out += js["results"]
        cursor = js["meta"].get("next_cursor")
        time.sleep(0.3)
    return out[:limit]


def slim(w, phrase):
    src = ((w.get("primary_location") or {}).get("source") or {})
    arxiv = ""
    for loc in w.get("locations") or []:
        u = (loc.get("landing_page_url") or "") + " " + (loc.get("pdf_url") or "")
        if "arxiv.org/abs/" in u:
            arxiv = u.split("arxiv.org/abs/")[1].split()[0].split("v")[0]
    return {
        "openalex_id": w["id"].rsplit("/", 1)[-1],
        "doi": (w.get("doi") or "").replace("https://doi.org/", "").lower(),
        "title": w.get("display_name") or w.get("title") or "",
        "year": w.get("publication_year"),
        "type": w.get("type"),
        "venue": src.get("display_name") or "",
        "venue_type": src.get("type") or "",
        "cited_by": w.get("cited_by_count", 0),
        "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])][:12],
        "abstract": abstract(w.get("abstract_inverted_index")),
        "oa_url": (w.get("open_access") or {}).get("oa_url") or "",
        "oa_pdf": ((w.get("best_oa_location") or {}).get("pdf_url")) or "",
        "arxiv_id": arxiv,
        "queries": [phrase],
    }


def main():
    rdir, years, limit, phrases = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4:]
    path = rdir / "search" / "openalex_hits.json"
    hits = {h["openalex_id"]: h for h in json.load(open(path))} if path.exists() else {}
    for p in phrases:
        res = run(p, years, limit)
        new = 0
        for w in res:
            s = slim(w, p)
            if s["openalex_id"] in hits:
                if p not in hits[s["openalex_id"]]["queries"]:
                    hits[s["openalex_id"]]["queries"].append(p)
            else:
                hits[s["openalex_id"]] = s
                new += 1
        print(f'{p!r}: {len(res)} hits, {new} new')
    json.dump(list(hits.values()), open(path, "w"), indent=1, ensure_ascii=False)
    print(f"total unique: {len(hits)} -> {path}")


if __name__ == "__main__":
    main()
