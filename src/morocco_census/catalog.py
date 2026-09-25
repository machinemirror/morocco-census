"""Load and validate catalog/variables.yaml against the published tables."""

import pandas as pd
import yaml

from .config import CATALOG, PROCESSED


def load() -> dict:
    return yaml.safe_load(CATALOG.read_text())


TEXT = ("en", "unit", "definition")


def problems(cat: dict) -> list[str]:
    out = []
    for ds in cat["datasets"]:
        cols = list(pd.read_csv(PROCESSED / ds["file"], nrows=0).columns)
        listed = list(ds["columns"])
        out += [f"{ds['id']}: column {c} not in catalogue" for c in cols if c not in listed]
        out += [f"{ds['id']}: catalogue lists {c}, not in file" for c in listed if c not in cols]
        if ds.get("source") and ds["source"] not in cat["sources"]:
            out.append(f"{ds['id']}: unknown source {ds['source']}")
        for c, spec in ds["columns"].items():
            if "indicator" in spec:
                if spec["indicator"] not in cat["indicators"]:
                    out.append(f"{ds['id']}.{c}: unknown indicator {spec['indicator']}")
                if not (spec.get("vintage") or ds.get("vintage")):
                    out.append(f"{ds['id']}.{c}: indicator column without a vintage")
            else:
                out += [
                    f"{ds['id']}.{c}: missing {k}" for k in TEXT if k not in spec
                ]
            source = spec.get("source") or ds.get("source")
            if not source:
                out.append(f"{ds['id']}.{c}: no source")
            elif source not in cat["sources"]:
                out.append(f"{ds['id']}.{c}: unknown source {source}")
    grouped = [th for g in cat["map_groups"].values() for th in g["themes"]]
    out += [f"map group theme {th} unknown or repeated" for th in grouped if th not in cat["themes"] or grouped.count(th) > 1]
    for i, ind in cat["indicators"].items():
        if ind["theme"] not in cat["themes"]:
            out.append(f"indicator {i}: unknown theme {ind['theme']}")
        out += [f"indicator {i}: missing {k}" for k in TEXT if k not in ind]
        # French and Arabic labels are HCP's own wording, never a translation of ours
        if ("fr" in ind or "ar" in ind) and not ind.get("label_source"):
            out.append(f"indicator {i}: fr/ar label without label_source")
    return out


def columns(cat: dict) -> pd.DataFrame:
    """Flat data dictionary: one row per published column."""
    rows = []
    for ds in cat["datasets"]:
        for c, spec in ds["columns"].items():
            ind = cat["indicators"].get(spec.get("indicator"), {})
            src = cat["sources"].get(spec.get("source") or ds.get("source"), {})
            rows.append(
                {
                    "dataset": ds["id"],
                    "file": ds["file"],
                    "column": c,
                    "indicator": spec.get("indicator", ""),
                    "vintage": spec.get("vintage") or ds.get("vintage") or "",
                    "theme": cat["themes"][ind["theme"]]["en"] if ind else "Identifier",
                    "label_en": ind.get("en") or spec.get("en"),
                    "label_fr": ind.get("fr", ""),
                    "label_ar": ind.get("ar", ""),
                    "label_source": ind.get("label_source", ""),
                    "unit": ind.get("unit") or spec.get("unit"),
                    "definition": ind.get("definition") or spec.get("definition"),
                    "note": ind.get("note", ""),
                    "comparable": ind.get("comparable", True) if ind else "",
                    "source_field": spec.get("from", ""),
                    "source": src.get("title", ""),
                    "source_url": src.get("url", ""),
                }
            )
    return pd.DataFrame(rows)


def on_map(cat: dict) -> set[str]:
    """Indicators observed in all three censuses: the only ones the map shows."""
    years: dict[str, set[int]] = {}
    for ind, year in series(cat):
        years.setdefault(ind, set()).add(year)
    return {i for i, y in years.items() if y == {2004, 2014, 2024}}


def series(cat: dict) -> dict[tuple[str, int], tuple[str, str]]:
    """(indicator, vintage) -> (dataset id, column), preferring per-vintage tables over the panel."""
    out = {}
    for ds in sorted(cat["datasets"], key=lambda d: d.get("vintage") is None):
        if ds["id"] in ("crosswalk_communes", "commune_indices_2004") or "slice" in ds:
            continue  # the panel carries these values keyed to the spine; slices are in slice_series
        for c, spec in ds["columns"].items():
            if "indicator" in spec:
                out.setdefault((spec["indicator"], int(spec.get("vintage") or ds["vintage"])), (ds["id"], c))
    return out


SLICES = {"urban": "milieu", "rural": "milieu", "male": "sex", "female": "sex"}


def slice_series(cat: dict) -> dict[tuple[str, int, str], tuple[str, str]]:
    """(indicator, vintage, slice) -> (dataset id, column). A slice table repeats its parent's column names; 2004
    urban/rural comes from the profiles themselves, whose units are either urban or rural (milieu04)."""
    ids = {d["id"]: d for d in cat["datasets"]}
    out = {}
    for (ind, year), (ds, col) in series(cat).items():
        for s, kind in SLICES.items():
            if ds == "communes_2004" and kind == "milieu":
                out[ind, year, s] = (ds, col)
            elif (sd := ids.get(f"{ds}_{kind}")) and col in sd["columns"]:
                out[ind, year, s] = (sd["id"], col)
    return out
