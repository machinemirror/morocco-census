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
    "pct_agriculture": ("activite_2014.xlsx", 19),
    "pct_no_diploma": ("diplome_2014.xlsx", 15),
    "_pct_deug_licence": ("diplome_2014.xlsx", 12),
    "_pct_master_doct": ("diplome_2014.xlsx", 13),
    "age_15_19": ("individus_2014.xlsx", 13),
    "age_20_24": ("individus_2014.xlsx", 14),
    "age_25_29": ("individus_2014.xlsx", 15),
    "age_30_34": ("individus_2014.xlsx", 16),
    "age_35_39": ("individus_2014.xlsx", 17),
    "age_40_44": ("individus_2014.xlsx", 18),
    "age_45_49": ("individus_2014.xlsx", 19),
    "age_50_54": ("individus_2014.xlsx", 20),
    "age_55_59": ("individus_2014.xlsx", 21),
    "age_60_64": ("individus_2014.xlsx", 22),
    "age_65_69": ("individus_2014.xlsx", 23),
    "age_70_74": ("individus_2014.xlsx", 24),
    "age_75plus": ("individus_2014.xlsx", 25),
    "pct_disability": ("individus_2014.xlsx", 31),
    "pct_single": ("individus_2014.xlsx", 26),
    "pct_married": ("individus_2014.xlsx", 27),
    "pct_divorced": ("individus_2014.xlsx", 28),
    "pct_widowed": ("individus_2014.xlsx", 29),
    "age_first_marriage": ("individus_2014.xlsx", 30),
    "completed_fertility": ("individus_2014.xlsx", 32),
    "school_enrolment": ("individus_2014.xlsx", 34),
    "edu_preschool": ("individus_2014.xlsx", 41),
    "edu_primary": ("individus_2014.xlsx", 42),
    "edu_lower_secondary": ("individus_2014.xlsx", 43),
    "edu_upper_secondary": ("individus_2014.xlsx", 44),
    "edu_higher": ("individus_2014.xlsx", 45),
    "dipl_primary": ("diplome_2014.xlsx", 9),
    "dipl_lower_secondary": ("diplome_2014.xlsx", 10),
    "dipl_upper_secondary": ("diplome_2014.xlsx", 11),
    "dipl_bachelor": ("diplome_2014.xlsx", 12),
    "dipl_master": ("diplome_2014.xlsx", 13),
    "voc_specialised_technician": ("diplome_2014.xlsx", 16),
    "voc_technician": ("diplome_2014.xlsx", 17),
    "voc_qualification": ("diplome_2014.xlsx", 18),
    "voc_specialisation": ("diplome_2014.xlsx", 19),
    "voc_initiation": ("diplome_2014.xlsx", 20),
    "pct_no_voc_diploma": ("diplome_2014.xlsx", 22),
    "lang_darija": ("individus_2014.xlsx", 46),
    "lang_tachelhit": ("individus_2014.xlsx", 47),
    "lang_tamazight": ("individus_2014.xlsx", 48),
    "lang_tarifit": ("individus_2014.xlsx", 49),
    "lang_hassania": ("individus_2014.xlsx", 50),
    "lit_arabic_only": ("individus_2014.xlsx", 36),
    "lit_arabic_french": ("individus_2014.xlsx", 37),
    "lit_arabic_french_english": ("individus_2014.xlsx", 38),
    "lit_other": ("individus_2014.xlsx", 39),
    "pct_employer": ("individus_2014.xlsx", 55),
    "pct_self_employed": ("individus_2014.xlsx", 56),
    "pct_public_employee": ("individus_2014.xlsx", 57),
    "pct_private_employee": ("individus_2014.xlsx", 58),
    "pct_family_worker": ("individus_2014.xlsx", 59),
    "pct_apprentice": ("individus_2014.xlsx", 60),
    "pct_partner": ("individus_2014.xlsx", 61),
    "pct_status_other": ("individus_2014.xlsx", 62),
    "occ_managers": ("activite_2014.xlsx", 9),
    "occ_technicians": ("activite_2014.xlsx", 10),
    "occ_clerks": ("activite_2014.xlsx", 11),
    "occ_traders": ("activite_2014.xlsx", 12),
    "occ_farmers": ("activite_2014.xlsx", 13),
    "occ_craft": ("activite_2014.xlsx", 14),
    "occ_agri_workers": ("activite_2014.xlsx", 15),
    "occ_operators": ("activite_2014.xlsx", 16),
    "occ_labourers": ("activite_2014.xlsx", 17),
    "occ_unclassified": ("activite_2014.xlsx", 18),
    "sec_industry": ("activite_2014.xlsx", 20),
    "sec_utilities": ("activite_2014.xlsx", 21),
    "sec_construction": ("activite_2014.xlsx", 22),
    "sec_trade": ("activite_2014.xlsx", 23),
    "sec_transport": ("activite_2014.xlsx", 24),
    "sec_services": ("activite_2014.xlsx", 25),
    "sec_public": ("activite_2014.xlsx", 26),
    "sec_other": ("activite_2014.xlsx", 27),
    "dwell_villa": ("menages_2014.xlsx", 12),
    "dwell_apartment": ("menages_2014.xlsx", 13),
    "dwell_moroccan": ("menages_2014.xlsx", 14),
    "dwell_rural": ("menages_2014.xlsx", 16),
    "dwell_other": ("menages_2014.xlsx", 17),
    "persons_per_room": ("menages_2014.xlsx", 18),
    "tenure_other": ("menages_2014.xlsx", 21),
    "dwell_age_lt10": ("menages_2014.xlsx", 22),
    "dwell_age_10_19": ("menages_2014.xlsx", 23),
    "dwell_age_20_49": ("menages_2014.xlsx", 24),
    "dwell_age_50plus": ("menages_2014.xlsx", 25),
    "pct_kitchen": ("menages_2014.xlsx", 26),
    "pct_toilet": ("menages_2014.xlsx", 27),
    "pct_bathroom": ("menages_2014.xlsx", 28),
    "sewer_public": ("menages_2014.xlsx", 31),
    "sewer_septic": ("menages_2014.xlsx", 32),
    "sewer_other": ("menages_2014.xlsx", 33),
    "waste_bin": ("menages_2014.xlsx", 34),
    "waste_truck": ("menages_2014.xlsx", 35),
    "waste_other": ("menages_2014.xlsx", 36),
    "cook_gas": ("menages_2014.xlsx", 37),
    "cook_electricity": ("menages_2014.xlsx", 38),
    "cook_charcoal": ("menages_2014.xlsx", 39),
    "cook_wood": ("menages_2014.xlsx", 40),
    "cook_dung": ("menages_2014.xlsx", 41),
    "road_distance": ("menages_2014.xlsx", 50),
    "pct_radio": ("menages_2014.xlsx", 43),
    "pct_landline": ("menages_2014.xlsx", 45),
    "pct_computer": ("menages_2014.xlsx", 47),
    "pct_satellite": ("menages_2014.xlsx", 48),
    "pct_fridge": ("menages_2014.xlsx", 49),
    "isf": ("individus_2014.xlsx", 33),
    "pct_no_education": ("individus_2014.xlsx", 40),
    "pct_slum": ("menages_2014.xlsx", 15),
    "pct_tv": ("menages_2014.xlsx", 42),
}
# {output_name: (file, [columns])}: shares summed across source columns
SUMS_2014 = {
    "age_60plus": ("individus_2014.xlsx", [22, 23, 24, 25]),
    "age_65plus": ("individus_2014.xlsx", [23, 24, 25]),
}
POP_COL_2014 = 9  # menages_2014.xlsx: col8 = population légale, col9 = population municipale
NAME_COL_2014, CODE_COL_2014 = 7, 6


def extract_2014() -> tuple[pd.DataFrame, dict]:
    files = {f for f, _ in [*SPEC_2014.values(), *SUMS_2014.values()]} | {"menages_2014.xlsx", "individus_2014.xlsx"}
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

    for out_name, (fname, cols) in SUMS_2014.items():
        df = raws[fname]
        code_f = df[CODE_COL_2014].astype(str)
        mask_f = code_f.str.count(r"\.") == 4
        series = pd.concat([to_num(df.loc[mask_f, c]) for c in cols], axis=1).sum(axis=1, min_count=1)
        series.index = code_f[mask_f].values
        out[out_name] = out["code14"].map(series)
        column_map[out_name] = f"{fname} cols {cols}: summed"

    ind = raws["individus_2014.xlsx"]
    code_i = ind[CODE_COL_2014].astype(str)
    mask_i = code_i.str.count(r"\.") == 4
    female = to_num(ind.loc[mask_i, 117]) / to_num(ind.loc[mask_i, 9]) * 100
    female.index = code_i[mask_i].values
    out["pct_female"] = out["code14"].map(female)
    column_map["pct_female"] = "individus_2014.xlsx col117 / col9: Féminin / Ensemble population municipale, x 100"

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
        "age_15_19": 9,
        "age_20_24": 10,
        "age_25_29": 11,
        "age_30_34": 12,
        "age_35_39": 13,
        "age_40_44": 14,
        "age_45_49": 15,
        "age_50_54": 16,
        "age_55_59": 17,
        "age_60_64": 18,
        "age_65_69": 19,
        "age_70_74": 20,
        "age_75plus": 21,
        "pct_disability": 30,
        "pct_single": 23,
        "pct_married": 24,
        "pct_divorced": 25,
        "pct_widowed": 26,
        "age_first_marriage": 27,
        "completed_fertility": 29,
        "school_enrolment": 32,
        "pct_illiterate_15plus": 36,
        "edu_preschool": 43,
        "edu_primary": 44,
        "edu_lower_secondary": 45,
        "edu_upper_secondary": 46,
        "edu_higher": 47,
        "lang_darija": 48,
        "lang_tachelhit": 49,
        "lang_tamazight": 50,
        "lang_tarifit": 51,
        "lang_hassania": 52,
        "read_arabic": 38,
        "read_tifinagh": 39,
        "read_english": 40,
        "read_french": 41,
        "pct_employer": 59,
        "pct_self_employed": 60,
        "pct_public_employee": 61,
        "pct_private_employee": 62,
        "pct_family_worker": 63,
        "pct_apprentice": 64,
        "pct_partner": 65,
        "pct_status_other": 66,
        "pct_female": 5,
        "isf": 28,
        "pop_active_occupee": 58,
    },
    "Ménages": {
        "n_households": 3,
        "hh_size_avg": 4,
        "pct_owner": 13,
        "pct_renter": 14,
        "pct_electricity": 23,
        "pct_water": 24,
        "dwell_villa": 6,
        "dwell_apartment": 7,
        "dwell_moroccan": 8,
        "dwell_rural": 10,
        "dwell_other": 11,
        "persons_per_room": 12,
        "tenure_other": 15,
        "dwell_age_lt10": 16,
        "dwell_age_10_19": 17,
        "dwell_age_20_49": 18,
        "dwell_age_50plus": 19,
        "pct_kitchen": 20,
        "pct_toilet": 21,
        "pct_bathroom": 22,
        "sewer_public": 25,
        "sewer_septic": 26,
        "sewer_other": 27,
        "waste_bin": 28,
        "waste_truck": 29,
        "cook_gas": 32,
        "cook_electricity": 33,
        "cook_charcoal": 34,
        "cook_wood": 35,
        "cook_other": 36,
        "road_distance": 37,
        "pct_slum": 9,
    },
}
SUMS_2024 = {
    "Population": {
        "age_60plus": [18, 19, 20, 21],
        "age_65plus": [19, 20, 21],
    },
    "Ménages": {
        "waste_other": [30, 31],
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

    for sheet, spec in SUMS_2024.items():
        df = sheets[sheet]
        code_s = pd.to_numeric(df[CODE_COL_2024], errors="coerce")
        mask_s = df[LABEL_COL_2024].astype(str).str.match(COMMUNE_LABEL_RE) & code_s.notna()
        for out_name, cols in spec.items():
            series = pd.concat([to_num(df.loc[mask_s, c]) for c in cols], axis=1).sum(axis=1, min_count=1)
            series.index = code_s[mask_s].astype("Int64").values
            out[out_name] = out["code24"].map(series)
            column_map[out_name] = f"indicateurs_demo_socioeco_2024.xlsx[{sheet}] cols {cols}: summed"

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

    out = extras_2024(out.drop_duplicates("code24").reset_index(drop=True), column_map)
    return out, column_map


# Other 2024 workbooks, joined to the indicators file on code24 (commune rows only).
TRANSPORT_2024 = {  # transport_domicile_travail_2024.xlsx, sheet Ensemble: % of employed sedentary 15+
    "commute_walk": 3,
    "commute_two_wheeler": 4,
    "commute_car": 5,
    "commute_bus": 6,
    "commute_taxi": 7,
    "commute_employer": 8,
    "commute_train": 9,
    "commute_tram": 10,
    "commute_informal": 11,
    "commute_animal": 12,
    "commute_other": 13,
    "commute_none": 14,
}
MIGRATION_2024 = {  # migration_interne_2024.xlsx: in-migration and out-migration indices (%)
    "Migration interne durée de vie": {"mig_in_lifetime": 6, "mig_out_lifetime": 8},
    "Mig_interne-10ans": {"mig_in_10y": 6, "mig_out_10y": 8},
    "Mig-interne-5ans ": {"mig_in_5y": 6, "mig_out_5y": 8},
    "Migration internationale": {"n_lived_abroad": 2},
}
URBAN_HOUSING_2024 = {  # parc_logement_urbain_2024.xlsx: urban dwellings, occupied or not
    "n_urban_dwellings": 2,
    "uh_occupied": 3,
    "uh_vacant": 4,
    "uh_secondary": 5,
    "uh_villa": 7,
    "uh_apartment": 8,
    "uh_moroccan_traditional": 9,
    "uh_moroccan_modern": 10,
    "uh_slum": 12,
    "uh_rural": 13,
    "uh_other": 14,
    "uh_age_lt20": 16,
    "uh_age_20_49": 17,
    "uh_age_50plus": 18,
    "uh_walls_concrete": 46,
    "uh_roof_slab": 49,
    "uh_grid_electricity": 53,
    "uh_grid_water": 54,
    "uh_grid_sewer": 55,
    "uh_deficit_rate": 56,
}
ESTAB_COUNTS_2024 = {  # cee_etablissements_eco_2024.xlsx: counts
    "n_establishments": 7,
    "n_public_services": 8,
    "n_nonprofits": 9,
    "n_souks": 10,
    "n_firms": 11,
    "n_firm_jobs": 12,
}
ESTAB_SHARES_2024 = {  # % of for-profit establishments (col 11)
    "firms_industry": [13],
    "firms_construction": [14],
    "firms_trade": [15],
    "firms_services": [16],
    "firms_size_1": [17],
    "firms_size_2_3": [18],
    "firms_size_4_9": [19],
    "firms_size_10plus": [20, 21],
    "firms_since_2011": [27, 28],
}
DOUAR_POP_2024 = {"rural_foreign": 11, "rural_civil_registration": 17}  # population-weighted douar means
DOUAR_HH_2024 = {  # household-weighted douar means
    "rural_dwell_hard": 15,
    "rural_dwell_pise": 16,
    "dist_track": 19,
    "dist_primary_school": 20,
    "dist_lower_secondary": 21,
    "dist_upper_secondary": 22,
    "dist_health": 23,
}
DOUAR_TYPES = {"douar_grouped": "دوار مجمع", "douar_fragmented": "دوار مجزأ", "douar_dispersed": "دوار مشتت"}


def commune_rows(df: pd.DataFrame) -> pd.DataFrame:
    code = pd.to_numeric(df[CODE_COL_2024], errors="coerce")
    m = df[LABEL_COL_2024].astype(str).str.match(COMMUNE_LABEL_RE) & code.notna()
    return df[m].set_axis(code[m].astype("Int64").values)


def extras_2024(out: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    cols = {}
    tr = commune_rows(pd.read_excel(RAW / "transport_domicile_travail_2024.xlsx", sheet_name="Ensemble", header=None))
    for k, c in TRANSPORT_2024.items():
        cols[k] = out.code24.map(to_num(tr[c]))
        column_map[k] = f"transport_domicile_travail_2024.xlsx[Ensemble] col{c}"
    for sheet, spec in MIGRATION_2024.items():
        mg = commune_rows(pd.read_excel(RAW / "migration_interne_2024.xlsx", sheet_name=sheet, header=None))
        for k, c in spec.items():
            cols[k] = out.code24.map(to_num(mg[c]))
            column_map[k] = f"migration_interne_2024.xlsx[{sheet.strip()}] col{c}"
    uh = commune_rows(pd.read_excel(RAW / "parc_logement_urbain_2024.xlsx", sheet_name=0, header=None))
    for k, c in URBAN_HOUSING_2024.items():
        cols[k] = out.code24.map(to_num(uh[c]))
        column_map[k] = f"parc_logement_urbain_2024.xlsx col{c}"

    # establishments use 2024 codes written as dotted segments; arrondissements are summed into their city
    ce = pd.read_excel(RAW / "cee_etablissements_eco_2024.xlsx", sheet_name=0, header=None, dtype=str)
    ce = ce[ce[4].notna() & ce[0].str.fullmatch(r"\d+", na=False)]
    key7 = ce[1].str.zfill(3) + ce[2].str.zfill(2) + ce[4].str.zfill(2)
    by7 = {str(c)[-7:]: c for c in out.code24}
    city = {str(c)[1:6]: c for c in out.code24 if len(str(c)) == 7}
    arr = ce[6].str.startswith("Arrondissement")
    code = key7.map(by7).where(~arr, key7.str[:5].map(city))
    counts = ce[range(7, 29)].apply(to_num).groupby(code.values).sum(min_count=1)
    for k, c in ESTAB_COUNTS_2024.items():
        cols[k] = out.code24.map(counts[c])
        column_map[k] = f"cee_etablissements_eco_2024.xlsx col{c} (arrondissements summed into cities)"
    for k, cs in ESTAB_SHARES_2024.items():
        cols[k] = out.code24.map(counts[cs].sum(axis=1, min_count=1) / counts[11] * 100)
        column_map[k] = f"cee_etablissements_eco_2024.xlsx cols {cs} / col11 x 100"
    pop = out.population24.where(out.population24 > 0).astype(float)
    cols["establishments_per_1000"] = cols["n_establishments"] / pop * 1000
    cols["firm_jobs_per_1000"] = cols["n_firm_jobs"] / pop * 1000
    cols["pct_lived_abroad"] = cols["n_lived_abroad"] / pop * 100
    column_map.update(
        establishments_per_1000="n_establishments / population24 x 1000",
        firm_jobs_per_1000="n_firm_jobs / population24 x 1000",
        pct_lived_abroad="n_lived_abroad / population24 x 100",
    )

    # douars: rural communes only; the douar code is province(3, leading zero dropped) cercle(2) commune(2)
    # milieu(1) fraction(2) douar(3), so the commune is the last 7 digits of code24
    xl = RAW / "population_menages_douars_2024.xlsx"
    dp, dh = (pd.read_excel(xl, sheet_name=i, header=None) for i in (0, 1))
    ok = pd.to_numeric(dp[0], errors="coerce").notna() & dp[0].astype(str).str.len().between(11, 13)
    dp, dh = dp[ok], dh[ok]
    com = dp[0].astype("int64").astype(str).str[:-6].str.zfill(7).map(by7)
    popw, hhw = to_num(dp[9]).fillna(0), to_num(dh[8]).fillna(0)

    def wmean(vals, w):
        num = (vals * w).groupby(com.values).sum(min_count=1)
        den = w.where(vals.notna(), 0).groupby(com.values).sum()
        return num / den.where(den > 0)

    for k, c in DOUAR_POP_2024.items():
        cols[k] = out.code24.map(wmean(to_num(dp[c]), popw))
        column_map[k] = f"population_menages_douars_2024.xlsx[0] col{c}, population-weighted over douars"
    for k, c in DOUAR_HH_2024.items():
        cols[k] = out.code24.map(wmean(to_num(dh[c]), hhw))
        column_map[k] = f"population_menages_douars_2024.xlsx[1] col{c}, household-weighted over douars"
    cols["n_douars"] = out.code24.map(com.value_counts())
    for k, label in DOUAR_TYPES.items():
        cols[k] = out.code24.map(
            popw.where(dp[7] == label, 0).groupby(com.values).sum() / popw.groupby(com.values).sum() * 100
        )
        column_map[k] = f"population_menages_douars_2024.xlsx: population in '{label}' douars / rural population x 100"
    column_map["n_douars"] = "population_menages_douars_2024.xlsx: douars per commune"
    return pd.concat([out, pd.DataFrame(cols)], axis=1)


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
