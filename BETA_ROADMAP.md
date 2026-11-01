# Beta roadmap

Ordered by value for the research and by dependency.

## P0: trust in the numbers

1. **Expose corrected flows** as a separate, labelled layer, next to raw flows.
2. **Overlay observations**: detector counts on the map and in road charts, with the published validation metrics. GPS only for shape, split by province and year, as in the manuscript.
3. **Full frozen regression**: regenerate every frozen day and compare it to the stored outputs in one command.
4. **Uncertainty on comparisons**: ensembles of seeds, once the partial seeding in `pawn.h` has been assessed. Differences smaller than seed spread should be flagged.

## P1: scenario capability

5. **Road closures.** Requires a decision and work in the engine: define the semantics (static or timed; rerouting of trips under way), then test conservation and unreachable destinations. The existing `polygon_closed` mode is area-based and untested here.
6. **Structured demand perturbations**: by demand class, province or time window. `scaled_sources` already supports class factors, but the per-class fit was rejected because volumes are not additive, so these need explicit caveats.
7. **Validation of scenario response** against real events (the 2020 lockdown is a candidate) before any predictive claim.

## P2: deployment and collaboration

8. **Docker Compose**, tested on a machine with Docker.
9. **Authentication and per-user access**, required before any non-localhost use given the proprietary-derived data. Add Django or an identity provider only if real requirements appear.
10. **Slurm back end** for the job runner, so that campaigns can run on the cluster.
11. **Results export** with provenance, and retention policies for run directories.

## P3: toward a digital twin

12. **Data assimilation** of live detector feeds; `platform/dashboard/crono` holds an earlier collector.
13. **PostGIS and vector tiles**, if the network grows well past the current 3,925 links.
14. **Forecast evaluation** with out-of-sample skill scores. The "digital twin" label should wait for this evidence.
