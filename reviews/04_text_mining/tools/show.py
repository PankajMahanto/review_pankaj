"""Print the reading excerpts of several papers (helper for the reading sessions).
Usage: python tools/show.py <key> [<key> ...] [--grep REGEX] [--full]
Default: a condensed view of each excerpt (section budgets below); --full prints the excerpt (14.5k chars);
--grep prints matching passages of the full text."""
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
BUDGET = {"ABSTRACT": 1500, "INTRO": 1100, "METHOD": 1000, "SETUP": 2300, "RESULTS": 2600, "LIMITATIONS": 1300,
          "CONCLUSION": 500, "TABLE": 600, "CODE": 300}
args = sys.argv[1:]
rx, full = None, "--full" in args
args = [a for a in args if a != "--full"]
if "--grep" in args:
    i = args.index("--grep")
    rx = re.compile(args[i + 1], re.I)
    args = args[:i] + args[i + 2:]
for k in args:
    if rx:
        t = (R / "fulltext" / "txt" / f"{k}.txt").read_text(errors="ignore")
        flat = re.sub(r"\s+", " ", t)
        print(f"#### {k}")
        for m in list(rx.finditer(flat))[:8]:
            print("  ..." + flat[max(0, m.start() - 250): m.end() + 350] + "...")
        continue
    text = (R / "excerpts" / f"{k}.md").read_text()
    if full:
        print(text[:14500])
    else:
        parts = re.split(r"\n(?=## )", text)
        out = [parts[0]]
        for p in parts[1:]:
            tag = p[3:].split()[0].strip("[]")
            b = BUDGET.get(tag, 800)
            out.append(p[:b] + (" …" if len(p) > b else ""))
        print("\n".join(out))
    print("\n" + "=" * 80 + "\n")
