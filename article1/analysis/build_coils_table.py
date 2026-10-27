#!/usr/bin/env python3
"""Build a 15-min MTS coil table from the regional open-data monthly files.

Source: Regione Emilia-Romagna, "Sistema MTS - Flussi di traffico al quarto d'ora" (CC BY),
https://rernitdatahub.blob.core.windows.net/open-datahub/DS-1944/<year>/<MM_Mese_year>.csv,
cached in /home/fede/data_cache/mts_monthly/<year>_<MM>.csv (retrieved 2026-10-27).

The open-data time labels (GIO_ID, HHMI_ID) are local time: converted to UTC they reproduce
the archived February 2020 table used by the project (checked on 12 February 2020; total
ratio 0.995). Counts are summed over all vehicle classes, as in the archived table.
The output follows the archived format (UTC timestamps, columns <station>_<direction>).

Usage: build_coils_table.py START_DATE END_DATE OUTDIR MONTHFILE [MONTHFILE ...]
"""
import sys
from pathlib import Path

import pandas as pd


def main():
    start, end, outdir, *files = sys.argv[1:]
    start, end = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    frames = []
    for f in files:
        for ch in pd.read_csv(f, dtype={"HHMI_ID": str}, chunksize=2_000_000):
            ch["t"] = pd.to_datetime(ch.GIO_ID.astype(str) + " " + ch.HHMI_ID)
            ch = ch[(ch.t >= start) & (ch.t < end)]
            if len(ch):
                ch["key"] = ch.APP_ID.astype(str) + "_" + ch.DIRMAR_COD.astype(str)
                frames.append(ch.groupby(["t", "key"]).NUM_TRANSITI.sum())
    s = pd.concat(frames).groupby(level=[0, 1]).sum()
    tab = s.unstack("key")
    tab = tab.reindex(pd.date_range(start, end, freq="15min", inclusive="left"))
    tab.index = tab.index.tz_localize("Europe/Rome", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    tab = tab[tab.index.notna()]
    tab.index.name = "datetime"
    t0, t1 = tab.index[0], tab.index[-1]
    name = f"coils_table_{t0:%y%m%d-%H%M%S}_{t1:%y%m%d-%H%M%S}.csv"
    out = Path(outdir) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    tab.index = tab.index.strftime("%Y-%m-%d %H:%M:%S+00:00")
    tab.to_csv(out, sep=";")
    print(out, tab.shape, "complete columns:", int(tab.notna().all().sum()))


if __name__ == "__main__":
    main()
