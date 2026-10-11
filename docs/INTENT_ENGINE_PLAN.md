# Intent × Content Engine — Redesign Plan

Fuze's job: you save content; Fuze understands **what each item is** and **what you're trying to do
right now** (a project, a task, a subtask, a question), and puts the right saved content in front of
you. Every decision below serves that, and nothing in the ranking path is a hardcoded keyword rule.

## 0. Status

| Phase | State |
|---|---|
| P0 bug fixes & cleanup | Done |
| P1 embedding model bake-off | Done: bge-small-en-v1.5 is the default; versioned embeddings + `scripts/reindex_content.py` |
| P2 content profiles | Done in code (Gemini JSON mode, strict validation, profile embedding); backfill on deploy |
| P3 intent | Done in code (context text + background intent statement/needs) |
| P4 engine | Done; legacy orchestrator, SmartEngine pipeline, shadow mode and keyword matchers deleted (~6,900 lines) |
| P5 search | Done: frontend endpoint and `/semantic` use passage search; keyword-blended RPC search removed |
| P6 numbers in README | Done |
| Schema | Done: migration 0012 (FK indexes, redundant indexes and dead columns dropped); models match migrations with zero autogenerate drift |

### Results (BEIR SciFact test split, 300 queries, production search code on Postgres + pgvector)

nDCG@10 (Recall@10 in brackets). "Long documents": each document buried at a random non-first
position among 8 unrelated abstracts, so the relevant text is past the model's input window.

| Model | Corpus | Today's search (1 vector / bookmark) | Passage search | Passage + reranker |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | original | 0.648 (0.788) | 0.652 (0.801) | – |
| all-MiniLM-L6-v2 | long documents | **0.001** (0.002) | **0.441** (0.582) | – |
| e5-small-v2 | original | 0.636 (0.769) | 0.687 (0.810) | – |
| **bge-small-en-v1.5** | original | 0.713 (0.831) | **0.718** (0.831) | 0.710 (0.834) |
| **bge-small-en-v1.5** | long documents | 0.016 (0.032) | **0.504** (0.611) | 0.508 (0.620) |

Decisions this drove:
- **Passage search** replaces one-vector-per-bookmark: the old approach is blind to anything past
  the first ~200 words (0.001 → 0.441–0.504 nDCG@10 on long documents) and is no worse on short ones.
- **bge-small-en-v1.5** replaces MiniLM: +10% nDCG@10 (0.652 → 0.718) and +14% on long documents
  (0.441 → 0.504) at the same 384 dimensions.
- **Reranker off**: the ms-marco MiniLM cross-encoder moved nDCG@10 by −0.008 / +0.004 while adding
  ~700 ms per query on CPU. It stays behind `SEARCH_RERANK_ENABLED` for future evaluation.
- Passage-search latency p50 9–15 ms, p95 22–31 ms (query embedding cached; local Postgres).

Raw outputs: `backend/eval/results/`. Reproduce: `backend/scripts/eval_retrieval.py --help`.

## 1. Where we were (verified against the code, Oct 2026)

| Area | Today | Problem |
|---|---|---|
| Content representation | One MiniLM embedding per bookmark | Model reads 256 tokens → only title + ~200 words count. Long articles are mostly invisible. |
| Content understanding | Gemini analysis → `content_analysis` | Never used for retrieval. On Gemini failure a keyword guess is saved as `SUCCESS` (`utils/gemini_utils.py:226`). |
| Intent | Gemini enum classification (goal/project_type/…) | Technologies always from regex; on cache miss the request uses `get_fallback_intent` keyword rules. |
| Task/subtask context | Frontend sends `task_id`/`subtask_id` | Handler drops them (`blueprints/recommendations.py`), task context ignored. |
| Ranking | ContextAwareEngine: 0.55 semantic + 0.45 rules | 25-word tech list (substring: "go" matches "google"), word-based content-type rules, TF-IDF on 2 docs, then ×(1+relevance×0.05) — up to ×6, query-independent (`orch:1583`). |
| Explanations | Templates per goal × content type | Not grounded in the content. |
| Search (`/supabase-semantic`) | Fetches ≤500 rows over Supabase HTTP, cosine in Python | No index use, silently ignores everything past 500 rows. |
| Overhead / bugs | Shadow mode default-on; pipeline built with no data layer | Second pipeline runs on every cache miss and always gets 0 candidates. Cache invalidation deletes keys that don't exist → new bookmarks hidden up to 30 min. |

## 2. Target architecture

```
            WRITE PATH (on save / edit)                         READ PATH (recommend / search)
 ┌───────────────────────────────────────────┐        ┌──────────────────────────────────────────────┐
 │ acquire page ─► passages (chunker)        │        │ Intent context                               │
 │      │                                    │        │  query │ project + task + subtask            │
 │      ├─► passage embeddings ──┐           │        │      │                                       │
 │      │                        ▼           │        │      ├─► intent_text  (composed, no parsing) │
 │      └─► Gemini content profile           │        │      └─► intent statement + needs (Gemini,   │
 │            summary · teaches/solves ·     │        │           precomputed & cached per context)  │
 │            key concepts · use_when ·      │        │                  │ embed (1–4 query vectors)  │
 │            type · level · technologies    │        │                  ▼                            │
 │                 │                         │        │  ANN over user's content_chunks               │
 │                 ▼                         │        │   (passages + profile), max-sim per bookmark  │
 │        profile embedding                  │        │                  ▼                            │
 │                 ▼                         │        │  cross-encoder rerank (intent, best passage)  │
 │   content_chunks (kind = passage|profile) │◄───────┤                  ▼                            │
 └───────────────────────────────────────────┘        │  MMR diversity ─► results + matched passage  │
                                                      └──────────────────────────────────────────────┘
```

### 2.1 Content side
- **Passages**: overlapping ~200-word chunks of the full text (`utils/chunking.py`), each embedded.
- **Content profile** (Gemini, one call per bookmark — replaces today's analysis call, not an extra one):
  `summary`, `teaches_or_solves[]`, `key_concepts[]`, `use_when` (situations this helps with),
  `content_type`, `level`, `technologies[]` — all LLM output with a JSON schema; stored with
  `model` + `prompt_version`. On failure: `analysis_status = FAILED`, retried with backoff. **No fake rows.**
- **Profile embedding**: `summary + use_when + key_concepts` embedded and stored as a `kind='profile'`
  row in `content_chunks`, so one ANN index covers both "what the text says" and "what it's for".
- **Versioned embeddings**: every chunk records its embedding model; a model change triggers a
  re-embed backfill and vectors from different models are never compared.

### 2.2 Intent side
- **intent_text** (instant, deterministic): the user's own words composed from the request —
  query, or project title/description/technologies + current task + current subtask. No parsing,
  no keyword classification. Always available, so there is never a rule-based fallback.
- **Intent statement + information needs** (Gemini, async): "Building X with Y; right now needs Z",
  plus 2–4 concrete needs. Precomputed when a project/task/subtask is created or edited, cached by
  context hash. When present it adds query vectors (multi-query retrieval); when absent the engine
  simply uses intent_text.

### 2.3 Ranking
1. **Retrieve**: for each query vector, ANN top-60 over the user's chunks (HNSW, pgvector 0.8 iterative
   scan for per-user filtering). Bookmark score = max similarity across its passages/profile; keep the
   best passage.
2. **Rerank** (flagged): cross-encoder scores (intent statement or query, best passage) for the top 30.
3. **Diversify**: MMR (λ≈0.7) over bookmark embeddings so the top 10 aren't near-duplicates.
4. **Score shown to users**: calibrated from the reranker/similarity — no multipliers, caps or tiers.
5. **Explanation**: the matched passage + the profile's `use_when`. Optional on-demand LLM line
   (existing `/generate-context`).
6. **Freshness**: results cached by (user, intent hash, content version); content version bumps on
   save/edit/delete, so new bookmarks show up immediately without fragile key deletion.

### 2.4 Search
`/api/search/supabase-semantic` (what the frontend calls) and `/semantic` run the same engine with
intent = the query. Same response shape. Users with no chunks yet fall back to document-level
pgvector search (not the 500-row HTTP scan).

## 3. What gets deleted
- All keyword/rule logic in ranking and intent: tech lists & synonym dicts
  (`universal_semantic_matcher.py`, `recommendation_config.py`, orchestrator), query keyword expansion,
  content-type/difficulty word rules, `get_fallback_intent`, regex technologies, Gemini keyword
  fallback analysis, hardcoded title/URL exclusion lists, TF-IDF "ML similarity".
- The ×6 relevance multiplier, penalty tiers, soft caps, threshold cascades, template reasons.
- FastSemanticEngine, ContextAwareEngine scoring internals, the empty RecommendationPipeline +
  shadow mode — replaced by one engine (`ml/intent_engine/`). Tests that pin old engine behaviour
  (golden regression, shadow tests) are replaced by eval-based regression tests.

## 4. Measuring it
| Eval | What it proves | Data |
|---|---|---|
| SciFact (BEIR) | Semantic search quality vs today's search | 5,183 docs, 300 labelled queries (already loaded locally) |
| Long-document SciFact | Whether full-text passages fix the 256-token blind spot | Each relevant abstract buried at a random position inside a long document of unrelated abstracts |
| Model bake-off | MiniLM vs bge-small vs e5-small (all 384-d: no schema change) | Same two evals |
| Intent → content | Recommendation quality for project/task contexts | Frozen set of project/task contexts × developer-content corpus, graded relevance |
| Latency | p50/p95 per stage on CPU | All of the above |

Metrics: nDCG@10, Recall@10/100, MRR@10, p50/p95 latency. Each phase ships only if it doesn't lose to
the previous best. Results are saved under `backend/eval/results/` and the headline numbers go in the README.

## 5. Phases

| # | Phase | Done when |
|---|---|---|
| P0 | Bug fixes & cleanup: pass task/subtask ids; versioned result cache; shadow mode off; remove lexical branch; no fake Gemini analysis | Full suite green |
| P1 | Embedding model bake-off + versioned embeddings + re-embed backfill | Best model chosen on SciFact + long-doc eval |
| P2 | Content profiles (new Gemini schema), profile embeddings, backfill | Profiles stored for all bookmarks; eval not worse |
| P3 | Intent: intent_text + async intent statement/needs, precomputed on project/task save | No rule-based intent anywhere |
| P4 | `ml/intent_engine/`: multi-query ANN → rerank → MMR → grounded explanations; orchestrator delegates to it; legacy scoring removed | Beats baseline on evals; p95 within budget |
| P5 | Search endpoints on the same engine | Frontend search unchanged in shape, better in results |
| P6 | Eval suite + CI regression test + README numbers | Numbers published |

Latency budget on the 2-vCPU host: p95 ≤ 600 ms without rerank, ≤ 1.2 s with rerank (measured,
not assumed; rerank stays off if it doesn't earn its cost).

## 6. Risks
- **Gemini quota/cost**: one call per bookmark (same as today) plus one per project/task edit; all async, cached, retried.
- **Reranker latency on CPU**: flag-gated, top-N tuned by measurement.
- **Supabase free tier**: chunks ≈ 1.5 KB each; 10k bookmarks × 10 chunks ≈ 150 MB — fine; monitored.
- **Model swap**: re-embedding is a backfill job; reads fall back to document-level search until done.

## 7. Later (enabled by this engine)
- **Ask your bookmarks**: grounded answers with citations, built on the same passage retrieval.
- **Learning from feedback**: helpful / not-relevant signals tune ranking per user (learned, not hand-set).
- **Interest memory**: a rolling vector of what the user has been saving and opening.
