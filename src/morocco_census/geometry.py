"""Commune geometry: HCP's commune boundaries, dissolved to the map units -> hcp_communes_2024.gpkg + queen weights;
then one point per map unit, inside its polygon -> communes_points.gpkg.

Gazetteer matches come from openly licensed sources:
  1. GeoNames (CC BY 4.0), matched by normalized name. Commune-level admin features (ADM3/ADM4)
     rank before populated places, primary names before alternate names, and candidates must lie
     near their province's anchor: the median of units with a single unambiguous candidate. A
     province-constrained fuzzy match, checked word by word, catches spelling variants.
  2. Wikidata (CC0) commune items: a unique name + province match whose recorded coordinates agree
     with one another and fall near the province anchor.
Where both gazetteers place a unit, their distance is written to points_crosscheck.csv. When they
disagree by more than CROSSCHECK_FLAG_KM, catalog/seed_review.csv records a reviewed choice of
source; without a review, the point nearer the province anchor is used. catalog/seed_names.csv gives the
gazetteer spelling of communes whose census name matches nothing (Mtalssa is Metalsa). Arrondissements collapse to
one unit per city, matched under the city's name.

Each unit's point is then the first of these that lies inside its HCP polygon (resolve): a reviewed choice; the
gazetteer match; a GeoNames populated place inside the polygon that carries the unit's name; the other gazetteer's
point; the match moved just inside, if within SNAP_KM; the polygon's representative point. A municipality's or
city's point is never an admin feature's. check_points states the invariant; `mc geometry` fails when it does not
hold, and so do the tests on the published points. The Natural Earth outline bounds the gazetteer search and draws
the map's coast and neighbours.
"""

import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import shapely.ops
from libpysal import weights as psw
from libpysal.io import open as psopen
from rapidfuzz import fuzz, process
from shapely.geometry import Point

from .config import (
    CITIES,
    GEOMETRY,
    P_BOUNDARY,
    P_CONTEXT,
    P_CROSSCHECK,
    P_CROSSWALK,
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
# populated-place codes a seat may carry, best first; abandoned, historical and destroyed places (PPLQ, PPLH, PPLW,
# PPLCH) are not seats
SEAT_CODES = ("PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPL", "PPLL", "PPLS", "PPLF", "PPLR", "PPLX")
SNAP_KM = 1.0
SNAP_INSET_M = 50
CENTROID_KM = 0.5  # a computed centroid fallback lands on the centroid; Znada, which contains its province's, is 0.7 km away
MIN_NAME_RATIO = 85  # HCP's polygon name against name14; the lowest, Oued L'bour / Ouad L'bour, scores 89
PROVINCE_NN_KM = 150  # the sparsest province (Boujdour) has a commune 145 km from its nearest neighbour

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
    u = cw.drop_duplicates("unit").copy()
    alias = pd.read_csv(SEED_NAMES).set_index("unit").gazetteer_name
    # a city unit is the city, not its first arrondissement
    city = u.unit.map({k: v[0] for k, v in CITIES.items()})
    u["match_name"] = u.unit.map(alias).fillna(city).fillna(u.name14)
    u["k_name"] = u.match_name.str.replace(r"\s*\((Mun|Arrond)\.\)", "", regex=True).map(norm)
    u["k_prov"] = u.prov14.map(norm)
    u["is_mun"] = u.name14.str.contains(r"\((?:Mun|Arrond)", na=False) | city.notna()
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


def review_table() -> pd.DataFrame:
    r = pd.read_csv(SEED_REVIEW, dtype=str, keep_default_na=False).set_index("unit")
    r["max_outside_km"] = pd.to_numeric(r.max_outside_km.replace("", "0"))
    return r


def polygons() -> gpd.GeoDataFrame:
    return gpd.read_file(P_HCP_GPKG).set_index("unit")


def seats_inside(u: pd.DataFrame, gn: pd.DataFrame, polys: gpd.GeoDataFrame) -> dict[str, list[dict]]:
    """Populated places inside each unit's polygon that carry the unit's name, best first."""
    ppl = gn[gn.fcode.isin(SEAT_CODES)]
    ppl = gpd.GeoDataFrame(ppl, geometry=gpd.points_from_xy(ppl.lon, ppl.lat), crs=4326)
    inside = gpd.sjoin(ppl, polys[["geometry"]].reset_index(), predicate="within")
    rank = {c: i for i, c in enumerate(SEAT_CODES)}
    by_unit = {unit: g for unit, g in inside.groupby("unit")}
    out = {}
    for r in u.itertuples():
        g = by_unit.get(r.unit)
        if g is None:
            continue
        key = "".join(words(r.match_name))
        found = []
        for f in g.itertuples():
            names = {norm(f.name), norm(f.asciiname)} | {norm(a) for a in f.altnames.split(",") if a}
            if r.k_name in names or f.key == key:
                how = "exact"
            elif fuzz.ratio(f.key, key) >= 88 and words_agree(r.match_name, f.name):
                how = "fuzzy"
            elif f.key.startswith(key) and words_agree(r.match_name, f.name):
                how = "prefix"  # "Imouzzer des Ida ou Tanane" for Imouzzer
            else:
                continue
            pop = int(f.pop) if f.pop.isdigit() else 0
            order = ("exact", "fuzzy", "prefix").index(how)
            found.append(((order, rank[f.fcode], -pop, int(f.geonameid)), seed(r, f.lon, f.lat, "geonames", f.geonameid, f.fcode, f.name, how)))
        out[r.unit] = [c for _, c in sorted(found, key=lambda x: x[0])]
    return out


def seed(r, lon, lat, src, source_id, feature, source_name, match) -> dict:
    return {
        "unit": r.unit,
        "name14": r.name14,
        "prov14": r.prov14,
        "lon": float(lon),
        "lat": float(lat),
        "pt_src": src,
        "source_id": str(source_id),
        "feature": feature,
        "source_name": source_name,
        "match": match,
    }


def allowed(c: dict, is_mun: bool) -> bool:
    # a municipality's point is its town: a populated place or the Wikidata settlement, never an admin feature's point
    if c["pt_src"] == "geonames":
        return c["feature"] in SEAT_CODES or (not is_mun and c["feature"] in ("ADM3", "ADM4"))
    return True


def snapped(c: dict, poly) -> dict | None:
    """The candidate moved just inside the polygon, if it lies within SNAP_KM of it."""
    p = gpd.GeoSeries([Point(c["lon"], c["lat"]), poly], crs=4326).to_crs(UTM)
    if p.iloc[0].distance(p.iloc[1]) > SNAP_KM * 1000:
        return None
    inner = p.iloc[1].buffer(-SNAP_INSET_M)
    target = inner if not inner.is_empty else p.iloc[1]
    q = gpd.GeoSeries([shapely.ops.nearest_points(target, p.iloc[0])[0]], crs=UTM).to_crs(4326).iloc[0]
    return c | {"lon": q.x, "lat": q.y, "pt_rule": "snapped"}


def resolve(u, gn_seeds, wd_seeds, chosen, seats, polys, review, gn, wd) -> pd.DataFrame:
    """One point per unit, the first candidate inside the unit's HCP polygon:
    reviewed choice > gazetteer match > named populated place in the polygon > the other gazetteer >
    the match snapped inside (within SNAP_KM) > the polygon's representative point."""
    gn_by, wd_by = gn_seeds.set_index("unit"), wd_seeds.set_index("unit")
    gn_id = gn.set_index("geonameid")
    rows = []
    for r in u.itertuples():
        poly = polys.geometry[r.unit]
        rep = poly.representative_point()
        polygon = seed(r, rep.x, rep.y, "hcp_polygon", r.unit, "representative_point", "", "") | {"pt_rule": "polygon"}
        if r.unit in review.index:
            rv = review.loc[r.unit]
            if rv.source == "hcp_polygon":
                c = polygon
            elif rv.source_id and rv.source == "geonames":
                f = gn_id.loc[rv.source_id]
                c = seed(r, f.lon, f.lat, "geonames", rv.source_id, f.fcode, f["name"], "review")
            elif rv.source_id:
                f = wd.set_index("qid").loc[rv.source_id]
                c = seed(r, f.lon, f.lat, "wikidata", rv.source_id, "", f.label, "review")
            else:
                c = (gn_by if rv.source == "geonames" else wd_by).loc[r.unit].to_dict() | {"unit": r.unit}
            rows.append(c | {"pt_rule": "review"})
            continue
        matches = [x.loc[r.unit].to_dict() | {"unit": r.unit} for x in (gn_by, wd_by) if r.unit in x.index]
        matches.sort(key=lambda c: c["pt_src"] != chosen.get(r.unit, "geonames"))
        order = [m | {"pt_rule": "match"} for m in matches[:1]]
        order += [s | {"pt_rule": "seat"} for s in seats.get(r.unit, [])]
        order += [m | {"pt_rule": "crosscheck"} for m in matches[1:]]
        order = [c for c in order if allowed(c, r.is_mun)]
        pick = next((c for c in order if poly.contains(Point(c["lon"], c["lat"]))), None)
        if pick is None:
            pick = next((s for c in order if c["pt_rule"] != "seat" and (s := snapped(c, poly))), polygon)
        rows.append(pick)
    return pd.DataFrame(rows)


def check_points(pts: gpd.GeoDataFrame, polys: gpd.GeoDataFrame, review: pd.DataFrame) -> list[str]:
    """The seed-point invariant; an empty list means every point satisfies it.

    1. one point per map unit, inside the unit's HCP polygon, unless a review in catalog/seed_review.csv allows
       a stated distance outside (max_outside_km);
    2. the point's source is GeoNames (a commune admin feature or a populated place), Wikidata, or the polygon's
       representative point; a municipality's or city's point is never an admin feature's, unless reviewed;
    3. no point within CENTROID_KM of its province's or region's centroid, unless reviewed;
    4. every point within PROVINCE_NN_KM of another point of its province;
    5. no two units share coordinates."""
    bad = []
    pts = pts.set_index("unit")
    if missing := sorted(set(polys.index) - set(pts.index)):
        bad.append(f"units without a point: {', '.join(missing)}")
    if extra := sorted(set(pts.index) - set(polys.index)):
        bad.append(f"points without a polygon: {', '.join(extra)}")
    if pts.index.duplicated().any():
        bad.append(f"units with several points: {', '.join(sorted(set(pts.index[pts.index.duplicated()])))}")
    pts = pts[~pts.index.duplicated() & pts.index.isin(polys.index)]
    tol = review.max_outside_km.reindex(pts.index).fillna(0)
    poly = polys.geometry.reindex(pts.index)
    inside = pts.geometry.within(poly)
    out_km = pts.geometry[~inside].to_crs(UTM).distance(poly[~inside].to_crs(UTM)) / 1000
    for unit, d in out_km.items():
        if d > tol[unit]:
            bad.append(f"{unit} {pts.name14[unit]}: {d:.2f} km outside its HCP polygon")
    is_mun = pts.name14.str.contains(r"\((?:Mun|Arrond)\.\)", na=False) | (pts.index.str.len() == 10)
    for unit, r in pts.iterrows():
        if r.pt_src not in ("geonames", "wikidata", "hcp_polygon"):
            bad.append(f"{unit} {r.name14}: source {r.pt_src}")
        elif r.pt_src == "geonames" and unit not in review.index and not allowed(r.to_dict(), is_mun[unit]):
            bad.append(f"{unit} {r.name14}: GeoNames {r.feature} is not an allowed feature for this unit")
    utm_polys = polys.to_crs(UTM)
    utm = pts.to_crs(UTM)
    for level, n in (("province", 6), ("region", 2)):
        centroid = utm_polys.geometry.groupby(utm_polys.index.str[:n]).agg(lambda g: g.union_all().centroid)
        d = utm.geometry.distance(gpd.GeoSeries(centroid.reindex(utm.index.str[:n]).values, index=utm.index, crs=UTM))
        for unit in d.index[(d < CENTROID_KM * 1000) & ~pts.index.isin(review.index)]:
            bad.append(f"{unit} {pts.name14[unit]}: {d[unit] / 1000:.2f} km from its {level}'s centroid")
    xy = np.c_[utm.geometry.x, utm.geometry.y]
    prov = utm.index.str[:6].to_numpy()
    for i, unit in enumerate(utm.index):
        others = (prov == prov[i]) & (np.arange(len(xy)) != i)
        if others.any() and (nn := np.hypot(*(xy[others] - xy[i]).T).min() / 1000) > PROVINCE_NN_KM:
            bad.append(f"{unit} {pts.name14[unit]}: {nn:.0f} km from the nearest point of its province")
    key = pts.geometry.x.round(5).astype(str) + "|" + pts.geometry.y.round(5).astype(str)
    if key.duplicated().any():
        bad.append(f"units sharing coordinates: {', '.join(sorted(key.index[key.duplicated(keep=False)]))}")
    return bad


def main(outline_path=None) -> gpd.GeoDataFrame:
    GEOMETRY.mkdir(parents=True, exist_ok=True)
    outline = (gpd.read_file(outline_path) if outline_path else boundary()).to_crs(4326).geometry.iloc[0]
    u = units()
    gn = load_geonames(outline)
    gn_seeds, anchor, radius = match_geonames(u, gn)
    print(f"GeoNames seed points: {len(gn_seeds)}/{len(u)} units ({(gn_seeds.match == 'fuzzy').sum()} fuzzy)")
    wd = load_wikidata()
    wd_all = match_wikidata(u, wd, anchor, radius)

    both = gn_seeds.merge(wd_all, on=["unit", "name14", "prov14"], suffixes=("_gn", "_wd")).join(anchor, on="prov14")
    both["km"] = km(both.lon_gn, both.lat_gn, both.lon_wd, both.lat_wd)
    both["flag"] = both.km > CROSSCHECK_FLAG_KM
    review = review_table()
    gazetteer_review = review.source[review.source.isin(["geonames", "wikidata"])]
    nearer = np.where(
        km(both.lon_gn, both.lat_gn, both.lon, both.lat) <= km(both.lon_wd, both.lat_wd, both.lon, both.lat),
        "geonames",
        "wikidata",
    )
    both["chosen"] = np.where(~both.flag, "geonames", both.unit.map(gazetteer_review).fillna(pd.Series(nearer, index=both.index)))
    both["decided_by"] = np.where(~both.flag, "agree", np.where(both.unit.isin(gazetteer_review.index), "review", "anchor"))
    both[["unit", "name14", "prov14", "source_id_gn", "source_id_wd", "km", "flag", "chosen", "decided_by"]].rename(
        columns={"source_id_gn": "geonameid", "source_id_wd": "qid"}
    ).to_csv(P_CROSSCHECK, index=False)
    print(
        f"cross-check: {len(both)} units in both gazetteers, median {both.km.median():.1f} km, "
        f"{both.flag.sum()} over {CROSSCHECK_FLAG_KM} km ({(both.decided_by == 'review').sum()} reviewed)"
    )
    # where the gazetteers agree, the GeoNames match comes first and Wikidata is the cross-check's fallback
    chosen = both.set_index("unit").chosen.to_dict() | {x: "wikidata" for x in set(wd_all.unit) - set(gn_seeds.unit)}
    u[~u.unit.isin(set(gn_seeds.unit) | set(wd_all.unit))][["unit", "name14", "prov14"]].to_csv(P_UNMATCHED, index=False)

    polys = polygons()
    seeds = resolve(u, gn_seeds, wd_all, chosen, seats_inside(u, gn, polys), polys, review, gn, wd)
    seeds = seeds.merge(u[["unit", "code24", "label04"]], on="unit")
    pts = gpd.GeoDataFrame(
        seeds[["unit", "name14", "prov14", "code24", "label04", "pt_src", "pt_rule", "source_id", "feature"]],
        geometry=gpd.points_from_xy(seeds.lon, seeds.lat),
        crs=4326,
    )
    if bad := check_points(pts, polys, review):
        raise SystemExit("seed points violate the invariant:\n  " + "\n  ".join(bad))
    seeds.drop(columns=["code24", "label04"]).round({"lon": 6, "lat": 6}).to_csv(P_SEEDS, index=False)
    P_POINTS.unlink(missing_ok=True)
    pts.to_file(P_POINTS, layer="points", driver="GPKG")
    print(
        f"points: {len(pts)}, all inside their HCP polygon; "
        + ", ".join(f"{k} {v}" for k, v in pts.pt_rule.value_counts().items())
        + "; "
        + ", ".join(f"{k} {v}" for k, v in pts.pt_src.value_counts().items())
    )
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
    assert cw.code14.isin(g.code14).all(), "2014 communes without an HCP polygon"
    g = g.merge(cw[["code14", "unit", "name14"]], on="code14", how="inner")
    # each commune's own feature (milieu 1 or 2) must carry its name, so a polygon can never sit under another code
    own = g[g.ISO.str[-1].isin(["1", "2"])]
    score = [fuzz.ratio("".join(words(a)), "".join(words(b))) for a, b in zip(own.NAME_2, own.name14)]
    # and its milieu digit its status: 1 for a municipality or arrondissement, 2 for a rural commune
    urban = own.name14.str.contains(r"\((?:Mun|Arrond)\.\)") == own.ISO.str.endswith("1")
    if bad := [f"{c} {a} / {b}" for c, a, b, x, m in zip(own.code14, own.NAME_2, own.name14, score, urban) if x < MIN_NAME_RATIO or not m]:
        raise SystemExit("HCP polygons whose name differs from the commune's:\n  " + "\n  ".join(bad))
    assert own.code14.nunique() == len(cw), "2014 communes without their own HCP feature"
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
