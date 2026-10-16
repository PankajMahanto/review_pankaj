# Review 03 — Retrieval-Augmented Generation (RAG): protocol, sources and search strings

Search date: 2026-10-16 (all automated searches were run on this date; the author-curated corpus was
assembled before, see `corpus_2025_2026/`).

## 1. Scope

Retrieval-augmented generation (RAG): systems in which a (large) language model conditions its output on
evidence that a retriever selects at inference time from an external, non-parametric knowledge source
(text corpus, web, knowledge graph, tables, images/video, code, memory store). The review covers the
whole RAG pipeline (indexing/chunking, query formulation, retrieval, re-ranking/filtering/compression,
generation and its training, iterative/adaptive/agentic control), graph- and multimodal RAG, evaluation
and benchmarks, robustness/security/privacy, and applications.

## 2. Research questions

* **RQ1 (techniques)** Which RAG architectures and paradigms have been proposed, and how can they be
  organised into a taxonomy?
* **RQ2 (components)** Which retrievers, generators and knowledge sources do RAG studies use, and how
  are retriever and generator coupled (frozen, fine-tuned, jointly trained, RL-optimised)?
* **RQ3 (evaluation)** Which benchmark datasets and evaluation metrics are used, and what do the
  reported results show when studies share a benchmark?
* **RQ4 (applications)** In which application domains is RAG used, and what evidence of benefit is reported?
* **RQ5 (trustworthiness)** Which robustness, faithfulness, security and privacy problems of RAG have been
  documented, and which defences have been proposed?
* **RQ6 (gaps)** Which open challenges and research directions follow from the evidence collected for RQ1–RQ5?

## 3. Sources

| Source | What | Coverage |
|---|---|---|
| Author-curated corpus (`corpus_2025_2026/pool.json`, bucket `retrieval-rag`) | DBLP records of 2025–2026 A*/A conferences and Q1/Q2 journals + arXiv sweep of July 2026 | 384 records |
| ACL Anthology (full dump, `sources/acl_anthology.jsonl`) | all ACL/EMNLP/NAACL/EACL/COLING/TACL/Findings/workshop papers with abstracts and DOIs | title match, 1999–2026 |
| Crossref REST API | DOI registry (ACM, IEEE, Springer, Elsevier, AAAI, ACL ...), relevance-ranked, <= 3,000 records per query | title match, 1999–2026 |
| arXiv API | preprints; used to reach NeurIPS/ICML/ICLR/COLM/TMLR papers (no DOIs) through their preprints, the published venue being read from the arXiv comment / journal-ref and then checked on OpenReview / proceedings | title match |

## 4. Title filter (applied to every source)

```
retrieval[- ]?augment|\bRAG\b|GraphRAG|retrieval[- ]enhanced|augmented language model|retrieval[- ]based (generation|language model)|retrieve[- ]and[- ]generate|retrieve[- ]then[- ]read|dense passage retrieval|open[- ]domain question answering|knowledge[- ]intensive|\bretriever|search[- ]augmented|search agent|agentic search|deep research
```

## 5. Crossref / arXiv query strings

See `search/search_log.txt` for the per-query hit counts. Queries (phrase searches):

1. retrieval-augmented generation
2. retrieval augmented large language model
3. retrieval-augmented language model
4. graph retrieval-augmented generation
5. knowledge graph retrieval-augmented generation
6. multimodal retrieval-augmented generation
7. agentic retrieval-augmented generation
8. retrieval-augmented generation benchmark
9. retrieval-augmented generation evaluation
10. retrieval-augmented generation hallucination
11. retrieval-augmented generation attack
12. retrieval-augmented generation privacy
13. open-domain question answering retriever
14. dense passage retrieval question answering
15. retrieval-augmented generation survey
16. adaptive retrieval augmented generation
17. search-augmented reasoning reinforcement learning
18. retrieval-augmented generation medical
19. retrieval-augmented generation legal
20. retrieval-augmented code generation
21. context compression retrieval-augmented generation
22. reranking retrieval-augmented generation
23. long context retrieval-augmented generation
24. knowledge-intensive language tasks retrieval

## 6. Eligibility criteria

Inclusion (all must hold):

* **IC1 topic** — the study proposes, analyses, evaluates, benchmarks, attacks/defends, or applies a
  system in which a generator (seq2seq model or LLM) is conditioned on retrieved external evidence; or it
  proposes a retrieval/re-ranking/compression component that is evaluated *within* a RAG or
  retriever–reader (open-domain QA) pipeline; or it is a survey of RAG.
* **IC2 publication** — peer-reviewed paper in an A*/A conference (CORE 2023) or Q1/Q2 journal (JCR/SJR),
  or a preprint/workshop paper that is a recognised foundation of the field (≥ 200 citations in Crossref
  or a widely adopted method/benchmark).
* **IC3 language and type** — English, full research article (long/short/findings/journal paper).
* **IC4 time window** — 2017–2026 (2017 = first neural retriever–reader systems); foundational works
  before 2020 are kept as background only.

Exclusion reason codes used in `search/screening.json`:

| Code | Meaning |
|---|---|
| EC1 | not about retrieval-augmented generation (title term used in another sense, retrieval for a non-generative task, recommendation without generation, ...) |
| EC2 | retrieval / ranking only — no generator and no RAG or reader-based evaluation (pure dense retrieval, IR efficiency, query performance prediction) |
| EC3 | venue below the quality threshold (not A*/A/Q1/Q2) and not a foundational highly cited preprint |
| EC4 | not a full research article (abstract reprint, student abstract, thesis proposal, demo, tutorial, shared-task system description, overview of a shared task) |
| EC5 | duplicate or superseded version of an included study (preprint of a published paper, conference version of an extended journal paper) |
| EC6 | outside the time window or not in English |
| EC7 | lower priority for full-text extraction: eligible but not selected by the impact/recency-stratified selection rule (Section 7) |

## 7. Selection for full-text assessment

The number of eligible records exceeds what can be read and extracted manually in full text. Records were
therefore selected for full-text assessment by an explicit, stratified rule (implemented in
`tools/screen.py`):

1. **Core 2025–2026 stratum**: every eligible peer-reviewed record of the author-curated corpus
   (2025–2026 A*/A conferences, Q1/Q2 journals).
2. **Foundations stratum (2017–2022)**: eligible records with the highest Crossref/ACL citation counts
   that introduced a retriever–reader / RAG paradigm, a retriever used by later RAG systems, or a
   benchmark used by later RAG studies (judged on title + abstract).
3. **2023–2025 stratum**: eligible records from A*/A venues ranked by citations per year since publication,
   covering every taxonomy category (graph, multimodal, agentic/RL, evaluation, security, efficiency,
   domains), until the full-text budget of ~300 is reached.

Full-text exclusion codes: FT1 no RAG contribution on reading; FT2 superseded by extended version;
FT3 no empirical or formal evaluation; FT4 full text not retrievable (open access copy not found).

## 8. Data extraction

One JSON record per included study (`evidence/<key>.json`): bibliographic data, read_from, evidence level,
taxonomy category/sub-category, task, problem, architecture, retriever, generator, knowledge source,
datasets (+ sizes), metrics, baselines, key results (numbers copied from the paper), strengths,
limitations (author-stated / reported in paper / reviewer observation from reported table), code link.
Every number, dataset name and code URL is checked automatically against the paper's full text
(`tools/review/verify_evidence.py`).

## 9. Quality assessment

Each included study is scored on five yes/partly/no items (Q1 clear problem and method; Q2 public or
standard datasets; Q3 comparison with strong/recent baselines; Q4 ablation or analysis of components;
Q5 code or data released, limitations discussed). Scores are reported in the supplementary table.
