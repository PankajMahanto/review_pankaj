"""Merge all identification sources of one review into a single de-duplicated candidate list.

Sources: author corpus (corpus_2025_2026/pool.json), ACL Anthology dump, Crossref hits, arXiv hits.
Each candidate keeps every identifier we know (DOI, ACL key, arXiv id) and the list of sources.
Venue quality tiers are assigned from an explicit whitelist (VENUE_TIERS) so the screening is auditable.

Usage:
  python tools/review/build_candidates.py <review_dir> <title_regex> [corpus_ids_file]
Output:
  <review_dir>/search/candidates.json
  <review_dir>/search/identification_counts.json
"""
import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2]

# Venue tiers (CORE 2023 for conferences, JCR/SJR quartile for journals; checked manually).
TIER_A_STAR = [
    r"\bACL\b|Association for Computational Linguistics \(Volume 1|Annual Meeting of the Association for Computational Linguistics",
    r"\bEMNLP\b|Empirical Methods in Natural Language Processing",
    r"Transactions of the Association for Computational Linguistics|\bTACL\b",
    r"Computational Linguistics$",
    r"NeurIPS|Neural Information Processing Systems",
    r"\bICML\b|International Conference on Machine Learning",
    r"\bICLR\b|Learning Representations",
    r"\bAAAI\b|AAAI Conference on Artificial Intelligence",
    r"\bIJCAI\b|International Joint Conference on Artificial Intelligence",
    r"\bKDD\b|Knowledge Discovery (and|&) Data Mining",
    r"\bWWW\b|The Web Conference|World Wide Web Conference|ACM Web Conference",
    r"\bSIGIR\b|Research and Development in Information Retrieval",
    r"Journal of Machine Learning Research",
    r"IEEE Transactions on Pattern Analysis and Machine Intelligence",
    r"IEEE Transactions on Knowledge and Data Engineering",
    r"IEEE Transactions on Neural Networks and Learning Systems",
    r"ACM Computing Surveys",
    r"Artificial Intelligence$",
]
TIER_A = [
    r"\bNAACL\b|North American Chapter of the Association for Computational Linguistics",
    r"\bEACL\b|European Chapter of the Association for Computational Linguistics",
    r"\bCOLING\b|International Conference on Computational Linguistics",
    r"Findings of the Association for Computational Linguistics",
    r"\bCIKM\b|Information and Knowledge Management",
    r"\bWSDM\b|Web Search and Data Mining",
    r"\bICDM\b|International Conference on Data Mining",
    r"\bSDM\b|SIAM International Conference on Data Mining",
    r"\bUAI\b|Uncertainty in Artificial Intelligence",
    r"\bAISTATS\b|Artificial Intelligence and Statistics",
    r"\bECIR\b|European Conference on Information Retrieval",
    r"ECML|PKDD|Machine Learning and Knowledge Discovery in Databases",
    r"Neurocomputing", r"Knowledge-Based Systems", r"Expert Systems with Applications",
    r"Information Processing (and|&) Management", r"Information Sciences", r"Pattern Recognition$",
    r"Neural Networks$", r"Information Fusion", r"Artificial Intelligence Review", r"Machine Learning$",
    r"Data Mining and Knowledge Discovery", r"ACM Transactions on Information Systems",
    r"ACM Transactions on Knowledge Discovery from Data", r"IEEE Transactions on Cybernetics",
    r"IEEE Transactions on Big Data", r"IEEE Transactions on Affective Computing",
    r"IEEE Transactions on Computational Social Systems", r"Engineering Applications of Artificial Intelligence",
    r"Information Systems$", r"Journal of the American Statistical Association", r"Annals of Applied Statistics",
    r"Journal of the Association for Information Science and Technology", r"Scientometrics",
    r"PLOS ONE", r"Communications of the ACM", r"Journal of Computational and Graphical Statistics",
    r"\bLREC\b|Language Resources and Evaluation", r"\bCoNLL\b|Computational Natural Language Learning",
    r"\bAACL\b|Asia-Pacific Chapter",
]


def tier(venue):
    v = venue or ""
    if re.search(r"workshop|student research|shared task|demo", v, re.I):
        return "workshop"
    for rx in TIER_A_STAR:
        if re.search(rx, v):
            return "A*"
    for rx in TIER_A:
        if re.search(rx, v, re.I if rx.islower() else 0):
            return "A"
    return "other"


def key(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


class Merger:
    def __init__(self):
        self.recs, self.by_key, self.by_doi, self.by_arxiv = [], {}, {}, {}

    def find(self, r):
        if r.get("doi") and r["doi"] in self.by_doi:
            return self.by_doi[r["doi"]]
        if r.get("arxiv_id") and r["arxiv_id"] in self.by_arxiv:
            return self.by_arxiv[r["arxiv_id"]]
        k = key(r["title"])
        if k in self.by_key:
            return self.by_key[k]
        if len(k) > 25:  # fuzzy match for small title edits between preprint and published version
            for kk, rec in self.by_key.items():
                if abs(len(kk) - len(k)) < 8 and fuzz.ratio(kk, k) >= 95:
                    return rec
        return None

    def add(self, r, source):
        hit = self.find(r)
        if hit is None:
            r = dict(r)
            r["sources"] = [source]
            r["cid"] = f"C{len(self.recs) + 1:05d}"
            self.recs.append(r)
            hit = r
        else:
            if source not in hit["sources"]:
                hit["sources"].append(source)
            # prefer peer-reviewed metadata over preprint metadata
            for f in ("doi", "acl_key", "acl_url", "arxiv_id", "abstract", "venue", "year", "cited_by", "pages"):
                if r.get(f) and (not hit.get(f) or (f == "venue" and hit.get("venue") in ("arXiv", "", None))):
                    hit[f] = r[f]
        for f, idx in (("doi", self.by_doi), ("arxiv_id", self.by_arxiv)):
            if hit.get(f):
                idx[hit[f]] = hit
        self.by_key[key(hit["title"])] = hit
        return hit


def main():
    rdir, rx = Path(sys.argv[1]), re.compile(sys.argv[2], re.I)
    corpus_ids = set(Path(sys.argv[3]).read_text().split()) if len(sys.argv) > 3 else set()
    m = Merger()
    counts = {}

    # 1) author-curated corpus (only the ids screened in for this review)
    pool = {r["id"]: r for r in json.load(open(ROOT / "corpus_2025_2026" / "pool.json"))}
    n = 0
    for pid in sorted(corpus_ids):
        r = pool[pid]
        m.add({"title": r["title"], "authors": r["authors"], "year": r["year"], "venue": r["venue"],
               "doi": r["doi"], "arxiv_id": r["arxiv_id"], "abstract": r["abstract"],
               "cited_by": r.get("cited_by") or 0, "corpus_id": pid}, "corpus")
        n += 1
    counts["corpus"] = n

    # 2) ACL Anthology (title match)
    n = 0
    for line in open(ROOT / "sources" / "acl_anthology.jsonl"):
        r = json.loads(line)
        if r["year"] and r["year"] >= 1999 and rx.search(r["title"]):
            m.add({"title": r["title"], "authors": r["authors"], "year": r["year"], "venue": r["venue"],
                   "doi": r["doi"], "acl_key": r["acl_key"], "acl_url": r["url"], "abstract": r["abstract"],
                   "pages": r["pages"]}, "acl_anthology")
            n += 1
    counts["acl_anthology"] = n

    # 3) Crossref and 4) arXiv
    for src, fname in (("crossref", "crossref_hits.json"), ("arxiv", "arxiv_hits.json")):
        p = rdir / "search" / fname
        hits = json.load(open(p)) if p.exists() else []
        n = 0
        for h in hits:
            if h.get("year") and h["year"] < 1999:
                continue
            rec = {"title": h["title"], "authors": h.get("authors", []), "year": h.get("year"),
                   "venue": h.get("venue") or ("arXiv" if src == "arxiv" else ""),
                   "doi": h.get("doi") or h.get("arxiv_doi", ""), "arxiv_id": h.get("arxiv_id", ""),
                   "abstract": h.get("abstract", ""), "cited_by": h.get("cited_by", 0),
                   "journal_ref": h.get("journal_ref", ""), "type": h.get("type", "")}
            if src == "arxiv":
                rec["doi"] = (h.get("arxiv_doi") or "").lower()
                # published venue named in the arXiv comment / journal-ref (e.g. "Accepted at ICLR 2024")
                rec["venue_hint"] = " ".join(x for x in (h.get("journal_ref", ""), h.get("comment", "")) if x)
            m.add(rec, src)
            n += 1
        counts[src] = n

    for r in m.recs:
        r["tier"] = tier(r.get("venue", ""))
        if r["tier"] == "other" and r.get("venue") in ("arXiv", "", None) and r.get("venue_hint"):
            t = tier(r["venue_hint"])
            if t in ("A*", "A"):
                r["tier"] = t + " (per arXiv comment)"
        if r["tier"] == "other" and r.get("acl_key"):
            r["tier"] = "A" if not re.search(r"workshop|student|shared task|demo", r["venue"], re.I) else "workshop"
    counts["identified_total"] = sum(v for k, v in counts.items())
    counts["after_dedup"] = len(m.recs)
    counts["duplicates_removed"] = counts["identified_total"] - counts["after_dedup"]
    json.dump(m.recs, open(rdir / "search" / "candidates.json", "w"), indent=1, ensure_ascii=False)
    json.dump(counts, open(rdir / "search" / "identification_counts.json", "w"), indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
