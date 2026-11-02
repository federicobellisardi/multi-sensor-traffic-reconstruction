# Digital twin (second paper)

Work towards a regional mobility digital twin. The name states the goal: the current platform is a simulator with a
dashboard, without data assimilation or predictive validation.

| Path | Content |
|---|---|
| `platform/` | Web platform: API, job runner, map dashboard. Start with `platform/docs/README_ALPHA.md` |
| `analysis/` | Experiments of the paper (to be created) |
| `results/` | Aggregate results; link-level outputs derived from proprietary data stay in `results/private/` (git-ignored) |
| `manuscript/` | Manuscript (to be created) |

## Start the web service

From the repository root. The first command is needed once, and on a machine where the environment already exists it can be skipped:

```sh
bash digital_twin/platform/scripts/setup.sh   # Python and Node environments, frontend build
bash digital_twin/platform/scripts/run.sh     # stop with Ctrl-C
```

Open <http://127.0.0.1:8765>; the API documentation is at `/docs`. Change the port with `ALPHA_PORT=8799 bash digital_twin/platform/scripts/run.sh`.

The simulator must already be built: if setup reports it missing, follow `platform/docs/README_ALPHA.md`, which also covers a machine without private data. First run: **Scenarios → Demo baseline (SYNTHETIC) → Launch**, then **View on map** when it completes.

The server has no authentication and research runs contain data derived from proprietary sources, so keep it on `127.0.0.1`. From another machine use a tunnel: `ssh -L 8765:127.0.0.1:8765 <host>`.

## Baseline

The frozen baseline is imported from `model/analysis`, never copied, so that the check against the stored outputs of the
first paper stays meaningful. `minimocas/` is shared: a change there must be checked by regenerating that baseline, and
must stay off by default if it alters the outputs.
