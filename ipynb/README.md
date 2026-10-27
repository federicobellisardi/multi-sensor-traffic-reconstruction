# Notebooks per le figure

Questa cartella contiene i notebook che rifanno le figure per il paper
riorganizzato a partire da `paper/main.tex`.

| File | Sorgenti principali | Figure prodotte |
| --- | --- | --- |
| `data.ipynb` | `MCF/data/raw_inputs/`, `MCF/data/derived/` | domanda e concentrazione OD, attivita mobile |
| `simulazione.ipynb` | `article/data/uniq/*.csv.corrected`, `carto.geojson` | profilo orario, carico di rete, effetto della correzione |
| `validazione.ipynb` | `article/results/*/global/penetrazione/` | distribuzione ed ECDF Viasat, classi e mappa spaziale |

Ogni notebook esporta sia `pdf` sia `png` sotto
`article/results/figures/<sezione>/`, insieme alle tabelle di supporto
utilizzate per i grafici quantitativi.

In `data.ipynb`, `REBUILD_DERIVED = False` usa i riepiloghi OD gia calcolati.
Impostandolo a `True`, le metriche vengono ricostruite dalle matrici OD
complete; l'elaborazione richiede piu memoria e tempo.
