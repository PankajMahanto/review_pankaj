# STATUS — review 04: text representation learning and semantic clustering (LLM era)

## Progress log
- 2026-10-16 — Folder created; protocol written (`search/queries.md`).
- 2026-10-16 — Identification: Crossref (4,808 title-matched hits from 26 query runs), arXiv (1,181), ACL Anthology title regex (983),
  author corpus (304 records re-screened), backward snowballing (78). After de-duplication: 5,767 candidates.
- 2026-10-16 — Screening (`tools/screen.py` rules + `tools/manual_decisions.py` manual decisions on 522 titles/abstracts):
  410 records sought for full-text retrieval (INC 345, FND 43, PRE-STD 16, PRE-RECENT 6).
- 2026-10-16 — Full-text retrieval running (`tools/review/fetch_fulltext.py`, log in `search/fetch_log.txt`).

## Next steps
1. Full-text retrieval -> excerpts -> reading + evidence batches (ingest_evidence.py, verifier must be clean).
2. Bibliography (myRef.bib from DOIs, citation order).
3. Paper sections, tables, figures, PRISMA, supplementary, compile.
