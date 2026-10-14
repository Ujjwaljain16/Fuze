# FUZE v2: from "saved" to "understood, connected and used"

Status: **proposal, no code yet.** This branch (`v2`) starts at the `v1.0.0` tag. The idea comes from one
scenario: a user shares an Instagram Reel from their phone. v1 saves the link. v2 should make that save useful
weeks later: findable, understood, connected to their projects, and optionally turned into an action.

Reels are the first case, not the whole feature. Everything below is written for any short social item
(Reel, YouTube Short, TikTok, a LinkedIn post), because the pipeline is the same and only the *evidence providers*
differ.

## 1. The one rule

**Capture must succeed even if every later step fails.** A shared Reel is saved immediately with its URL, the
time, the source and any note, and stays findable by those alone. Understanding is a second, separate outcome
("ready" arrives later), and a failed stage is retried on its own without redoing the others.

## 2. What FUZE already has, and what is missing

v2 builds on these. It does not add a second content system, a new vector database or a new recommender.

| Need | Already in v1 | Gap for v2 |
|---|---|---|
| Share from the phone | PWA share target opens `/share`, which keeps title, text and link through sign-in | iOS cannot be a share target (see 8) |
| Save without waiting | `quick-save` persists the bookmark first and queues a job (`BookmarkCreated` event, RQ) | none |
| Deduplicate | exact URL and a normalized URL (tracking parameters dropped) | Instagram shares carry a new `?igsh=` token every time, and one Reel has several spellings (`/reel/`, `/reels/`, `/p/`, another host), so re-sharing makes duplicates |
| Stage status and retry | `bookmark_events` per stage with sequence numbers, a reconciler that retries stuck stages with backoff, live status over SSE | stages for evidence and enrichment |
| Evidence handling | per-field provenance when a page is fetched (`scrapers/normalizer`), extension capture, share-sheet text kept as notes | evidence is not stored as its own typed records; interpretation and evidence share one text column |
| Understanding | one LLM call produces a validated content profile (summary, concepts, `use_when`) stored in `content_analysis` | the schema is generic; no per-content-type extraction |
| Retrieval | passage chunks plus profile rows in pgvector, MMR, cross-encoder weak-match check, `Ask` with citations | transcript/OCR chunks do not exist yet |
| Connections | intent engine matches saves to a project, task, subtask or query | nothing runs at save time ("this relates to your Docker project") |
| Feedback | thumbs up/down stored per project (`user_feedback`) | no intent or action feedback |

## 3. What Instagram actually allows (decide before building)

A Reel URL is not the Reel's contents, and for Instagram the server cannot read it:

- `instagram.com/robots.txt` disallows automated access and Reels sit behind a login wall. Fuze honours robots.txt;
  the LinkedIn adapter is a deliberate one-off exception and **should not be extended to Instagram** (Instagram
  blocks and bans aggressively, and the item is rarely public anyway).
- Meta's official oEmbed needs a registered app and an access token, returns little (author, thumbnail, embed
  markup), and the caption is not guaranteed. It is a possible Level A source, not a given.
- No transcript or on-screen text is available from the link itself.

So, honestly, most Reels arrive at **Level D** (below) from the server's point of view. The evidence has to come
from the user's side, which is what FUZE already does well:

| Evidence source | Works for | Notes |
|---|---|---|
| The user's note and the share sheet's title/text | every share | already stored as notes |
| Extension capture (rendered page, signed in) | desktop | caption, creator, hashtags visible in the page; no audio |
| Paste (caption, or a transcript the user already has) | any device | one extra step, always permitted |
| User-supplied media (a video file shared into the PWA) | Android, if Instagram offers the file | enables transcription and frame OCR on **the user's own file**; needs a budget decision |
| Official APIs (YouTube oEmbed, Meta oEmbed with a token) | per site | keyed, rate limited, metadata mostly |

### The evidence ladder

Each item records the highest level it actually reached, and the UI says so ("saved with the link only").

- **A. Metadata and caption**: identifiable, caption readable. Summary of the available text only.
- **B. Transcript**: spoken words indexed, with timestamps where known.
- **C. Visual text**: on-screen code, ingredients, product names, places.
- **D. Inaccessible**: URL, note, any share-sheet text, and the reason. Offer "paste the caption or a transcript".

Never promise that every shared Reel can be read, and never use scraping tricks or session-cookie automation to
reach a higher level.

## 4. The pipeline

```
share -> validate and canonicalize URL -> deduplicate -> persist (user, time, source, note) -> "Saved"   [synchronous]
      -> enqueue ->  1 evidence      collect what is permitted and available, record level and provenance
                     2 understand    classify the content type, extract with that type's schema, validate
                     3 index         chunks (caption, transcript, OCR, summary), embeddings, lexical index
                     4 connect       related saves, matching projects and goals, from the existing retrieval
                     5 suggest       optional next step, user-correctable intent
      -> "Ready" event (or "partial: needs attention")                                                      [asynchronous]
```

- Each stage is its own RQ job with its own attempt counter, so a failed OCR does not repeat the caption stage
  and the reconciler retries only what failed (this machinery exists today).
- A deterministic pipeline with typed outputs and few model calls. No tool-calling agent per item.
- At most **one** LLM call for understanding per item (it also returns intent and suggestions), cached by content
  hash. v1 already runs on small LLM quotas, so a per-user daily budget is part of the design, not an afterthought.

## 5. The knowledge record: evidence kept apart from interpretation

Two ideas, stored separately so a user can correct the AI without losing what was actually observed:

1. **Evidence** (new table, `content_evidence`): one row per piece, with `kind` (caption, transcript, ocr, note,
   metadata), `text`, `origin` (share_sheet, extension, paste, oembed, user_media), `provenance` (observed,
   extracted, inferred, user) and an optional timestamp range. Never overwritten by interpretation.
2. **Interpretation** (extends `content_analysis`): summary, topics, entities, takeaways, content type, the
   type-specific fields, `limitations`, and `evidence_level`. Every claim points at the evidence rows it came from.

A creator saying "₹500" is stored as a claim from the source with its location, not as a market price.
Model self-reported confidence is not treated as a calibrated probability.

### Type-specific extraction

First classify, then use that type's schema (validated, never free-form JSON inserted blindly):

| Type | Fields |
|---|---|
| Coding tutorial | language, framework, prerequisites, commands, steps, code references |
| Explainer | main claims, concepts, definitions, support |
| Recipe | ingredients, quantities, steps, time |
| Travel | place, location, budget if stated, source |
| Product | product, claimed benefits and drawbacks, price if stated, unverified claims |
| Idea | problem, audience, solution, assumptions to test |
| Workout | exercise, sets/reps if stated, equipment, technique |
| Entertainment | short description, topics, tags |

The summary is short and decision-oriented: what it is, key takeaways (only if supported), why it may matter, how
to use it, limitations, source and timestamps. A short item gets a one-line summary, not padded bullets.

## 6. Intent and action

People save for different reasons: learn, try, buy, visit, build, share, reference, "don't know yet". The system
infers a likely intent, shows it, and the user corrects it with one tap. Nothing becomes a task silently.

- New: a per-item `intent` (inferred value, confirmed value, who set it) and optional `next_step`.
- Feedback worth more than better summaries: opened again, followed the steps, added to a project, dismissed,
  task completed. These feed ranking and resurfacing (the `user_feedback` pattern already exists).
- "Resurfacing": surface a saved item when a project or task it matches becomes active (the intent engine already
  does the matching; v2 triggers it from the item's side).

## 7. Phases

| Phase | What | Done when |
|---|---|---|
| **P0 Capture** | Canonical Instagram/short-video URLs (drop `igsh`, collapse `/reel/`, `/reels/`, `/p/`, hosts); one record per media; `source` recorded; visible status; failed enrichment never loses the item | Re-sharing the same Reel any way gives one record and one job; an item whose every later step fails is still saved and searchable by URL and note |
| **P1 Evidence** | `content_evidence`; providers for share-sheet text, extension capture and paste; evidence level on every item; "paste a caption/transcript" in the UI; optional oEmbed provider | Each item shows its level; an item with no readable content says so and offers the paste route |
| **P2 Understanding and search** | Content-type classification and per-type schemas; provenance on claims; chunks from evidence; hybrid (lexical plus vector) retrieval over evidence and summaries | A natural-language query finds the right item from its caption, transcript or note; claims cite evidence |
| **P3 Connections and intent** | Related saves and project matches at save time; user-correctable intent; optional next step; resurfacing | Suggestions are accepted more often than dismissed on the eval set |
| **P4 Hardening** | Per-user isolation tests, URL-fetch protections, idempotent jobs, deletion propagation to evidence and chunks, output validation, rate limits, cost per item | A cost and latency budget is written down and measured |

Build in that order. P0 and P1 deliver most of the user-visible value.

## 8. Mobile reach

- **Android**: the installed PWA is a share target (fixed in v1).
- **iPhone**: iOS does not support the Web Share Target. A workable alternative is an iOS Shortcut ("Share Sheet
  -> Get contents of URL -> POST to the quick-save endpoint with the user's token"), which needs a documented,
  scoped API token. This is a design item for P0, not code yet.
- **Desktop**: the extension.

## 9. How we will know it is good (before tuning prompts)

Build a small labelled set first: coding tutorials, recipes, travel items, inaccessible Reels, caption-only items,
duplicate shares, and items where speech contradicts on-screen text. FUZE already has an evaluation harness
(`backend/eval`: BEIR-style retrieval and recommendation runs) to extend.

| Metric | Success |
|---|---|
| Capture reliability | a confirmed save survives any downstream failure (tested by forcing each stage to fail) |
| Extraction quality | structured fields match the source evidence |
| Retrieval | Recall@10 and nDCG@10 on the labelled query set |
| Grounding | claims supported by evidence; unsupported claims and omissions counted |
| Duplicates | repeated shares create no extra records or jobs |
| Action relevance | accepted vs dismissed vs completed, tracked separately |
| Cost | LLM and compute cost per processed item, per user per day |

## 10. Deliberately not doing

- Downloading every Reel because a URL was shared; any scraping or cookie automation for Instagram.
- An LLM call per stage; an agent with tools per item.
- Treating every save as a task.
- Keeping only a summary and an embedding and discarding the evidence.
- Reprocessing everything when one stage fails.
- Assuming a transcript, media or caption exists.
- A new vector store or recommender before the current one is shown to be insufficient.

## 11. Decisions needed from the owner

1. **Instagram access policy.** Permitted sources only (note, share text, extension, paste, optional oEmbed), as
   proposed, or also a LinkedIn-style exception. Recommendation: permitted sources only.
2. **Scope.** Reels only, or the generic "short social item" pipeline (Reels first). Recommendation: generic.
3. **Media and transcription.** Accept only text the user gives, or also transcribe media the user shares from their
   own device (needs a model choice and a per-user budget). Recommendation: text first, media later.
4. **LLM budget.** Provider, model and the daily per-user cap for the one understanding call per item.
5. **iPhone route.** Build the Shortcut-based path (needs scoped API tokens), or Android and desktop only for now.
6. **Naming and release.** Keep this as `v2` on its own branch with a CHANGELOG section per phase, merged phase by
   phase, or one long-lived branch. Recommendation: merge each phase to `main` when its acceptance test passes.
