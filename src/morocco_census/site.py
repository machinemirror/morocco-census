"""Export the static site's data: map/index.json (units, HCP names, the three-census indicators) with one
values file per theme, communes.geojson (simplified cells), catalog.json, and the downloads folder (tables as
CSV + Parquet, geometry, dictionary, zip)."""

import json
import shutil
import zipfile
from importlib.metadata import version

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from . import catalog
from .config import (
    P_BOUNDARY,
    P_COMMUNES,
    P_CONTEXT,
    P_CROSSWALK,
    P_CROSSWALK_APP,
    P_GAL,
    P_GPKG,
    P_HCP_GPKG,
    P_PANEL,
    PROCESSED,
    SITE,
)

# the six arrondissement cities: one map unit each (the 2014 cercle code), one commune each in 2024
CITIES = {
    "01.511.01.": ("Tanger", 1511010),
    "03.231.01.": ("Fès", 3231010),
    "04.421.01.": ("Rabat", 4421010),
    "04.441.01.": ("Salé", 4441010),
    "06.141.01.": ("Casablanca", 6141010),
    "07.351.01.": ("Marrakech", 7351010),
}
SIMPLIFY_M = 250


def unit_of(cw: pd.DataFrame) -> pd.Series:
    arr = cw.name14.str.contains(r"\(Arrond", na=False)
    return cw.code14.where(~arr, cw.code14.str.extract(r"^(\d+\.\d+\.\d+\.)")[0])


def keyed_tables() -> dict[str, tuple[pd.DataFrame, str]]:
    """dataset id -> (table with a `unit` column, weight column)."""
    cw = pd.read_csv(P_CROSSWALK, dtype={"code14": str})
    cw["unit"] = unit_of(cw)
    cw["code24"] = pd.to_numeric(cw.code24).astype("Int64")
    by14 = cw.set_index("code14").unit

    t14 = pd.read_csv(P_COMMUNES[2014], dtype={"code14": str}).copy()  # consolidate blocks before adding columns
    t14["unit"] = t14.code14.map(by14)

    app = pd.read_csv(P_CROSSWALK_APP, dtype=str).set_index("app_code").code14
    t04 = pd.read_csv(P_COMMUNES[2004], dtype={"app_code": str}).copy()
    t04["unit"] = t04.app_code.map(app).map(by14)

    by24 = cw.dropna(subset=["code24"]).drop_duplicates("code24").set_index("code24").unit
    by24 = pd.concat([by24, pd.Series({c24: u for u, (_, c24) in CITIES.items()})])
    t24 = pd.read_csv(P_COMMUNES[2024]).copy()
    t24["unit"] = t24.code24.map(by24)

    panel = pd.read_csv(P_PANEL, dtype={"code14": str})
    panel = panel[panel.level == "commune"].copy()
    panel["unit"] = panel.code14.map(by14)
    return {
        "communes_2004": (t04, "population04"),
        "communes_2014": (t14, "population14"),
        "communes_2024": (t24, "population24"),
        "panel_commune": (panel, "population14"),
    }


def aggregate(df: pd.DataFrame, col: str, weight: str, spec: dict) -> pd.Series:
    d = df.dropna(subset=["unit"])
    if spec.get("agg") == "sum":
        return d.groupby("unit")[col].sum(min_count=1)
    if spec["unit"] == "flag":
        return d.groupby("unit")[col].max()
    w = d[weight].where(d[col].notna(), 0).fillna(0)
    num = (d[col] * w).groupby(d.unit).sum(min_count=1)
    den = w.groupby(d.unit).sum()
    plain = d.groupby("unit")[col].mean()  # communes with no weight still get a value
    return (num / den.replace(0, np.nan)).fillna(plain)


def rounded(s: pd.Series, spec: dict) -> list:
    if spec.get("agg") == "sum" and spec["unit"] != "%":
        return [None if pd.isna(v) else round(v) for v in s]
    return [None if pd.isna(v) else float(f"{v:.4g}") for v in s]


def unit_frame(cells: gpd.GeoDataFrame, hcp: gpd.GeoDataFrame) -> pd.DataFrame:
    """Map units: the Thiessen cells in order, then units only HCP's boundaries draw (no seed point)."""
    pts = gpd.read_file(P_GPKG, layer="points").set_index("unit")
    cw = pd.read_csv(P_CROSSWALK, dtype=str).set_index("code14")
    extra = hcp[~hcp.unit.isin(cells.unit)]
    f = pd.concat(
        [
            cells[["unit", "name14", "prov14"]],
            pd.DataFrame(
                {"unit": extra.unit, "name14": extra.unit.map(cw.name14), "prov14": extra.unit.map(cw.prov14)}
            ),
        ],
        ignore_index=True,
    )
    rp = hcp.set_index("unit").representative_point()
    f["lon"] = pts.geometry.x.reindex(f.unit).fillna(rp.x.reindex(f.unit)).values
    f["lat"] = pts.geometry.y.reindex(f.unit).fillna(rp.y.reindex(f.unit)).values
    f["pt_src"] = pts.pt_src.reindex(f.unit).fillna("hcp2024").values
    return f


def hcp_names(units: list[str]) -> pd.DataFrame:
    """French and Arabic commune and province names as HCP writes them, per map unit."""
    cw = pd.read_csv(P_CROSSWALK, dtype={"code14": str})
    cw["unit"] = unit_of(cw)
    code = cw.dropna(subset=["code24"]).drop_duplicates("unit").set_index("unit").code24.astype("int64")
    code = pd.concat([code[~code.index.isin(CITIES)], pd.Series({u: c for u, (_, c) in CITIES.items()})])
    t24 = pd.read_csv(P_COMMUNES[2024]).set_index("code24")
    n = t24.reindex(code.reindex(units).values).set_axis(units)
    return pd.DataFrame(
        {
            "name_fr": n.name24.str.replace(r"^Commune (de |d')", "", regex=True),
            "name_ar": n.name24_ar.str.replace(r"^جماعة ", "", regex=True),
            "prov_fr": n.province24,
            "prov_ar": n.province24_ar,
        }
    )


def map_data(cat: dict, uf: pd.DataFrame) -> dict:
    """The map's index (units, themes, indicators) and its values, one file per theme."""
    units = uf.unit.tolist()
    tables = keyed_tables()
    shown = catalog.on_map(cat)
    group_of = {th: g for g, spec in cat["map_groups"].items() for th in spec["themes"]}
    values, indicators = {}, {}
    for (ind, year), (ds, col) in sorted(catalog.series(cat).items()):
        if ind not in shown:
            continue
        df, weight = tables[ds]
        spec = cat["indicators"][ind]
        if spec.get("weight") == "households" and "n_households" in df:
            weight = "n_households"
        s = aggregate(df, col, weight, spec).reindex(units)
        values.setdefault(spec["theme"], {})[f"{ind}|{year}"] = rounded(s, spec)
        entry = indicators.setdefault(
            ind,
            {k: spec[k] for k in ("theme", "en", "fr", "ar", "unit", "agg", "definition", "note") if k in spec}
            | {"group": group_of[spec["theme"]], "comparable": spec.get("comparable", True), "vintages": {}},
        )
        entry["vintages"][year] = {"dataset": ds, "column": col, "n": int(s.notna().sum())}

    names = hcp_names(units)
    provs = pd.DataFrame({"en": uf.prov14.values, "fr": names.prov_fr.values, "ar": names.prov_ar.values})
    prov_table = provs.drop_duplicates().reset_index(drop=True)
    prov_idx = provs.merge(prov_table.reset_index(), how="left").loc[:, "index"]
    # column-wise, with provinces as a lookup table: a third of the size of one object per unit
    index = {
        "units": {
            "id": units,
            "name": [CITIES[u][0] if u in CITIES else n for u, n in zip(units, uf.name14)],
            "name_fr": names.name_fr.tolist(),
            "name_ar": names.name_ar.tolist(),
            "prov": prov_idx.tolist(),
            "lon": [round(x, 4) for x in uf.lon],
            "lat": [round(y, 4) for y in uf.lat],
            "pt": uf.pt_src.tolist(),
        },
        "provinces": prov_table.to_dict(orient="records"),
        "groups": {k: {x: v[x] for x in ("en", "fr", "ar")} for k, v in cat["map_groups"].items()},
        "indicators": indicators,
    }
    return {"index": index, "values": values}


def simplified(cells: gpd.GeoDataFrame, ids=None) -> gpd.GeoDataFrame:
    utm = cells.to_crs(32629)
    if ids is not None:
        utm["geometry"] = utm.geometry.buffer(0)  # HCP polygons: reprojection can leave degenerate slivers
    # coverage simplification keeps shared edges shared (no slivers between neighbours)
    geom = shapely.coverage_simplify(np.asarray(utm.geometry.values), SIMPLIFY_M)
    ids = range(len(cells)) if ids is None else list(ids)
    return gpd.GeoDataFrame({"i": ids}, geometry=geom, crs=32629).to_crs(4326)


def write_geojson(gdf: gpd.GeoDataFrame, path, precision: int = 4) -> None:
    gdf.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=precision, RFC7946="YES")


def downloads(cat: dict, cells: gpd.GeoDataFrame, dest) -> list[dict]:
    dest.mkdir(parents=True, exist_ok=True)
    files = []
    for ds in cat["datasets"]:
        src = PROCESSED / ds["file"]
        df = pd.read_csv(src, dtype=str)  # keep codes such as app_code '0106601031' intact
        typed = pd.read_csv(src)
        for c in ("app_code", "code14", "cercle"):
            if c in typed:
                typed[c] = df[c]
        shutil.copy(src, dest / ds["file"])
        typed.to_parquet(dest / ds["file"].replace(".csv", ".parquet"), index=False)
        files.append(
            {
                "dataset": ds["id"],
                "en": ds["en"],
                "rows": len(df),
                "cols": df.shape[1],
                "formats": ["csv", "parquet"],
                "stem": ds["file"].removesuffix(".csv"),
            }
        )
    shutil.copy(P_GPKG, dest / "communes.gpkg")
    shutil.copy(P_GAL, dest / "communes_queen.gal")
    shutil.copy(P_BOUNDARY, dest / "boundary_mar_esh.gpkg")
    write_geojson(cells, dest / "communes_thiessen.geojson", 6)
    gpd.read_file(P_GPKG, layer="points").pipe(write_geojson, dest / "communes_points.geojson", 6)
    catalog.columns(cat).to_csv(dest / "data_dictionary.csv", index=False)
    bundle = dest / f"morocco-census-data-{version('morocco-census')}.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dest.iterdir()):
            if f != bundle and f.suffix != ".zip":
                z.write(f, f.name)
        for f in ("LICENSE-DATA", "README.md"):
            z.write(PROCESSED.parents[1] / f, f)
    return files


def main() -> None:
    cat = catalog.load()
    if bad := catalog.problems(cat):
        raise SystemExit("catalogue problems:\n  " + "\n  ".join(bad))
    out = SITE / "data"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    cells = gpd.read_file(P_GPKG, layer="thiessen")

    hcp = gpd.read_file(P_HCP_GPKG)
    uf = unit_frame(cells, hcp)
    data = map_data(cat, uf)
    (out / "map").mkdir()
    (out / "map" / "index.json").write_text(json.dumps(data["index"], ensure_ascii=False, separators=(",", ":")))
    for theme, vals in data["values"].items():
        (out / "map" / f"{theme}.json").write_text(json.dumps(vals, separators=(",", ":")))
    write_geojson(simplified(cells), out / "communes.geojson")
    hcp = hcp.set_index("unit").loc[[u for u in uf.unit if u in set(hcp.unit)]].reset_index()
    hcp["i"] = hcp.unit.map({u: i for i, u in enumerate(uf.unit)})
    write_geojson(simplified(hcp, hcp.i), out / "communes_hcp2024.geojson")
    write_geojson(gpd.read_file(P_BOUNDARY), out / "outline.geojson")
    write_geojson(gpd.read_file(P_CONTEXT)[["NAME", "geometry"]], out / "context.geojson", 3)

    files = downloads(cat, cells, out / "downloads")
    dictionary = catalog.columns(cat).fillna("")
    (out / "catalog.json").write_text(
        json.dumps(
            {
                "version": version("morocco-census"),
                "themes": cat["themes"],
                "sources": cat["sources"],
                "datasets": [{k: v for k, v in ds.items() if k != "columns"} for ds in cat["datasets"]],
                "files": files,
                "sizes": {f.name: f.stat().st_size for f in sorted((out / "downloads").iterdir())},
                "columns": dictionary.to_dict(orient="records"),
                "on_map": sorted(data["index"]["indicators"]),
                "coverage": {
                    ds["id"]: {**pd.read_csv(PROCESSED / ds["file"], dtype=str).notna().sum().astype(int).to_dict()}
                    | {"_rows": len(pd.read_csv(PROCESSED / ds["file"], usecols=[0]))}
                    for ds in cat["datasets"]
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    sizes = {f.name: f.stat().st_size for f in out.iterdir() if f.is_file()}
    sizes |= {f"map/{f.name}": f.stat().st_size for f in (out / "map").iterdir()}
    print(
        f"site/data: {len(uf)} units, {len(data['index']['indicators'])} map indicators;",
        ", ".join(f"{k} {v / 1e3:.0f} kB" for k, v in sizes.items()),
    )
