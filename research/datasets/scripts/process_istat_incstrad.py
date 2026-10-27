#!/usr/bin/env python3
"""Extract Emilia-Romagna records from the ISTAT public-use road-accident microdata.

Input : research/datasets/raw/istat_incstrad/<year>/MICRODATI/INCSTRAD_Microdati_<year>.txt
        (tab-separated, one record per injury accident; downloaded 2026-10-27 from
        https://www.istat.it/microdati/rilevazione-degli-incidenti-stradali-con-lesioni-a-persone-3/)
Output: research/datasets/processed/istat_incstrad_er_2017_2024.csv

Conventions (ISTAT, DescrizioneFile / NotaMetodologica):
* The coding of `Ora` differs between releases (checked against the regional Table 9):
  - 2017, 2018, 2023: k in 1..24, k covering (k-1:00, k:00] (00:00 coded 24), 25 = unknown;
    stored as hour0 = k-1 (convention "end").
  - 2019-2022, 2024: k in 0..23 = clock hour of the accident, i.e. [k:00, k+1:00);
    stored as hour0 = k (convention "start").
  The two conventions differ only for accidents recorded exactly on the hour, which are frequent
  (time heaping); `hour_convention` keeps track of it.
* `giorno` 1=Monday ... 7=Sunday.
* road number (`denominazione_della_strada`) and km point are only available up to 2018.
"""
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "research/datasets/raw/istat_incstrad"
OUT = ROOT / "research/datasets/processed/istat_incstrad_er_2017_2024.csv"

ER_PROV = {"033": "Piacenza", "034": "Parma", "035": "Reggio Emilia", "036": "Modena", "037": "Bologna",
           "038": "Ferrara", "039": "Ravenna", "040": "Forli-Cesena", "099": "Rimini"}
# localizzazione_incidente (var6)
LOC = {0: "regional_urban", 1: "urban_street", 2: "provincial_urban", 3: "state_urban",
       4: "municipal_extraurban", 5: "provincial", 6: "state", 7: "motorway", 8: "other", 9: "regional"}
LOC_GROUP = {0: "urban", 1: "urban", 2: "urban", 3: "urban", 4: "extraurban", 5: "extraurban",
             6: "extraurban", 9: "extraurban", 7: "motorway", 8: "other"}
KEEP = {"anno": "anno", "provincia": "provincia", "comune": "comune", "giorno": "weekday",
        "localizzazione_incidente": "loc", "denominazione_della_strada": "road_number",
        "tronco_di_strada_o_autostrada": "tronco", "tipo_di_strada": "carriageway",
        "intersezione_o_non_interse3": "intersection", "condizioni_meteorologiche": "weather",
        "natura_incidente": "nature", "morti_entro_30_giorni": "deaths30", "feriti": "injured",
        "Ora": "ora", "chilometri": "km", "ettometrica": "hm", "trimestre": "quarter"}


def load(year):
    f = RAW / str(year) / "MICRODATI" / f"INCSTRAD_Microdati_{year}.txt"
    d = pd.read_csv(f, sep="\t", dtype=str, encoding="latin1", usecols=list(KEEP), quoting=3)
    d = d.rename(columns=KEEP)
    d["provincia"] = d["provincia"].str.strip().str.zfill(3)
    d = d[d.provincia.isin(ER_PROV)].copy()
    d["year"] = year
    for c in ["weekday", "loc", "ora", "quarter", "deaths30", "injured", "carriageway"]:
        d[c] = pd.to_numeric(d[c].str.strip(), errors="coerce")
    if not ((d.ora == 0).any() and not (d.ora == 24).any()):
        d["hour0"] = np.where(d.ora.between(1, 24), d.ora - 1, np.nan)
        d["hour_convention"] = "end"
    else:
        d["hour0"] = np.where(d.ora.between(0, 23), d.ora, np.nan)
        d["hour_convention"] = "start"
    d["province"] = d.provincia.map(ER_PROV)
    d["loc_name"] = d["loc"].map(LOC)
    d["loc_group"] = d["loc"].map(LOC_GROUP)
    for c in ["road_number", "tronco", "km", "hm", "comune"]:
        d[c] = d[c].str.strip()
    return d.drop(columns=["anno"])


def main():
    years = [int(y) for y in sys.argv[1:]] or list(range(2017, 2025))
    out = pd.concat([load(y) for y in years], ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(out.groupby("year").size().to_string())
    print(out.groupby(["year", "loc_group"]).size().unstack().to_string())
    print("unknown hour share", out.hour0.isna().mean())


if __name__ == "__main__":
    main()
