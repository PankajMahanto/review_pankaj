"""Step 1: merge the metadata into one candidate pool with stable IDs.

Input : metadata/ranked_master.json (924 records: DBLP 2025+ venues + arXiv 2026-07 sweep)
Output: data/pool.json  (one record per paper, with id, normalised fields, topical bucket)

Run:  python scripts/01_build_pool.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "metadata" / "ranked_master.json"
OUT = ROOT / "corpus_2025_2026" / "pool.json"

# Ordered rules: the first match decides the primary bucket.
BUCKET_RULES = [
    ("topic-model", r"topic model|topic modell?ing|topic discovery|latent dirichlet|\blda\b|bertopic|"
                    r"neural topic|topic coherence|dynamic topic|topic extraction|topic mining"),
    ("text-clustering", r"short[- ]text|text clustering|document clustering|semantic clustering|intent discovery|"
                        r"clustering of (short )?text|cluster(ing)? text|news event clustering|deep clustering"),
    ("llm-text-mining", r"(large language model|llm).{0,80}(cluster|topic|taxonom|theme|qualitative|coding|corpus exploration)|"
                        r"(cluster|topic|taxonom|theme).{0,80}(large language model|llm)"),
    ("keyphrase-aspect", r"keyphrase|aspect extraction|aspect term|aspect-based|concept discovery|taxonomy induction|"
                         r"aspect category|keyword extraction"),
    ("text-representation", r"sentence embedding|text embedding|document embedding|document representation|"
                            r"text representation|representation learning|embedding model|contrastive"),
    ("retrieval-rag", r"retrieval[- ]augmented|\brag\b|dense retrieval|retriever|reranking|re-ranking|passage retrieval"),
]


def clean(s):
    s = html.unescape(s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def bucket_of(title, abstract):
    t = f"{title} {abstract}".lower()
    for name, rx in BUCKET_RULES:
        if re.search(rx, t):
            return name
    return "other"


def main():
    recs = json.load(open(SRC))
    recs.sort(key=lambda x: -x.get("score", 0))
    pool, seen = [], set()
    for x in recs:
        title = clean(x["title"]).rstrip(".")
        key = re.sub(r"[^a-z0-9]", "", title.lower())
        if key in seen:
            continue
        seen.add(key)
        abstract = clean(x.get("abstract"))
        pool.append({
            "id": f"P{len(pool) + 1:04d}",
            "title": title,
            "authors": [re.sub(r"\s\d{4}$", "", a) for a in (x.get("authors") or [])],  # drop DBLP homonym suffix
            "year": x.get("year"),
            "venue": x.get("venue") or "",
            "venue_tier": x.get("venue_tier") or "",
            "peer_reviewed": bool(x.get("peer_reviewed")),
            "doi": (x.get("doi") or "").lower(),
            "arxiv_id": re.sub(r"v\d+$", "", x.get("arxiv_id") or ""),
            "pdf_url": x.get("pdf_url") or "",
            "landing_url": x.get("landing_url") or "",
            "cited_by": x.get("cited_by") or 0,
            "local_pdf": x.get("local_pdf") or "",
            "abstract": abstract,
            "abstract_source": "metadata" if abstract else "",
            "matched_query": x.get("matched_query") or [],
            "rank_score": x.get("score", 0),
            "bucket": bucket_of(title, abstract),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(pool, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"{len(pool)} unique records -> {OUT}")


if __name__ == "__main__":
    main()
