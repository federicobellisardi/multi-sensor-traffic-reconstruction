# MTS archive recovery, 2026-10-27

Raw traffic data remain outside the repository in
`/home/fede/data_cache/mts_monthly/`; no proprietary data were copied or staged.

| File | Official source | Retrieval |
|---|---|---|
| `2018_03.csv` | https://rernitdatahub.blob.core.windows.net/open-datahub/DS-1944/2018/03_Marzo_2018.csv | 2026-10-27 |
| `monthly_index.csv` | https://rernitdatahub.blob.core.windows.net/open-datahub/DS-1944/Flussi%20di%20Traffico/DGCTA%20-%20Flussi%20di%20Traffico.csv | 2026-10-27 |
| `station_directions.csv` | https://rernitdatahub.blob.core.windows.net/open-datahub/DS-1944/V_OPD_ADT_APP_DIRMAR.csv | 2026-10-27 |

Current vehicle dictionary inspected on the same date:
https://rernitdatahub.blob.core.windows.net/open-datahub/DS-1944/V_OPD_ADT_VEI_CLASSE.csv

The regional catalogue lists the licence as CC BY; the exact licence version
and attribution text have not yet been independently archived. Confirm these
before redistributing data. Downloads are public HTTP resources.

The monthly archive contains station, direction, vehicle code and time-labelled
transit counts. It is not a vehicle-kilometre dataset. Historical codes absent
from the current dictionary, time zone/DST rules, zero-versus-missing semantics
and historical station availability require further verification. The current
registry must not be assumed to describe station locations in 2018.

Reproduce the structural audit from the repository root:

```sh
python3 research/datasets/scripts/audit_mts_monthly.py \
  /home/fede/data_cache/mts_monthly/2018_03.csv \
  --output research/reports/mts_2018_03_audit.json
```

No exposure estimates or road-safety conclusions are produced by this audit.
