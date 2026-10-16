"""Step 2: enrich the pool with abstracts, TLDRs, arXiv IDs and open-access PDF links.

Sources (all free, no key needed):
  * Semantic Scholar Graph API (batch endpoint)  -> abstract, tldr, externalIds, openAccessPdf
  * arXiv API (title search)                      -> arXiv id for papers that also have a preprint

Results are cached in data/cache/ so the script can be re-run safely.
Run:  python scripts/02_enrich.py
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "corpus_2025_2026" / "pool.json"
CACHE = ROOT / "corpus_2025_2026" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
S2_CACHE = CACHE / "s2_batch.json"
ARXIV_CACHE = CACHE / "arxiv_title_search.json"

S2_URL = ("https://api.semanticscholar.org/graph/v1/paper/batch"
          "?fields=title,abstract,tldr,externalIds,openAccessPdf,citationCount,venue,year")


def http(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                          "User-Agent": "review-toolkit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def s2_ids(rec):
    if rec["doi"]:
        return f"DOI:{rec['doi']}"
    if rec["arxiv_id"]:
        return f"ARXIV:{rec['arxiv_id']}"
    return None


def enrich_s2(pool):
    cache = json.load(open(S2_CACHE)) if S2_CACHE.exists() else {}
    todo = [s2_ids(r) for r in pool if s2_ids(r) and s2_ids(r) not in cache]
    for i in range(0, len(todo), 400):
        chunk = todo[i:i + 400]
        for attempt in range(12):
            try:
                out = json.loads(http(S2_URL, json.dumps({"ids": chunk}).encode()))
                for pid, res in zip(chunk, out):
                    cache[pid] = res
                json.dump(cache, open(S2_CACHE, "w"))
                print(f"  S2 batch {i // 400 + 1}: {len(chunk)} ids ok")
                break
            except Exception as e:  # 429 rate limit on shared IPs -> back off
                wait = 15 * (attempt + 1)
                print(f"  S2 retry in {wait}s ({e})")
                time.sleep(wait)
    return cache


def arxiv_search(title):
    q = urllib.parse.quote(f'ti:"{title}"')
    xml = http(f"https://export.arxiv.org/api/query?search_query={q}&max_results=3", timeout=90)
    for m in re.finditer(r"<entry>.*?<id>http://arxiv.org/abs/([^<]+)</id>.*?<title>(.*?)</title>", xml, re.S):
        aid, t = m.group(1), re.sub(r"\s+", " ", m.group(2))
        if norm(t) == norm(title):
            return re.sub(r"v\d+$", "", aid)
    return ""


def main():
    pool = json.load(open(POOL))
    cache = enrich_s2(pool)
    for r in pool:
        res = cache.get(s2_ids(r) or "", None) or {}
        ext = res.get("externalIds") or {}
        if not r["abstract"] and res.get("abstract"):
            r["abstract"], r["abstract_source"] = re.sub(r"\s+", " ", res["abstract"]).strip(), "semantic_scholar"
        r["tldr"] = ((res.get("tldr") or {}).get("text") or "")
        if not r["arxiv_id"] and ext.get("ArXiv"):
            r["arxiv_id"] = ext["ArXiv"]
        oa = (res.get("openAccessPdf") or {}).get("url") or ""
        r["oa_pdf"] = oa
        r["s2_citations"] = res.get("citationCount")
        r["acl_id"] = ext.get("ACL", "")
    json.dump(pool, open(POOL, "w"), indent=1, ensure_ascii=False)
    print("abstracts:", sum(1 for r in pool if r["abstract"]), "/", len(pool),
          "| arXiv ids:", sum(1 for r in pool if r["arxiv_id"]),
          "| OA pdf:", sum(1 for r in pool if r["oa_pdf"]))


if __name__ == "__main__":
    main()
