"""Title/abstract screening of the de-duplicated candidates (PRISMA 'screening' stage).

Rules are applied in a fixed order; a manual decision (search/manual_screening.tsv) always overrides them.
Every record ends with decision in {include, exclude} and a reason code (see search/queries.md):
  EC1 retrieval/RAG/QA only      EC2 topic model / keyphrase      EC3 non-text or cross-modal
  EC4 features for a downstream supervised task                   EC5 workshop / shared task / demo / not an article
  EC6 time window or venue quality                                EC7 word-level only           EC8 off-topic
Include codes: INC (peer-reviewed, 2023-2026), FND (foundational pre-2023 work), PRE-STD (standard preprint
model/benchmark used as a baseline by included studies), PRE-RECENT (2026 preprint from the author corpus).

Usage: python tools/screen.py <review_dir>
Output: search/screening.json, search/to_screen_manually.txt (records that still need a manual decision)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

JOURNALS = [
    r"Expert Systems with Applications", r"Expert Syst\. Appl\.", r"Knowledge-Based Systems", r"Knowl\. Based Syst\.",
    r"Information Processing (&|&amp;|and) Management", r"Inf\. Process\. Manag\.", r"Neurocomputing", r"Neural Networks",
    r"Information Sciences", r"Information Fusion", r"Pattern Recognition", 
    r"Engineering Applications of Artificial Intelligence", r"Applied Soft Computing", 
    r"Artificial Intelligence Review", r"IEEE Transactions on Knowledge and Data Engineering",
    r"IEEE Trans\. Knowl\. Data Eng\.", r"IEEE Transactions on Neural Networks and Learning Systems",
    r"IEEE Transactions on Pattern Analysis and Machine Intelligence", r"IEEE Transactions on Big Data", r"IEEE Trans\. Big Data",
    r"IEEE Transactions on Cybernetics", r"IEEE/ACM Transactions on Audio, Speech,? and Language Processing",
    r"IEEE Transactions on Affective Computing", r"IEEE Transactions on Computational Social Systems", 
    r"ACM Transactions on Information Systems", r"ACM Transactions on Knowledge Discovery from Data",
    r"ACM Trans\. Knowl\. Discov\. Data", r"ACM Transactions on Intelligent Systems and Technology",
    r"ACM Trans\. Intell\. Syst\. Techn.*", r"ACM Computing Surveys", r"Data Mining and Knowledge Discovery",
    r"Data Min\. Knowl\. Discov\.", r"Machine Learning", r"Mach\. Learn\.", 
    
    r"Journal of Big Data", r"Scientific Reports", 
    r"Complex (&|&amp;|and) Intelligent Systems", 
    r"Cognitive Computation", r"Journal of the Association for Information Science and Technology", r"Scientometrics",
    r"Journal of Informetrics", r"Journal of Biomedical Informatics", r"Artificial Intelligence in Medicine",
    r"Computers in Biology and Medicine", r"Bioinformatics", 
    r"Big Data and Cognitive Computing", r"Royal Society Open Science", r"Transactions on Machine Learning Research",
]
# Q2 / mega-journals (IEEE Access, MDPI, PLOS ONE, PeerJ CS, KAIS, Applied Intelligence, NCA, CSL, NLE, LRE, WWW journal,
# Information Systems, IJMLC, PRL) were removed from the whitelist on 2026-10-16 (protocol change, see queries.md).
JRX = re.compile(r"^(?:" + "|".join(JOURNALS) + r")$", re.I)
ACM_CONF = re.compile(r"SIGIR|SIGKDD|Knowledge Discovery and Data Mining|Web Conference|World Wide Web|"
                      r"Information and Knowledge Management|Information & Knowledge Management|Web Search and Data Mining", re.I)
WORKSHOP = re.compile(r"workshop|student research|shared task|demo|tutorial|SemEval|\bWMT\b|findings of the.*shared", re.I)
ACL_MAIN = re.compile(r"Annual Meeting of the Association for Computational Linguistics|Empirical Methods in Natural Language|"
                      r"North American Chapter|Transactions of the Association for Computational Linguistics|"
                      r"^Computational Linguistics$|European Chapter|Findings of the Association|International Conference on "
                      r"Computational Linguistics|Language Resources and Evaluation Conference|International Conference on Language "
                      r"Resources and Evaluation|Joint International Conference on Computational Linguistics, Language Resources|"
                      r"Asia-Pacific Chapter|Conference on Computational Natural Language Learning|^(ACL|EMNLP|NAACL|EACL|COLING|"
                      r"LREC|TACL|AACL|CoNLL)\b", re.I)

EC1 = re.compile(r"retriev|\bRAG\b|question[- ]answer|\bQA\b|re-?rank|passage|search engine|\bquer(y|ies)\b", re.I)
EC2 = re.compile(r"topic model|topic discover|keyphrase|keyword extraction", re.I)
EC3 = re.compile(r"\bimages?\b|\bvisual|\bvideo|\bspeech\b|\baudio\b|acoustic|\bspeaker|multi-?modal|\bvision\b|vision-language|"
                 r"molecul|protein|text-to-image|diffusion model|cross-modal|\bCLIP\b|\bsign language", re.I)
EC8 = re.compile(r"knowledge graph (embedding|completion)|graph embedding model|network embedding|temporal knowledge graph|"
                 r"signed network|\bmalware\b|time series|recommend", re.I)


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def venue_tier(r, pool):
    if "snowball" in r["sources"]:
        return "foundational"
    if r.get("corpus_id"):
        vt = pool[r["corpus_id"]].get("venue_tier", "")
        return {"J1": "J", "J2": "J", "preprint": "preprint"}.get(vt, vt or "other")
    doi, venue = (r.get("doi") or "").lower(), (r.get("venue") or "").strip()
    if r.get("acl_key") or doi.startswith(("10.18653/", "10.1162/tacl", "10.1162/coli")):
        if WORKSHOP.search(venue):
            return "workshop"
        return "A" if ACL_MAIN.search(venue) else "acl-other"
    if doi.startswith("10.1609/aaai") or doi.startswith("10.24963/ijcai"):
        return "A*"
    if doi.startswith("10.1145/") and ACM_CONF.search(venue):
        return "A" if not WORKSHOP.search(venue) else "workshop"
    if doi.startswith(("10.2139/ssrn", "10.21203/rs", "10.20944/preprints")):
        return "preprint"
    if JRX.match(venue):
        return "J"
    if re.search(r"Advances in Neural Information Processing Systems|International Conference on Learning Representations|"
                 r"International Conference on Machine Learning|IEEE International Conference on Data Mining", venue):
        return "A*"
    if venue in ("", "arXiv"):
        return "preprint"
    return "other"


def main():
    rdir = Path(sys.argv[1])
    cands = json.load(open(rdir / "search" / "candidates.json"))
    pool = {r["id"]: r for r in json.load(open(ROOT / "corpus_2025_2026" / "pool.json"))}
    manual = {}
    mp = rdir / "search" / "manual_screening.tsv"
    if mp.exists():
        for line in open(mp):
            if not line.strip() or line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            manual[f[0]] = {"decision": f[1], "code": f[2], "note": f[3] if len(f) > 3 else ""}
    out, todo = [], []
    for r in cands:
        y = r.get("year") or 0
        t = venue_tier(r, pool)
        rec = {"cid": r["cid"], "title": r["title"], "year": y, "venue": r.get("venue", ""), "tier": t,
               "doi": r.get("doi", ""), "arxiv_id": r.get("arxiv_id", ""), "sources": r["sources"]}
        m = manual.get(r["cid"]) or manual.get(norm(r["title"]))
        if m and m["code"] == "INC" and (t in ("other", "acl-other", "preprint", "workshop") or y < 2023):
            # a topical include still has to satisfy the venue / time criteria (IC2, IC3)
            rec.update(decision="exclude", code="EC6" if t != "workshop" else "EC5",
                       note=f"on-topic but venue/time criterion not met ({t})", stage="manual+rule")
        elif m:
            rec.update(decision=m["decision"], code=m["code"], note=m["note"], stage="manual")
        elif t == "foundational":
            if (r.get("doi") or "").lower().startswith("10.48550") and (r.get("venue") or "arXiv") == "arXiv":
                rec.update(decision="include", code="PRE-STD", note="snowballing: preprint model/benchmark used as a baseline", stage="rule")
            elif y >= 2023:
                rec.update(decision="include", code="INC", note="added by snowballing (peer-reviewed 2023-2026)", stage="rule")
            else:
                rec.update(decision="include", code="FND", note="snowballing: foundational pre-2023 work", stage="rule")
        elif y < 2013:
            rec.update(decision="exclude", code="EC6", note="before 2013", stage="rule")
        elif t == "workshop":
            rec.update(decision="exclude", code="EC5", note="workshop / shared task / demo", stage="rule")
        elif y < 2023:
            rec.update(decision="exclude", code="EC6", note="pre-2023 and not foundational", stage="rule")
        elif t in ("other", "acl-other"):
            rec.update(decision="exclude", code="EC6", note=f"venue not in the quality whitelist ({t})", stage="rule")
        elif t == "preprint":
            rec.update(decision="exclude", code="EC6", note="preprint without peer review", stage="rule")
        elif EC1.search(r["title"]):
            rec.update(decision="exclude", code="EC1", note="retrieval / RAG / QA title", stage="rule")
        elif EC2.search(r["title"]):
            rec.update(decision="exclude", code="EC2", note="topic model / keyphrase title", stage="rule")
        elif EC3.search(r["title"]):
            rec.update(decision="exclude", code="EC3", note="non-text or cross-modal title", stage="rule")
        elif EC8.search(r["title"]):
            rec.update(decision="exclude", code="EC8", note="off-topic use of matched words", stage="rule")
        else:
            rec.update(decision="unscreened", code="", note="", stage="")
            todo.append(rec)
        out.append(rec)
    json.dump(out, open(rdir / "search" / "screening.json", "w"), indent=1, ensure_ascii=False)
    with open(rdir / "search" / "to_screen_manually.txt", "w") as f:
        for r in sorted(todo, key=lambda x: x["title"]):
            f.write(f"{r['cid']}\t{r['year']}\t{r['tier']}\t{r['venue'][:30]}\t{r['title']}\n")
    print(Counter((r["decision"], r["code"]) for r in out).most_common())
    print("still to screen manually:", len(todo))


if __name__ == "__main__":
    main()
