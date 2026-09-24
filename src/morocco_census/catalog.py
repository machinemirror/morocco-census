"""Load and validate catalog/variables.yaml against the published tables."""

import pandas as pd
import yaml

from .config import CATALOG, PROCESSED


def load() -> dict:
    return yaml.safe_load(CATALOG.read_text())


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
                if spec.get("source") and spec["source"] not in cat["sources"]:
                    out.append(f"{ds['id']}.{c}: unknown source {spec['source']}")
            else:
                out += [f"{ds['id']}.{c}: missing {k}" for k in ("en", "fr", "unit", "definition") if k not in spec]
    for i, ind in cat["indicators"].items():
        if ind["theme"] not in cat["themes"]:
            out.append(f"indicator {i}: unknown theme {ind['theme']}")
        out += [f"indicator {i}: missing {k}" for k in ("en", "fr", "unit", "definition") if k not in ind]
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
                    "label_fr": ind.get("fr") or spec.get("fr"),
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


def series(cat: dict) -> dict[tuple[str, int], tuple[str, str]]:
    """(indicator, vintage) -> (dataset id, column), preferring per-vintage tables over the panel."""
    out = {}
    for ds in sorted(cat["datasets"], key=lambda d: d.get("vintage") is None):
        if ds["id"] in ("crosswalk_communes", "commune_indices_2004"):
            continue  # the panel carries these values keyed to the spine
        for c, spec in ds["columns"].items():
            if "indicator" in spec:
                out.setdefault((spec["indicator"], int(spec.get("vintage") or ds["vintage"])), (ds["id"], c))
    return out
