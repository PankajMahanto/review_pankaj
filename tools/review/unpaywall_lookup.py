"""Find legal open-access copies (publisher OA, author or repository versions) for records
whose full text has not been retrieved yet, using the Unpaywall API.

Adds `oa_pdfs` (list of PDF URLs, best first) to each record in search/fulltext_queue.json.

Usage:  python tools/review/unpaywall_lookup.py <review_dir>
"""
import json
import sys
import time
from pathlib import Path

import requests

EMAIL = "review.pipeline@example.org"
# hosts that answer scripted requests with a browser challenge
BLOCKED = ("dl.acm.org", "sciencedirect.com", "ieeexplore.ieee.org", "onlinelibrary.wiley.com")


def lookup(doi):
    for attempt in range(3):
        try:
            r = requests.get(f"https://api.unpaywall.org/v2/{doi}", params={"email": EMAIL}, timeout=30)
            if r.status_code == 404:
                return []
            r.raise_for_status()
            d = r.json()
            urls = []
            for loc in d.get("oa_locations") or []:
                u = loc.get("url_for_pdf")
                if u and not any(b in u for b in BLOCKED) and u not in urls:
                    urls.append(u)
            return urls
        except Exception:
            time.sleep(2 * (attempt + 1))
    return []


def main():
    rdir = Path(sys.argv[1])
    qp = rdir / "search" / "fulltext_queue.json"
    queue = json.load(open(qp))
    manifest = json.load(open(rdir / "fulltext" / "manifest.json"))
    found = 0
    for rec in queue:
        if manifest.get(rec["key"], {}).get("version") not in (None, "not-retrieved"):
            continue
        if not rec.get("doi"):
            continue
        urls = lookup(rec["doi"])
        if urls:
            rec["oa_pdfs"] = urls
            found += 1
            print(rec["key"], urls[0])
        time.sleep(0.2)
    json.dump(queue, open(qp, "w"), indent=1, ensure_ascii=False)
    print(f"open-access copies found for {found} records")


if __name__ == "__main__":
    main()
