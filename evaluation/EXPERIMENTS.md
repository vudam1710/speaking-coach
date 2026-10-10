# Experiments

One change per round. Every round: same answer set → item-by-item teacher review (✓ / ~ / ✗ + problem label) → `evaluation/score.py`.

## v1 — baseline (2026-10-10)
- Prompts: `coach_v1` (expression feedback) + `upgrade_v1` (+1 level, 3–4 changes, learner's structure kept).
- Code checks: every Vietnamese chunk gets a lesson · quotes exist in the answer · no Vietnamese left in suggestions · "advanced" phrase does not leak into the simple ways · upgraded answer assembled by code from the chosen changes.
- Set: 4 synthetic answers (`data/samples`). Teacher read-through: "close to how I teach". 0 code warnings. ~$0.03 per answer (step 1).
- Not yet item-coded → first coded round = pilot answers (`pull_sheet.py`).

| Group | ✓ | ~ | ✗ | ✓ % |
|---|---|---|---|---|
| _to fill after first review_ | | | | |
