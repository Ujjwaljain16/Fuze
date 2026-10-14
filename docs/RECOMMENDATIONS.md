# Recommendations

How Fuze chooses which saved items to show for a project, task, subtask or free-text query. The code is
`backend/ml/intent_engine/`; the decision record is [ADR-007](adr/ADR-007-intent-engine.md).

Ranking uses embeddings and a cross-encoder only. There are no keyword lists, hand-set boosts or rule-based
fallbacks.

## Write path: what is stored for each bookmark

- **Passages.** The extracted text is split into overlapping chunks of about 200 words (40 words of overlap, at
  most 40 chunks; `utils/chunking.py`), each prefixed with the title, embedded, and stored in
  `content_chunks` with `kind = 'passage'` (`services/hybrid_search.index_content_chunks`).
- **Content profile.** One Gemini call returns a validated JSON profile (summary, what it teaches or solves,
  key concepts, `use_when`, content type, audience level, technologies; `services/content_profile.py`). It is
  stored in `content_analysis` and its text is embedded as a `kind = 'profile'` row in `content_chunks`. An
  analysis without a `profile_version` is ignored when results are shown.
- **Versioned vectors.** Every chunk records its `embedding_model`; retrieval compares only vectors from the
  active model (`BAAI/bge-small-en-v1.5`, 384 dimensions).

## Read path: `engine.recommend`

1. **Intent** (`intent.py`). The user's own words are composed into one text: the current subtask, task, the
   query, the project title and description, and the project's technologies, most specific first. This is
   always available, so there is no fallback to rules. Gemini turns that text into a short statement and
   2-4 information needs in a background RQ job (`compute_intent_job`); they are cached for 7 days by
   context hash, and a request never waits for them. Until they exist, only the composed text is used.
2. **Query vectors.** The composed text, the statement and each need are embedded (`embed_query`).
3. **Retrieval.** For each query vector, the 60 nearest chunks (passages and profiles) of that user's content,
   by cosine distance over the HNSW index (`hybrid_search.retrieve`). Each bookmark keeps its best chunk. Users
   whose bookmarks have no chunks yet are served from the document embedding instead.
4. **Rerank (optional).** With `SEARCH_RERANK_ENABLED=true`, a cross-encoder
   (`SEARCH_RERANK_MODEL`, default `cross-encoder/ms-marco-MiniLM-L-6-v2`) scores the intent statement
   (or the composed text) against the best passage of the top 30. Without it, relevance is the clamped cosine
   similarity. It is off by default; see the measurements below.
5. **Diversity.** Maximal marginal relevance with lambda 0.7 over the bookmarks' embeddings, so the list is not
   near-duplicates.
6. **Result.** The score shown is the relevance as a percentage. The reason is the passage that matched.
   Summary, concepts and `use_when` come from the content profile.

Results are cached in Redis for 10 minutes. The key includes the user, the intent hash, the limit, the rerank
setting, the embedding model and a per-user content version that changes on every save, edit and delete, so
new bookmarks appear without invalidating keys.

### Several interests ("General")

One query that lists unrelated topics ("React, python, system design, backend") matches none of them well, so the
General choice sends the profile's technology interests as a list (`interests`) and the engine searches each on its
own (`recommend_interests`): one nearest-passage search per interest, then a round robin over the lists, best
first, no bookmark twice. Every interest is visible near the top and gets about `limit / n` of the places; an
interest with few good bookmarks runs out and the others fill in. Each result is tagged
`metadata.matched_interest` and its weak-match check uses that interest as the query. At most 6 interests are used,
which costs 6 database round trips. On the 238-bookmark library, one blended query gave 6 strong results of 10,
and the per-interest search 9 of 10, with all four interests represented. With no interests saved the page sends
a generic sentence instead.

### Weak matches

Ranking is by passage similarity plus diversity (nDCG 0.97 on the judged requests below), but the engine always
returns up to `limit` results, so a project with few matching bookmarks gets padded with loosely related ones.
After the results are picked, a small cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`, about 0.3 s for ten
pairs, baked into the image) scores each (intent, best passage) pair and marks results under a raw score of -5 as
`weak_match`. The page folds them behind "Show N weaker matches"; nothing is removed and the order is untouched.

Where the floor came from: 15 requests (5 projects, 10 tasks, 150 results) over a real library of 238 bookmarks,
each result labelled as clearly useful, loosely related or irrelevant. The labels were assigned by the AI
assistant that built the check, not by the library's owner, so read these figures as a calibration on one library,
not as a benchmark. Unfiltered, 60% were clearly useful.
With the floor at -5, 89% of the irrelevant and 45% of the loosely related results are marked weak and the strong
list is 81% clearly useful; 23% of the useful ones are marked weak too, mostly bookmarks with no readable page text.
Cosine similarity cannot make this cut (irrelevant results reached 77% while some useful ones were at 66%), which is
why the check uses the cross-encoder. Turn it off with `RECOMMENDATION_CONFIDENCE_ENABLED=false`.

### Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/recommendations/unified-orchestrator` | Recommendations for a `project_id`, `task_id`, `subtask_id` or free text. The name is historical; the frontend uses it. |
| `POST /api/recommendations/task/<id>`, `.../subtask/<id>` | The same engine for one task or subtask. |
| `POST /api/recommendations/generate-context` | On-demand Gemini explanation of how one item helps with the current intent. Uses the caller's own Gemini key (`ml/intent_engine/explain.py`). |
| `POST /api/recommendations/feedback` | Records a judgment (below). |

Search (`/api/search/semantic`, `/api/search/supabase-semantic`) uses the same passage retrieval with the
query as the intent; see [OPTIMIZATIONS.md](OPTIMIZATIONS.md) for how its database round trips were reduced.

## Feedback

The recommendations page sends helpful / not-relevant / clicked judgments (`positive`, `negative`, `neutral`
are mapped to `helpful`, `not_relevant`, `clicked`). They are stored in `user_feedback` with the project the
item was judged for (`project_id`, kept only if the user owns that project, `ON DELETE SET NULL`), the
position it was shown at and its score. One current judgment is kept per user, bookmark and project: rating
again replaces it instead of adding a row (a unique index enforces it). Feedback does not change ranking today; it is stored so rankings can
be evaluated on real judgments.

`backend/scripts/export_feedback_eval.py` turns one user's judgments into a BEIR-format folder (queries per
judged project, the user's embedded bookmarks as the corpus, qrels from helpful/like/saved/completed against
not_relevant/dislike). It only reads the database. Labels exist only for items that were shown, so they favour
what the current engine already ranks high; a few dozen judgments per project can compare settings but not
support an absolute accuracy figure.

## Evaluating

Both scripts run against a throwaway local Postgres with pgvector and refuse other targets
(`core/destructive_guard.py`). Run them from `backend/`.

- `scripts/eval_retrieval.py` compares one vector per bookmark (`doc_vector`), best passage per bookmark
  (`chunk_vector`) and the same with the cross-encoder (`chunk_vector_rerank`) on a BEIR dataset through the
  production search code. Its outputs are committed in `backend/eval/results/`.
- `scripts/eval_recommendations.py` loads a BEIR dataset as one synthetic user's bookmarks and each query as a
  project, then scores `engine.recommend(project_id=...)` end to end: MMR lambda, intent augmentation,
  reranking, the same intent as a task, per-user isolation, and latency. It writes
  `recs_<dataset>_<model>_<timestamp>.json` and `.md` to `backend/eval/results/` by default. It also accepts
  the folder `export_feedback_eval.py` produces as `--data-dir`.

Committed results (BEIR SciFact test split, 300 queries, nDCG@10; "long" buries each relevant abstract among
8 unrelated ones):

| Embedding model | Corpus | One vector per bookmark | Passages | Passages + rerank |
|---|---|---|---|---|
| bge-small-en-v1.5 | original | 0.713 | 0.718 | 0.710 |
| bge-small-en-v1.5 | long | 0.016 | 0.504 | 0.508 |
| all-MiniLM-L6-v2 | original | 0.648 | 0.652 | not run |
| all-MiniLM-L6-v2 | long | 0.001 | 0.441 | not run |
| e5-small-v2 | original | 0.636 | 0.687 | not run |

The "long" corpus is synthetic: it is built to defeat truncation, so one vector per bookmark scoring near zero there
is expected, not a bug that was fixed. BM25 (`rank_bm25`, lowercase alphanumeric tokens over title and text, same
queries and metric code, run once outside the committed scripts) scores 0.652 on the original corpus (published:
0.665) and 0.5035 on the long one, which ties the 0.504 of bge-small passages. Passages are therefore not shown to
beat a lexical baseline on long documents; on the original corpus they add +0.005 over one vector per bookmark.

Files: `backend/eval/results/scifact_{orig,long8}_<model>_<timestamp>.json`. Reranking moved nDCG@10 by -0.008
(original) and +0.004 (long) at a p50 of about 715 ms per query against 8-15 ms without it on the machine that
ran the benchmark, which is why it is off by default.
