"""Commune-level variables for 2014 and 2024 -> communes_2014.csv, communes_2024.csv.

2014: menages/individus/activite/diplome_2014.xlsx, sheet Indic.Ensemble. Commune rows have a
dotted code14 with 4 dots (e.g. "01.051.01.01.").
2024: indicateurs_demo_socioeco_2024.xlsx, sheets Population and Ménages (Population_Rurale
for the urban flag). Commune rows are labelled "Commune de "/"Commune d'"; key code24.

SPEC_2014 / SPEC_2024 name the exact 0-indexed source column of every variable; the
column_map returned by each extractor records the original French header for the catalogue.
"""

import re

import pandas as pd

from .config import P_COMMUNES, P_CROSSWALK, RAW

NA_TOKENS = {"pm", "-", "..", "...", "n.d.", "nd", "na", "n/a", ""}


def to_num(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s.where(~s.isin(NA_TOKENS))
    return pd.to_numeric(s, errors="coerce")


def header_label(df: pd.DataFrame, col: int) -> str:
    parts = [str(df.iloc[r, col]).strip() for r in range(3) if pd.notna(df.iloc[r, col])]
    return " | ".join(parts) if parts else f"(col {col})"


# {output_name: (file, column_index)} in the raw Indic.Ensemble sheet
SPEC_2014 = {
    "n_households": ("menages_2014.xlsx", 10),
    "hh_size_avg": ("menages_2014.xlsx", 11),
    "pct_owner": ("menages_2014.xlsx", 19),
    "pct_renter": ("menages_2014.xlsx", 20),
    "pct_electricity": ("menages_2014.xlsx", 29),
    "pct_water": ("menages_2014.xlsx", 30),
    "pct_cellphone": ("menages_2014.xlsx", 44),
    "pct_internet": ("menages_2014.xlsx", 46),
    "age_0_4": ("individus_2014.xlsx", 10),
    "age_5_9": ("individus_2014.xlsx", 11),
    "age_10_14": ("individus_2014.xlsx", 12),
    "pct_illiterate": ("individus_2014.xlsx", 35),
    "activity_rate": ("individus_2014.xlsx", 53),
    "unemployment_rate": ("individus_2014.xlsx", 54),
    "pct_women_divorced": ("individus_2014.xlsx", 136),
    "pop_active_occupee": ("activite_2014.xlsx", 8),
    "pct_sector_agri": ("activite_2014.xlsx", 19),
    "pct_no_diploma": ("diplome_2014.xlsx", 15),
    "_pct_deug_licence": ("diplome_2014.xlsx", 12),
    "_pct_master_doct": ("diplome_2014.xlsx", 13),
}
POP_COL_2014 = 9  # menages_2014.xlsx: col8 = population légale, col9 = population municipale
NAME_COL_2014, CODE_COL_2014 = 7, 6


def extract_2014() -> tuple[pd.DataFrame, dict]:
    files = {f for f, _ in SPEC_2014.values()} | {"menages_2014.xlsx"}
    raws = {f: pd.read_excel(RAW / f, sheet_name="Indic.Ensemble", header=None) for f in files}

    column_map = {}
    base = raws["menages_2014.xlsx"]
    code = base[CODE_COL_2014].astype(str)
    # depth 4 with COM set; the 8 Casablanca préfectures d'arrondissements (06.141.01.0. ...) have no COM
    mask = (code.str.count(r"\.") == 4) & base[4].notna()
    out = pd.DataFrame(
        {
            "code14": code[mask],
            "name14": base.loc[mask, NAME_COL_2014].astype(str).str.strip(),
            "population14": to_num(base.loc[mask, POP_COL_2014]),
        }
    )
    column_map["population14"] = f"menages_2014.xlsx col{POP_COL_2014}: {header_label(base, POP_COL_2014)}"

    for out_name, (fname, col) in SPEC_2014.items():
        df = raws[fname]
        code_f = df[CODE_COL_2014].astype(str)
        mask_f = code_f.str.count(r"\.") == 4
        series = to_num(df.loc[mask_f, col])
        series.index = code_f[mask_f].values
        out[out_name] = out["code14"].map(series)
        column_map[out_name] = f"{fname} col{col}: {header_label(df, col)}"

    out["pct_higher_ed"] = out["_pct_deug_licence"].fillna(0) + out["_pct_master_doct"].fillna(0)
    out.loc[out["_pct_deug_licence"].isna() & out["_pct_master_doct"].isna(), "pct_higher_ed"] = pd.NA
    out = out.drop(columns=["_pct_deug_licence", "_pct_master_doct"])
    column_map["pct_higher_ed"] = "diplome_2014.xlsx col12 + col13: DEUG/Licence + Master/Doctorat (Ensemble), summed"

    out["is_urban"] = out["name14"].str.contains(r"\((?:Mun|Arrond)\.\)", regex=True).astype(int)
    column_map["is_urban"] = "menages_2014.xlsx col7 name suffix '(Mun.)' or '(Arrond.)' -> 1, else 0"

    out["pop_share"] = out["population14"] / out["population14"].sum() * 100
    column_map["pop_share"] = "population14 / sum(population14 over commune rows) * 100"

    return out.drop_duplicates("code14").reset_index(drop=True), column_map


SPEC_2024 = {
    "Population": {
        "age_0_4": 6,
        "age_5_9": 7,
        "age_10_14": 8,
        "pct_illiterate": 34,
        "pct_no_education": 42,
        "activity_rate": 56,
        "unemployment_rate": 57,
        "pct_women_divorced": 149,
    },
    "Ménages": {
        "n_households": 3,
        "hh_size_avg": 4,
        "pct_owner": 13,
        "pct_renter": 14,
        "pct_electricity": 23,
        "pct_water": 24,
    },
}
CODE_COL_2024, LABEL_COL_2024 = 0, 1
POP_COL_2024 = 3  # Population sheet: 'Population municipale'
COMMUNE_LABEL_RE = re.compile(r"^Commune (de |d')")


def extract_2024() -> tuple[pd.DataFrame, dict]:
    sheets = {
        s: pd.read_excel(RAW / "indicateurs_demo_socioeco_2024.xlsx", sheet_name=s, header=None)
        for s in ["Population", "Ménages", "Population_Rurale"]
    }
    column_map = {}

    pop_df = sheets["Population"]
    code = pd.to_numeric(pop_df[CODE_COL_2024], errors="coerce")
    label = pop_df[LABEL_COL_2024].astype(str)
    mask = label.str.match(COMMUNE_LABEL_RE) & code.notna()
    out = pd.DataFrame(
        {
            "code24": code[mask].astype("Int64"),
            "name24": label[mask].str.strip(),
            "population24": to_num(pop_df.loc[mask, POP_COL_2024]),
        }
    )
    column_map["population24"] = (
        f"indicateurs_demo_socioeco_2024.xlsx[Population] col{POP_COL_2024}: {header_label(pop_df, POP_COL_2024)}"
    )

    for sheet, spec in SPEC_2024.items():
        df = sheets[sheet]
        code_s = pd.to_numeric(df[CODE_COL_2024], errors="coerce")
        mask_s = df[LABEL_COL_2024].astype(str).str.match(COMMUNE_LABEL_RE) & code_s.notna()
        for out_name, col in spec.items():
            series = to_num(df.loc[mask_s, col])
            series.index = code_s[mask_s].astype("Int64").values
            out[out_name] = out["code24"].map(series)
            column_map[out_name] = f"indicateurs_demo_socioeco_2024.xlsx[{sheet}] col{col}: {header_label(df, col)}"

    # every commune appears in both milieu sheets ('-' when empty), so presence says nothing: a commune is
    # urban (a municipality) when it has no rural population; matches 2014 '(Mun.)' status for all matched rows
    rur = sheets["Population_Rurale"]
    rur_code = pd.to_numeric(rur[CODE_COL_2024], errors="coerce")
    rur_mask = rur[LABEL_COL_2024].astype(str).str.match(COMMUNE_LABEL_RE) & rur_code.notna()
    rural = rur_code[rur_mask & (to_num(rur[POP_COL_2024]) > 0)].astype("Int64")
    out["is_urban"] = (~out["code24"].isin(set(rural.tolist()))).astype(int)
    column_map["is_urban"] = "no rural population in sheet Population_Rurale -> 1, else 0"

    out["pop_share"] = out["population24"] / out["population24"].sum() * 100
    column_map["pop_share"] = "population24 / sum(population24 over commune rows) * 100"

    return out.drop_duplicates("code24").reset_index(drop=True), column_map


def main() -> tuple[dict, dict]:
    df14, cmap14 = extract_2014()
    df24, cmap24 = extract_2024()
    df14.to_csv(P_COMMUNES[2014], index=False)
    df24.to_csv(P_COMMUNES[2024], index=False)
    cw = pd.read_csv(P_CROSSWALK)
    m14 = df14.code14.isin(set(cw.code14)).sum()
    m24 = df24.code24.isin(set(pd.to_numeric(cw.code24, errors="coerce").dropna().astype("Int64"))).sum()
    print(f"2014: {len(df14)} rows ({m14} in crosswalk); 2024: {len(df24)} rows ({m24} in crosswalk)")
    return cmap14, cmap24
