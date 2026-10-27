#!/usr/bin/env python3
"""Script version of article/ipynb/regenerate_figures_05_incident_risk.ipynb.

Changes with respect to the notebook: the non-working-day exposure is labelled
"weekend" (the runs are 2023 Sundays driven by the Saturday-Sunday OD matrix),
paths are relative to the repository, and a bootstrap confidence interval is
computed for the exponent of A ~ E^alpha (see the end of the file).
"""
def display(x):
    print(x if not hasattr(x, "head") else x.head())
# ---- cell 1
# Common paper palette and style, aligned with notebooks 01--04.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, LogNorm

PALETTE = {
    "src_dest": "#E7D1D1",
    "rnd_rnd": "#DCC7DF",
    "rnd_dest": "#C4DADD",
    "src_rnd": "#C8DEC8",
    "roads_main": "#8D8D8D",
    "roads_minor": "#CFCFCF",
    "text": "#2F2F2F",
    "background": "#FAFAFA",
    "grid": "#DDDDDD",
}

ACCIDENT_COLORS = {
    "incidents": "#B84A62",
    "deaths": "#252525",
    "injured": "#6B8FA6",
    "weekday": "#8D8D8D",
    "holiday": "#D08C60",
    "risk": "#B84A62",
    "exposure": "#2A9D8F",
}

paper_cmap = LinearSegmentedColormap.from_list(
    "paper_cmap",
    ["#F7F7F7", "#DAD7CD", "#A3B18A", "#588157", "#3A5A40"],
)

risk_cmap = LinearSegmentedColormap.from_list(
    "risk_cmap",
    ["#F7F7F7", "#F4D6CC", "#D08C60", "#B84A62", "#6D213C"],
)

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": PALETTE["background"],
    "axes.edgecolor": PALETTE["text"],
    "axes.labelcolor": PALETTE["text"],
    "text.color": PALETTE["text"],
    "xtick.color": PALETTE["text"],
    "ytick.color": PALETTE["text"],
    "axes.titlesize": 22,
    "axes.labelsize": 18,
    "xtick.labelsize": 15,
    "ytick.labelsize": 15,
    "legend.fontsize": 14,
    "font.family": "DejaVu Sans",
    "savefig.dpi": 300,
})

# ---- cell 2
# Imports, paths and output utility.
from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    from shapely import wkt
except Exception as exc:
    gpd = None
    wkt = None
    print(f"Geospatial stack unavailable: {exc}")

# CartoDB tiles now require an API key (they return watermarked tiles), so the
# maps are drawn on the road network only.
cx = None

# ---------------------------------------------------------------------
# Edit these paths if needed.
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
INCIDENT_DATA_DIR = ROOT / "work_incidenti/data"
SIM_DATA_DIR = ROOT / "work_iconsultin/data2"

# Sandbox/local fallback, useful only when testing this exported notebook elsewhere.
if not INCIDENT_DATA_DIR.exists():
    INCIDENT_DATA_DIR = Path("/mnt/data")
if not SIM_DATA_DIR.exists():
    SIM_DATA_DIR = Path("/mnt/data")

WEEKDAY_DIR = SIM_DATA_DIR / "feriali"
HOLIDAY_DIR = SIM_DATA_DIR / "festivi"

# If folders are absent, the loader below also falls back to CSVs directly inside SIM_DATA_DIR.
OUTPUT_DIR = ROOT / "article/ipynb/figures_incident_risk"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INCIDENT_FILES = {
    2022: INCIDENT_DATA_DIR / "2022.xlsx",
    2023: INCIDENT_DATA_DIR / "2023.xlsx",
    2024: INCIDENT_DATA_DIR / "2024.xlsx",
}
# Some regional downloads use a longer 2024 filename.
if not INCIDENT_FILES[2024].exists():
    alt_2024 = INCIDENT_DATA_DIR / "08-emila-romagna-tavole-2024.xlsx"
    if alt_2024.exists():
        INCIDENT_FILES[2024] = alt_2024

HOUR_TICKS = np.arange(0, 24, 3)
HOUR_LABELS = [f"{h:02d}:00" for h in range(24)]


def save_fig_local(fig, stem):
    """Save figures as PNG and PDF, following the convention of notebooks 01--04."""
    png = OUTPUT_DIR / f"{stem}.png"
    pdf = OUTPUT_DIR / f"{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"Saved: {png}")
    print(f"Saved: {pdf}")


def clean_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.8, alpha=0.75, zorder=0)
    ax.set_axisbelow(True)

# ---- cell 4
# Accident-table extractors.

def _as_number(x):
    return pd.to_numeric(x, errors="coerce")


def _parse_hour_label(value):
    """Convert ISTAT hour labels ('1', '1a ora', '24a "') to 0--23."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip().lower()
    match = re.search(r"(\d+)", s)
    if not match:
        return np.nan
    h = int(match.group(1))
    if 1 <= h <= 24:
        return h - 1
    if 0 <= h <= 23:
        return h
    return np.nan


def extract_tavola9_hourly(path, year):
    df = pd.read_excel(path, sheet_name="Tavola 9", header=None)
    records = []
    for _, row in df.iterrows():
        hour = _parse_hour_label(row.iloc[1] if len(row) > 1 else np.nan)
        incidents = _as_number(row.iloc[2] if len(row) > 2 else np.nan)
        deaths = _as_number(row.iloc[3] if len(row) > 3 else np.nan)
        injured = _as_number(row.iloc[4] if len(row) > 4 else np.nan)
        if pd.notna(hour) and pd.notna(incidents):
            records.append({
                "year": year,
                "hour": int(hour),
                "incidents": float(incidents),
                "deaths": float(deaths) if pd.notna(deaths) else np.nan,
                "injured": float(injured) if pd.notna(injured) else np.nan,
            })
    out = pd.DataFrame(records)
    out = out[out["hour"].between(0, 23)].sort_values(["year", "hour"])
    return out


def extract_tavola8_weekday(path, year):
    df = pd.read_excel(path, sheet_name="Tavola 8", header=None)
    day_order = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    records = []
    for _, row in df.iterrows():
        day = row.iloc[1] if len(row) > 1 else None
        if isinstance(day, str) and day.strip() in day_order:
            records.append({
                "year": year,
                "day": day.strip(),
                "day_index": day_order.index(day.strip()),
                "incidents": float(_as_number(row.iloc[2])),
                "deaths": float(_as_number(row.iloc[3])),
                "injured": float(_as_number(row.iloc[4])),
            })
    return pd.DataFrame(records).sort_values(["year", "day_index"])


def extract_tavola7_monthly(path, year):
    df = pd.read_excel(path, sheet_name="Tavola 7", header=None)
    month_order = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
    ]
    records = []
    for _, row in df.iterrows():
        month = row.iloc[1] if len(row) > 1 else None
        if isinstance(month, str) and month.strip() in month_order:
            mi = month_order.index(month.strip()) + 1
            season = {
                12: "winter", 1: "winter", 2: "winter",
                3: "spring", 4: "spring", 5: "spring",
                6: "summer", 7: "summer", 8: "summer",
                9: "autumn", 10: "autumn", 11: "autumn",
            }[mi]
            records.append({
                "year": year,
                "month": month.strip(),
                "month_index": mi,
                "season": season,
                "incidents": float(_as_number(row.iloc[2])),
                "deaths": float(_as_number(row.iloc[3])),
                "injured": float(_as_number(row.iloc[4])),
            })
    return pd.DataFrame(records).sort_values(["year", "month_index"])


def extract_tavola5_road_category(path, year):
    df = pd.read_excel(path, sheet_name="Tavola 5", header=None)
    wanted = {"Strade urbane", "Autostrade e raccordi", "Altre strade (c)", "Totale"}
    records = []
    for _, row in df.iterrows():
        category = row.iloc[1] if len(row) > 1 else None
        if isinstance(category, str) and category.strip() in wanted:
            records.append({
                "year": year,
                "road_category": category.strip().replace(" (c)", ""),
                "incidents": float(_as_number(row.iloc[2])),
                "deaths": float(_as_number(row.iloc[3])),
                "injured": float(_as_number(row.iloc[4])),
            })
    return pd.DataFrame(records)


def load_accident_tables(files):
    hourly, weekdays, monthly, categories = [], [], [], []
    for year, path in files.items():
        if not path.exists():
            print(f"Missing accident workbook for {year}: {path}")
            continue
        print(f"Loading accident workbook {year}: {path}")
        hourly.append(extract_tavola9_hourly(path, year))
        weekdays.append(extract_tavola8_weekday(path, year))
        monthly.append(extract_tavola7_monthly(path, year))
        categories.append(extract_tavola5_road_category(path, year))
    return {
        "hourly": pd.concat(hourly, ignore_index=True) if hourly else pd.DataFrame(),
        "weekday": pd.concat(weekdays, ignore_index=True) if weekdays else pd.DataFrame(),
        "monthly": pd.concat(monthly, ignore_index=True) if monthly else pd.DataFrame(),
        "road_category": pd.concat(categories, ignore_index=True) if categories else pd.DataFrame(),
    }

acc = load_accident_tables(INCIDENT_FILES)
for name, df in acc.items():
    print(f"{name:>14}: {df.shape}")
    display(df.head())

# ---- cell 6
# Simulation loaders.

def read_csv_flexible(path):
    """Read comma- or semicolon-separated simulation CSVs."""
    path = Path(path)
    # Try Python engine with automatic delimiter detection first.
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        df = pd.read_csv(path)
    # Some files can be parsed as one column; retry with the other separator.
    if df.shape[1] == 1:
        for sep in [";", ","]:
            try:
                cand = pd.read_csv(path, sep=sep)
                if cand.shape[1] > 1:
                    return cand
            except Exception:
                pass
    return df


def _load_aggregate_simulation(path, label):
    df = read_csv_flexible(path)
    if "poly_lid" not in df.columns or "counter" not in df.columns:
        raise KeyError(f"Expected columns poly_lid and counter in {path}. Found: {list(df.columns)}")
    df["source"] = label
    df["counter"] = pd.to_numeric(df["counter"], errors="coerce").fillna(0.0)
    if "hour" in df.columns:
        df["hour"] = pd.to_numeric(df["hour"], errors="coerce").astype("Int64")
    elif "datetime" in df.columns:
        dt = pd.to_datetime(df["datetime"], errors="coerce")
        df["hour"] = dt.dt.hour.astype("Int64")
    else:
        raise KeyError(f"No hour or datetime column found in {path}")
    if "season" not in df.columns:
        df["season"] = "all"
    return df


def _load_individual_simulation_files(folder, label):
    folder = Path(folder)
    files = sorted(folder.glob("*.csv")) if folder.exists() else []
    files = [p for p in files if p.name.lower() not in {"feriali.csv", "festivi.csv"}]
    # Sandbox/testing fallback: if no weekday folder exists, use CSVs directly in SIM_DATA_DIR.
    # Do not apply this fallback to holidays, otherwise weekday files could be duplicated as holidays.
    if not files and label == "weekday":
        files = [p for p in sorted(SIM_DATA_DIR.glob("*.csv")) if p.name.lower() not in {"feriali.csv", "festivi.csv"}]
    pieces = []
    for p in files:
        df = read_csv_flexible(p)
        if not {"poly_lid", "datetime", "counter"}.issubset(df.columns):
            continue
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df["hour"] = df["datetime"].dt.hour.astype("Int64")
        df["counter"] = pd.to_numeric(df["counter"], errors="coerce").fillna(0.0)
        df["season"] = "all"
        df["source"] = label
        pieces.append(df[["poly_lid", "hour", "counter", "season", "source"]])
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True)


def load_simulation(kind):
    """Load weekday or holiday exposure tables."""
    assert kind in {"weekday", "holiday"}
    folder = WEEKDAY_DIR if kind == "weekday" else HOLIDAY_DIR
    aggregate_name = "feriali.csv" if kind == "weekday" else "festivi.csv"
    aggregate_candidates = [folder / aggregate_name, SIM_DATA_DIR / aggregate_name]
    for candidate in aggregate_candidates:
        if candidate.exists():
            print(f"Loading {kind} aggregate simulation: {candidate}")
            return _load_aggregate_simulation(candidate, kind)
    print(f"No aggregate {kind} file found. Trying individual CSV files in {folder}.")
    return _load_individual_simulation_files(folder, kind)


weekday_sim = load_simulation("weekday")
holiday_sim = load_simulation("holiday")

print("weekday_sim", weekday_sim.shape)
print("holiday_sim", holiday_sim.shape)
display(weekday_sim.head())
if not holiday_sim.empty:
    display(holiday_sim.head())
else:
    print("Holiday simulation not found. Holiday-specific panels will be skipped or shown as unavailable.")

# ---- cell 7
# Build exposure tables and optional GeoDataFrames.

def hourly_exposure(sim_df):
    if sim_df.empty:
        return pd.Series(dtype=float)
    out = sim_df.dropna(subset=["hour"]).groupby("hour")["counter"].sum().reindex(range(24), fill_value=0.0)
    out.index = out.index.astype(int)
    return out


def seasonal_exposure(sim_df):
    if sim_df.empty or "season" not in sim_df.columns:
        return pd.DataFrame()
    out = sim_df.groupby("season")["counter"].sum().reset_index()
    return out


def link_hour_matrix(sim_df):
    if sim_df.empty:
        return pd.DataFrame()
    mat = (
        sim_df.dropna(subset=["hour"])
        .pivot_table(index="poly_lid", columns="hour", values="counter", aggfunc="sum", fill_value=0.0)
        .reindex(columns=range(24), fill_value=0.0)
    )
    return mat


def link_geometries(sim_df):
    if sim_df.empty or "geometry" not in sim_df.columns or gpd is None or wkt is None:
        return None
    geom_df = sim_df[["poly_lid", "geometry"]].dropna().drop_duplicates("poly_lid").copy()
    if geom_df.empty:
        return None
    geom_df["geometry"] = geom_df["geometry"].apply(lambda x: wkt.loads(x) if isinstance(x, str) else x)
    return gpd.GeoDataFrame(geom_df, geometry="geometry", crs="EPSG:4326")

weekday_hourly = hourly_exposure(weekday_sim)
holiday_hourly = hourly_exposure(holiday_sim)
weekday_link_hour = link_hour_matrix(weekday_sim)
holiday_link_hour = link_hour_matrix(holiday_sim)
weekday_geom = link_geometries(weekday_sim)
holiday_geom = link_geometries(holiday_sim)

print("weekday total exposure", weekday_hourly.sum())
print("holiday total exposure", holiday_hourly.sum() if not holiday_hourly.empty else "missing")
print("weekday link-hour matrix", weekday_link_hour.shape)
print("geometry available", weekday_geom is not None)

# ---- cell 9
# 8a_accident_overview.png - yearly accidents and road-category distribution.
try:
    hourly_acc = acc["hourly"]
    road_cat = acc["road_category"]

    yearly = hourly_acc.groupby("year")[["incidents", "deaths", "injured"]].sum().reset_index()
    road_cat_no_total = road_cat[road_cat["road_category"] != "Totale"].copy()

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8), constrained_layout=True)

    ax = axes[0]
    ax.plot(yearly["year"], yearly["incidents"], marker="o", linewidth=2.2,
            color=ACCIDENT_COLORS["incidents"], label="Incidents")
    ax2 = ax.twinx()
    ax2.plot(yearly["year"], yearly["deaths"], marker="s", linewidth=2.0,
             color=ACCIDENT_COLORS["deaths"], label="Deaths")
    ax.set_xlabel("Year")
    ax.set_ylabel("Incidents")
    ax2.set_ylabel("Deaths")
    ax.set_xticks(yearly["year"])
    clean_axis(ax)
    ax2.spines["top"].set_visible(False)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left", frameon=True)

    ax = axes[1]
    pivot = road_cat_no_total.pivot_table(index="year", columns="road_category", values="incidents", aggfunc="sum")
    shares = pivot.div(pivot.sum(axis=1), axis=0) * 100
    bottom = np.zeros(len(shares))
    colors = ["#8D8D8D", "#D08C60", "#6B8FA6"]
    for color, col in zip(colors, shares.columns):
        ax.bar(shares.index.astype(str), shares[col], bottom=bottom, color=color, label=col,
               edgecolor="white", linewidth=0.8)
        bottom += shares[col].values
    ax.set_ylabel("Share of incidents (%)")
    ax.set_xlabel("Year")
    ax.set_ylim(0, 100)
    clean_axis(ax)
    ax.legend(loc="upper right", frameon=True)

    save_fig_local(fig, "8a_accident_overview")
    plt.close("all")
except Exception as exc:
    print(f"ERROR 8a_accident_overview: {type(exc).__name__}: {exc}")
    raise

# ---- cell 10
# 8b_hourly_accidents_vs_exposure.png - hourly accidents versus simulated exposure.
try:
    hourly_acc_mean = acc["hourly"].groupby("hour")["incidents"].mean().reindex(range(24), fill_value=0.0)
    hourly_acc_share = hourly_acc_mean / hourly_acc_mean.sum()

    weekday_share = weekday_hourly / weekday_hourly.sum()
    holiday_share = holiday_hourly / holiday_hourly.sum() if not holiday_hourly.empty and holiday_hourly.sum() > 0 else None

    x = np.arange(24)
    fig, ax = plt.subplots(figsize=(9.5, 4.8), constrained_layout=True)

    ax.plot(x, hourly_acc_share.values * 100, color=ACCIDENT_COLORS["incidents"],
            marker="o", linewidth=2.2, markersize=4.5, label="Accidents, 2022--2024 mean")
    ax.plot(x, weekday_share.values * 100, color=ACCIDENT_COLORS["weekday"],
            marker="s", linewidth=2.0, markersize=4.2, label="Weekday simulated exposure")

    if holiday_share is not None:
        ax.plot(x, holiday_share.values * 100, color=ACCIDENT_COLORS["holiday"],
                linestyle=(0, (4, 2)), marker="^", markevery=2, linewidth=2.0,
                label="Weekend simulated exposure")

#     ax.set_title("Hourly accident distribution and simulated traffic exposure", loc="left", fontweight="bold")
    ax.set_ylabel("Daily share (%)")
    ax.set_xlabel("Time")
    ax.set_xticks(HOUR_TICKS)
    ax.set_xticklabels([HOUR_LABELS[i] for i in HOUR_TICKS], rotation=45, ha="right")
    clean_axis(ax)
    ax.legend(loc="upper left", frameon=True, ncol=1)

    save_fig_local(fig, "8b_hourly_accidents_vs_exposure")
    plt.close("all")
except Exception as exc:
    print(f"ERROR 8b_hourly_accidents_vs_exposure: {type(exc).__name__}: {exc}")
    raise

# ---- cell 11
# 8c_exposure_normalized_hourly_risk.png - risk intensity normalized by simulated exposure.
try:
    hourly_acc_mean = acc["hourly"].groupby("hour")["incidents"].mean().reindex(range(24), fill_value=0.0)
    hourly_acc_share = hourly_acc_mean / hourly_acc_mean.sum()

    def relative_hourly_risk(exposure):
        exposure_share = exposure / exposure.sum()
        risk = hourly_acc_share / exposure_share.replace(0, np.nan)
        return risk / risk.replace([np.inf, -np.inf], np.nan).mean()

    weekday_risk = relative_hourly_risk(weekday_hourly)
    holiday_risk = relative_hourly_risk(holiday_hourly) if not holiday_hourly.empty and holiday_hourly.sum() > 0 else None

    x = np.arange(24)
    fig, ax = plt.subplots(figsize=(9.5, 4.8), constrained_layout=True)

    ax.axhline(1.0, color="#555555", linestyle="--", linewidth=1.2, alpha=0.8, label="Daily average risk")
    ax.bar(x - 0.18, weekday_risk.values, width=0.36, color=ACCIDENT_COLORS["weekday"],
           edgecolor="white", linewidth=0.6, label="Using weekday exposure", zorder=3)
    if holiday_risk is not None:
        ax.bar(x + 0.18, holiday_risk.values, width=0.36, color=ACCIDENT_COLORS["holiday"],
               edgecolor="white", linewidth=0.6, label="Using weekend exposure", zorder=3)

    # ax.set_title("Exposure-normalized hourly accident intensity", loc="left", fontweight="bold")
    ax.set_ylabel("Relative risk index")
    ax.set_xlabel("Time")
    ax.set_xticks(HOUR_TICKS)
    ax.set_xticklabels([HOUR_LABELS[i] for i in HOUR_TICKS], rotation=45, ha="right")
    ax.set_ylim(0, max(2.5, np.nanmax(weekday_risk.values) * 1.15))
    clean_axis(ax)
    ax.legend(loc="upper right", frameon=True)

    save_fig_local(fig, "8c_exposure_normalized_hourly_risk")
    plt.close("all")
except Exception as exc:
    print(f"ERROR 8c_exposure_normalized_hourly_risk: {type(exc).__name__}: {exc}")
    raise

# ---- cell 13
# 8d_seasonal_exposure_vs_accidents.png - seasonal traffic exposure and accident seasonality.
try:
    monthly = acc["monthly"].copy()
    incident_season = monthly.groupby("season")["incidents"].sum()
    incident_season_share = incident_season / incident_season.sum() * 100

    weekday_season = seasonal_exposure(weekday_sim)
    if weekday_season.empty or weekday_season["season"].nunique() <= 1:
        raise ValueError("Seasonal simulation exposure not available. Expected a 'season' column with multiple seasons.")

    weekday_season_share = weekday_season.set_index("season")["counter"]
    weekday_season_share = weekday_season_share / weekday_season_share.sum() * 100

    season_order = ["winter", "spring", "summer", "autumn"]
    incident_season_share = incident_season_share.reindex(season_order)
    weekday_season_share = weekday_season_share.reindex(season_order)

    fig, ax = plt.subplots(figsize=(8.4, 4.8), constrained_layout=True)
    x = np.arange(len(season_order))
    width = 0.36

    ax.bar(x - width/2, incident_season_share.values, width=width,
           color=ACCIDENT_COLORS["incidents"], edgecolor="white", linewidth=0.8,
           label="Accidents, 2022--2024")
    ax.bar(x + width/2, weekday_season_share.values, width=width,
           color=ACCIDENT_COLORS["exposure"], edgecolor="white", linewidth=0.8,
           label="Weekday simulated exposure")

    ax.set_ylabel("Annual share (%)")
    ax.set_xlabel("Season")
    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in season_order])
    clean_axis(ax)
    ax.legend(loc="upper left", frameon=True)

    save_fig_local(fig, "8d_seasonal_exposure_vs_accidents")
    plt.close("all")
except Exception as exc:
    print(f"SKIPPED 8d_seasonal_exposure_vs_accidents: {type(exc).__name__}: {exc}")

# ---- cell 15
# Helper for hazard-weighted link exposure.

def compute_hazard_weighted_exposure(link_hour, exposure_hourly, hourly_accidents):
    if link_hour.empty:
        return pd.Series(dtype=float)
    acc_share = hourly_accidents / hourly_accidents.sum()
    exp_share = exposure_hourly / exposure_hourly.sum()
    risk = acc_share / exp_share.replace(0, np.nan)
    risk = risk.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    risk = risk / risk[risk > 0].mean()
    risk = risk.reindex(range(24), fill_value=1.0)
    return (link_hour.reindex(columns=range(24), fill_value=0.0) * risk.values).sum(axis=1)

hourly_acc_mean = acc["hourly"].groupby("hour")["incidents"].mean().reindex(range(24), fill_value=0.0)
weekday_hazard = compute_hazard_weighted_exposure(weekday_link_hour, weekday_hourly, hourly_acc_mean)
holiday_hazard = compute_hazard_weighted_exposure(holiday_link_hour, holiday_hourly, hourly_acc_mean) if not holiday_link_hour.empty else pd.Series(dtype=float)

hazard_summary = pd.DataFrame({
    "weekday_hazard": weekday_hazard,
    "weekday_total_flow": weekday_link_hour.sum(axis=1) if not weekday_link_hour.empty else pd.Series(dtype=float),
})
if not holiday_hazard.empty:
    hazard_summary["holiday_hazard"] = holiday_hazard
    hazard_summary["holiday_total_flow"] = holiday_link_hour.sum(axis=1)

hazard_summary.to_csv(OUTPUT_DIR / "hazard_weighted_exposure_summary.csv")
display(hazard_summary.head())
print(f"Saved summary: {OUTPUT_DIR / 'hazard_weighted_exposure_summary.csv'}")

# ---- cell 16
# 8e_hazard_weighted_exposure_map.png - map of weekday hazard-weighted exposure.
try:
    if weekday_geom is None:
        raise ValueError("No geometry available in the simulation table. Use aggregated feriali.csv/festivi.csv with WKT geometry.")

    map_df = weekday_geom.merge(
        hazard_summary.reset_index().rename(columns={"index": "poly_lid"}),
        on="poly_lid",
        how="left",
    )
    map_df["weekday_hazard"] = map_df["weekday_hazard"].fillna(0.0)
    map_web = map_df.to_crs(epsg=3857)

    active = map_web[map_web["weekday_hazard"] > 0]
    vmin = max(1, active["weekday_hazard"].quantile(0.05)) if not active.empty else 1
    vmax = active["weekday_hazard"].quantile(0.98) if not active.empty else 10

    fig, ax = plt.subplots(figsize=(10.5, 6.6), constrained_layout=True)
    map_web.plot(ax=ax, color=PALETTE["roads_minor"], linewidth=0.42, alpha=0.48, zorder=1)
    active.plot(ax=ax, column="weekday_hazard", cmap=risk_cmap, linewidth=1.15,
                norm=LogNorm(vmin=vmin, vmax=max(vmax, vmin + 1)), zorder=3)

    if cx is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, attribution=False, alpha=0.72, zorder=0)
            except Exception as exc:
                print(f"Basemap unavailable: {exc}")

    sm = plt.cm.ScalarMappable(cmap=risk_cmap, norm=LogNorm(vmin=vmin, vmax=max(vmax, vmin + 1)))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.74, pad=0.012)
    cbar.set_label("Hazard-weighted simulated exposure", fontsize=15, fontweight="bold")
    cbar.ax.tick_params(labelsize=13)

    ax.set_axis_off()

    save_fig_local(fig, "8e_hazard_weighted_exposure_map")
    plt.close("all")
except Exception as exc:
    print(f"SKIPPED 8e_hazard_weighted_exposure_map: {type(exc).__name__}: {exc}")

# ---- cell 17
# 8f_weekday_holiday_hazard_difference.png - difference map when holiday simulations are available.
try:
    if weekday_geom is None:
        raise ValueError("No geometry available in the simulation table.")
    if holiday_hazard.empty:
        raise ValueError("Holiday simulation not available.")

    diff = pd.DataFrame({
        "poly_lid": sorted(set(weekday_hazard.index) | set(holiday_hazard.index))
    })
    diff["weekday_hazard"] = diff["poly_lid"].map(weekday_hazard).fillna(0.0)
    diff["holiday_hazard"] = diff["poly_lid"].map(holiday_hazard).fillna(0.0)
    diff["relative_difference"] = (
        (diff["weekday_hazard"] - diff["holiday_hazard"]) /
        (diff["weekday_hazard"] + diff["holiday_hazard"]).replace(0, np.nan)
    ).fillna(0.0)

    map_df = weekday_geom.merge(diff, on="poly_lid", how="left").fillna({"relative_difference": 0.0})
    map_web = map_df.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(10.5, 6.6), constrained_layout=True)
    map_web.plot(ax=ax, color=PALETTE["roads_minor"], linewidth=0.40, alpha=0.38, zorder=1)
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    map_web.plot(ax=ax, column="relative_difference", cmap="RdBu_r", norm=norm,
                 linewidth=1.15, alpha=0.95, zorder=3)

    if cx is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, attribution=False, alpha=0.72, zorder=0)
            except Exception as exc:
                print(f"Basemap unavailable: {exc}")

    sm = plt.cm.ScalarMappable(cmap="RdBu_r", norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.74, pad=0.012)
    cbar.set_label(r"Weekday-weekend contrast $D_i$", fontsize=15, fontweight="bold")
    cbar.ax.tick_params(labelsize=13)

    ax.set_axis_off()

    save_fig_local(fig, "8f_weekday_holiday_hazard_difference")
    plt.close("all")
except Exception as exc:
    print(f"SKIPPED 8f_weekday_holiday_hazard_difference: {type(exc).__name__}: {exc}")

# ---- cell 18
# ==========================================================
# 9. Preparation for advanced incident-risk analyses
# ----------------------------------------------------------
# This cell defines the variables used by the next four cells:
# - hourly_compare
# - hourly_risk_mean
# - road_exposure_gdf
# It only uses variables already created in this notebook.
# ==========================================================

try:
    if gpd is None:
        raise ImportError("geopandas is not available.")
    if weekday_geom is None:
        raise ValueError(
            "weekday_geom is not available. The simulation table must contain a WKT 'geometry' column, "
            "as in feriali/feriali.csv."
        )
    if weekday_sim.empty:
        raise ValueError("weekday_sim is empty.")
    if weekday_hourly.empty or weekday_hourly.sum() <= 0:
        raise ValueError("weekday_hourly exposure is empty or zero.")

    HOURS = np.arange(24)

    # ------------------------------------------------------
    # Hourly accident distribution, averaged over 2022--2024
    # ------------------------------------------------------
    hourly_acc_mean = (
        acc["hourly"]
        .groupby("hour")["incidents"]
        .mean()
        .reindex(HOURS, fill_value=0.0)
        .astype(float)
    )

    accident_share = hourly_acc_mean / hourly_acc_mean.sum()

    # ------------------------------------------------------
    # Weekday/holiday simulated exposure shares
    # ------------------------------------------------------
    weekday_exposure = weekday_hourly.reindex(HOURS, fill_value=0.0).astype(float)
    weekday_exposure_share = weekday_exposure / weekday_exposure.sum()

    has_holiday = (
        isinstance(holiday_hourly, pd.Series)
        and not holiday_hourly.empty
        and holiday_hourly.sum() > 0
    )

    if has_holiday:
        holiday_exposure = holiday_hourly.reindex(HOURS, fill_value=0.0).astype(float)
        holiday_exposure_share = holiday_exposure / holiday_exposure.sum()
    else:
        holiday_exposure = pd.Series(np.nan, index=HOURS)
        holiday_exposure_share = pd.Series(np.nan, index=HOURS)

    # ------------------------------------------------------
    # Exposure-normalized risk profiles
    # risk = accident share / exposure share, normalized to mean 1
    # ------------------------------------------------------
    def normalized_risk(acc_share, exp_share):
        risk = acc_share / exp_share.replace(0, np.nan)
        risk = risk.replace([np.inf, -np.inf], np.nan)
        mean_positive = risk[risk > 0].mean()
        if pd.isna(mean_positive) or mean_positive == 0:
            mean_positive = 1.0
        return (risk / mean_positive).fillna(1.0)

    risk_weekday = normalized_risk(accident_share, weekday_exposure_share)

    if has_holiday:
        risk_holiday = normalized_risk(accident_share, holiday_exposure_share)
    else:
        risk_holiday = pd.Series(np.nan, index=HOURS)

    hourly_compare = pd.DataFrame({
        "hour": HOURS,
        "accidents": hourly_acc_mean.values,
        "accident_share": accident_share.values,
        "weekday_exposure": weekday_exposure.values,
        "weekday_exposure_share": weekday_exposure_share.values,
        "risk_weekday": risk_weekday.values,
        "holiday_exposure": holiday_exposure.values,
        "holiday_exposure_share": holiday_exposure_share.values,
        "risk_holiday": risk_holiday.values,
    })

    # This is the risk profile used to weight every link-hour exposure.
    hourly_risk_mean = pd.Series(
        hourly_compare["risk_weekday"].values,
        index=hourly_compare["hour"].astype(int),
        name="hazard_factor",
    )

    # ------------------------------------------------------
    # Build long-format link-hour GeoDataFrame from weekday simulation
    # ------------------------------------------------------
    exposure_cols = ["poly_lid", "hour", "counter"]
    if "season" in weekday_sim.columns:
        exposure_cols.append("season")

    weekday_long = weekday_sim[exposure_cols].copy()
    weekday_long = weekday_long.dropna(subset=["poly_lid", "hour"])
    weekday_long["poly_lid"] = weekday_long["poly_lid"].astype(weekday_geom["poly_lid"].dtype)
    weekday_long["hour"] = weekday_long["hour"].astype(int)
    weekday_long["counter"] = pd.to_numeric(weekday_long["counter"], errors="coerce").fillna(0.0)

    road_exposure_gdf = weekday_geom.merge(
        weekday_long,
        on="poly_lid",
        how="inner",
    )

    road_exposure_gdf["hazard_factor"] = (
        road_exposure_gdf["hour"]
        .map(hourly_risk_mean)
        .fillna(hourly_risk_mean.mean())
    )

    road_exposure_gdf["hazard_weighted_exposure"] = (
        road_exposure_gdf["counter"].astype(float)
        * road_exposure_gdf["hazard_factor"].astype(float)
    )

    print("Created hourly_compare:", hourly_compare.shape)
    print("Created road_exposure_gdf:", road_exposure_gdf.shape)
    print("Unique road links:", road_exposure_gdf["poly_lid"].nunique())
    print("Hour range:", sorted(road_exposure_gdf["hour"].dropna().unique())[:3], "...", sorted(road_exposure_gdf["hour"].dropna().unique())[-3:])

    display(hourly_compare.head())
    display(
        road_exposure_gdf[
            ["poly_lid", "hour", "counter", "hazard_factor", "hazard_weighted_exposure"]
        ].head()
    )

except Exception as exc:
    print(f"ERROR preparing advanced risk variables: {type(exc).__name__}: {exc}")
    raise

# ---- cell 19
# 9a_risk_centrality.png - Geolocate links ranked by hazard-weighted exposure centrality.
try:
    risk_gdf = road_exposure_gdf.copy()

    ranking = (
        risk_gdf
        .groupby("poly_lid", as_index=False)
        .agg(
            total_exposure=("counter", "sum"),
            hazard_weighted_exposure=("hazard_weighted_exposure", "sum"),
            mean_hazard_factor=("hazard_factor", "mean"),
            geometry=("geometry", "first"),
        )
    )

    total_hazard = ranking["hazard_weighted_exposure"].sum()
    if total_hazard <= 0:
        raise ValueError("Total hazard-weighted exposure is zero.")

    ranking["risk_centrality"] = ranking["hazard_weighted_exposure"] / total_hazard
    ranking = ranking.sort_values("risk_centrality", ascending=False)

    top = ranking.head(20).copy()
    top["poly_lid_label"] = top["poly_lid"].astype(str)

    ranking_gdf = gpd.GeoDataFrame(
        ranking,
        geometry="geometry",
        crs=road_exposure_gdf.crs,
    )
    map_gdf = ranking_gdf.to_crs(epsg=3857)
    top_gdf = ranking_gdf.head(20).to_crs(epsg=3857)
    label_gdf = ranking_gdf.head(6).to_crs(epsg=3857)

    fig, (ax_map, ax_rank) = plt.subplots(
        1,
        2,
        figsize=(15.2, 7.0),
        gridspec_kw={"width_ratios": [1.45, 0.95]},
        constrained_layout=True,
    )

    map_gdf.plot(
        ax=ax_map,
        color=PALETTE["roads_minor"],
        linewidth=0.45,
        alpha=0.34,
        zorder=1,
    )
    top_gdf.plot(
        ax=ax_map,
        column="risk_centrality",
        cmap=risk_cmap,
        linewidth=3.2,
        alpha=0.96,
        legend=True,
        zorder=4,
        legend_kwds={
            "label": "Risk centrality",
            "shrink": 0.70,
        },
    )

    if cx is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                cx.add_basemap(
                    ax_map,
                    source=cx.providers.CartoDB.Positron,
                    attribution=False,
                    alpha=0.65,
                    zorder=0,
                )
            except Exception as exc:
                print(f"Basemap unavailable: {exc}")

    for _, row in label_gdf.iterrows():
        point = row.geometry.interpolate(0.5, normalized=True)
        ax_map.annotate(
            str(row["poly_lid"]),
            xy=(point.x, point.y),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=14,
            fontweight="bold",
            color=PALETTE["text"],
            bbox={"boxstyle": "round,pad=0.22", "fc": "white", "ec": "#DDDDDD", "alpha": 0.92},
            zorder=5,
        )

    top10 = top.head(10).copy()
    ax_rank.barh(
        top10["poly_lid_label"][::-1],
        100 * top10["risk_centrality"][::-1],
        color=ACCIDENT_COLORS["risk"],
        edgecolor="white",
        linewidth=1.0,
        zorder=3,
    )
    ax_rank.set_xlabel("Share of hazard-weighted exposure (%)", fontsize=18)
    ax_rank.set_ylabel("Polyline ID", fontsize=18)
    ax_rank.tick_params(axis="both", labelsize=14)
    ax_rank.grid(axis="x", color=PALETTE["grid"], alpha=0.7, zorder=0)
    ax_rank.set_axisbelow(True)
    ax_rank.spines["top"].set_visible(False)
    ax_rank.spines["right"].set_visible(False)

    ax_map.set_axis_off()

    if fig.axes:
        for extra_ax in fig.axes:
            if extra_ax not in (ax_map, ax_rank):
                extra_ax.tick_params(labelsize=13)
                extra_ax.set_ylabel("Risk centrality", fontsize=15, fontweight="bold")

    save_fig_local(fig, "9a_risk_centrality")

    ranking.to_csv(OUTPUT_DIR / "risk_centrality_ranking.csv", index=False)
    print(f"Saved: {OUTPUT_DIR / 'risk_centrality_ranking.csv'}")
    display(ranking.head(20)[["poly_lid", "total_exposure", "hazard_weighted_exposure", "risk_centrality"]])

except Exception as exc:
    print(f"ERROR 9a_risk_centrality: {type(exc).__name__}: {exc}")
    raise

# ---- cell 20
# 9b_exposure_elasticity.png - Scaling between simulated exposure and accident intensity by hour.
try:
    elasticity_df = hourly_compare.copy()
    elasticity_df = elasticity_df.replace([np.inf, -np.inf], np.nan)

    elasticity_df = elasticity_df.dropna(
        subset=["accident_share", "weekday_exposure_share"]
    )

    elasticity_df = elasticity_df[
        (elasticity_df["accident_share"] > 0)
        & (elasticity_df["weekday_exposure_share"] > 0)
    ].copy()

    if len(elasticity_df) < 3:
        raise ValueError("Not enough valid hourly points for a log-log fit.")

    x_log = np.log(elasticity_df["weekday_exposure_share"].values)
    y_log = np.log(elasticity_df["accident_share"].values)

    slope, intercept = np.polyfit(x_log, y_log, 1)
    r = np.corrcoef(x_log, y_log)[0, 1]
    r2 = r**2

    fig, ax = plt.subplots(figsize=(8.5, 7.0), constrained_layout=True)

    ax.scatter(
        elasticity_df["weekday_exposure_share"],
        elasticity_df["accident_share"],
        s=95,
        color=ACCIDENT_COLORS["incidents"],
        edgecolor="white",
        linewidth=0.8,
        alpha=0.92,
        zorder=3,
    )

    xx = np.geomspace(
        elasticity_df["weekday_exposure_share"].min(),
        elasticity_df["weekday_exposure_share"].max(),
        200,
    )
    yy = np.exp(intercept) * xx**slope

    ax.plot(
        xx,
        yy,
        color=PALETTE["text"],
        linewidth=2.3,
        linestyle="--",
        label=rf"$I \sim E^{{{slope:.2f}}}$",
        zorder=4,
    )

    for _, row in elasticity_df.iterrows():
        ax.text(
            row["weekday_exposure_share"],
            row["accident_share"],
            f"{int(row['hour']):02d}",
            fontsize=12,
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            zorder=5,
        )

    ax.set_xscale("log")
    ax.set_yscale("log")

    from matplotlib.ticker import LogLocator, FuncFormatter
    _log_fmt = FuncFormatter(lambda v, _: f"{v:.3g}")
    for _axis in (ax.xaxis, ax.yaxis):
        _axis.set_major_formatter(_log_fmt)
        _axis.set_minor_locator(LogLocator(base=10.0, subs=[2, 3, 5], numticks=30))
        _axis.set_minor_formatter(_log_fmt)
    ax.tick_params(axis="both", which="minor", labelsize=10)
    ax.tick_params(axis="both", which="major", labelsize=13)

    ax.set_xlabel("Simulated weekday exposure share", fontsize=18)
    ax.set_ylabel("Accident share", fontsize=18)

    ax.text(
        0.04,
        0.96,
        rf"Elasticity $\alpha$ = {slope:.2f}" + "\n" + rf"$R^2$ = {r2:.2f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=18,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            edgecolor="#DDDDDD",
            alpha=0.92,
        ),
    )

    ax.grid(True, color=PALETTE["grid"], alpha=0.65)
    ax.legend(loc="lower right", fontsize=17)

    save_fig_local(fig, "9b_exposure_elasticity")

    print(f"Elasticity alpha = {slope:.3f}; R2 = {r2:.3f}")

except Exception as exc:
    print(f"ERROR 9b_exposure_elasticity: {type(exc).__name__}: {exc}")
    raise

# ---- cell 21
# 9c_hourly_risk_clusters.png - Cluster hours by exposure-normalized risk profile.
try:
    from scipy.cluster.hierarchy import linkage, fcluster

    cluster_df = hourly_compare.copy()

    candidate_features = [
        "accident_share",
        "weekday_exposure_share",
        "risk_weekday",
    ]

    # Use holiday features only if the holiday simulation exists.
    if "holiday_exposure_share" in cluster_df.columns and cluster_df["holiday_exposure_share"].notna().any():
        candidate_features.append("holiday_exposure_share")
    if "risk_holiday" in cluster_df.columns and cluster_df["risk_holiday"].notna().any():
        candidate_features.append("risk_holiday")

    features = cluster_df[candidate_features].replace([np.inf, -np.inf], np.nan)
    features = features.fillna(features.median(numeric_only=True))

    X = features.values.astype(float)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    X = (X - X.mean(axis=0)) / std

    Z = linkage(X, method="ward")

    n_clusters = 3
    cluster_df["risk_cluster"] = fcluster(Z, n_clusters, criterion="maxclust")

    cluster_palette = {
        1: ACCIDENT_COLORS["incidents"],
        2: ACCIDENT_COLORS["weekday"],
        3: ACCIDENT_COLORS["holiday"],
    }

    fig, ax = plt.subplots(figsize=(11.5, 6.5), constrained_layout=True)

    for cluster, group in cluster_df.groupby("risk_cluster"):
        color = cluster_palette.get(int(cluster), PALETTE["text"])

        ax.scatter(
            group["hour"],
            group["risk_weekday"],
            s=125,
            color=color,
            edgecolor="white",
            linewidth=1.1,
            label=f"Risk cluster {int(cluster)}",
            zorder=4,
        )

        ax.plot(
            group["hour"],
            group["risk_weekday"],
            color=color,
            linewidth=2.8,
            alpha=0.70,
            zorder=3,
        )

    ax.axhline(
        1.0,
        color=PALETTE["text"],
        linestyle="--",
        linewidth=1.8,
        alpha=0.75,
        label="Daily average risk",
    )

    ax.set_xlabel("Time", fontsize=18)
    ax.set_ylabel("Relative risk index", fontsize=18)
    ax.set_xticks(HOUR_TICKS)
    ax.set_xticklabels([HOUR_LABELS[h] for h in HOUR_TICKS], rotation=45, ha="right")
    ax.grid(True, axis="y", color=PALETTE["grid"], alpha=0.7)
    ax.legend(loc="upper right", fontsize=17)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    save_fig_local(fig, "9c_hourly_risk_clusters")

    cluster_df.to_csv(OUTPUT_DIR / "hourly_risk_clusters.csv", index=False)
    print(f"Saved: {OUTPUT_DIR / 'hourly_risk_clusters.csv'}")
    display(cluster_df[["hour", "risk_cluster", "risk_weekday", "risk_holiday"]])

except Exception as exc:
    print(f"ERROR 9c_hourly_risk_clusters: {type(exc).__name__}: {exc}")
    raise

# ---- cell 22
# 9d_high_risk_anomaly_map.png - Map links with high hazard relative to exposure.
try:
    anomaly_gdf = road_exposure_gdf.copy()

    link_stats = (
        anomaly_gdf
        .groupby("poly_lid", as_index=False)
        .agg(
            exposure=("counter", "sum"),
            hazard=("hazard_weighted_exposure", "sum"),
            mean_hazard_factor=("hazard_factor", "mean"),
            geometry=("geometry", "first"),
        )
    )

    link_stats = gpd.GeoDataFrame(
        link_stats,
        geometry="geometry",
        crs=road_exposure_gdf.crs,
    )

    link_stats = link_stats[link_stats["exposure"] > 0].copy()

    link_stats["exposure_rank"] = link_stats["exposure"].rank(pct=True)
    link_stats["hazard_rank"] = link_stats["hazard"].rank(pct=True)
    link_stats["risk_anomaly"] = link_stats["hazard_rank"] - link_stats["exposure_rank"]

    # High anomaly = much higher hazard rank than exposure rank.
    high_anomaly = link_stats[
        link_stats["risk_anomaly"] >= link_stats["risk_anomaly"].quantile(0.95)
    ].copy()

    map_gdf = link_stats.to_crs(epsg=3857)
    high_anomaly = high_anomaly.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(13.0, 7.2), constrained_layout=True)

    map_gdf.plot(
        ax=ax,
        color=PALETTE["roads_minor"],
        linewidth=0.55,
        alpha=0.38,
        zorder=2,
    )

    if not high_anomaly.empty:
        high_anomaly.plot(
            ax=ax,
            column="risk_anomaly",
            cmap="Reds",
            linewidth=3.4,
            alpha=0.96,
            legend=True,
            zorder=4,
            legend_kwds={
                "label": "Hazard rank - exposure rank",
                "shrink": 0.72,
            },
        )

    if cx is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                cx.add_basemap(
                    ax,
                    source=cx.providers.CartoDB.Positron,
                    attribution=False,
                    alpha=0.65,
                    zorder=0,
                )
            except Exception as exc:
                print(f"Basemap unavailable: {exc}")

    ax.set_axis_off()

    save_fig_local(fig, "9d_high_risk_anomaly_map")

    link_stats.to_csv(OUTPUT_DIR / "high_risk_anomaly_links.csv", index=False)
    print(f"Saved: {OUTPUT_DIR / 'high_risk_anomaly_links.csv'}")

    display(
        link_stats
        .sort_values("risk_anomaly", ascending=False)
        .head(20)
        [["poly_lid", "exposure", "hazard", "mean_hazard_factor", "risk_anomaly"]]
    )

except Exception as exc:
    print(f"ERROR 9d_high_risk_anomaly_map: {type(exc).__name__}: {exc}")
    raise


# ---- bootstrap of the exposure exponent (24 hourly points, resampled with replacement)
import json
rng = np.random.default_rng(12345)
xl = np.log(elasticity_df["weekday_exposure_share"].values)
yl = np.log(elasticity_df["accident_share"].values)
boots = []
for _ in range(10000):
    idx = rng.integers(0, len(xl), len(xl))
    if np.unique(xl[idx]).size < 3:
        continue
    boots.append(np.polyfit(xl[idx], yl[idx], 1)[0])
boots = np.array(boots)
res = {"n_points": int(len(xl)), "alpha": float(slope), "r2": float(r2),
       "alpha_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
       "n_boot": int(len(boots)),
       "risk_weekday": {int(h): float(v) for h, v in zip(hourly_compare.hour, hourly_compare.risk_weekday)},
       "accident_share": {int(h): float(v) for h, v in zip(hourly_compare.hour, hourly_compare.accident_share)},
       "weekday_exposure_share": {int(h): float(v) for h, v in zip(hourly_compare.hour, hourly_compare.weekday_exposure_share)},
       "n_weekday_runs": int(len(list(WEEKDAY_DIR.glob("2*.csv")))), "n_weekend_runs": int(len(list(HOLIDAY_DIR.glob("2*.csv")))),
       "yearly": acc["hourly"].groupby("year")["incidents"].sum().to_dict()}
out = ROOT / "article/results/revision"; out.mkdir(parents=True, exist_ok=True)
(out / "incident_summary.json").write_text(json.dumps(res, indent=2, default=float))
print(res["alpha"], res["alpha_ci95"], res["n_points"])
