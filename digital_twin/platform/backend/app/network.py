"""Road network for the map: project cartography (OSM-derived, public), simplified and cached on disk."""
import csv
import gzip
import json
from pathlib import Path

from shapely.geometry import LineString, shape

CARTO = "model/results/carto_a059fb0.geojson"
ROAD_CLASS = "model/results/road_class.csv"
SHAPES = "vars/extra/er-shapes.geojson"
CLASS_ORDER = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "unmatched"]
TOLERANCE_DEG = 0.0002  # about 20 m, display only


def road_classes(root: Path) -> dict[int, str]:
    with open(root / ROAD_CLASS, newline="") as f:
        return {int(r["poly_cid"]): r["road_class"] for r in csv.DictReader(f)}


def build(root: Path, out: Path) -> Path:
    classes = road_classes(root)
    src = json.load(open(root / CARTO))
    features = []
    for f in src["features"]:
        p = f["properties"]
        g = shape(f["geometry"]).simplify(TOLERANCE_DEG, preserve_topology=False)
        if not isinstance(g, LineString) or g.is_empty:
            g = shape(f["geometry"])
        cid = int(p["poly_cid"])
        features.append({"type": "Feature", "id": cid,
                         "geometry": {"type": "LineString", "coordinates": [[round(x, 5), round(y, 5)] for x, y in g.coords]},
                         "properties": {"poly_cid": cid, "length_m": p["length"], "road_class": classes.get(cid, "unmatched"), "oneway": p["oneway"]}})
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as z:
        json.dump({"type": "FeatureCollection", "features": features}, z, separators=(",", ":"))
    tmp.replace(out)
    return out


def network_file(root: Path, state_dir: Path) -> Path:
    out = state_dir / "cache" / "network.geojson.gz"
    if not out.exists() or out.stat().st_mtime < (root / CARTO).stat().st_mtime:
        build(root, out)
    return out
