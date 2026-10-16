"""Check every evidence record against the paper's own full text.

For each evidence/<key>.json that has a full text:
  * every number written in key_results / datasets must occur in the full text
  * every dataset name must occur in the full text (case-insensitive, punctuation-insensitive)
  * the code URL (if any) must occur in the full text
Anything that cannot be found is reported so it can be corrected by re-reading the paper.

Usage:  python tools/review/verify_evidence.py <review_dir>
"""
import json
import re
import sys
from pathlib import Path


def norm(s):
    return re.sub(r"[^a-z0-9.%+-]", "", s.lower())


def numbers(text):
    # decimals, percentages and integers with >= 2 digits (skip years and single digits)
    out = []
    for m in re.finditer(r"(?<![\w.])(\d+(?:,\d{3})*(?:\.\d+)?)(?!\w)", text):
        v = m.group(1)
        if re.fullmatch(r"(19|20)\d\d", v) or (len(v) == 1):
            continue
        out.append(v)
    return out


def main():
    rdir = Path(sys.argv[1])
    bad = 0
    files = sorted((rdir / "evidence").glob("*.json"))
    for f in files:
        ev = json.load(open(f))
        txt_path = ev.get("fulltext_txt")
        if not txt_path or not Path(txt_path).exists():
            continue
        full = Path(txt_path).read_text(errors="ignore")
        flat = re.sub(r"-\n", "", full)
        flat_n = norm(flat)
        flat_nums = set(numbers(flat.replace("−", "-")))
        problems = []
        for res in ev.get("key_results", []):
            for v in numbers(res):
                if v not in flat_nums and v.replace(",", "") not in flat_nums:
                    problems.append(f"number {v!r} in result not found")
        for d in ev.get("datasets", []):
            name = d["name"] if isinstance(d, dict) else d
            alts = [a.strip() for a in re.split(r"/|\(|\)", name) if len(a.strip()) > 1]
            if not any(norm(a) in flat_n for a in alts):
                problems.append(f"dataset {name!r} not found")
            details = d.get("details", "") if isinstance(d, dict) else ""
            for v in numbers(details):
                if v not in flat_nums and v.replace(",", "") not in flat_nums:
                    problems.append(f"number {v!r} in dataset details of {name!r} not found")
        code = ev.get("code", "")
        if code.startswith("http") and norm(code.rstrip("/").split("://")[1][:40]) not in flat_n:
            problems.append(f"code url {code!r} not found")
        if problems:
            bad += 1
            print(f"{f.stem}:")
            for p in problems:
                print("   -", p)
    print(f"checked {len(files)} records, {bad} with issues")


if __name__ == "__main__":
    main()
