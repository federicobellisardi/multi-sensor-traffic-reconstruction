# Digital twin (second paper)

Work towards a regional mobility digital twin. The name states the goal: the current platform is a simulator with a
dashboard, without data assimilation or predictive validation.

| Path | Content |
|---|---|
| `platform/` | Web platform: API, job runner, map dashboard. Start with `platform/docs/README_ALPHA.md` |
| `analysis/` | Experiments of the paper (to be created) |
| `results/` | Aggregate results; link-level outputs derived from proprietary data stay in `results/private/` (git-ignored) |
| `manuscript/` | Manuscript (to be created) |

The frozen baseline is imported from `model/analysis`, never copied, so that the check against the stored outputs of the
first paper stays meaningful. `minimocas/` is shared: a change there must be checked by regenerating that baseline, and
must stay off by default if it alters the outputs.
