# STATUS — Review 03 (RAG)

Progress log (newest last). Every step writes its outputs to disk so work can resume after interruption.

- 2026-10-16: folder created; protocol written (`search/queries.md`).
- 2026-10-16: identification done (corpus 404, ACL Anthology 1436, Crossref 5658, arXiv 1790 -> 7305 after de-dup;
  `search/identification_counts.json`). Rule-based screening `tools/screen.py` (+ `search/manual_decisions.json`).
- Stratum A (core 2025-2026 corpus, 229 records) queued in `search/fulltext_queue.json`; full texts fetched with
  `tools/fetch_fulltext.py` (copy of shared tool; arXiv API returned 429 so arXiv web search is used).
- Backward citation searching: `tools/snowball.py count` over core reference lists -> `search/snowball_counts.json`;
  seeds in `search/snowball_seeds.txt`; metadata of cited seeds via `tools/resolve_titles.py` -> `search/citation_hits.json`.
- Evidence extraction started: read excerpts with `tools/show.py . --next 3`, write batch JSON, ingest with
  `tools/ingest.py . <batch.json>` (fills provenance, runs verifier). Evidence in `evidence/<key>.json`.
