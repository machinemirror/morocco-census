"""Checks of the published tables against independent sources -> data/processed/validation.json.

Tracked, so the numbers a release reports can be read without the raw files:
  - population: each census's commune table against HCP's separately published legal population;
  - linkage: crosswalk match counts and imputation flags;
  - seeds: agreement between the two gazetteers behind the commune points.
"""

import json

import pandas as pd

from .config import (
    P_COMMUNES,
    P_CROSSCHECK,
    P_CROSSWALK,
    P_CROSSWALK_APP,
    P_PANEL,
    P_SEEDS,
    P_SLICES,
    P_UNMATCHED,
    PROCESSED,
    RAW,
)
from .site import CITIES

P_VALIDATION = PROCESSED / "validation.json"
SHORTFALLS = 8


def legal_2014() -> tuple[pd.DataFrame, int]:
    d = pd.read_excel(RAW / "poplegale_2014_12reg.xlsx", sheet_name=0, header=None, skiprows=5)
    d = d.rename(columns={0: "code", 1: "legal_name", 3: "legal"})
    national = int(d.loc[d.code.astype(str) == "Total", "legal"].iloc[0])
    d = d[d.code.astype(str).str.count(r"\.") == 4]
    # "pm" (pour mémoire): HCP gives no figure for four Oued Ed-Dahab communes
    d["legal"] = pd.to_numeric(d.legal, errors="coerce")
    return d[["code", "legal_name", "legal"]], national


def legal_2024() -> tuple[pd.DataFrame, int]:
    d = pd.read_excel(RAW / "poplegale_2024.xlsx", header=None, skiprows=7)
    d = d.rename(columns={0: "legal_name", 3: "legal", 6: "code"})
    national = int(d.loc[d.legal_name.astype(str).str.startswith("Ensemble"), "legal"].iloc[0])
    d = d[d.code.notna()]
    d["code"] = d.code.astype(str).str.replace(r"\.0$", "", regex=True)
    return d[["code", "legal_name", "legal"]], national


def reconcile(year: int, key: str, name: str, pop: str, legal: tuple[pd.DataFrame, int]) -> dict:
    legal, national = legal
    t = pd.read_csv(P_COMMUNES[year], dtype={key: str})
    m = t[[key, name, pop]].merge(legal.rename(columns={"code": key}), on=key, how="left")
    both = m[m.legal.notna() & m[pop].notna()]
    diff = both[pop] - both.legal
    pct = (diff.abs() / both.legal * 100).where(both.legal > 0)
    worst = both.assign(diff=diff).nsmallest(SHORTFALLS, "diff")
    return {
        "communes": len(t),
        "in_legal_list": int(m.legal_name.notna().sum()),
        "compared": len(both),
        "exact": int((diff == 0).sum()),
        "within_1pct": int((pct <= 1).sum()),
        "median_abs_pct": round(float(pct.median()), 4),
        "sum_table": int(t[pop].sum()),
        "sum_legal_compared": int(both.legal.sum()),
        "national_legal": national,
        "largest_shortfalls": [
            {"name": r[name], "table": int(r[pop]), "legal": int(r.legal)} for _, r in worst.iterrows()
        ],
    }


def slices() -> dict:
    """Urban + rural and male + female populations against each commune's total."""
    out = {}
    for year, key in ((2014, "code14"), (2024, "code24")):
        pop = f"population{str(year)[2:]}"
        total = pd.read_csv(P_COMMUNES[year], dtype={key: str}).set_index(key)[pop]
        out[str(year)] = {}
        for kind in ("milieu", "sex"):
            parts = pd.read_csv(P_SLICES[year, kind], dtype={key: str}).groupby(key)[pop].sum().reindex(total.index)
            out[str(year)][kind] = {"communes": int(parts.notna().sum()), "sum_equals_total": int((parts == total).sum())}
    t04 = pd.read_csv(P_COMMUNES[2004], dtype={"app_code": str}).set_index("app_code")
    sex = pd.read_csv(P_SLICES[2004, "sex"], dtype={"app_code": str}).groupby("app_code").population04.sum()
    out["2004"] = {
        "milieu": {k: int(v) for k, v in t04.groupby("milieu04").population04.sum().items()},
        "sex": {"units": int(sex.notna().sum()), "sum_equals_total": int((sex == t04.population04).sum())},
    }
    return out


def main() -> dict:
    cw = pd.read_csv(P_CROSSWALK, dtype=str)
    app = pd.read_csv(P_CROSSWALK_APP, dtype=str)
    panel = pd.read_csv(P_PANEL, dtype=str)
    # city aggregate rows carry no flags; the catalogue defines an empty src14/src24 as direct
    communes = panel[panel.level != "city"]
    seeds = pd.read_csv(P_SEEDS, dtype=str)
    check = pd.read_csv(P_CROSSCHECK)
    t24 = pd.read_csv(P_COMMUNES[2024], dtype={"code24": str})
    city_codes = {str(code) for _, code in CITIES.values()}
    out = {
        "population": {
            "2014": reconcile(2014, "code14", "name14", "population14", legal_2014()),
            "2024": reconcile(2024, "code24", "name24", "population24", legal_2024()),
        },
        "linkage": {
            "spine_2014": len(cw),
            "linked_2004_annex": int(cw.label04.notna().sum()),
            "linked_2004_profiles": int(app.code14.nunique()),
            "profile_links": {k: int(v) for k, v in app.link.value_counts().items()},
            "linked_2024": int(cw.code24.notna().sum()),
            "linked_all_three": int((cw.code24.notna() & cw.label04.notna()).sum()),
            # 2024 communes with no 2014 counterpart; the arrondissement cities link through their arrondissements
            "unlinked_2024": sorted(
                set(t24.name24[~t24.code24.isin(cw.code24.dropna()) & ~t24.code24.isin(city_codes)])
            ),
            "imputation": {
                f: {k: int(v) for k, v in communes[f].fillna("direct").value_counts().items()} for f in ("src04", "src14", "src24")
            },
        },
        "seeds": {
            "units": len(seeds) + len(pd.read_csv(P_UNMATCHED)),
            "placed": len(seeds),
            "by_source": {k: int(v) for k, v in seeds.pt_src.value_counts().items()},
            "fuzzy": int((seeds.match == "fuzzy").sum()),
            "both_gazetteers": len(check),
            "median_km": round(float(check.km.median()), 2),
            "p90_km": round(float(check.km.quantile(0.9)), 2),
            "over_25km": int(check.flag.sum()),
            "decided_by": {k: int(v) for k, v in check.decided_by.value_counts().items()},
        },
    }
    out["slices"] = slices()
    P_VALIDATION.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    p = out["population"]
    for y in p:
        print(
            f"{y}: {p[y]['exact']}/{p[y]['compared']} communes equal the legal population, median |diff| {p[y]['median_abs_pct']}%"
        )
    return out
