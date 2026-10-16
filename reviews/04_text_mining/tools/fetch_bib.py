"""Fetch authentic BibTeX for every record in the full-text queue (plus extra general references).

Order of sources: ACL Anthology .bib (ACL DOIs 10.18653/ and TACL/CL), doi.org content negotiation
(Crossref / DataCite, incl. arXiv DOIs 10.48550), and a hand-checked entry from tools/manual_bib.bib for venues
without DOIs (NeurIPS / ICML / ICLR / COLM proceedings and OpenReview pages).
Raw entries are stored in latex/bib_raw/<key>.bib with the citation key replaced by our key.
Usage: python tools/fetch_bib.py <review_dir>
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

S = requests.Session()
S.headers["User-Agent"] = "review-toolkit/1.0 (academic literature review)"


def acl_bib(rec):
    url = rec.get("acl_url") or ""
    if not url and rec["doi"].startswith("10.18653/v1/"):
        url = "https://aclanthology.org/" + rec["doi"].split("/v1/")[-1] + "/"
    if not url:
        return None
    r = S.get(url.rstrip("/") + ".bib", timeout=60)
    return r.text if r.ok and r.text.lstrip().startswith("@") else None


def doi_bib(doi):
    r = S.get("https://doi.org/" + doi, headers={"Accept": "application/x-bibtex; charset=utf-8"}, timeout=60)
    return r.content.decode("utf-8") if r.ok and r.text.lstrip().startswith("@") else None


def rekey(bib, key):
    return re.sub(r"^(\s*@\w+\s*\{)\s*[^,]+,", lambda m: m.group(1) + key + ",", bib.strip(), count=1)


def main():
    rdir = Path(sys.argv[1])
    out = rdir / "latex" / "bib_raw"
    out.mkdir(parents=True, exist_ok=True)
    queue = json.load(open(rdir / "search" / "fulltext_queue.json"))
    manual = {}
    mp = rdir / "tools" / "manual_bib.bib"
    if mp.exists():
        for m in re.finditer(r"(@\w+\{([^,]+),.*?\n\})", mp.read_text(), re.S):
            manual[m.group(2).strip()] = m.group(1)
    log = []
    for rec in queue:
        p = out / f"{rec['key']}.bib"
        if p.exists():
            continue
        doi = (rec.get("doi") or "").strip()
        bib, src = None, ""
        try:
            if rec["key"] in manual:
                bib, src = manual[rec["key"]], "manual (proceedings page checked)"
            elif doi.startswith("10.18653/") or rec.get("acl_url") or doi.startswith("10.1162/tacl"):
                bib, src = acl_bib(rec), "acl-anthology"
                if not bib and doi:
                    bib, src = doi_bib(doi), "doi.org"
            elif doi:
                bib, src = doi_bib(doi), "doi.org"
        except Exception as e:
            src = f"error {e!r}"
        if bib:
            p.write_text(rekey(bib, rec["key"]) + "\n")
        log.append({"key": rec["key"], "doi": doi, "source": src if bib else "MISSING " + src})
        time.sleep(0.3)
    lp = rdir / "latex" / "bib_raw" / "_log.json"
    old = json.load(open(lp)) if lp.exists() else []
    json.dump(old + log, open(lp, "w"), indent=1)
    print(sum(1 for l in log if not l["source"].startswith("MISSING")), "fetched;",
          [l["key"] for l in log if l["source"].startswith("MISSING")], "missing")


if __name__ == "__main__":
    main()
