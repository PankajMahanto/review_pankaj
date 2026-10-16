"""Step 4: retrieve full texts of the included records (open-access copies only).

Order of sources tried for each paper:
  1. PDF already in the repo (pdf/ folder, arXiv 2026-07 sweep)
  2. Publisher open access: ACL Anthology, AAAI OJS, OpenReview, IJCAI, NeurIPS, JMLR
  3. Semantic Scholar openAccessPdf link
  4. arXiv version (known arXiv id, else exact-title search on the arXiv API)

IMPORTANT: an arXiv copy is used for READING only. Citations always point to the published
version (venue + DOI) - see scripts/07_build_bib.py.

Output: data/fulltext_pdf/<id>.pdf, data/fulltext_txt/<id>.txt, data/fulltext_manifest.json
Run:    python scripts/04_fetch_fulltext.py
"""
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf
import requests
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "corpus_2025_2026" / "pool.json"
SCREEN = ROOT / "corpus_2025_2026" / "screening.json"
PDF_DIR = ROOT / "corpus_2025_2026" / "fulltext_pdf"
TXT_DIR = ROOT / "corpus_2025_2026" / "fulltext_txt"
MANIFEST = ROOT / "corpus_2025_2026" / "fulltext_manifest.json"
PDF_DIR.mkdir(parents=True, exist_ok=True)
TXT_DIR.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (literature-review toolkit; academic use)"}


SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def get(url, timeout=90):
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content, r.url


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def is_pdf(b):
    return b[:5] == b"%PDF-" and len(b) > 20000


def aaai_pdf(rec):
    """Resolve the AAAI OJS landing page and return the main PDF galley download URL."""
    if not rec["doi"]:
        return None
    html, final = get(f"https://doi.org/{rec['doi']}")
    html = html.decode("utf-8", "ignore")
    galleys = sorted(set(re.findall(r'href="https://ojs\.aaai\.org/index\.php/AAAI/article/view/(\d+/\d+)"', html)),
                     key=lambda g: int(g.split("/")[1]))
    return f"https://ojs.aaai.org/index.php/AAAI/article/download/{galleys[0]}" if galleys else None


def openreview_pdf(rec):
    for u in (rec["pdf_url"], rec["landing_url"]):
        m = re.search(r"openreview\.net/(?:forum|pdf)\?id=([\w-]+)", u or "")
        if m:
            return f"https://openreview.net/pdf?id={m.group(1)}"
    return None


def arxiv_title_search(title):
    """Find an arXiv copy by title (fuzzy match >= 92, so minor title edits still match)."""
    clean = re.sub(r"[^A-Za-z0-9 ]", " ", title)
    words_ = [w for w in clean.split() if len(w) > 3][:8]
    queries = [f'ti:"{clean}"', " AND ".join(f"ti:{w}" for w in words_)]
    for q in queries:
        xml, _ = get("https://export.arxiv.org/api/query?search_query="
                     + urllib.parse.quote(q) + "&max_results=8", timeout=120)
        xml = xml.decode("utf-8", "ignore")
        for m in re.finditer(r"<entry>.*?<id>http://arxiv.org/abs/([^<]+)</id>.*?<title>(.*?)</title>", xml, re.S):
            if fuzz.ratio(norm(m.group(2)), norm(title)) >= 92:
                return re.sub(r"v\d+$", "", m.group(1))
        time.sleep(3)
    return ""


def candidates(rec):
    """Yield (label, version, url) in priority order."""
    if rec["local_pdf"] and (ROOT / "pdf" / rec["local_pdf"]).exists():
        yield "local", "arxiv-preprint", str(ROOT / "pdf" / rec["local_pdf"])
    u = rec["pdf_url"] or ""
    if "aclanthology.org" in u:
        yield "acl-anthology", "published", u
    if rec["venue"] == "AAAI":
        yield "aaai-ojs", "published", "AAAI"
    if "openreview" in (u + rec["landing_url"]):
        yield "openreview", "published", "OPENREVIEW"
    if re.search(r"ijcai\.org|papers\.nips\.cc|proceedings\.neurips|jmlr\.org|proceedings\.mlr", u):
        yield "publisher-oa", "published", u
    if rec.get("oa_pdf"):
        yield "s2-open-access", "open-access-copy", rec["oa_pdf"]
    if rec["arxiv_id"]:
        yield "arxiv", "arxiv-preprint", f"https://arxiv.org/pdf/{rec['arxiv_id']}"
    yield "arxiv-title-search", "arxiv-preprint", "SEARCH"


def fetch(rec):
    out = PDF_DIR / f"{rec['id']}.pdf"
    if out.exists() and is_pdf(out.read_bytes()[:30] + b" " * 20001):
        return rec["id"], None
    tried = []
    for label, version, url in candidates(rec):
        try:
            if label == "local":
                data = Path(url).read_bytes()
            else:
                if url == "AAAI":
                    url = aaai_pdf(rec)
                elif url == "OPENREVIEW":
                    url = openreview_pdf(rec)
                elif url == "SEARCH":
                    aid = arxiv_title_search(rec["title"])
                    if not aid:
                        tried.append(f"{label}:no-match")
                        continue
                    rec["arxiv_id"] = aid
                    url = f"https://arxiv.org/pdf/{aid}"
                if not url:
                    tried.append(f"{label}:no-url")
                    continue
                data, url = get(url)
            if is_pdf(data):
                out.write_bytes(data)
                return rec["id"], {"source": label, "version": version, "url": url,
                                   "arxiv_id": rec["arxiv_id"]}
            tried.append(f"{label}:not-pdf")
        except Exception as e:  # network errors, 403/404 -> try next source
            tried.append(f"{label}:{type(e).__name__}")
            time.sleep(1)
    return rec["id"], {"source": "", "version": "not-retrieved", "url": "", "tried": tried}


def extract_text(pid):
    pdf = PDF_DIR / f"{pid}.pdf"
    txt = TXT_DIR / f"{pid}.txt"
    if txt.exists() or not pdf.exists():
        return
    doc = pymupdf.open(pdf)
    parts = [f"\n=== PAGE {i + 1} ===\n" + p.get_text() for i, p in enumerate(doc)]
    txt.write_text("".join(parts))


def main():
    pool = {r["id"]: r for r in json.load(open(POOL))}
    inc = [s["id"] for s in json.load(open(SCREEN)) if s["decision"] == "include"]
    manifest = json.load(open(MANIFEST)) if MANIFEST.exists() else {}
    todo = [pool[i] for i in inc if manifest.get(i, {}).get("version") in (None, "not-retrieved")]
    print(f"{len(todo)} papers to fetch")
    with ThreadPoolExecutor(max_workers=4) as ex:
        for pid, info in ex.map(fetch, todo):
            if info:
                manifest[pid] = info
                print(pid, info["version"], info.get("source"), info.get("tried", ""))
    json.dump(manifest, open(MANIFEST, "w"), indent=1)
    for pid in inc:
        extract_text(pid)
    got = sum(1 for i in inc if manifest.get(i, {}).get("version") not in (None, "not-retrieved"))
    print(f"full text retrieved: {got}/{len(inc)}")


if __name__ == "__main__":
    main()
