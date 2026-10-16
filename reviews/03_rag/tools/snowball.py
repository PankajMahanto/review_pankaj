"""Backward citation searching (snowballing) from the core-stratum full texts.

For every core (stratum A) full text, the reference list is cut out and normalised; each eligible
candidate title and each seed title (search/snowball_seeds.txt) is then looked up in every reference
list. The number of core studies that cite a record is its "core citation count".

Usage:
  python snowball.py <review_dir> count            -> search/snowball_counts.json
  python snowball.py <review_dir> select K_old K_new N_max
        -> search/snowball_selected.json  (cid -> stratum B for 2017-2022, C for 2023-2025)
"""
import json
import re
import sys
from pathlib import Path

RDIR = Path(sys.argv[1])


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def ref_blob(txt):
    lines = txt.split("\n")
    idx = None
    for i, l in enumerate(lines):
        if re.fullmatch(r"\s*(\d+\.?\s*)?(References|REFERENCES|Bibliography|Reference|REFERENCE)\s*", l):
            idx = i
    if idx is None:
        return ""
    return norm(re.sub(r"-\n", "", "\n".join(lines[idx:])))


def title_key(t):
    n = norm(re.sub(r"\$[^$]*\$", "", t))
    return n[:70] if len(n) >= 30 else None


def count():
    queue = json.load(open(RDIR / "search" / "fulltext_queue.json"))
    blobs = {}
    for q in queue:
        if q["stratum"] != "A":
            continue
        p = RDIR / "fulltext" / "txt" / f"{q['key']}.txt"
        if p.exists():
            b = ref_blob(p.read_text(errors="ignore"))
            if b:
                blobs[q["key"]] = b
    scr = json.load(open(RDIR / "search" / "screening.json"))
    core_cids = {q["cid"] for q in queue if q["stratum"] == "A"}
    out = {}
    targets = [(r["cid"], r["title"], r["year"], r["decision"], r["code"]) for r in scr if r["cid"] not in core_cids]
    seeds = [l.strip() for l in open(RDIR / "search" / "snowball_seeds.txt") if l.strip() and not l.startswith("#")]
    known = {title_key(t[1]) for t in targets}
    targets += [("seed:" + s, s, None, "seed", "") for s in seeds if title_key(s) not in known]
    for cid, title, year, dec, code in targets:
        k = title_key(title)
        if not k:
            continue
        citing = [key for key, b in blobs.items() if k in b]
        if citing:
            out[cid] = {"title": title, "year": year, "decision": dec, "code": code, "n": len(citing), "citing": citing}
    json.dump(dict(sorted(out.items(), key=lambda kv: -kv[1]["n"])), open(RDIR / "search" / "snowball_counts.json", "w"),
              indent=1, ensure_ascii=False)
    print(f"{len(blobs)} core reference lists; {len(out)} records cited at least once")
    for cid, v in sorted(out.items(), key=lambda kv: -kv[1]["n"])[:60]:
        print(v["n"], cid, v["year"], v["decision"], v["code"], v["title"][:80])


def select(k_old, k_new, n_max):
    counts = json.load(open(RDIR / "search" / "snowball_counts.json"))
    scr = {r["cid"]: r for r in json.load(open(RDIR / "search" / "screening.json"))}
    sel = {}
    ranked = sorted(((cid, v) for cid, v in counts.items() if cid in scr and scr[cid]["decision"] == "eligible"),
                    key=lambda kv: -kv[1]["n"])
    for cid, v in ranked:
        y = scr[cid]["year"] or 0
        if y <= 2022 and v["n"] >= k_old:
            sel[cid] = "B"
        elif 2023 <= y <= 2025 and v["n"] >= k_new:
            sel[cid] = "C"
        if len(sel) >= n_max:
            break
    json.dump(sel, open(RDIR / "search" / "snowball_selected.json", "w"), indent=1)
    from collections import Counter
    print(len(sel), Counter(sel.values()))


if __name__ == "__main__":
    if sys.argv[2] == "count":
        count()
    else:
        select(int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
