# Article 1 — journal fit and readiness

Assessment: 2026-10-27. The manuscript is a **working research draft, not ready
for submission**. Journal recommendations are provisional judgments, not
predictions of acceptance. No manuscript or data have been submitted or uploaded.

## Journal options

| Role | Journal | Assessment |
|---|---|---|
| Preferred after essential experiments | Scientific Reports | Broad engineering scope accommodates an empirical regional assessment. Needs corrected independent count evaluation, reproducibility and a substantive finding beyond diagnosing code defects. |
| Realistic applied alternative to assess | European Transport Research Review | European traffic/demand and ITS audience; the transport-system implication must be clear. A regional methodological assessment could fit, but it still needs complete validation. |
| More ambitious conditional alternative | Transportation Research Part C | Appropriate subject matter for estimation and emerging sensing, but methodological and comparative evidence are currently too weak. Needs a credible corrected method, competitive baselines and geographic holdouts. |

Scientific Reports official [scope](https://www.nature.com/srep/about/aims) and
[submission guidance](https://www.nature.com/srep/author-instructions/submission-guidelines)
were checked. Its guidance recommends a concise main text, an abstract of no
more than 200 words, and limited display items. The current Springer-derived
draft has six main figures and one main table. Final journal formatting has not
yet been enforced. Its [data policies](https://www.nature.com/srep/journal-policies/editorial-policies)
require explicit restrictions and arrangements for evaluating and replicating
results based on third-party data; a vague promise of access is insufficient.

ETRR's official [scope](https://link.springer.com/journal/12544/aims-and-scope)
includes traffic management, ITS and transport-system implications. Its current
article-type instructions, access costs and data/code policies require a further
check before a target is finalized. Do not infer them from another Springer journal.

The official [TRC page](https://www.sciencedirect.com/journal/transportation-research-part-c-emerging-technologies)
and aims page returned HTTP 403 in this session. Its current detailed submission
and publication policies are therefore **not verified** here. The ambitious
ranking is a scientific judgment based on the closest published method papers,
not a verified journal-policy comparison.

EPJ Data Science was also considered. Its official
[scope and guidelines](https://link.springer.com/journal/13688/submission-guidelines)
expect new insights into human/social systems and caution against descriptive
applications of standard techniques. Merely integrating familiar inputs in a
region is a weak fit. Retaining its visual template does not establish scientific
fit. A stronger finding about observation bias or network identifiability would
be needed to make it a persuasive choice.

## Separation from Articles 2 and 3

Article 1 owns the reconstruction methods, independent GPS profile assessment,
counter holdouts, coverage/demand sensitivity and associated uncertainty.
Article 2 owns accident/exposure models and safety conclusions. Article 3 owns
software architecture, operational workflows, deployment and performance.
Shared input descriptions should be brief and cross-referenced once those
manuscripts exist. No fictitious publication status or invented cross-citation
has been introduced. Historical source figures and results must not be presented
as independent discoveries in multiple manuscripts.

## Essential work before submission

1. Recover the historical simulator environment or explain the numerical replay
   discrepancy; establish a common environment for all candidate reruns.
2. Preserve directed output support, correct clock handling and evaluate a
   documented correction algorithm with complete held-out observations.
3. Extend the one-day random-sensor pilot across campaign dates; include
   geographic/sensor-group holdouts and an uncertainty design acknowledging
   spatial dependence. Do not select depth using test errors and report it as
   independent validation.
4. Confirm OD hour labels and evaluate all-24-hour demand, demand scaling and
   realistic endpoint assumptions. A fixed RNG is not stochastic uncertainty.
5. Regenerate inherited figures from identified scripts, verify map attribution,
   and remove author/provenance TODOs after confirmation.
6. Agree legitimate reviewer/replication access for TIM and Viasat, establish
   simulator licensing, and archive a distributable analysis subset.

## Referee-style assessment

**Strength:** all-link assessment and baselines prevent selective examples and
simulation-derived scaling from overstating accuracy. The day-type and probe
count analyses are reproducible, and defects are exposed rather than hidden.

**Weakness:** the evaluated temporal model does not beat a simple counter
profile, while absolute count evidence has clock and missing-direction problems.
Historical simulation replay fails numerical equivalence. These are substantive
scientific limitations, not presentational details.

**Decision today:** major additional experimental work. The source and compiled
PDFs are suitable for internal co-author discussion and continuation, not a
submission-ready deliverable.
