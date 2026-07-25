# ADR-003: Shadow Execution & Dual-Runner Rollout Strategy

## Status
Accepted

## Context
Refactoring the core recommendation orchestrator carries the risk of recommendation quality regressions or subtle rank flips impacting end-user experience.

## Decision
1. **Shadow Mode Execution**:
   - Production traffic executes both legacy orchestrator (returns response to user) and new `RecommendationPipeline` in shadow mode.
2. **Quality Evaluation Metrics**:
   - Overlap Ratio: $\text{Overlap@1} \ge 0.85$, $\text{Overlap@10} \ge 0.90$.
   - MRR Delta: $|\Delta \text{MRR}| \le 0.02$.
   - NDCG Delta: $|\Delta \text{NDCG@10}| \le 0.02$.
   - Latency Delta: $\text{Latency}_{\text{new}} \le \text{Latency}_{\text{legacy}}$.
3. **Traffic Cutover Gate**:
   - 1,000 shadow executions with zero quality regressions and 100% test pass rate required before flipping production feature flag.

## Consequences
- Guaranteed zero-downtime cutover with empirical quality proof before users see new pipeline output.
