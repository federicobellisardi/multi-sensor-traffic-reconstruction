# Literature and positioning — Article 1

Checked 2026-10-27. This is a focused review supporting the present draft, not a
systematic review. Search coverage is incomplete and should be extended before
submission. Every DOI below has a saved authoritative Crossref response in
`reference_metadata.json`; BibTeX is generated from those records. Publisher or
author-hosted abstracts/text were consulted for the comparisons below. A DOI
metadata check verifies bibliographic identity, not every substantive claim.

## Closest work and implications

| Work | Verified source | Relevance and limit of our contribution |
|---|---|---|
| Toole et al. (2015), *The path most traveled* | https://doi.org/10.1016/j.trc.2015.04.022 ; author PDF https://humnetlab.berkeley.edu/wp-content/uploads/2020/02/ThePath_TRC.pdf | Already joins mobile demand, networks, assignment and visualization. Integration alone is not new. |
| Çolak, Lima & González (2016), *Understanding congested travel in urban areas* | https://www.nature.com/articles/ncomms10793 | Couples phone-derived demand and network assignment across cities. Our single-region assessment does not supersede its assignment results. |
| Cascetta (1984), generalized least-squares trip-matrix estimation | https://doi.org/10.1016/0191-2615(84)90012-2 | Counter-constrained demand inference predates this workflow. Our local post-processing does not estimate an optimal OD matrix. |
| Herrera et al. (2010), Mobile Century | https://www.sciencedirect.com/science/article/pii/S0968090X09001430 | Field evaluation of vehicle probes; sampling and fleet coverage matter. We lack an independent penetration estimate. |
| Work et al. (2010), velocity assimilation | https://doi.org/10.1093/amrx/abq002 | A physical assimilation framework already exists. Our residual propagation is heuristic and is not its equivalent. |
| Seo et al. (2017), traffic-state-estimation survey | https://www.sciencedirect.com/science/article/pii/S1367578817300226 | Positions observation, modelling and estimation choices. We evaluate hourly link profiles, not full density/speed state recovery. |
| Castillo et al. (2015), observability and sensor locations | https://doi.org/10.1155/2015/903563 | Sparse detector placement limits flow identification. Our random sensor pilot is not a proof of observability or optimal placement. |
| Lin et al. (2024), Tel2Veh | https://doi.org/10.1145/3589335.3651442 ; institutional record https://scholars.lib.ntu.edu.tw/entities/publication/9595d0ee-c672-4906-9aab-59a2809f476c | Telecom and vehicle-count fusion for camera-free prediction exists. Our independent GPS layer and simulator assessment are different experimental choices, not proof of greater accuracy. |
| Lei, Xu & Wang (2024), conditional diffusion | https://doi.org/10.1016/j.trc.2024.104798 | Probabilistic sensor-free estimation is an established comparator category. No uncertainty or performance superiority is claimed here. |
| Maiti, Seppecher & Leclercq (2025), sparse stationary sensor scaling | https://doi.org/10.1016/j.trc.2025.105213 | Addresses sparse coverage with hierarchical scaling and network inference. Their macroscopic target differs from our hourly link shares. No common-data benchmark exists. |

Supporting method identities also verified: Boeing (2017), OSMnx;
Dijkstra (1959); Horni et al. (2016), MATSim; Lopez et al. (2018), SUMO;
Treiber & Kesting (2013), *Traffic Flow Dynamics*; Ward (1963) and
Murtagh & Legendre (2014). Citing established simulators does not establish that
`minimocas` implements their congestion, behavioural or calibration capabilities.

## Defensible gap and claims

The potentially useful contribution is an independently auditable regional case
study showing which observations constrain which output quantities. It includes
all-link profile assessment, temporal baselines, withheld-counter diagnostics,
day-type analysis and implementation failure modes. Its originality and journal
fit remain conditional on a stronger corrected experiment.

Do not claim first heterogeneous fusion, validated regional volumes, a conserved
post-correction field, unbiased fleet penetration, universal temporal behaviour,
probabilistic uncertainty coverage, or superiority over contemporary methods.
Adjacent links share trajectories, and detector clusters are spatially dependent.

## Bibliographic correction found

The inherited `herrera2010` entry had DOI `10.1016/j.trb.2009.10.005`.
Crossref confirms the Mobile Century article at **10.1016/j.trc.2009.10.006**.
The correction is restricted to `article1/references.bib`; the original file is
preserved. Titles, authors and publication fields for the selected 17 DOI-bearing
references are generated from Crossref rather than copied from the old draft.

## Further review needed

Extend to joint OD/flow inference, boundary-demand treatment, fleet selection
bias, counter placement with geographic holdouts, trajectory dependence and
uncertainty calibration. Read the full recent method papers before making
detailed algorithmic comparisons. Do not cite search snippets as evidence for
unread performance tables. A 2026 article with a November issue date appeared
in search; it was not used because its publication status at the current date
was not independently resolved.

## Extension, 2026-10-27

38 further references added (Crossref-verified, see `verify_references.py`), covering
mobile-phone OD estimation, phone-demand assignment, count-based OD/agent calibration,
probe sampling, multi-sensor fusion, sensor location, demand uncertainty, simulation
validation, historical-profile baselines, OSM completeness, COVID-19 mobility change and
prior Bologna-group mobility studies. Closest additional comparators for novelty:
Wang et al. 2012 (phone OD → road usage, Sci. Rep.), Flötteröd et al. 2011 (Bayesian
calibration of agent-based demand to counts; our post-hoc correction does not
recalibrate demand), Nantes et al. 2016 (heterogeneous-data state estimation in corridors;
real-time speed/density, not regional hourly link volumes). These were checked at
abstract level only.
