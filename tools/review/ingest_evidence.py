"""Split a batch file of evidence records (JSON list) into evidence/<key>.json and attach provenance.

Each record must have: key, source_id (corpus id like P0001 or candidate id), and the evidence fields.
The script adds the path of the full text that was read, then runs the verifier on the new records.

Usage: python tools/review/ingest_evidence.py <review_dir> <batch.json>
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ["key", "source_id", "title", "category", "task", "problem", "architecture", "datasets", "metrics",
            "baselines", "key_results", "strengths", "limitations", "code", "evidence_level"]


def fulltext_for(rdir, sid):
    for p in (rdir / "fulltext" / "txt" / f"{sid}.txt", ROOT / "corpus_2025_2026" / "fulltext_txt" / f"{sid}.txt"):
        if p.exists():
            return str(p)
    return ""


def main():
    rdir, batch = Path(sys.argv[1]), Path(sys.argv[2])
    recs = json.load(open(batch))
    out = rdir / "evidence"
    out.mkdir(exist_ok=True)
    for r in recs:
        miss = [f for f in REQUIRED if f not in r]
        if miss:
            sys.exit(f"{r.get('key')}: missing fields {miss}")
        r["fulltext_txt"] = fulltext_for(rdir, r["source_id"])
        json.dump(r, open(out / f"{r['key']}.json", "w"), indent=1, ensure_ascii=False)
    print(f"wrote {len(recs)} evidence records")
    batch.unlink()
    subprocess.run([sys.executable, str(ROOT / "tools" / "review" / "verify_evidence.py"), str(rdir)])


if __name__ == "__main__":
    main()
