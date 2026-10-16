"""Step 5: build reading excerpts from each full text.
(Review-03 copy: sections whose start falls inside text already shown are skipped/trimmed, so the same
passage is not repeated under two headings; otherwise unchanged.)

For every retrieved paper the excerpt keeps the parts that carry the evidence we extract:
  * Abstract + end of Introduction (contribution list)
  * Start of the Method / Model / Framework section (architecture)
  * Datasets / Experimental setup (datasets, sizes, metrics, baselines, LLMs/encoders)
  * Results (main tables and the text that interprets them)
  * Limitations + Conclusion (author-stated limitations, future work)
  * Any code link (github / huggingface / zenodo)

Usage:  python tools/review/make_excerpts.py <review_dir>
Reads   <review_dir>/fulltext/txt/<key>.txt and <review_dir>/search/fulltext_queue.json
Writes  <review_dir>/excerpts/<key>.md
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
import sys
RDIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
TXT = RDIR / "fulltext" / "txt" if RDIR else None
OUT = RDIR / "excerpts" if RDIR else None

HEAD = r"^\s*(?:\d{{1,2}}(?:\.\d{{1,2}})?\.?|[IVX]{{1,4}}\.)?\s*{}\b[^\n]{{0,60}}$"
SECTIONS = [
    ("METHOD", ["Method", "Methodology", "Proposed Method", "Proposed Model", "Model", "Approach",
                "Framework", "Our Approach", "Our Method", "Problem Formulation", "Preliminaries"], 420),
    ("SETUP", ["Experimental Setup", "Experimental Settings", "Experiment Setup", "Experiments", "Experiment",
               "Datasets", "Dataset", "Data", "Evaluation Setup", "Experimental Design", "Setup"], 750),
    ("RESULTS", ["Results", "Main Results", "Experimental Results", "Results and Analysis",
                 "Results and Discussion", "Evaluation", "Overall Performance", "Analysis"], 750),
    ("LIMITATIONS", ["Limitations", "Limitation", "Limitations and Future Work", "Discussion"], 380),
    ("CONCLUSION", ["Conclusion", "Conclusions", "Conclusion and Future Work", "Conclusions and Future Work"], 260),
]


def words(s, n):
    w = s.split()
    return " ".join(w[:n]) + (" …" if len(w) > n else "")


def find_heading(lines, names, start=0):
    for name in names:
        rx = re.compile(HEAD.format(re.escape(name)), re.I)
        for i in range(start, len(lines)):
            if rx.match(lines[i]) and len(lines[i].split()) <= 9:
                return i
    return None


def body(text):
    """Cut the reference list and appendix noise."""
    m = re.search(r"\n\s*(References|REFERENCES|Bibliography)\s*\n", text)
    return text[: m.start()] if m else text


def make(pid, rec):
    raw = (TXT / f"{pid}.txt").read_text(errors="ignore")
    text = body(raw)
    lines = [l.strip() for l in text.split("\n")]
    flat = re.sub(r"-\n(?=[a-z])", "", text)
    flat = re.sub(r"\s+", " ", flat)
    parts = [f"# {pid} — {rec['title']}", f"Venue: {rec.get('venue', '')} {rec.get('year', '')} | DOI: {rec.get('doi') or '-'}"]

    # abstract + introduction end (contributions)
    m = re.search(r"\babstract\b(.{0,2600})", flat, re.I)
    parts.append("## ABSTRACT\n" + words(m.group(1) if m else flat[:2000], 300))
    intro_i = find_heading(lines, ["Introduction"])
    next_i = None
    if intro_i is not None:
        next_i = next((j for j in range(intro_i + 3, len(lines))
                       if re.match(r"^\s*(2|II)\.?\s+[A-Z]", lines[j]) and len(lines[j].split()) <= 9), None)
        intro = " ".join(lines[intro_i + 1: next_i or intro_i + 120])
        w = intro.split()
        parts.append("## INTRO (last part, contributions)\n" + " ".join(w[-380:]))

    covered = []  # line ranges already shown, so a passage is not repeated under two headings
    for tag, names, n in SECTIONS:
        i = find_heading(lines, names, start=(next_i or 0) if tag != "CONCLUSION" else 0)
        if i is None:
            continue
        for a, b in sorted(covered):
            if a <= i < b:
                i = b
        j, cnt = i, 0
        while j < len(lines) and cnt < n:
            cnt += len(lines[j].split())
            j += 1
        for a, b in covered:
            if i < a < j:
                j = a
        if j - i < 3:
            continue
        covered.append((i, j))
        parts.append(f"## {tag} [{lines[i][:60]}]\n" + " ".join(lines[i:j]))

    # table captions with surrounding numbers
    caps = re.findall(r"(Table \d+[:.][^\n]{0,200})", text)
    if caps:
        parts.append("## TABLE CAPTIONS\n" + "\n".join(dict.fromkeys(c.strip() for c in caps[:12])))
    code = sorted(set(re.findall(r"https?://(?:github\.com|huggingface\.co|zenodo\.org|gitlab\.com)/[^\s)\]}>,;]+", raw)))
    parts.append("## CODE LINKS\n" + ("\n".join(code[:6]) if code else "none found in text"))
    (OUT / f"{pid}.md").write_text("\n\n".join(parts))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    queue = json.load(open(RDIR / "search" / "fulltext_queue.json"))
    n = 0
    for rec in queue:
        if (TXT / f"{rec['key']}.txt").exists() and not (OUT / f"{rec['key']}.md").exists():
            make(rec["key"], rec)
            n += 1
    print(f"{n} new excerpts written to {OUT}")


if __name__ == "__main__":
    main()
