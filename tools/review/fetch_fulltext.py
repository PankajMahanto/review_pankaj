"""Download open-access full texts for the papers selected for full-text reading in one review.

Input : <review_dir>/search/fulltext_queue.json  - list of records, each with at least
        key, title and any of: doi, arxiv_id, acl_url, venue, corpus_id, oa_pdf
Output: <review_dir>/fulltext/pdf/<key>.pdf, <review_dir>/fulltext/txt/<key>.txt,
        <review_dir>/fulltext/manifest.json (source, version read, URL; or why it failed)

Sources tried in order: corpus copy -> ACL Anthology -> AAAI OJS -> OpenReview -> other publisher OA
-> Semantic-Scholar/OpenAlex OA link -> arXiv (known id, else fuzzy title search).
An arXiv copy is used for READING only; citations always use the published version (DOI).

Usage: python tools/review/fetch_fulltext.py <review_dir> [--workers 4]
"""
import json
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf
import requests
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2]
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def get(url, timeout=90):
    r = S.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content, r.url


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def is_pdf(b):
    return b[:5] == b"%PDF-" and len(b) > 20000


def aaai_pdf(rec):
    if not rec.get("doi"):
        return None
    html, _ = get(f"https://doi.org/{rec['doi']}")
    gal = sorted(set(re.findall(r'href="https://ojs\.aaai\.org/index\.php/AAAI/article/view/(\d+/\d+)"',
                                html.decode("utf-8", "ignore"))), key=lambda g: int(g.split("/")[1]))
    return f"https://ojs.aaai.org/index.php/AAAI/article/download/{gal[0]}" if gal else None


def arxiv_title_search(title):
    clean = re.sub(r"[^A-Za-z0-9 ]", " ", title)
    words = [w for w in clean.split() if len(w) > 3][:8]
    for q in (f'ti:"{clean}"', " AND ".join(f"ti:{w}" for w in words)):
        xml, _ = get("https://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q) + "&max_results=8", 120)
        for m in re.finditer(r"<entry>.*?<id>http://arxiv.org/abs/([^<]+)</id>.*?<title>(.*?)</title>",
                             xml.decode("utf-8", "ignore"), re.S):
            if fuzz.ratio(norm(m.group(2)), norm(title)) >= 92:
                return re.sub(r"v\d+$", "", m.group(1))
        time.sleep(3)
    return ""


def candidates(rec):
    cid = rec.get("corpus_id")
    if cid and (ROOT / "corpus_2025_2026" / "fulltext_pdf" / f"{cid}.pdf").exists():
        yield "corpus-copy", "see corpus manifest", str(ROOT / "corpus_2025_2026" / "fulltext_pdf" / f"{cid}.pdf")
    acl = rec.get("acl_url") or ""
    if acl:
        yield "acl-anthology", "published", acl.rstrip("/") + (".pdf" if not acl.endswith(".pdf") else "")
    if (rec.get("doi") or "").startswith("10.18653/"):
        yield "acl-anthology", "published", "https://aclanthology.org/" + rec["doi"].split("/v1/")[-1] + ".pdf"
    if "aaai" in (rec.get("venue") or "").lower() or (rec.get("doi") or "").startswith("10.1609/aaai"):
        yield "aaai-ojs", "published", "AAAI"
    for u in (rec.get("pdf_url"), rec.get("landing_url")):
        m = re.search(r"openreview\.net/(?:forum|pdf)\?id=([\w-]+)", u or "")
        if m:
            yield "openreview", "published", f"https://openreview.net/pdf?id={m.group(1)}"
        if u and re.search(r"ijcai\.org|papers\.nips\.cc|proceedings\.neurips|jmlr\.org|proceedings\.mlr", u):
            yield "publisher-oa", "published", u
    if rec.get("oa_pdf"):
        yield "oa-link", "open-access-copy", rec["oa_pdf"]
    if rec.get("arxiv_id"):
        yield "arxiv", "arxiv-preprint", f"https://arxiv.org/pdf/{rec['arxiv_id']}"
    yield "arxiv-title-search", "arxiv-preprint", "SEARCH"


def fetch(args):
    rec, pdf_dir = args
    out = pdf_dir / f"{rec['key']}.pdf"
    tried = []
    for label, version, url in candidates(rec):
        try:
            if label == "corpus-copy":
                data = Path(url).read_bytes()
                man = json.load(open(ROOT / "corpus_2025_2026" / "fulltext_manifest.json")).get(rec["corpus_id"], {})
                version, url = man.get("version", version), man.get("url", url)
            else:
                if url == "AAAI":
                    url = aaai_pdf(rec)
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
                return rec["key"], {"source": label, "version": version, "url": url, "arxiv_id": rec.get("arxiv_id", "")}
            tried.append(f"{label}:not-pdf")
        except Exception as e:
            tried.append(f"{label}:{type(e).__name__}")
            time.sleep(1)
    return rec["key"], {"source": "", "version": "not-retrieved", "url": "", "tried": tried}


def to_text(pdf, txt):
    doc = pymupdf.open(pdf)
    txt.write_text("".join(f"\n=== PAGE {i + 1} ===\n" + p.get_text() for i, p in enumerate(doc)))


def main():
    rdir = Path(sys.argv[1])
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    pdf_dir, txt_dir = rdir / "fulltext" / "pdf", rdir / "fulltext" / "txt"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)
    man_path = rdir / "fulltext" / "manifest.json"
    manifest = json.load(open(man_path)) if man_path.exists() else {}
    queue = json.load(open(rdir / "search" / "fulltext_queue.json"))
    todo = [r for r in queue if manifest.get(r["key"], {}).get("version") in (None, "not-retrieved")
            and not (pdf_dir / f"{r['key']}.pdf").exists()]
    print(f"{len(todo)} to fetch of {len(queue)}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for key, info in ex.map(fetch, [(r, pdf_dir) for r in todo]):
            manifest[key] = info
            print(key, info["version"], info.get("source", ""), info.get("tried", ""), flush=True)
            json.dump(manifest, open(man_path, "w"), indent=1)
    for r in queue:
        p, t = pdf_dir / f"{r['key']}.pdf", txt_dir / f"{r['key']}.txt"
        if p.exists() and not t.exists():
            try:
                to_text(p, t)
            except Exception as e:
                print("text extraction failed", r["key"], e)
    got = sum(1 for r in queue if (txt_dir / f"{r['key']}.txt").exists())
    print(f"full texts available: {got}/{len(queue)}")


if __name__ == "__main__":
    main()
