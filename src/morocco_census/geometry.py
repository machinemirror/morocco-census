"""Commune geometry: one point per commune from open gazetteers -> communes_points.gpkg; HCP's commune boundaries,
dissolved to the map units -> hcp_communes_2024.gpkg + queen weights.

Points come only from openly licensed gazetteers:
  1. GeoNames (CC BY 4.0), matched by normalized name. Commune-level admin features (ADM3/ADM4)
     rank before populated places, primary names before alternate names, and candidates must lie
     near their province's anchor: the median of units with a single unambiguous candidate. A
     province-constrained fuzzy match, checked word by word, catches spelling variants.
  2. Wikidata (CC0) for units GeoNames misses: a unique name + province match whose recorded
     coordinates agree with one another and fall near the province anchor.
Where both gazetteers place a unit, their distance is written to points_crosscheck.csv. When they
disagree by more than CROSSCHECK_FLAG_KM, catalog/seed_review.csv records a reviewed choice of
source; without a review, the point nearer the province anchor is used. catalog/seed_names.csv gives the
gazetteer spelling of communes whose census name matches nothing (Mtalssa is Metalsa). Arrondissements collapse to
one unit per city. The Natural Earth outline bounds the gazetteer search and draws the map's coast and neighbours.
"""

import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from libpysal import weights as psw
from libpysal.io import open as psopen
from rapidfuzz import fuzz, process
from shapely.geometry import Point

from .config import (
    GEOMETRY,
    P_BOUNDARY,
    P_CONTEXT,
    P_CROSSCHECK,
    P_CROSSWALK,
    P_DUP_POINTS,
    P_HCP_GAL,
    P_HCP_GPKG,
    P_POINTS,
    P_SEEDS,
    P_UNMATCHED,
    R_GEONAMES,
    R_HCP_BOUNDARIES,
    R_NATURAL_EARTH,
    R_WIKIDATA,
    SEED_NAMES,
    SEED_REVIEW,
)
from .crosswalk import norm, norm_app

UTM = 32629
HCP_SIMPLIFY_M = 100
HCP_GAP_M = 50  # the per-province files leave hairline gaps along province borders
KM_PER_DEG = 111.0
MIN_RADIUS_DEG = 0.5  # ~55 km: floor on the province search radius
MAX_RADIUS_DEG = 3.0  # ~330 km: one stray first-pass match must not open a whole region
CROSSCHECK_FLAG_KM = 25

GEONAMES_COLS = [
    "geonameid",
    "name",
    "asciiname",
    "altnames",
    "lat",
    "lon",
    "fclass",
    "fcode",
    "cc",
    "cc2",
    "adm1",
    "adm2",
    "adm3",
    "adm4",
    "pop",
    "elev",
    "dem",
    "tz",
    "mod",
]


def boundary() -> gpd.GeoDataFrame:
    ne = gpd.read_file(f"zip://{R_NATURAL_EARTH}")
    b = gpd.GeoDataFrame(geometry=[ne[ne.ADM0_A3.isin(["MAR", "SAH"])].union_all()], crs=4326)
    b.to_file(P_BOUNDARY, driver="GPKG")
    # neighbouring land for map context, so the site needs no third-party basemap
    ctx = ne[~ne.ADM0_A3.isin(["MAR", "SAH"])].clip((-24, 16, 6, 42))
    ctx[["ADM0_A3", "NAME", "geometry"]].to_file(P_CONTEXT, driver="GPKG")
    return b


def units() -> pd.DataFrame:
    cw = pd.read_csv(P_CROSSWALK)
    cw["is_arr"] = cw.name14.str.contains(r"\(Arrond", na=False)
    cw["unit"] = np.where(cw.is_arr, cw.code14.str.extract(r"^(\d+\.\d+\.\d+\.)")[0], cw.code14)
    u = cw.drop_duplicates("unit").copy()
    alias = pd.read_csv(SEED_NAMES).set_index("unit").gazetteer_name
    u["match_name"] = u.unit.map(alias).fillna(u.name14)
    u["k_name"] = u.match_name.str.replace(r"\s*\((Mun|Arrond)\.\)", "", regex=True).map(norm)
    u["k_prov"] = u.prov14.map(norm)
    u["is_mun"] = u.name14.str.contains(r"\((?:Mun|Arrond)", na=False)
    return u


def words(s: str) -> list[str]:
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(s))  # "Sidi YahyaBni Zeroual"
    s = re.sub(r"\s*\((Mun|Arrond)\.\)", "", s)
    s = norm_app(s)
    for a, b in (("ouled", "oulad"), ("sid", "sidi"), ("si", "sidi"), ("my", "moulay"), ("bni", "beni")):
        s = re.sub(rf"\b{a}\b", b, s)
    return s.split()


def words_agree(census: str, gazetteer: str) -> bool:
    # every word of the census name needs a close counterpart; GeoNames sometimes truncates the last word
    g = words(gazetteer)
    return all(
        any(fuzz.ratio(w, x) >= 75 or (x == g[-1] and len(x) >= 3 and w.startswith(x)) for x in g)
        for w in words(census)
        if len(w) > 2
    )


def load_geonames(outline) -> pd.DataFrame:
    gn = pd.concat(
        [pd.read_csv(f, sep="\t", names=GEONAMES_COLS, dtype=str, keep_default_na=False) for f in R_GEONAMES]
    )
    gn = gn[gn.fclass.isin(["P", "A"])]
    # cercles, pachaliks and higher units share names with communes but are not communes
    gn = gn[~gn["name"].str.match(r"(?i)cercle|pachalik|province|prefecture|region")]
    gn["lat"] = gn.lat.astype(float)
    gn["lon"] = gn.lon.astype(float)
    inside = outline.buffer(0.05)
    gn = gn[[inside.contains(Point(x, y)) for x, y in zip(gn.lon, gn.lat)]].reset_index(drop=True)
    gn["tier"] = gn.fcode.map(lambda c: 0 if c in ("ADM3", "ADM4") else 1 if c.startswith("PPL") else 2)
    gn["key"] = ["".join(words(n)) for n in gn["name"]]
    return gn


def match_geonames(u: pd.DataFrame, gn: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    primary: dict[str, set[int]] = {}
    any_name: dict[str, set[int]] = {}
    for i, r in gn.iterrows():
        names = {norm(r["name"]), norm(r.asciiname)}
        for k in names:
            primary.setdefault(k, set()).add(i)
        for k in names | {norm(a) for a in r.altnames.split(",") if a}:
            if len(k) >= 4:
                any_name.setdefault(k, set()).add(i)

    def candidates(k: str) -> pd.DataFrame:
        c = gn.loc[sorted(any_name.get(k, set()))].copy()
        c["rank"] = 2 * c.tier + [0 if i in primary.get(k, set()) else 1 for i in c.index]
        return c

    cands = {r.unit: candidates(r.k_name) for r in u.itertuples()}
    first = []
    for r in u.itertuples():
        c = cands[r.unit]
        if len(c) and c["rank"].min() < 4 and (c["rank"] == c["rank"].min()).sum() == 1:
            b = c.loc[c["rank"].idxmin()]
            first.append((r.prov14, b.lon, b.lat))
    f = pd.DataFrame(first, columns=["prov14", "lon", "lat"])
    anchor = f.groupby("prov14")[["lon", "lat"]].median()
    f = f.join(anchor, on="prov14", rsuffix="_a")
    f["d"] = np.hypot(f.lon - f.lon_a, f.lat - f.lat_a)
    radius = (3 * f.groupby("prov14").d.quantile(0.75)).clip(MIN_RADIUS_DEG, MAX_RADIUS_DEG)

    def near(c: pd.DataFrame, prov: str) -> pd.DataFrame:
        if prov not in anchor.index:
            return c.assign(d=0.0)
        ax, ay = anchor.loc[prov]
        c = c.assign(d=np.hypot(c.lon - ax, c.lat - ay))
        return c[c.d <= radius.get(prov, MIN_RADIUS_DEG)]

    communes = gn[gn.tier <= 1]
    rows = []
    for r in u.itertuples():
        c = near(cands[r.unit], r.prov14)
        how = "exact"
        if len(c):
            b = c.sort_values(["rank", "d"]).iloc[0]
        elif r.prov14 in anchor.index:
            pool = near(communes, r.prov14)
            if not len(pool):
                continue
            best = process.extract("".join(words(r.match_name)), pool.key.tolist(), scorer=fuzz.ratio, limit=2)
            clear = len(best) == 1 or best[0][1] - best[1][1] >= 5
            b = pool.iloc[best[0][2]]
            if not (best[0][1] >= 88 and clear and words_agree(r.match_name, b["name"])):
                continue
            how = "fuzzy"
        else:
            continue
        rows.append(
            {
                "unit": r.unit,
                "name14": r.name14,
                "prov14": r.prov14,
                "lon": float(b.lon),
                "lat": float(b.lat),
                "pt_src": "geonames",
                "source_id": b.geonameid,
                "feature": b.fcode,
                "source_name": b["name"],
                "match": how,
            }
        )
    return pd.DataFrame(rows), anchor, radius


def load_wikidata() -> pd.DataFrame:
    wd = pd.read_csv(R_WIKIDATA, dtype=str)
    xy = wd.coord.str.extract(r"Point\(([-\d.]+) ([-\d.]+)\)").astype(float)
    wd["lon"], wd["lat"] = xy[0], xy[1]
    wd["qid"] = wd.item.str.rsplit("/", n=1).str[-1]
    g = wd.groupby("qid")
    out = g.agg(label=("label", "first"), fr=("fr", "first"), adm=("admLabel", "first"), lon=("lon", "median"), lat=("lat", "median"))
    # an item with several coordinates is usable only if they agree to within ~15 km
    out["spread"] = np.hypot(g.lon.max() - g.lon.min(), g.lat.max() - g.lat.min())
    out = out[out.spread <= 0.15].reset_index()
    out["k"] = out.label.fillna(out.fr).map(norm)
    out["k_fr"] = out.fr.fillna(out.label).map(norm)
    out["k_prov"] = out.adm.fillna("").str.replace(r"(?i)\b(province|prefecture)\b|\(|\)", "", regex=True).map(norm)
    return out


def match_wikidata(u: pd.DataFrame, wd: pd.DataFrame, anchor: pd.DataFrame, radius: pd.Series) -> pd.DataFrame:
    rows = []
    for r in u.itertuples():
        c = wd[(wd.k == r.k_name) | (wd.k_fr == r.k_name)]
        if not len(c):
            c = wd.loc[[fuzz.ratio(k, r.k_name) >= 88 and words_agree(r.match_name, lab) for k, lab in zip(wd.k, wd.label.fillna(wd.fr))]]
        # Wikidata states each commune's province, so that replaces the anchor-radius test when present
        same_prov = np.array([fuzz.ratio(p, r.k_prov) >= 70 for p in c.k_prov], dtype=bool)
        if r.prov14 in anchor.index:
            ax, ay = anchor.loc[r.prov14]
            near = np.hypot(c.lon - ax, c.lat - ay).to_numpy() <= radius.get(r.prov14, MIN_RADIUS_DEG)
        else:
            near = np.ones(len(c), dtype=bool)
        c = c[same_prov | ((c.k_prov == "").to_numpy() & near)]
        if len(c) != 1:
            continue
        b = c.iloc[0]
        rows.append(
            {
                "unit": r.unit,
                "name14": r.name14,
                "prov14": r.prov14,
                "lon": float(b.lon),
                "lat": float(b.lat),
                "pt_src": "wikidata",
                "source_id": b.qid,
                "feature": "",
                "source_name": b.label if isinstance(b.label, str) else b.fr,
                "match": "exact" if r.k_name in (b.k, b.k_fr) else "fuzzy",
            }
        )
    return pd.DataFrame(rows)


def km(lon1, lat1, lon2, lat2) -> np.ndarray:
    a = gpd.GeoSeries(gpd.points_from_xy(lon1, lat1), crs=4326).to_crs(UTM)
    b = gpd.GeoSeries(gpd.points_from_xy(lon2, lat2), crs=4326).to_crs(UTM)
    return (a.distance(b) / 1000).round(2).to_numpy()


def place(seeds: pd.DataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    seeds = seeds.copy()
    # homonym urban/rural pairs matched to one gazetteer feature are distinct communes: offset later shares ~2 km east
    shared = seeds.groupby("source_id").cumcount()
    seeds.loc[shared > 0, "lon"] = seeds.lon + 0.02 * shared
    key = seeds.lon.round(3).astype(str) + "|" + seeds.lat.round(3).astype(str)
    dup = key.duplicated(keep="first")
    pts = gpd.GeoDataFrame(
        seeds.loc[~dup, ["unit", "name14", "prov14", "code24", "label04", "pt_src"]],
        geometry=[Point(xy) for xy in zip(seeds.lon[~dup], seeds.lat[~dup])],
        crs=4326,
    )
    return pts, seeds.loc[dup, ["unit", "name14", "prov14"]]


def main(outline_path=None) -> gpd.GeoDataFrame:
    GEOMETRY.mkdir(parents=True, exist_ok=True)
    outline = (gpd.read_file(outline_path) if outline_path else boundary()).to_crs(4326).geometry.iloc[0]
    u = units()
    gn_seeds, anchor, radius = match_geonames(u, load_geonames(outline))
    print(f"GeoNames seed points: {len(gn_seeds)}/{len(u)} units ({(gn_seeds.match == 'fuzzy').sum()} fuzzy)")
    wd_all = match_wikidata(u, load_wikidata(), anchor, radius)

    both = gn_seeds.merge(wd_all, on=["unit", "name14", "prov14"], suffixes=("_gn", "_wd")).join(anchor, on="prov14")
    both["km"] = km(both.lon_gn, both.lat_gn, both.lon_wd, both.lat_wd)
    both["flag"] = both.km > CROSSCHECK_FLAG_KM
    review = pd.read_csv(SEED_REVIEW).set_index("unit").source
    nearer = np.where(
        km(both.lon_gn, both.lat_gn, both.lon, both.lat) <= km(both.lon_wd, both.lat_wd, both.lon, both.lat),
        "geonames",
        "wikidata",
    )
    both["chosen"] = np.where(~both.flag, "geonames", both.unit.map(review).fillna(pd.Series(nearer, index=both.index)))
    both["decided_by"] = np.where(~both.flag, "agree", np.where(both.unit.isin(review.index), "review", "anchor"))
    both[["unit", "name14", "prov14", "source_id_gn", "source_id_wd", "km", "flag", "chosen", "decided_by"]].rename(
        columns={"source_id_gn": "geonameid", "source_id_wd": "qid"}
    ).to_csv(P_CROSSCHECK, index=False)
    print(
        f"cross-check: {len(both)} units in both gazetteers, median {both.km.median():.1f} km, "
        f"{both.flag.sum()} over {CROSSCHECK_FLAG_KM} km ({(both.decided_by == 'review').sum()} reviewed)"
    )

    use_wd = set(both.unit[both.chosen == "wikidata"]) | (set(wd_all.unit) - set(gn_seeds.unit))
    seeds = pd.concat([gn_seeds[~gn_seeds.unit.isin(use_wd)], wd_all[wd_all.unit.isin(use_wd)]], ignore_index=True)
    print(f"seed points: {len(seeds)}/{len(u)} ({(seeds.pt_src == 'wikidata').sum()} from Wikidata)")
    seeds = seeds.merge(u[["unit", "code24", "label04"]], on="unit")
    seeds.drop(columns=["code24", "label04"]).to_csv(P_SEEDS, index=False)
    u[~u.unit.isin(set(seeds.unit))][["unit", "name14", "prov14"]].to_csv(P_UNMATCHED, index=False)

    pts, dups = place(seeds)
    dups.to_csv(P_DUP_POINTS, index=False)
    P_POINTS.unlink(missing_ok=True)
    pts.to_file(P_POINTS, layer="points", driver="GPKG")
    print(f"points: {len(pts)} ({len(dups)} duplicate-coordinate units dropped)")
    return pts


def hcp_boundaries() -> gpd.GeoDataFrame:
    """HCP's commune polygons (RGPH 2024 platform, 2014 codes), dissolved to the map units (urban centres into their rural commune,
    arrondissements into their city). Sebta and Melilla have no census data and are dropped."""
    frames = [gpd.read_file(f) for f in sorted(R_HCP_BOUNDARIES.glob("*.geojson"))]
    # the files declare CRS84 but carry Web Mercator metres
    g = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True)).set_crs(3857, allow_override=True)
    iso = g.ISO.str.removeprefix("MA-").str.split("-", expand=True)
    g["code14"] = iso[0] + "." + iso[1] + "." + iso[2].str[:2] + "." + iso[2].str[2:4] + "."
    cw = pd.read_csv(P_CROSSWALK)
    arr = cw.name14.str.contains(r"\(Arrond", na=False)
    cw["unit"] = np.where(arr, cw.code14.str.extract(r"^(\d+\.\d+\.\d+\.)")[0], cw.code14)
    g = g.merge(cw[["code14", "unit"]], on="code14", how="inner")
    g["geometry"] = g.geometry.make_valid().buffer(0)  # buffer(0) drops the stray lines make_valid can leave
    out = g.dissolve("unit", as_index=False)[["unit", "geometry"]].to_crs(UTM)
    out["geometry"] = out.geometry.buffer(0)
    # coverage simplification keeps shared edges shared; the site simplifies further, to SIMPLIFY_M
    out["geometry"] = shapely.coverage_simplify(np.asarray(out.geometry.values), HCP_SIMPLIFY_M)
    out = out.to_crs(4326)
    out["geometry"] = out.geometry.buffer(0)  # reprojection can collapse a sliver ring to too few points
    P_HCP_GPKG.unlink(missing_ok=True)
    out.to_file(P_HCP_GPKG, layer="communes", driver="GPKG")
    # queen contiguity, tolerant of those gaps (strict queen leaves 12 communes without neighbours)
    w = psw.fuzzy_contiguity(out.to_crs(UTM), buffering=True, buffer=HCP_GAP_M)
    f = psopen(str(P_HCP_GAL), "w")
    f.write(w)
    f.close()
    print(
        f"HCP boundaries: {len(frames)} provinces, {len(g)} polygons -> {len(out)} map units; "
        f"weights mean {pd.Series(w.cardinalities).mean():.2f} neighbours, {len(w.islands)} islands"
    )
    return out
