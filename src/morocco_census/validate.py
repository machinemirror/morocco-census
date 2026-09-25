"""Checks of the published tables against independent sources -> data/processed/validation.json.

Tracked, so the numbers a release reports can be read without the raw files:
  - population: each census's commune table against HCP's separately published legal population;
  - linkage: crosswalk match counts and imputation flags;
  - seeds: agreement between the two gazetteers behind the commune points.
"""

import json
import re

import numpy as np
import pandas as pd
from pypdf import PdfReader

from .config import (
    HCP_2004_ON_2014,
    P_COMMUNES,
    P_CROSSCHECK,
    P_CROSSWALK,
    P_CROSSWALK_APP,
    P_PANEL,
    P_SEEDS,
    P_SLICES,
    P_UNMATCHED,
    PROCESSED,
    R_APP_INDEX,
    R_HCP04_CASABLANCA,
    R_HCP04_SETTAT,
    RAW,
)
from .crosswalk import norm

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


def linked_2004() -> pd.Series:
    """2004 population the profile links give each 2014 commune."""
    app = pd.read_csv(P_CROSSWALK_APP, dtype={"app_code": str, "code14": str})
    pop = pd.read_csv(P_COMMUNES[2004], dtype={"app_code": str}).set_index("app_code").population04
    return (app.app_code.map(pop) * app.weight).groupby(app.code14).sum()


def compare(ref: pd.DataFrame, groups: dict[str, pd.Series]) -> dict:
    ref = ref.copy()
    ref["linked"] = ref.code14.map(linked_2004()).fillna(0).round().astype(int)
    ref["pct"] = (ref.linked / ref.population04_hcp * 100 - 100).round(1)
    ref["ok"] = ref.pct.abs() <= 2
    out = {"communes": len(ref), "within_2pct": int(ref.ok.sum())}
    for name, mask in groups.items():
        m = mask.reindex(ref.index, fill_value=False)
        out[name] = {"communes": int(m.sum()), "within_2pct": int((ref.ok & m).sum())}
    out["largest_gaps"] = [
        {"name": r.name14, "linked": int(r.linked), "hcp": int(r.population04_hcp), "pct": float(r.pct)}
        for _, r in ref[~ref.ok].sort_values("pct", key=abs, ascending=False).iterrows()
    ]
    return out


def link_kind(codes: pd.Series) -> pd.Series:
    """calibrated (a weight set from an HCP figure), one_to_one (exact links only) or other_links."""
    app = pd.read_csv(P_CROSSWALK_APP, dtype={"app_code": str, "code14": str}, keep_default_na=False)
    by = app.groupby("code14")
    calibrated = codes.isin(app.code14[app.weight_basis == "hcp"])
    one_to_one = codes.map(by.link.agg(lambda s: set(s) == {"exact"})).fillna(False).astype(bool)
    return pd.Series(np.select([calibrated, one_to_one], ["calibrated", "one_to_one"], "other_links"), index=codes.index)


def backcast() -> dict:
    """The 2004 population our links give each 2014 commune, against HCP's own figure on 2014 boundaries.

    catalog/hcp_2004_on_2014.csv also sets split weights, so its communes are split into those it calibrated and the
    rest; the out-of-sample set, parsed from two HCP documents, never feeds a weight. HCP's figures are legal
    population (they include the population comptée à part), so small negative gaps are expected."""
    ref = pd.read_csv(HCP_2004_ON_2014, dtype={"code14": str})
    kind = link_kind(ref.code14)
    out = compare(ref, {k: kind == k for k in ("calibrated", "one_to_one", "other_links")})
    test = hcp_2004_test()
    test = test[~test.code14.isin(ref.code14)].reset_index(drop=True)
    kind = link_kind(test.code14)
    oos = compare(test, {k: kind == k for k in ("one_to_one", "other_links")})
    oos["by_source"] = {k: int(v) for k, v in test.source.value_counts().items()}
    out["out_of_sample"] = oos
    return out


def numbers(tokens: list[str], n: int) -> list[tuple[int, ...]]:
    """Every reading of digit tokens as n numbers written with space-separated thousands ('2 603 15 607')."""
    if n == 0:
        return [()] if not tokens else []
    out = []
    for k in range(1, len(tokens) + 1):
        g = tokens[:k]
        if len(g) == 1 or (len(g[0]) <= 3 and all(len(x) == 3 for x in g[1:])):
            out += [(int("".join(g)),) + rest for rest in numbers(tokens[k:], n - 1)]
    return out


def plausible(households: int, population: int) -> bool:
    return 2.5 <= population / households <= 12


def hcp_2004_settat() -> tuple[pd.DataFrame, int]:
    """Communes of Settat and Benslimane on post-2009 codes (households, population), and the national total as the
    sum of the region rows (the document's total line does not extract cleanly)."""
    rows, regions = [], {}
    for page in PdfReader(R_HCP04_SETTAT).pages:
        for line in (page.extract_text() or "").split("\n"):
            if m := re.match(r"^(\d{2}\.\d{3}\.\d{2}\.\d{2}\.)\s+(.+?)\s+(\d[\d ]*\d)", line):
                (_, pop), *more = [r for r in numbers(m.group(3).split(), 2) if plausible(*r)]
                assert not more, line
                rows.append({"code14": m.group(1), "name": m.group(2), "population04_hcp": pop})
            elif (m := re.match(r"^(\d{2}) (\D+?) ([\d ]+)$", line.strip())) and m.group(1) not in regions:
                readings = [r for r in numbers(m.group(3).split(), 2) if plausible(*r)]
                if len(readings) == 1:
                    regions[m.group(1)] = readings[0][1]
    assert len(regions) == 16
    return pd.DataFrame(rows).assign(source="HCP Settat, population légale 2004"), sum(regions.values())


def hcp_2004_casablanca() -> pd.DataFrame:
    """Communes of the Grand Casablanca region, 2004 on 2014 boundaries. Each row is read so that its 2014 figure
    equals the commune's 2014 legal population, which fixes how its digits group."""
    t14 = pd.read_csv(P_COMMUNES[2014], dtype={"code14": str})
    t14 = t14[t14.code14.str.match(r"06\.(141|355|371|385)\.")]
    code = {norm(n): c for n, c in zip(t14.name14, t14.code14)}
    legal = t14.set_index("code14").pop_legal14
    rows = {}
    for i, page in enumerate(PdfReader(R_HCP04_CASABLANCA).pages, start=1):
        # the province tables (pp. 5-8) give population before households, the arrondissement annex the reverse
        order = ("p04", "h04", "p14", "h14") if i < 9 else ("h04", "p04", "h14", "p14")
        for line in (page.extract_text() or "").split("\n"):
            m = re.match(r"^\s*(?:C\.R\.\s+)?(.+?\((?:Arrond|Mun)\.\)|[A-Z][^\d]+?)\s+(\d[\d ]*)", line)
            if not m or "Dont" in line or (c := code.get(norm(m.group(1)))) is None:
                continue
            tokens = m.group(2).split()
            for k in range(4, len(tokens) + 1):
                for r in numbers(tokens[:k], 4):
                    d = dict(zip(order, r))
                    if d["p14"] == legal[c] and plausible(d["h04"], d["p04"]) and plausible(d["h14"], d["p14"]):
                        rows.setdefault(c, set()).add(d["p04"])
    assert all(len(v) == 1 for v in rows.values()) and len(rows) == len(t14)
    return pd.DataFrame(
        {"code14": list(rows), "population04_hcp": [v.pop() for v in rows.values()]}
    ).assign(source="HCP Grand Casablanca, note premiers résultats RGPH 2014")


def hcp_2004_test() -> pd.DataFrame:
    t14 = pd.read_csv(P_COMMUNES[2014], dtype={"code14": str}).set_index("code14").name14
    test = pd.concat([hcp_2004_settat()[0], hcp_2004_casablanca()], ignore_index=True)
    test["name14"] = test.code14.map(t14)
    assert test.name14.notna().all()
    return test[["code14", "name14", "population04_hcp", "source"]]


def unplaced_2004() -> dict:
    """2004 population the profile links place on no 2014 commune: unlinked units and the unplaced share of splits,
    by the unit's 2004 province."""
    app = pd.read_csv(P_CROSSWALK_APP, dtype={"app_code": str})
    t04 = pd.read_csv(P_COMMUNES[2004], dtype={"app_code": str}).set_index("app_code")
    placed = app.groupby("app_code").weight.sum().reindex(t04.index).fillna(0)
    left = (t04.population04 * (1 - placed).clip(lower=0)).round()
    province = pd.read_csv(R_APP_INDEX, dtype=str).set_index("commune_code").province
    by = left[left > 0].groupby(province).sum()
    return {
        "unlinked_units": int((placed == 0).sum()),
        "partial_units": int(((placed > 0) & (placed < 0.999)).sum()),
        "population": int(left.sum()),
        "by_province_2004": {k: int(v) for k, v in by.sort_values(ascending=False).items()},
    }


def main() -> dict:
    cw = pd.read_csv(P_CROSSWALK, dtype=str)
    app = pd.read_csv(P_CROSSWALK_APP, dtype=str)
    panel = pd.read_csv(P_PANEL, dtype=str)
    # city aggregate rows carry no flags; the catalogue defines an empty src14/src24 as direct
    communes = panel[panel.level != "city"]
    seeds = pd.read_csv(P_SEEDS, dtype=str)
    check = pd.read_csv(P_CROSSCHECK)
    t24 = pd.read_csv(P_COMMUNES[2024], dtype={"code24": str})
    out = {
        "population": {
            "2014": reconcile(2014, "code14", "name14", "population14", legal_2014()),
            "2024": reconcile(2024, "code24", "name24", "population24", legal_2024()),
        },
        "linkage": {
            "spine_2014": len(cw),
            "linked_2004_annex": int(cw.label04.notna().sum()),
            "linked_2004_profiles": int(app.code14.nunique()),
            "unplaced_2004": unplaced_2004(),
            "profile_links": {k: int(v) for k, v in app.link.value_counts().items()},
            "linked_2024": int(cw.code24.notna().sum()),
            "linked_all_three": int((cw.code24.notna() & cw.label04.notna()).sum()),
            # 2024 communes with no 2014 counterpart
            "unlinked_2024": sorted(set(t24.name24[~t24.code24.isin(cw.code24_commune.dropna())])),
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
    out["backcast_2004"] = backcast()
    P_VALIDATION.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    p = out["population"]
    for y in p:
        print(
            f"{y}: {p[y]['exact']}/{p[y]['compared']} communes equal the legal population, median |diff| {p[y]['median_abs_pct']}%"
        )
    return out
