"""Select eligible records for full-text assessment (stratified rule, see search/queries.md Section 7)
and write search/fulltext_queue.json for tools/review/fetch_fulltext.py.

Stratum A  core 2025-2026: every eligible record of the author-curated corpus (year >= 2025).
Stratum B  foundations 2017-2022 and Stratum C 2023-2025: eligible records cited by at least
           K core-stratum full texts (backward citation searching, search/snowball_counts.json),
           plus seed titles found by citation searching (search/snowball_added.json).
Citation keys are kept stable in search/keys.json.

Usage: python select_fulltext.py <review_dir> [--strata A|AB C]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "review"))
from keys import make_key  # noqa: E402

RDIR = Path(sys.argv[1])
STRATA = sys.argv[sys.argv.index("--strata") + 1] if "--strata" in sys.argv else "A"


def main():
    cands = {r["cid"]: r for r in json.load(open(RDIR / "search" / "candidates.json"))}
    scr = {r["cid"]: r for r in json.load(open(RDIR / "search" / "screening.json"))}
    pool = {r["id"]: r for r in json.load(open(ROOT / "corpus_2025_2026" / "pool.json"))}
    kp = RDIR / "search" / "keys.json"
    keys = json.load(open(kp)) if kp.exists() else {}
    taken = set(keys.values())
    sel_p = RDIR / "search" / "selection.json"
    selection = json.load(open(sel_p)) if sel_p.exists() else {}

    if "A" in STRATA:
        for cid, s in scr.items():
            if s["decision"] == "eligible" and "corpus" in s["sources"] and (s["year"] or 0) >= 2025:
                selection.setdefault(cid, "A")
    if "B" in STRATA or "C" in STRATA:
        snow = json.load(open(RDIR / "search" / "snowball_selected.json"))
        for cid, stratum in snow.items():
            selection.setdefault(cid, stratum)

    # records excluded at title/abstract level after an earlier selection (e.g. demo track found via DOI)
    selection = {cid: st for cid, st in selection.items() if scr.get(cid, {}).get("decision") == "eligible"}
    queue = []
    for cid, stratum in selection.items():
        r = cands[cid]
        if cid not in keys:
            keys[cid] = make_key(r.get("authors") or [], r.get("year"), r["title"], taken)
        pr = pool.get(r.get("corpus_id") or "", {})
        queue.append({"key": keys[cid], "cid": cid, "stratum": stratum, "title": r["title"],
                      "authors": r.get("authors") or [], "year": r.get("year"), "venue": r.get("venue", ""),
                      "doi": r.get("doi", ""), "arxiv_id": r.get("arxiv_id") or pr.get("arxiv_id", ""),
                      "acl_url": r.get("acl_url") or (pr.get("pdf_url") if "aclanthology" in (pr.get("pdf_url") or "") else ""),
                      "corpus_id": r.get("corpus_id", ""), "oa_pdf": pr.get("oa_pdf", ""),
                      "pdf_url": pr.get("pdf_url", "") or r.get("pdf_url", ""),
                      "landing_url": pr.get("landing_url", "") or r.get("landing_url", "")})
    json.dump(keys, open(kp, "w"), indent=1)
    json.dump(selection, open(sel_p, "w"), indent=1)
    json.dump(queue, open(RDIR / "search" / "fulltext_queue.json", "w"), indent=1, ensure_ascii=False)
    from collections import Counter
    print(len(queue), Counter(q["stratum"] for q in queue))


if __name__ == "__main__":
    main()
