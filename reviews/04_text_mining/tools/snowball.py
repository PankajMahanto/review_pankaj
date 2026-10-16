"""Resolve the backward-snowballing list (foundational works cited by the included studies) to metadata.

Input : search/snowball_seed.tsv  (title<TAB>doi<TAB>arxiv_id<TAB>venue<TAB>landing_url<TAB>year)
Output: search/snowball.json (title, authors, year, venue, doi, arxiv_id, abstract, landing_url)
Crossref is used for DOI records, the arXiv API for preprint-only records (abstract + authors).
Usage: python tools/snowball.py <review_dir>
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


def crossref(doi):
    r = S.get("https://api.crossref.org/works/" + urllib.parse.quote(doi), timeout=60)
    r.raise_for_status()
    m = r.json()["message"]
    return {"title": re.sub(r"<[^>]+>|\s+", " ", (m.get("title") or [""])[0]).strip(),
            "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in m.get("author", [])][:12],
            "year": ((m.get("published") or m.get("issued") or {}).get("date-parts") or [[None]])[0][0],
            "venue": (m.get("container-title") or [""])[0],
            "abstract": re.sub(r"<[^>]+>|\s+", " ", m.get("abstract", "")).strip()}


def arxiv(aid):
    xml = S.get(f"https://export.arxiv.org/api/query?id_list={aid}", timeout=60).text
    e = re.search(r"<entry>(.*?)</entry>", xml, re.S).group(1)
    return {"title": re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip(),
            "authors": re.findall(r"<name>(.*?)</name>", e)[:12],
            "year": int(re.search(r"<published>(\d{4})", e).group(1)),
            "abstract": re.sub(r"\s+", " ", re.search(r"<summary>(.*?)</summary>", e, re.S).group(1)).strip()}


def main():
    rdir = Path(sys.argv[1])
    out_p = rdir / "search" / "snowball.json"
    done = {r["title_seed"]: r for r in json.load(open(out_p)) if not r.get("error")} if out_p.exists() else {}
    out = []
    for line in open(rdir / "search" / "snowball_seed.tsv"):
        if not line.strip() or line.startswith("#"):
            continue
        f = (line.rstrip("\n").split("\t") + [""] * 6)[:6]
        title, doi, aid, venue, url, year = [x.strip() for x in f]
        if title in done:
            out.append(done[title])
            continue
        rec = {"title_seed": title, "doi": doi.lower(), "arxiv_id": aid, "venue": venue, "landing_url": url}
        try:
            if doi and not doi.startswith("10.48550"):
                rec.update({k: v for k, v in crossref(doi).items() if v})
            if aid:
                a = arxiv(aid)
                time.sleep(3)
                for k, v in a.items():
                    if not rec.get(k):
                        rec[k] = v
                if not doi:
                    rec["doi"] = f"10.48550/arxiv.{aid}"
            if venue:
                rec["venue"] = venue
            if year:
                rec["year"] = int(year)
        except Exception as ex:
            rec["error"] = repr(ex)
        rec.setdefault("title", title)
        print(rec.get("year"), "|", rec.get("venue", "")[:40], "|", rec["title"][:90], "|", rec.get("error", ""), flush=True)
        out.append(rec)
    json.dump(out, open(out_p, "w"), indent=1, ensure_ascii=False)
    print(len(out), "snowball records")


if __name__ == "__main__":
    main()
