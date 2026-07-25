# ADR-006 — Two-Stage Retrieval Rollout Gates

**Status:** Accepted  
**Deciders:** Engineering team  
**Context:** ITEM 2 in the infrastructure roadmap changes the recommendation candidate retrieval
architecture from a flat ORM fetch (`data_layer.py → get_user_bookmarks(limit=N)`) to a
two-stage ANN → rerank pipeline (`retrieval.py → ANN top-100 → scorer top-20`). This ADR
defines the objective, automated gates that must pass before the `RECOMMENDATIONS_TWO_STAGE`
feature flag is advanced at any rollout percentage.

---

## Decision

Rollout of two-stage retrieval is **automated and gate-driven**.

- No human may approve a stage transition that fails a gate.
- No human may override a gate failure.
- Gates are evaluated by two independent mechanisms:
  - **Static Gate** — evaluated by CI against the frozen golden baseline artifact.
  - **Dynamic Gate** — evaluated by `ShadowEvaluator` against live production traffic.

Both must pass independently. One cannot substitute for the other.

---

## Gate 0 — Embedding Null Rate (Pre-condition)

Must be satisfied **before shadow evaluation begins**. If not satisfied, do not start the
shadow run and do not enable the flag at any percentage.

```
SELECT COUNT(*) FROM saved_content WHERE embedding IS NULL = 0
```

Measured by: running `scripts/backfill_embeddings.py --verify` after backfill completes.

**Block condition:** Any NULL embedding rows remain → re-run backfill → re-verify.

---

## Gate 1 — Static Quality Gate (CI)

**Source:** `backend/tests/golden/golden_baseline_v1.json`

This file is the **frozen baseline artifact** generated once from the validated legacy
orchestrator (`ml/unified_recommendation_orchestrator.py`) at the point of architectural
freeze. It is committed to version control and never regenerated from live traffic.

**Purpose:** Deterministic regression testing in CI. Answers the question:
> Does the new two-stage pipeline produce equivalent quality to the legacy orchestrator
> on a known, reproducible benchmark?

**Thresholds (evaluated against `golden_baseline_v1.json`):**

```
MRR Delta   >= -0.03   (new pipeline MRR must be within 3 points of baseline MRR)
NDCG@10 Delta >= -0.03  (new pipeline NDCG@10 must be within 3 points of baseline NDCG@10)
```

Example: if `golden_baseline_v1.json` records `legacy_mrr: 0.91`, new pipeline must score
`>= 0.88`. If baseline records `legacy_ndcg10: 0.96`, new pipeline must score `>= 0.93`.

**Test file:** `backend/tests/test_two_stage_baseline_regression.py`  
**Run in CI:** Every PR that touches `retrieval.py`, `data_layer.py`, `pipeline.py`, `scorer.py`.

**Block condition:** Either delta exceeds -0.03 → CI fails → no merge → no deployment.

---

## Gate 2 — Dynamic Quality Gate (Shadow Run)

**Source:** Live production traffic via `ShadowEvaluator.evaluate_shadow_run()`

**Purpose:** Real-world validation. Answers the question:
> On actual user queries with actual user bookmark data, does the new pipeline produce
> recommendations that agree with the legacy orchestrator?

This is a different validation from Gate 1. The golden dataset uses synthetic benchmark
queries against a fixed candidate pool. The shadow run uses real queries against real data.
Both are necessary.

### Minimum Sample Size

Shadow run must satisfy **both** conditions before Gate 2 results are evaluated:

```
Minimum recommendation requests:  10,000
Minimum wall-clock duration:       48 hours
```

Whichever takes longer — both must be met simultaneously. Not 200 requests. Not a
few manual tests.

### Overlap Thresholds

```
Overlap@1  >= 0.90
Overlap@3  >= 0.85
Overlap@10 >= 0.80
```

**Rationale:** The retrieval architecture is changing; recommendation philosophy is not.
A top-1 agreement rate below 90% means users are seeing a fundamentally different first
recommendation than the validated legacy system produces. This is a correctness failure,
not a quality improvement.

**Measured by:**
- `ShadowEvaluator.compute_overlap_at_k(legacy_ids, new_ids, k=1)`
- `ShadowEvaluator.compute_overlap_at_k(legacy_ids, new_ids, k=3)`
- `ShadowEvaluator.compute_overlap_at_k(legacy_ids, new_ids, k=10)`

---

## Gate 3 — Latency Gate

Latency baseline is captured from the **legacy orchestrator path** during the same shadow
run window. Both paths are instrumented via `core/metrics.py`
(`recommendation_latency_seconds` histogram).

```
P50 <= legacy_p50 + 20ms
P95 <= legacy_p95 + 50ms
P99 <= legacy_p99 + 100ms
```

**Rationale:** Two-stage retrieval adds a second DB round-trip (ANN fetch) plus Python
rerank over 100 candidates. This must not produce a latency regression beyond the stated
bounds. The ANN fetch via HNSW should be fast enough that total latency stays bounded.

**Measured by:** `recommendation_latency_seconds` Prometheus histogram, labels:
`engine=two_stage` vs `engine=legacy`. Grafana dashboard panels evaluate p50/p95/p99
over the shadow window.

**Prerequisite:** ITEM 8A (Prometheus `/metrics` endpoint) must be deployed and the
Grafana datasource must be connected **before** the shadow run begins. Latency gate
cannot be evaluated without metrics infrastructure.

---

## Rollout Stages

All gates (0, 1, 2, 3) must pass before the `0% → 5%` transition.

Each subsequent stage requires:
- Minimum **24-hour hold** at the current percentage
- Continuous gate monitoring (Gates 2 and 3) during the hold period
- Any gate violation during a hold period triggers **automatic rollback** to the previous percentage

```
0%  →  5%  →  25%  →  50%  →  100%
         ↑        ↑        ↑        ↑
       24h      24h      24h      24h
```

---

## Rollback Criteria

Any of the following at any rollout stage triggers immediate kill switch:

| Condition | Gate |
|---|---|
| Overlap@1 drops below 0.90 | Gate 2 |
| Overlap@3 drops below 0.85 | Gate 2 |
| Overlap@10 drops below 0.80 | Gate 2 |
| P99 exceeds `legacy_p99 + 100ms` for 10 consecutive minutes | Gate 3 |
| `embedding NULL rate > 1%` detected post-backfill | Gate 0 |
| CI Gate 1 regression detected on any merged change | Gate 1 |

**Rollback mechanism:** `FeatureFlagService.kill_switch('two_stage_retrieval')`  
Takes effect within the in-process cache TTL (5 seconds). No redeploy required.

---

## Baseline Artifact — `golden_baseline_v1.json`

### What it contains

```json
{
  "version": "1",
  "generated_at": "<ISO timestamp>",
  "generated_from": "unified_recommendation_orchestrator.py",
  "queries": [
    {
      "query": "<benchmark query title>",
      "user_id": "<anonymised or synthetic>",
      "legacy_top10": [<candidate_id>, ...],
      "legacy_mrr": 0.91,
      "legacy_ndcg10": 0.96
    }
  ],
  "aggregate": {
    "avg_mrr": 0.91,
    "avg_ndcg10": 0.95
  }
}
```

### How it is generated

Run `backend/scripts/generate_golden_baseline.py` once against the validated legacy
orchestrator before any two-stage code is merged. The output is committed to
`backend/tests/golden/golden_baseline_v1.json`.

**This file is never regenerated from live traffic.** It is the permanent regression target.

If the legacy orchestrator is intentionally improved (e.g., new scoring weights validated
via a separate A/B test), a new versioned baseline (`golden_baseline_v2.json`) is created
with a corresponding ADR amendment, and the old baseline is archived, not deleted.

### What it does NOT contain

- User PII (only anonymised or synthetic user IDs)
- Raw document content
- Timestamps that would make it non-reproducible

---

## Two-Track Validation Summary

| Track | Source | Purpose | When evaluated |
|---|---|---|---|
| **Static Gate (CI)** | `golden_baseline_v1.json` | Deterministic regression — known benchmark | Every PR, mandatory before merge |
| **Dynamic Gate (Shadow)** | Live production traffic | Real-world validation — real queries, real data | 48h / 10K requests before flag advance |

These are different validations. The static gate catches regressions in CI before they reach
production. The dynamic gate validates real-world behaviour before traffic is shifted.

---

## Consequences

**Positive:**
- Rollout decisions are objective, reproducible, and documented
- `ShadowEvaluator`, `FeatureFlagService`, and `Prometheus` are used as designed
- The golden baseline is a permanent, version-controlled regression target
- No subjective override path — eliminates "Overlap@10 is 0.63 but looks okay to me"

**Negative:**
- A genuinely improved pipeline that intentionally shifts ranking philosophy (not a bug)
  may fail Overlap gates — this is an acceptable tradeoff given the existing system is
  validated and the purpose of this change is architecture, not ranking philosophy
- Static gate requires maintaining `golden_baseline_v1.json` as candidate IDs change —
  the baseline uses anonymised IDs and must be refreshed when the underlying golden
  dataset (`golden_recommendations.json`) is versioned up

---

## Related ADRs

- ADR-002 — Anti-God Pipeline Rules (established pipeline/engine/scorer separation)
- ADR-003 — Shadow Evaluator framework
- ADR-005 — Feature Flag platform (kill switch mechanism)
