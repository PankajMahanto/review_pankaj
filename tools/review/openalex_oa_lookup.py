"""For papers whose full text was not retrieved, ask OpenAlex for open-access locations
(arXiv id, repository PDF) by DOI, falling back to an exact-title search.
Updates <review_dir>/search/fulltext_queue.json in place (fields arxiv_id, oa_pdf).

Usage: python tools/review/openalex_oa_lookup.py <review_dir>
"""
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from rapidfuzz import fuzz

S = requests.Session()
S.headers["User-Agent"] = "review-toolkit/1.0 (academic literature review)"
BLOCKED = ("sciencedirect.com", "elsevier", "dl.acm.org", "ieeexplore", "springer.com", "wiley.com", "tandfonline")


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def work_for(rec):
    if rec.get("doi") and not rec["doi"].startswith("10.48550"):
        r = S.get(f"https://api.openalex.org/works/doi:{rec['doi']}", timeout=60)
        if r.status_code == 200:
            return r.json()
    q = urllib.parse.quote(rec["title"][:200])
    r = S.get(f"https://api.openalex.org/works?search={q}&per-page=5", timeout=60)
    if r.status_code == 200:
        for w in r.json().get("results", []):
            if fuzz.ratio(norm(w.get("display_name")), norm(rec["title"])) >= 92:
                return w
    return None


def main():
    rdir = Path(sys.argv[1])
    qpath = rdir / "search" / "fulltext_queue.json"
    queue = json.load(open(qpath))
    man = json.load(open(rdir / "fulltext" / "manifest.json"))
    n = found = 0
    for rec in queue:
        if man.get(rec["key"], {}).get("version") != "not-retrieved":
            continue
        n += 1
        try:
            w = work_for(rec)
        except Exception as e:
            print(rec["key"], "error", e)
            continue
        time.sleep(0.2)
        if not w:
            continue
        for loc in w.get("locations") or []:
            u = (loc.get("landing_page_url") or "") + " " + (loc.get("pdf_url") or "")
            m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", u)
            if m and not rec.get("arxiv_id"):
                rec["arxiv_id"] = m.group(1)
            pdf = loc.get("pdf_url") or ""
            if pdf and not any(b in pdf for b in BLOCKED) and not rec.get("oa_pdf"):
                rec["oa_pdf"] = pdf
        if rec.get("arxiv_id") or rec.get("oa_pdf"):
            found += 1
            print(rec["key"], rec.get("arxiv_id", ""), rec.get("oa_pdf", "")[:80])
    json.dump(queue, open(qpath, "w"), indent=1, ensure_ascii=False)
    print(f"looked up {n}, found an open copy for {found}")


if __name__ == "__main__":
    main()
