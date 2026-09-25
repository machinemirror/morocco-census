"""Three-census commune panel -> panel_commune.csv.

One row per 2014-spine commune (code14): crosswalk identifiers; 2004 annex indices (poverty,
vulnerability, severity, inequality, IDH, IDS); poverty-map MPI 2004 and 2014; MPI-database
MPI/rate/intensity/vulnerability for 2014 and 2024; legal households and population 2014 (weights).
Arrondissements stay as rows and city rows are appended (level='city'): legal population and households
summed, rates population-weighted.
Values missing because of post-2004/2014 reorganisations are filled with the population-weighted
mean of same-cercle communes (fallback: province) and flagged in src04/src14/src24.
"""

import pandas as pd

from .config import CITIES, P_CROSSWALK, P_INDICES_2004, P_PANEL, R_CARTO, R_MPI, RAW


def main() -> pd.DataFrame:
    cw = pd.read_csv(P_CROSSWALK, dtype={"code24": "Int64", "code24_commune": "Int64"})

    d04 = pd.read_csv(P_INDICES_2004)
    d04 = d04.rename(
        columns={c: f"{c}04" for c in ["taux_pauvrete", "vulnerabilite", "severite", "inegalite", "idh", "ids"]}
    )
    d04 = d04[["label", "taux_pauvrete04", "vulnerabilite04", "severite04", "inegalite04", "idh04", "ids04"]]
    p = cw.merge(
        d04.rename(columns={"label": "label04"}).drop_duplicates("label04"),
        on="label04",
        how="left",
        suffixes=("", "_dup"),
    )
    p = p.drop(columns=[c for c in p.columns if c.endswith("_dup")])

    # poverty map 2004-2014 (MPI)
    x = pd.ExcelFile(R_CARTO)
    frames = []
    for s in x.sheet_names:
        if s == "Ensemble":
            continue
        df = x.parse(s, header=None, skiprows=5)
        df = df.rename(
            columns={
                0: "prov",
                1: "commune",
                2: "centre",
                3: "mpi_rate14c",
                4: "mpi_idx14c",
                5: "mpi_int14c",
                6: "mpi_rate04c",
                7: "mpi_idx04c",
                8: "mpi_int04c",
                16: "pov_glob14c",
            }
        )
        frames.append(
            df[df.commune.notna() & df.centre.isna()][
                [
                    "prov",
                    "commune",
                    "mpi_rate04c",
                    "mpi_idx04c",
                    "mpi_int04c",
                    "mpi_rate14c",
                    "mpi_idx14c",
                    "mpi_int14c",
                    "pov_glob14c",
                ]
            ]
        )
    carto = pd.concat(frames).reset_index(drop=True)
    carto["name_carto"] = carto.commune
    p = p.merge(carto.drop(columns=["prov", "commune"]).drop_duplicates("name_carto"), on="name_carto", how="left")

    # MPI database 2014/2024 by code24
    df = pd.read_excel(R_MPI, sheet_name="Ensemble", header=None, skiprows=6)
    df = df.rename(
        columns={
            0: "label",
            1: "code24",
            2: "level",
            3: "year",
            4: "mpi",
            5: "mpi_rate",
            6: "mpi_intensity",
            7: "vulnerability",
        }
    )
    df["code24"] = pd.to_numeric(df.code24, errors="coerce").astype("Int64")
    mm = df[df.level.isin(["commune", "commune casa"])][
        ["code24", "year", "mpi", "mpi_rate", "mpi_intensity", "vulnerability"]
    ]
    wide = mm.pivot_table(index="code24", columns="year", values=["mpi", "mpi_rate", "mpi_intensity", "vulnerability"])
    wide.columns = [f"{a}{int(b)}" for a, b in wide.columns]
    p = p.merge(wide.reset_index(), on="code24", how="left")

    # menages_2014 codes use the 12-region numbering, so take weights from the 12-region legal population
    pop = pd.read_excel(RAW / "poplegale_2014_12reg.xlsx", sheet_name=0, header=None, skiprows=6)
    pop = pop.rename(columns={0: "code14", 2: "households_legal14", 3: "pop_legal14"})
    pop = pop[pop.code14.astype(str).str.count("\\.") == 4][["code14", "households_legal14", "pop_legal14"]]
    for c in ("households_legal14", "pop_legal14"):
        pop[c] = pd.to_numeric(pop[c], errors="coerce")
    p = p.merge(pop.drop_duplicates("code14"), on="code14", how="left")

    p["level"] = "commune"
    arr = p[
        p.name14.str.contains(r"\(Arrond", na=False) | p.name24.astype(str).str.contains("Arrondissement", na=False)
    ].copy()
    if len(arr):
        arr["city"] = arr.code14.str.extract(r"^(\d+\.\d+\.\d+\.)")[0]
        rows = []
        num = [c for c in p.columns if p[c].dtype.kind == "f" and c not in ("households_legal14", "pop_legal14")]
        for city, g in arr.groupby("city"):
            w = g.pop_legal14.fillna(0)
            r = {
                "code14": city,
                "name14": f"CITY {g.prov14.iloc[0]}",
                "prov14": g.prov14.iloc[0],
                "unit": city,
                "code24": CITIES[city][1],
                "code24_commune": CITIES[city][1],
                "level": "city",
                "households_legal14": g.households_legal14.sum(),
                "pop_legal14": g.pop_legal14.sum(),
            }
            for c in num:
                v, wv = g[c], w.where(g[c].notna(), 0)
                r[c] = (v * wv).sum() / wv.sum() if wv.sum() > 0 else float("nan")
            rows.append(r)
        p = pd.concat([p, pd.DataFrame(rows)], ignore_index=True)

    p["cercle"] = p.code14.astype(str).str.extract(r"^(\d+\.\d+\.\d+\.)")[0]
    cols04 = [
        "taux_pauvrete04",
        "vulnerabilite04",
        "severite04",
        "inegalite04",
        "idh04",
        "ids04",
        "mpi_rate04c",
        "mpi_idx04c",
        "mpi_int04c",
    ]
    cols14 = ["mpi2014", "mpi_rate2014", "mpi_intensity2014", "vulnerability2014"]
    cols24 = ["mpi2024", "mpi_rate2024", "mpi_intensity2024", "vulnerability2024"]

    def impute(cols, flag_col, donors_col):
        p[flag_col] = p.get(flag_col)
        p[donors_col] = pd.NA
        # donors are communes only: a city row shares its arrondissements' cercle code and would count them twice
        w = p.pop_legal14.fillna(0).where(p.level.eq("commune"), 0)
        for group, tag in ((["cercle"], "imputed_cercle"), (["prov14"], "imputed_province")):
            need = p[cols[0]].isna() & p.level.eq("commune")
            if not need.any():
                break
            keys = [p[g] for g in group]
            donors = (p[cols[0]].notna() & p.level.eq("commune")).groupby(keys).transform("sum")
            # a cercle with one donor would copy one commune's value (a lone municipality in the pseudo-cercle 01,
            # say), so those communes fall through to the province
            enough = donors >= 2 if tag == "imputed_cercle" else donors >= 1
            for c in [c for c in cols if c in p.columns]:
                num = (p[c] * w).groupby(keys).transform("sum")
                den = w.where(p[c].notna(), 0).groupby(keys).transform("sum")
                fill = need & enough & p[c].isna() & (den > 0)
                p.loc[fill, c] = (num / den)[fill]
            done = need & p[cols[0]].notna()
            p.loc[done, flag_col] = tag
            p.loc[done, donors_col] = donors[done]
        p[donors_col] = p[donors_col].astype("Int64")

    impute(cols04, "src04", "n_donors04")
    impute(cols14, "src14", "n_donors14")
    impute(cols24, "src24", "n_donors24")

    p.to_csv(P_PANEL, index=False)
    core = p[p.level == "commune"]
    print(f"panel: {len(p)} rows ({len(core)} communes + {len(p) - len(core)} city aggregates)")
    for f in ("src04", "src14", "src24"):
        print(f"  {f}:", core[f].value_counts(dropna=False).to_dict())
    return p
