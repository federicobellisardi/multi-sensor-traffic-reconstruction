#!/usr/bin/env python3
"""Assemble the multi-panel manuscript figures from the single panels in article/tex/images.

Each row is scaled to a common height and the composite is resized to WIDTH pixels,
which is about 300 dpi at the text width of the journal template (17.4 cm). Figures
dominated by maps are written as high-quality JPEG to keep the PDF small.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
IMG = ROOT / "article/tex/images"
INC = ROOT / "article/ipynb/figures_incident_risk"
WIDTH = 2400
GAP = 30
FONT = None
for cand in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
    if Path(cand).exists():
        FONT = cand
        break


CROP_TOP = {"1c_coils_mapping.png": 0.105}  # drop the title left in the stand-alone panel


def load(p):
    im = Image.open(p).convert("RGB")
    f = CROP_TOP.get(Path(p).name)
    if f:
        im = im.crop((0, round(im.height * f), im.width, im.height))
    pad = round(0.09 * im.height)  # white band that hosts the panel letter
    out = Image.new("RGB", (im.width, im.height + pad), "white")
    out.paste(im, (0, pad))
    return out


def row(images, letters):
    h = min(im.height for im in images)
    scaled = [im.resize((round(im.width * h / im.height), h), Image.LANCZOS) for im in images]
    w = sum(im.width for im in scaled) + GAP * (len(scaled) - 1)
    canvas = Image.new("RGB", (w, h), "white")
    x = 0
    pos = []
    for im in scaled:
        canvas.paste(im, (x, 0))
        pos.append(x)
        x += im.width + GAP
    return canvas, list(zip(pos, letters))


def compose(rows, out, jpeg=False, extra_letters=()):
    built = [row([load(p) for p in r], l) for r, l in rows]
    scaled = []
    for canvas, letters in built:
        f = WIDTH / canvas.width
        scaled.append((canvas.resize((WIDTH, round(canvas.height * f)), Image.LANCZOS),
                       [(round(x * f), l) for x, l in letters]))
    H = sum(c.height for c, _ in scaled) + GAP * (len(scaled) - 1)
    fig = Image.new("RGB", (WIDTH, H), "white")
    draw = ImageDraw.Draw(fig)
    font = ImageFont.truetype(FONT, 64) if FONT else ImageFont.load_default()
    y = 0
    for canvas, letters in scaled:
        fig.paste(canvas, (0, y))
        for x, l in letters:
            if l:
                draw.text((x + 6, y + 4), l, fill="black", font=font)
        y += canvas.height + GAP
    for (fx, fy, l) in extra_letters:
        draw.text((round(fx * WIDTH), round(fy * H)), l, fill="black", font=font)
    if jpeg:
        fig.save(IMG / f"{out}.jpg", quality=90, dpi=(300, 300), optimize=True)
    else:
        fig.save(IMG / f"{out}.png", dpi=(300, 300), optimize=True)
    print(out, fig.size)


def panel_d_with_inset():
    """Coil-282 profile with the location map as an inset (top-left corner)."""
    prof = load(IMG / "1d_coil_profile.png")
    loc = load(IMG / "coil_282_location.png")
    s = round(prof.height * 0.40)
    loc = loc.resize((s, s), Image.LANCZOS)
    x0, y0 = round(prof.width * 0.13), round(prof.height * 0.04)
    d = ImageDraw.Draw(prof)
    prof.paste(loc, (x0, y0))
    d.rectangle([x0, y0, x0 + s, y0 + s], outline="#888888", width=4)
    out = IMG / "1d_coil_profile_inset.png"
    prof.save(out)
    return out


if __name__ == "__main__":
    compose([((IMG / "1a_map_study_area.png", IMG / "1b_od_demand.png"), "ab"),
             ((IMG / "1c_coils_mapping.png", panel_d_with_inset()), "cd")], "fig1", jpeg=True)
    compose([((IMG / "4_poly_flow.png", IMG / "5_simulated_daily_flux_map.png"), "ab")], "fig3", jpeg=True)
    compose([((IMG / "6a_viasat_coverage_2020.png", IMG / "6b_penetration_statistics_2020.png", IMG / "6c_cluster_2020.png"), "abc"),
             ((IMG / "6a_viasat_coverage_2021.png", IMG / "6b_penetration_statistics_2021.png", IMG / "6c_cluster_2021.png"), "def")],
            "fig4", jpeg=True)
    compose([((IMG / "7a_dendrogram.png", IMG / "7b_dendrogram_geoloc.png"), "ab")], "fig5")
    compose([((IMG / "8a_cluster_black.png", IMG / "8c_cluster_red.png"), "ab"),
             ((IMG / "8b_cluster_blue.png", IMG / "8d_representative_polylines_location.png"), "cd")], "fig6")
    compose([((INC / "8b_hourly_accidents_vs_exposure.png", INC / "8c_exposure_normalized_hourly_risk.png"), "ab"),
             ((INC / "9c_hourly_risk_clusters.png", INC / "9b_exposure_elasticity.png"), "cd")], "fig7")
    compose([((INC / "8e_hazard_weighted_exposure_map.png", INC / "8f_weekday_holiday_hazard_difference.png"), "ab"),
             ((INC / "9a_risk_centrality.png", INC / "9d_high_risk_anomaly_map.png"), "ce")], "fig8", jpeg=True,
            extra_letters=[(0.30, 0.545, "d")])
