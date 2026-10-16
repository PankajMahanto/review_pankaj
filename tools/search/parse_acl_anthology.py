"""Parse the ACL Anthology BibTeX dump (with abstracts) into JSON lines.

Download first (42 MB):
  curl -o sources/anthology+abstracts.bib.gz https://aclanthology.org/anthology+abstracts.bib.gz
Run:
  python tools/search/parse_acl_anthology.py
Output: sources/acl_anthology.jsonl  (one paper per line: key, title, authors, year, venue, doi, url, abstract)
"""
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "sources" / "anthology+abstracts.bib.gz"
OUT = ROOT / "sources" / "acl_anthology.jsonl"

FIELD = re.compile(r'\s*(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}|(\d+))\s*,?', re.S)


def latex_clean(s):
    s = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", s)
    s = s.replace("{", "").replace("}", "").replace("\\&", "&").replace("--", "–")
    return re.sub(r"\s+", " ", s).strip()


def entries(text):
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.S):
        etype, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)
        if etype not in ("inproceedings", "article"):
            continue
        f = {}
        for fm in FIELD.finditer(body):
            f[fm.group(1).lower()] = fm.group(2) or fm.group(3) or fm.group(4) or ""
        yield etype, key, f


def main():
    text = gzip.open(SRC, "rt", encoding="utf-8").read()
    n = 0
    with open(OUT, "w") as out:
        for etype, key, f in entries(text):
            rec = {
                "acl_key": key,
                "type": etype,
                "title": latex_clean(f.get("title", "")),
                "authors": [latex_clean(a) for a in f.get("author", "").split(" and ") if a.strip()],
                "year": int(f["year"]) if f.get("year", "").isdigit() else None,
                "venue": latex_clean(f.get("booktitle") or f.get("journal") or ""),
                "publisher": latex_clean(f.get("publisher", "")),
                "pages": f.get("pages", "").replace("--", "-"),
                "doi": f.get("doi", "").lower(),
                "url": f.get("url", ""),
                "abstract": latex_clean(f.get("abstract", "")),
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} entries -> {OUT}")


if __name__ == "__main__":
    main()
