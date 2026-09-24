"""Approximate commune geometry -> communes.gpkg (layers thiessen, points) + queen weights.

HCP publishes no commune boundaries, so each commune gets a seed point and a Thiessen (Voronoi)
cell clipped to the national outline. Seed points, in order of preference:
  1. GADM 4.1 level-4 representative points, matched to the crosswalk by normalized
     name + province (GADM provinces are pre-2015, so a fuzzy province tie-break is allowed);
  2. the GeoNames gazetteer for units GADM lacks (post-2015 provinces, Western Sahara),
     disambiguated by distance to the province's centroid of already-placed points.
Arrondissements collapse to one unit per city. The outline is Natural Earth (public domain);
GADM itself is never redistributed, only the derived seed coordinates.
"""

import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from libpysal import weights as psw
from libpysal.io import open as psopen
from rapidfuzz import fuzz
from shapely.geometry import Point

from .config import (
    GEOMETRY,
    I_GADM_CENTROIDS,
    INTERIM,
    P_BOUNDARY,
    P_CONTEXT,
    P_CROSSWALK,
    P_DUP_POINTS,
    P_GAL,
    P_GEOCODED,
    P_GPKG,
    P_UNMATCHED,
    R_GADM_L4,
    R_GEONAMES,
    R_NATURAL_EARTH,
)
from .crosswalk import norm

UTM = 32629


def gadm_centroids() -> pd.DataFrame:
    g = gpd.read_file(R_GADM_L4)
    pt = g.to_crs(UTM).geometry.representative_point().to_crs(4326)
    out = g[["NAME_1", "NAME_2", "NAME_3", "NAME_4", "VARNAME_4", "TYPE_4"]].assign(lon=pt.x, lat=pt.y)
    INTERIM.mkdir(parents=True, exist_ok=True)
    out.to_csv(I_GADM_CENTROIDS, index=False)
    return out


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
    u["k_name"] = u.name14.str.replace(r"\s*\((Mun|Arrond)\.\)", "", regex=True).map(norm)
    u["k_prov"] = u.prov14.map(norm)
    u["is_mun"] = u.name14.str.contains(r"\((?:Mun|Arrond)", na=False)
    return u


def match_gadm(u: pd.DataFrame, g: pd.DataFrame) -> pd.Series:
    g = g.copy()
    g["k_name"] = g.NAME_4.map(norm)
    g["k_prov"] = g.NAME_2.map(norm)
    g = g.reset_index(drop=True)
    g["is_mun"] = g.TYPE_4.astype(str).str.lower() != "commune rural"
    d3 = g.drop_duplicates(["k_name", "k_prov", "is_mun"])
    lut3 = {k: i for i, k in zip(d3.index, d3.set_index(["k_name", "k_prov", "is_mun"]).index)}
    d2 = g.drop_duplicates(["k_name", "k_prov"])
    lut = {k: i for i, k in zip(d2.index, d2.set_index(["k_name", "k_prov"]).index)}
    uniq = g[g.k_name.map(g.k_name.value_counts()) == 1].set_index("k_name")
    spine_counts = u.k_name.value_counts()
    by_name = {}
    for i, r in g.iterrows():
        by_name.setdefault((r.k_name, r.is_mun), []).append(i)
        by_name.setdefault((r.k_name, None), []).append(i)

    def find(row):
        i = lut3.get((row.k_name, row.k_prov, row.is_mun))
        if i is not None:
            return i
        i = lut.get((row.k_name, row.k_prov))
        if i is not None:
            return i
        # among same-name candidates pick the one whose (pre-2015) province is fuzzy-closest, by a clear margin
        for key in ((row.k_name, row.is_mun), (row.k_name, None)):
            cand = by_name.get(key, [])
            if len(cand) == 1 and spine_counts.get(row.k_name, 0) == 1:
                return cand[0]
            if len(cand) > 1:
                scored = sorted(((fuzz.ratio(row.k_prov, g.k_prov[i]), i) for i in cand), reverse=True)
                if scored[0][0] >= 60 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 10):
                    return scored[0][1]
        if row.is_arr and norm(row.prov14) in uniq.index:  # arrondissement city: match on the city name
            return uniq.loc[norm(row.prov14)].name
        if row.k_name in uniq.index and spine_counts.get(row.k_name, 0) == 1:
            return uniq.loc[row.k_name].name
        return None

    gi = u.apply(find, axis=1)
    return gi, g


def place(matched: pd.DataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    matched = matched[matched.lon.notna() & matched.lat.notna()].copy()
    # homonym urban/rural pairs sharing one GADM polygon are distinct communes: offset later shares ~2 km east
    shared = matched.groupby("gi").cumcount()
    matched.loc[shared > 0, "lon"] = matched.lon + 0.02 * shared
    key = matched.lon.round(3).astype(str) + "|" + matched.lat.round(3).astype(str)
    dup = key.duplicated(keep="first")
    pts = gpd.GeoDataFrame(
        matched.loc[~dup, ["unit", "name14", "prov14", "code24", "label04", "pt_src"]],
        geometry=[Point(xy) for xy in zip(matched.lon[~dup], matched.lat[~dup])],
        crs=4326,
    )
    return pts, matched.loc[dup, ["unit", "name14", "prov14"]]


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


def geonames(unmatched: pd.DataFrame, pts: gpd.GeoDataFrame, outline) -> pd.DataFrame:
    gn = pd.concat(
        [pd.read_csv(f, sep="\t", names=GEONAMES_COLS, dtype=str, keep_default_na=False) for f in R_GEONAMES]
    )
    gn["lat"] = gn.lat.astype(float)
    gn["lon"] = gn.lon.astype(float)
    gn = gn[gn.fclass.isin(["P", "A"])].reset_index(drop=True)
    lut: dict[str, list[int]] = {}
    for i, r in gn.iterrows():
        for k in {norm(r["name"]), norm(r.asciiname)} | {norm(a) for a in r.altnames.split(",") if a}:
            if len(k) >= 4:
                lut.setdefault(k, []).append(i)

    anchors = pts.assign(x=pts.geometry.x, y=pts.geometry.y).groupby("prov14")[["x", "y"]].mean()
    inside = outline.buffer(0.05)
    rows = []
    for _, r in unmatched.iterrows():
        name = re.sub(r"\s*\((Mun|Arrond)\.\)", "", str(r.name14)).strip()
        cands = gn.loc[lut.get(norm(name), [])]
        cands = cands[[inside.contains(Point(x, y)) for x, y in zip(cands.lon, cands.lat)]]
        if not len(cands):
            continue
        if r.prov14 in anchors.index and len(cands) > 1:
            ax, ay = anchors.loc[r.prov14]
            d = np.hypot(cands.lon - ax, cands.lat - ay)
            if d.min() > 3.0:  # >~300 km from the province anchor: refuse
                continue
            best = cands.loc[d.idxmin()]
        else:
            best = cands.sort_values("fclass").iloc[0]  # A (admin) before P (populated place)
        rows.append(
            {
                "unit": r.unit,
                "name14": r.name14,
                "prov14": r.prov14,
                "lon": float(best.lon),
                "lat": float(best.lat),
                "geonameid": best.geonameid,
                "fcode": best.fcode,
                "display": best["name"],
            }
        )
    return pd.DataFrame(rows)


def tessellate(pts: gpd.GeoDataFrame, outline) -> gpd.GeoDataFrame:
    p = pts.to_crs(UTM)
    coords = np.round(np.column_stack([p.geometry.x, p.geometry.y]), 1)
    cells = gpd.GeoDataFrame(geometry=list(shapely.voronoi_polygons(shapely.multipoints(coords)).geoms), crs=UTM)
    cells = gpd.clip(cells, gpd.GeoSeries([outline], crs=4326).to_crs(UTM).iloc[0])
    # voronoi_polygons does not preserve input order: assign cells to points spatially
    joined = gpd.sjoin(cells, p[["geometry"]], predicate="contains", how="inner")
    cell_for_point = joined.reset_index().drop_duplicates("index_right").set_index("index_right")["geometry"]
    t = p.copy()
    t["geometry"] = t.index.map(cell_for_point)
    t = gpd.GeoDataFrame(t[t.geometry.notna()], geometry="geometry", crs=UTM)
    return t[~t.geometry.is_empty]


def main(outline_path=None) -> gpd.GeoDataFrame:
    GEOMETRY.mkdir(parents=True, exist_ok=True)
    outline = (gpd.read_file(outline_path) if outline_path else boundary()).to_crs(4326).geometry.iloc[0]
    u = units()
    gi, g = match_gadm(u, gadm_centroids())
    u["gi"] = gi
    matched = u[u.gi.notna()].copy()
    unmatched = u[u.gi.isna()]
    matched["lon"] = pd.to_numeric(matched.gi.map(g.lon), errors="coerce")
    matched["lat"] = pd.to_numeric(matched.gi.map(g.lat), errors="coerce")
    matched["pt_src"] = "gadm"
    print(f"GADM seed points: {len(matched)}/{len(u)} units")

    pts_gadm, _ = place(matched)
    gc = geonames(unmatched, pts_gadm, outline)
    gc.to_csv(P_GEOCODED, index=False)
    add = unmatched.merge(gc[["unit", "lon", "lat"]], on="unit", how="inner").assign(pt_src="geonames")
    print(f"GeoNames seed points: {len(add)}/{len(unmatched)}")
    unmatched[~unmatched.unit.isin(set(gc.unit))][["unit", "name14", "prov14"]].to_csv(P_UNMATCHED, index=False)

    pts, dups = place(pd.concat([matched, add], ignore_index=True))
    dups.to_csv(P_DUP_POINTS, index=False)
    # a coarse coastline can leave a coastal seed just offshore (Harhoura with Natural Earth): keep its cell
    offshore = pts[~pts.within(outline)]
    if len(offshore):
        outline = outline.union(offshore.to_crs(UTM).buffer(1000).to_crs(4326).union_all())
        print(f"outline extended around {len(offshore)} offshore seed point(s): {', '.join(offshore.name14)}")
    thiessen = tessellate(pts, outline)
    print(f"cells: {len(thiessen)} ({len(dups)} duplicate-coordinate units dropped)")

    P_GPKG.unlink(missing_ok=True)
    thiessen.to_crs(4326).to_file(P_GPKG, layer="thiessen", driver="GPKG")
    pts.to_file(P_GPKG, layer="points", driver="GPKG")
    w = psw.Queen.from_dataframe(thiessen, use_index=False)
    f = psopen(str(P_GAL), "w")
    f.write(w)
    f.close()
    print(f"queen weights: n={w.n}, mean neighbours={pd.Series(w.cardinalities).mean():.2f}, islands={len(w.islands)}")
    return thiessen.to_crs(4326)
