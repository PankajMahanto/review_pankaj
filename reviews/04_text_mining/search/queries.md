# Review protocol: text representation learning and semantic clustering for text mining in the LLM era

Working title: *Text representation learning and semantic clustering for text mining in the LLM era: a systematic review*

The protocol follows PRISMA 2020 (identification, screening, eligibility, inclusion). It was fixed before
screening started; changes made during the review are logged at the end of this file.

## 1. Scope

The review covers methods that map sentences, short texts and documents to vectors (sentence / text /
document embeddings), the benchmarks and metrics used to evaluate those vectors, and the use of such
vectors (and of large language models, LLMs) to group texts by meaning (semantic text clustering,
short-text clustering, document clustering, intent discovery). Topic modelling, keyphrase extraction and
retrieval-augmented generation (RAG) are covered by separate reviews and appear here only as related tasks.

## 2. Research questions

| RQ | Question |
|----|----------|
| RQ1 | Which text-representation paradigms (static vectors, contextual encoders, contrastive sentence encoders, general-purpose embedding models, LLM-based and training-free LLM embeddings) are used, and how did they change between 2023 and 2026? |
| RQ2 | Which benchmarks, datasets and evaluation metrics are used for text embeddings and for semantic text clustering, and what results do the studies report? |
| RQ3 | How are embeddings and LLMs used for semantic (short-)text clustering: deep and contrastive clustering, LLM-guided clustering, and intent discovery? |
| RQ4 | In which application domains are these representations and clustering methods used? |
| RQ5 | Which limitations do the studies themselves report, and which open problems and research directions follow from them? |

## 3. Information sources

| Source | How it was used | Date |
|--------|-----------------|------|
| Author-curated corpus (`corpus_2025_2026/pool.json`, 924 records from DBLP venue lists 2025-2026 and an arXiv sweep of July 2026) | records whose bucket or earlier screening group is `text-representation`, `text-clustering`, `multimodal-semantic`, `llm-text-mining` or `related-surveys`; all re-screened against the criteria below | 2026-10 |
| ACL Anthology (full metadata dump, 128k papers) | title regular expression (Sec. 4) | 2026-10 |
| Crossref REST API | relevance-ranked `query.bibliographic`, title regular expression applied to every hit | 2026-10 |
| arXiv API | `ti:"q" OR abs:"q"`, title regular expression applied; arXiv copies used for reading and for venues without DOIs (NeurIPS/ICML/ICLR) | 2026-10 |
| Backward snowballing | foundational works cited by the included studies (word2vec, GloVe, Sentence-BERT, SimCSE, MTEB, E5, DEC, SCCL, ...) that the searches above did not return | 2026-10 |

OpenAlex and Semantic Scholar were not used (quota exhausted / rate-limited during the search window).

## 4. Search strings

Title regular expression (applied to ACL Anthology, Crossref and arXiv records, case-insensitive), stored in `title_regex.txt`:

```
sentence[- ](embedding|representation|encoder|vector|similarit) | text[- ]embedding | embedding model |
universal (text|sentence) | document[- ](embedding|representation) | semantic textual similarity | \bSTS\b |
text clustering | short[- ]text clustering | document clustering | clustering (of )?(short )?(texts|documents) |
intent discovery | intent induction | new intent | \bMTEB\b | contrastive.{0,40}sentence | sentence.{0,40}contrastive |
(LLM|large language model)s?\b.{0,40}\bcluster | cluster\w*\b.{0,40}(LLM|large language model) |
text representation learning | sentence embeddings?
```

Crossref and arXiv query phrases (15):

1. sentence embeddings
2. sentence representation learning
3. text embeddings large language models
4. contrastive learning sentence embeddings
5. general-purpose text embedding model
6. massive text embedding benchmark
7. semantic textual similarity
8. short text clustering
9. text clustering large language models
10. document clustering embeddings
11. deep clustering short text
12. intent discovery clustering
13. multilingual sentence embeddings
14. interpretable text embeddings
15. unsupervised sentence embedding

## 5. Eligibility criteria

### Inclusion (all must hold)

* **IC1 Topic.** The study proposes, adapts, analyses or benchmarks (a) a method that produces vector
  representations of sentences, short texts or documents for general semantic use (similarity, clustering,
  classification, retrieval as one of several tasks), or (b) a method for semantic clustering of texts
  (short texts, documents, utterances/intents) based on learned representations and/or LLMs.
* **IC2 Peer review.** Journal article, or main/Findings paper of a peer-reviewed conference
  (CORE A*/A or JCR/SJR Q1-Q2 journal). Exception: a preprint that introduced a model or benchmark that the
  included peer-reviewed studies use as a standard baseline (e.g. E5, GTE, Qwen3-Embedding); such preprints
  are listed with the code `PRE-STD` in `screening.json`.
* **IC3 Time.** 2013-2026. Studies published before 2023 are admitted only as *foundational* works
  (introduced a representation, training objective, benchmark or clustering method used as a standard
  baseline by the 2023-2026 studies).
* **IC4 Evidence.** Reports an empirical evaluation on public data or a formal analysis.
* **IC5 Language.** English full text.

### Exclusion codes (title/abstract screening)

| Code | Reason |
|------|--------|
| EC1 | Retrieval / RAG / QA system or retriever-only training (no general-purpose text-representation contribution); covered by the RAG review |
| EC2 | Topic modelling or keyphrase extraction is the main contribution (separate reviews) |
| EC3 | Non-text modality or cross-modal representation (image, speech, video, graph/molecule, text-to-image conditioning) |
| EC4 | Embeddings used only as input features for a supervised downstream task (classification, NER, sentiment, ...), no representation or clustering contribution |
| EC5 | Not a full research article (workshop, shared task, student, demo, tutorial, thesis, erratum), unless foundational |
| EC6 | Outside the time window or venue-quality criteria (pre-2013; pre-2023 and not foundational; unranked venue / non-peer-reviewed preprint) |
| EC7 | Word-level or lexical-semantics study only (no sentence/text-level representation), unless foundational |
| EC8 | Other off-topic use of the matched words (e.g. "embedding" in a non-NLP sense, clustering of non-text data) |

### Full-text exclusion codes

| Code | Reason |
|------|--------|
| FT1 | On reading, no sentence/text-representation or text-clustering contribution |
| FT2 | Duplicate or superseded by an extended version of the same work |
| FT3 | No empirical evaluation or formal analysis |
| NR  | Report not retrieved (no open-access full text and no usable abstract) |

## 6. Screening procedure

1. Automatic de-duplication (DOI, arXiv id, normalised title, fuzzy title ratio >= 95).
2. Rule-based pre-screening: year window, venue tier, workshop/shared-task markers (EC5/EC6), and
   off-topic title patterns (EC1, EC2, EC3, EC8). Every rule is in `tools/screen.py`.
3. Manual title + abstract screening of all records that pass step 2 (one reviewer, decisions and reason
   codes recorded in `screening.json`).
4. Full-text retrieval (ACL Anthology, AAAI OJS, OpenReview, open-access publisher copies, arXiv copies for
   reading) and full-text eligibility assessment.

## 7. Data extraction

One JSON evidence record per included study (`evidence/<key>.json`), extracted from the study's own text:
category and sub-category in the taxonomy, task, problem, architecture, encoder/LLM used, datasets (with
sizes), metrics, baselines, key results (numbers copied from the paper), strengths, limitations (marked
`author-stated` or `reviewer-observed`, the latter only when it follows directly from the paper's own setup),
code link. `tools/review/verify_evidence.py` checks that every number, dataset name and code link in a record
occurs in the paper's full text.

## 8. Quality assessment

Each included study is scored on six binary items derived from its evidence record:
Q1 clearly stated problem and method; Q2 public datasets; Q3 comparison against at least three baselines;
Q4 standard metrics; Q5 code or model released; Q6 limitations discussed by the authors.
The score (0-6) is reported in the supplementary evidence matrix. Studies are not excluded on quality;
the score is used when weighing evidence in the synthesis.

## 9. Synthesis

Narrative synthesis organised by the taxonomy (Sec. 4 of the paper), with result tables compiled only from
numbers reported by the studies (no re-computation, no cross-paper averaging when settings differ).

## 10. Protocol changes

* 2026-10-16: OpenAlex/Semantic Scholar replaced by Crossref + arXiv (API limits).
