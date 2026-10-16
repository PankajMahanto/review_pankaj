"""Title/abstract screening for the RAG review (stage 1, rule-based and auditable).

Every candidate in search/candidates.json receives exactly one decision:
  eligible                -> passes IC1-IC4 (may still be EC7 = not selected for full text later)
  exclude + reason code   -> EC1 ... EC6 (see search/queries.md)
Manual decisions (search/manual_decisions.json) override the rules; each carries its own note.

Venue quality is decided by an explicit whitelist (CORE 2023 A*/A conferences, JCR Q1 journals).

Usage: python reviews/03_rag/tools/screen.py reviews/03_rag
Output: search/screening.json, search/screening_counts.json
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

RDIR = Path(sys.argv[1])

# ------------------------------------------------------------------ venue whitelist
A_STAR = [
    r"Annual Meeting of the Association for Computational Linguistics|^ACL$",
    r"Empirical Methods in Natural Language Processing|^EMNLP$",
    r"Transactions of the Association for Computational Linguistics",
    r"^Computational Linguistics$",
    r"Neural Information Processing Systems|NeurIPS",
    r"International Conference on Machine Learning|\bICML\b",
    r"Learning Representations|\bICLR\b",
    r"AAAI Conference on Artificial Intelligence|^AAAI$",
    r"International Joint Conference on Artificial Intelligence|\bIJCAI\b",
    r"Knowledge Discovery and Data Mining|\bKDD\b",
    r"Web Conference|World Wide Web Conference|^WWW$",
    r"International ACM SIGIR Conference on Research and Development in Information Retrieval|^SIGIR$",
    r"IEEE Transactions on Pattern Analysis and Machine Intelligence",
    r"IEEE Transactions on Knowledge and Data Engineering|IEEE Trans\. Knowl\. Data Eng\.",
    r"IEEE Transactions on Neural Networks and Learning Systems",
    r"ACM Computing Surveys",
    r"^Artificial Intelligence$",
    r"Journal of Machine Learning Research",
    r"Conference on Computer Vision and Pattern Recognition \(CVPR\)|International Conference on Computer Vision \(ICCV\)|\bECCV\b|European Conference on Computer Vision",
    r"ACM International Conference on Multimedia$|^Proceedings of the \d+(st|nd|rd|th) ACM International Conference on Multimedia$",
    r"USENIX Security|Symposium on Security and Privacy|Computer and Communications Security|\bNDSS\b",
    r"Proceedings of the VLDB Endowment|International Conference on Data Engineering \(ICDE\)|\bSIGMOD\b|Management of Data",
    r"International Conference on Software Engineering \(ICSE\)|Automated Software Engineering \(ASE\)|Foundations of Software Engineering",
]
A = [
    r"North American Chapter of the Association for Computational Linguistics|^NAACL$",
    r"European Chapter of the Association for Computational Linguistics|^EACL$",
    r"International Conference on Computational Linguistics|^COLING$",
    r"Findings of the Association for Computational Linguistics",
    r"Asia-Pacific Chapter of the Association for Computational Linguistics|\bAACL\b",
    r"Conference on Information and Knowledge Management|^CIKM$",
    r"Web Search and Data Mining|^WSDM$",
    r"European Conference on Information Retrieval|^ECIR$|^Advances in Information Retrieval$",
    r"Conference on Language Modeling|\bCOLM\b",
    r"Transactions on Machine Learning Research",
    r"International Conference on Data Mining|^ICDM$|SIAM International Conference on Data Mining",
    r"Machine Learning and Knowledge Discovery in Databases",
    r"Language Resources and Evaluation|\bLREC\b",
    r"Computational Natural Language Learning|\bCoNLL\b",
    # JCR Q1 journals (CS / IS / AI) — full and DBLP-abbreviated names
    r"^Neurocomputing$", r"^Knowledge-Based Systems$|^Knowl\. Based Syst\.$",
    r"^Expert Systems with Applications$|^Expert Syst\. Appl\.$",
    r"^Information Processing (and|&|&amp;) Management$|^Inf\. Process\. Manag\.$",
    r"^Information Sciences$|^Inf\. Sci\.$", r"^Pattern Recognition$", r"^Neural Networks$", r"^Information Fusion$",
    r"^Artificial Intelligence Review$", r"^Machine Learning$|^Mach\. Learn\.$",
    r"^ACM Transactions on Information Systems$|^ACM Trans\. Inf\. Syst\.$",
    r"ACM Transactions on Knowledge Discovery from Data|ACM Trans\. Knowl\. Discov\. Data",
    r"^IEEE Transactions on Cybernetics$", r"^IEEE Transactions on Big Data$",
    r"IEEE Transactions on Affective Computing|IEEE Trans\. Affect\. Comput\.",
    r"^Engineering Applications of Artificial Intelligence$", r"^Data Mining and Knowledge Discovery$",
    r"^IEEE Transactions on Audio, Speech and Language Processing$",
    r"^IEEE Transactions on Dependable and Secure Computing$",
    r"^IEEE Transactions on Information Forensics and Security$",
    r"^IEEE Transactions on Multimedia$", r"^IEEE Transactions on Image Processing$",
    r"^IEEE Transactions on Software Engineering$", r"^ACM Transactions on Software Engineering and Methodology$",
    r"^Advanced Engineering Informatics$", r"^Automation in Construction$", r"^Computers in Industry$",
    r"^Journal of Manufacturing Systems$",
    r"^npj Digital Medicine$", r"^Journal of the American Medical Informatics Association$",
    r"^Journal of Biomedical Informatics$", r"^Journal of Medical Internet Research$",
    r"^Nature$|^Nature Medicine$|^Nature Communications$|^Nature Machine Intelligence$|^NEJM AI$",
    r"^Radiology: Artificial Intelligence$|^The Lancet Digital Health$",
    r"^Journal of the Association for Information Science and Technology$",
]
LOW_TRACK = r"workshop|student research|shared task|demo|tutorial|symposium series|companion|doctoral|poster volume"


def tier(venue):
    v = (venue or "").strip()
    if not v or v == "arXiv":
        return "preprint"
    if re.search(LOW_TRACK, v, re.I):
        return "workshop/demo"
    if re.search(r"ICTIR|Asia Pacific Region|Symposium Series", v):
        return "other"
    for rx in A_STAR:
        if re.search(rx, v):
            return "A*"
    for rx in A:
        if re.search(rx, v):
            return "A"
    return "other"


# ------------------------------------------------------------------ topic rules
RAG_TITLE = re.compile(
    r"retrieval[- ]?augment|\bRAG\b|[A-Za-z0-9]RAG\b|GraphRAG|retrieval[- ]enhanced|augmented language model|"
    r"retrieve[- ]and[- ]generate|retrieve[- ]then[- ]read|search[- ]augmented|agentic search|deep research|"
    r"search agent|open[- ]domain question answering|knowledge[- ]intensive", re.I)
RAG_ABS = re.compile(r"retrieval[- ]augmented|\bRAG\b|open[- ]domain question answering|knowledge[- ]intensive"
                     r"|retriever[- ]reader|large language model|\bLLMs?\b|question answering|reader", re.I)
NLP_CTX = re.compile(r"language model|\bLLMs?\b|generat|question|answer|retriev|NLP|text|document|corpus|knowledge", re.I)
OTHER_SENSE = re.compile(
    r"golden retriever|labrador|\bRAG ?[12]\b|recombination[- ]activating|red[- ]amber[- ]green|\bRAG status|"
    r"knowledge[- ]intensive (business|service|firm|organi[sz]ation|entrepreneur|industr|compan|economy|"
    r"sector|employ|innovation|region|manufactur)", re.I)
NON_TEXT_GEN = re.compile(
    r"image generation|text-to-image|diffusion|video generation|motion generation|3D generation|music generation|"
    r"speech synthesis|text-to-speech|traffic|time[- ]series forecast|weather|molecul(e|ar) generation|protein design|"
    r"trajectory|point cloud|image restoration|super[- ]resolution", re.I)
RETRIEVAL_ONLY = re.compile(r"dense retriev|dense passage retriev|\bretriever|re-?rank|passage retrieval|"
                            r"embedding model|text embedding|query (expansion|reformulation|rewriting)|"
                            r"information retrieval|search engine|document retrieval", re.I)
GEN_TERMS = re.compile(r"retrieval[- ]augmented|\bRAG\b|[A-Za-z]RAG\b|generat|question answering|\bQA\b|reader|"
                       r"\bLLM|language model|answer", re.I)
NOT_ARTICLE_TITLE = re.compile(r"\(student abstract\)|abstract reprint|thesis proposal|\bat SemEval|at CheckThat|"
                               r"at LongEval|at FinMMEval|shared task|^overview of|^tutorial|: a tutorial|"
                               r"\bproceedings\b|keynote|panel discussion|^preface|^editorial|book review", re.I)
BAD_TYPES = {"book", "monograph", "edited-book", "reference-entry", "reference-book", "component", "dataset",
             "peer-review", "report", "other", "proceedings", "database"}


def non_english(t):
    letters = [ch for ch in t if ch.isalpha()]
    return bool(letters) and sum(1 for ch in letters if ord(ch) > 591) / len(letters) > 0.3


def decide(r):
    t, ab = r.get("title", ""), r.get("abstract", "") or ""
    y = r.get("year") or 0
    tr = tier(r.get("venue"))
    r["tier2"] = tr
    if y and (y < 2017 or y > 2027):
        return "exclude", "EC6", f"year {y} outside 2017-2026"
    if non_english(t):
        return "exclude", "EC6", "non-English title"
    if OTHER_SENSE.search(t):
        return "exclude", "EC1", "title term used in another sense"
    if (r.get("type") or "") in BAD_TYPES:
        return "exclude", "EC4", f"record type '{r['type']}'"
    doi = (r.get("doi") or "").lower()
    if re.search(r"\.\w+-(demo|demos|tutorials?)\.", doi):
        return "exclude", "EC4", "system demonstration track (DOI)"
    if re.search(r"\.\w+-srw\.|\.\w+-ws\.|\.wnu-|\.repl4nlp-", doi):
        return "exclude", "EC3", "student research workshop / workshop track (DOI)"
    if NOT_ARTICLE_TITLE.search(t):
        return "exclude", "EC4", "not a full research article (title)"
    if not NLP_CTX.search(t + " " + ab):
        return "exclude", "EC1", "no language/retrieval context"
    rag_title = bool(RAG_TITLE.search(t))
    if NON_TEXT_GEN.search(t) and not re.search(r"language model|\bLLM|question answering|\bVQA\b|report", t, re.I):
        return "exclude", "EC1", "retrieval for non-text generation or non-generative prediction"
    if not rag_title:
        if RETRIEVAL_ONLY.search(t) and not GEN_TERMS.search(t):
            if not re.search(r"retrieval[- ]augmented|\bRAG\b|open[- ]domain question answering|retriever[- ]reader", ab, re.I):
                return "exclude", "EC2", "retrieval/ranking only (no generator or RAG evaluation)"
        if not RAG_ABS.search(ab) and not RAG_ABS.search(t):
            return "exclude", "EC1", "no RAG component in title/abstract"
        if not re.search(r"retrieval[- ]augmented|\bRAG\b|open[- ]domain question answering|retriever|knowledge[- ]intensive|search", t + " " + ab, re.I):
            return "exclude", "EC1", "no RAG component in title/abstract"
    if tr in ("workshop/demo",):
        return "exclude", "EC3", "workshop/demo/shared-task venue"
    if tr in ("other",):
        return "exclude", "EC3", "venue not in A*/A/Q1 whitelist"
    if tr == "preprint":
        hint = r.get("venue_hint", "") or ""
        if re.search(r"accepted|published|to appear|camera|proceedings|main conference|findings", hint, re.I) and tier(hint) in ("A*", "A"):
            r["tier2"] = tier(hint) + " (per arXiv comment)"
            return "eligible", "", "preprint of A*/A paper (venue verified later)"
        return "exclude", "EC3", "preprint without peer-reviewed version (unless foundational, see manual decisions)"
    return "eligible", "", ""


def main():
    cands = json.load(open(RDIR / "search" / "candidates.json"))
    man_p = RDIR / "search" / "manual_decisions.json"
    manual = json.load(open(man_p)) if man_p.exists() else {}
    out, cnt = [], Counter()
    for r in cands:
        d, code, why = decide(r)
        src = "rule"
        if r["cid"] in manual:
            m = manual[r["cid"]]
            d, code, why, src = m["decision"], m.get("code", ""), m.get("note", ""), "manual"
        rec = {"cid": r["cid"], "title": r["title"], "year": r.get("year"), "venue": r.get("venue"),
               "tier": r["tier2"], "doi": r.get("doi", ""), "arxiv_id": r.get("arxiv_id", ""),
               "corpus_id": r.get("corpus_id", ""), "sources": r["sources"], "cited_by": r.get("cited_by", 0),
               "decision": d, "code": code, "reason": why, "decided_by": src}
        out.append(rec)
        cnt[(d, code)] += 1
    json.dump(out, open(RDIR / "search" / "screening.json", "w"), indent=1, ensure_ascii=False)
    summary = {f"{d}{(':' + c) if c else ''}": n for (d, c), n in sorted(cnt.items())}
    json.dump(summary, open(RDIR / "search" / "screening_counts.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
