# Architecture decision records

| ADR | Title | Status | Decision |
|---|---|---|---|
| [007](ADR-007-intent-engine.md) | Intent x content recommendation engine | Accepted | Recommend by retrieving passages and content profiles that match the user's own context, with an optional cross-encoder rerank and MMR, instead of rule-based scoring over one vector per bookmark. |

## Removed records

ADR-001 to ADR-006 described the earlier recommendation stack (a domain model for scoring, a pipeline and
strategy architecture, shadow-mode rollout, pure scoring functions, engine contracts, and rollout gates for
two-stage retrieval). That stack was removed in commit `4446a9a`, and none of the modules they name exist, so
the records were deleted rather than left describing code that is gone. They remain in git history, for
example `git show 4446a9a^:docs/adr/ADR-006-two-stage-retrieval-rollout-gates.md`.
