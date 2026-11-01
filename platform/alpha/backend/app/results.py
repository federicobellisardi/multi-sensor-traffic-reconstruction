"""Reading engine outputs (the _uniq_ link-flow table). Never modifies them."""
import csv
from functools import lru_cache
from pathlib import Path

import numpy as np


class FlowTable:
    """Hourly flows per link and direction: flows[direction][link index, hour]."""

    def __init__(self, path: Path):
        with open(path, newline="") as f:
            r = csv.reader(f, delimiter=";")
            head = next(r)
            self.times = head[3:]
            cids, dirs, vals = [], [], []
            for row in r:
                cids.append(int(row[1]))
                dirs.append(row[2])
                vals.append([float(v) for v in row[3:]])
        order = sorted(set(cids))
        idx = {c: i for i, c in enumerate(order)}
        self.cids = np.array(order)
        self.index = idx
        self.ft = np.zeros((len(order), len(self.times)))
        self.tf = np.zeros_like(self.ft)
        for c, d, v in zip(cids, dirs, vals):
            (self.ft if d == "FT" else self.tf)[idx[c]] = v

    def values(self, direction: str = "both") -> np.ndarray:
        return {"both": self.ft + self.tf, "FT": self.ft, "TF": self.tf}[direction]


@lru_cache(maxsize=8)
def load(path_str: str, mtime_ns: int) -> FlowTable:
    return FlowTable(Path(path_str))


def table(path: Path) -> FlowTable:
    return load(str(path), path.stat().st_mtime_ns)


def compare(a: FlowTable, b: FlowTable, mask: np.ndarray | None = None) -> dict:
    """Descriptive differences of daily link volumes on the hours common to both runs (B minus A)."""
    n = min(len(a.times), len(b.times))
    if not np.array_equal(a.cids, b.cids):
        raise ValueError("runs are on different networks")
    if [t[11:] for t in a.times[:n]] != [t[11:] for t in b.times[:n]]:
        raise ValueError("runs have different time bins")
    va, vb = a.values()[:, :n], b.values()[:, :n]
    if mask is not None:
        va, vb = va[mask], vb[mask]
    da, db = va.sum(1), vb.sum(1)
    corr = float(np.corrcoef(da, db)[0, 1]) if da.std() > 0 and db.std() > 0 else None
    return {
        "common_hours": n, "links": int(len(da)),
        "total_a": float(da.sum()), "total_b": float(db.sum()),
        "relative_total_change": float(db.sum() / da.sum() - 1) if da.sum() > 0 else None,
        "mean_abs_link_diff": float(np.abs(db - da).mean()) if len(da) else None,
        "pearson_daily_volume": corr,
        "profile_a": va.sum(0).tolist(), "profile_b": vb.sum(0).tolist(),
        "hours": [t[11:16] for t in a.times[:n]],
    }
