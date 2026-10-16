"""Step 3: title/abstract screening with explicit, documented decisions (PRISMA 2020).

Every one of the 924 records gets a decision:
  include  -> goes to full-text retrieval, with a review group (where it is discussed)
  exclude  -> with an exclusion code (EC1..EC6)

Decisions were made manually by reading every title and, for borderline records, the abstract.
They are written here explicitly so the screening is reproducible and auditable.

Review scope (inclusion criteria)
  IC1  Topic models of any family (algebraic, probabilistic, neural, embedding-clustering, LLM-based),
       including cross-lingual, multimodal, dynamic, hierarchical, streaming and supervised variants.
  IC2  Unsupervised / weakly supervised text clustering (short text, documents, multi-view, LLM-guided),
       taxonomy or theme induction from text corpora.
  IC3  Text representation learning used for semantic structure discovery: sentence / document embeddings,
       LLM-based embedders, embedding benchmarks that include clustering, interpretable embeddings.
  IC4  Unsupervised keyphrase / aspect / concept discovery that yields topic-like semantic units.
  IC5  Evaluation methodology for topic models or text clustering.
  IC6  Applications whose core analytical method is topic modeling or semantic clustering
       (incl. topic/cluster-structured retrieval and RAG).
  Time window 2025-2026, English full text.

Exclusion codes
  EC1  Retrieval / RAG / QA system without a topic or cluster-structure component
  EC2  Supervised information extraction or classification (e.g. ABSA triplets, detection tasks)
  EC3  Vision-, speech- or graph-only work without text semantic discovery
  EC4  Off-topic NLP (generation, LLM safety/privacy, detection of machine text, etc.)
  EC5  Not a research article (workshop summary, erratum, demo without evaluation)
  EC6  Domain survey without methodological content on the review topic

Run:  python scripts/03_screen.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "corpus_2025_2026" / "pool.json"
OUT = ROOT / "corpus_2025_2026" / "screening.json"

# ---- review groups -------------------------------------------------------------
TM = "topic-models"            # IC1 methods
TMEVAL = "topic-evaluation"    # IC5
CL = "text-clustering"         # IC2
REP = "text-representation"    # IC3
KEY = "keyphrase-concept"      # IC4
MM = "multimodal-semantic"     # IC1/IC2 with images
APP = "applications"           # IC6
SURV = "related-surveys"       # surveys used for the comparison table

INCLUDE = {}


def add(group, ids):
    for i in ids.split():
        INCLUDE[i] = group


add(TM, """P0001 P0002 P0003 P0004 P0005 P0006 P0007 P0008 P0009 P0010 P0011 P0012 P0013 P0015 P0016
P0017 P0018 P0019 P0020 P0021 P0022 P0023 P0024 P0025 P0026 P0027 P0029 P0030 P0031 P0032 P0033 P0034
P0037 P0038 P0039 P0041 P0042 P0043 P0044 P0045 P0046 P0048 P0050 P0051 P0055 P0056 P0058 P0061 P0063
P0065 P0066 P0067 P0070 P0071 P0075 P0076 P0077 P0080 P0082 P0109 P0246 P0260 P0876""")
add(TMEVAL, "P0036 P0052 P0054 P0060 P0069")
add(SURV, "P0040 P0047 P0053 P0107 P0552")
add(CL, """P0057 P0072 P0074 P0078 P0079 P0083 P0086 P0087 P0091 P0096 P0097 P0104 P0119 P0127 P0128
P0218 P0245 P0267 P0268 P0291 P0298 P0300 P0319 P0346 P0414 P0405 P0429 P0452 P0459 P0460 P0461
P0483 P0554 P0578 P0580 P0662 P0126 P0317""")
add(REP, """P0068 P0084 P0088 P0089 P0090 P0092 P0093 P0094 P0095 P0101 P0102 P0103 P0105 P0108 P0112
P0118 P0125 P0129 P0130 P0131 P0132 P0139 P0140 P0148 P0149 P0152 P0157 P0168 P0172 P0173 P0182
P0200 P0249 P0254 P0255 P0269 P0292 P0293 P0302 P0303 P0304 P0327 P0330 P0331 P0348 P0388 P0390
P0392 P0409 P0416 P0435 P0436 P0438 P0439 P0440 P0466 P0467 P0468 P0471 P0472 P0540 P0576 P0592
P0648 P0651 P0700 P0748 P0749 P0775 P0849""")
add(KEY, "P0124 P0166 P0243 P0287 P0353 P0426 P0427 P0481 P0556 P0573 P0600 P0653")
add(MM, "P0098 P0383 P0433 P0537 P0538")
add(APP, """P0014 P0028 P0035 P0039 P0049 P0059 P0064 P0073 P0138 P0299 P0307 P0313 P0318 P0338 P0355
P0370 P0250 P0406 P0407 P0535 P0607 P0608 P0609 P0649 P0674 P0699 P0707 P0742""")

# ---- explicit exclusion codes for records that a keyword rule would have let through ----
EXCLUDE_CODE = {
    # topic/cluster keyword hits that are not in scope
    "P0062": "EC4", "P0818": "EC4", "P0135": "EC4", "P0290": "EC4", "P0143": "EC1", "P0160": "EC1",
    "P0171": "EC3", "P0194": "EC2", "P0236": "EC1", "P0376": "EC4", "P0434": "EC4", "P0675": "EC6",
    "P0788": "EC4", "P0819": "EC4", "P0828": "EC1", "P0899": "EC4", "P0195": "EC3", "P0196": "EC3",
    "P0301": "EC2", "P0356": "EC4", "P0380": "EC4", "P0537x": "EC3", "P0579": "EC3", "P0680": "EC3",
    "P0765": "EC2", "P0855": "EC1", "P0147": "EC3", "P0657": "EC3", "P0462": "EC3", "P0664": "EC3",
    "P0665": "EC3", "P0381": "EC4", "P0596": "EC4", "P0647": "EC6", "P0482": "EC5", "P0215": "EC5",
    "P0586": "EC5", "P0625": "EC6", "P0391": "EC2", "P0156": "EC4", "P0581": "EC2", "P0120": "EC2",
    "P0325": "EC2", "P0432": "EC1", "P0497": "EC1", "P0247": "EC2", "P0698": "EC4", "P0720": "EC4",
    "P0756": "EC4", "P0601": "EC2", "P0558": "EC4", "P0610": "EC4", "P0525": "EC4", "P0542": "EC4",
    "P0106": "EC1",
}
BUCKET_DEFAULT_CODE = {
    "retrieval-rag": "EC1", "keyphrase-aspect": "EC2", "text-representation": "EC4",
    "other": "EC4", "text-clustering": "EC3", "llm-text-mining": "EC4", "topic-model": "EC4",
}
# aspect-sentiment triplet / aspect-term extraction papers are supervised IE (EC2)
ASTE_HINTS = ("triplet", "aspect term", "aspect-based sentiment", "aspect sentiment", "quadruple")


def main():
    pool = json.load(open(POOL))
    out = []
    for r in pool:
        rid = r["id"]
        if rid in INCLUDE:
            dec, code, group = "include", "", INCLUDE[rid]
        else:
            dec, group = "exclude", ""
            t = r["title"].lower()
            if rid in EXCLUDE_CODE:
                code = EXCLUDE_CODE[rid]
            elif any(h in t for h in ASTE_HINTS):
                code = "EC2"
            elif r["bucket"] == "other" and any(k in t for k in ("image", "video", "visual", "3d", "speech", "audio")):
                code = "EC3"
            else:
                code = BUCKET_DEFAULT_CODE.get(r["bucket"], "EC4")
        out.append({"id": rid, "decision": dec, "group": group, "exclusion_code": code})
    json.dump(out, open(OUT, "w"), indent=1)
    inc = [o for o in out if o["decision"] == "include"]
    print("included for full-text:", len(inc), Counter(o["group"] for o in inc))
    print("excluded at screening:", len(out) - len(inc),
          Counter(o["exclusion_code"] for o in out if o["decision"] == "exclude"))
    missing = [i for i in INCLUDE if i not in {r["id"] for r in pool}]
    assert not missing, missing


if __name__ == "__main__":
    main()
