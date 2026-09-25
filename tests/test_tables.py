import json

import geopandas as gpd
import pandas as pd
import pytest

from morocco_census.config import (
    LINK_REVIEW,
    P_COMMUNES,
    P_CROSSCHECK,
    P_CROSSWALK,
    P_CROSSWALK_APP,
    P_INDICES_2004,
    P_PANEL,
    P_POINTS,
    P_SEEDS,
    P_SLICES,
    SEED_NAMES,
    SEED_REVIEW,
)
from morocco_census.validate import P_VALIDATION


@pytest.fixture(scope="module")
def cw():
    return pd.read_csv(P_CROSSWALK, dtype={"code14": str})


@pytest.fixture(scope="module")
def panel():
    return pd.read_csv(P_PANEL, dtype={"code14": str})


def test_row_counts_and_keys():
    t04 = pd.read_csv(P_COMMUNES[2004], dtype={"app_code": str})
    t14 = pd.read_csv(P_COMMUNES[2014], dtype={"code14": str})
    t24 = pd.read_csv(P_COMMUNES[2024])
    assert (len(t04), len(t14), len(t24)) == (1689, 1538, 1503)
    assert t04.app_code.is_unique and t04.app_code.str.len().eq(10).all()
    assert t14.code14.is_unique and t14.code14.str.fullmatch(r"\d{2}\.\d{3}\.\d{2}\.\d{2}\.").all()
    assert t24.code24.is_unique
    assert len(pd.read_csv(P_INDICES_2004)) == 1677


def test_crosswalk_coverage(cw):
    assert len(cw) == 1538 and cw.code14.is_unique
    full = cw.dropna(subset=["code24", "label04"])
    assert len(full) / len(cw) >= 0.953
    assert set(cw.src04.dropna()) <= {"direct", "fuzzy"}
    t14 = pd.read_csv(P_COMMUNES[2014], dtype={"code14": str})
    assert set(t14.code14) == set(cw.code14)


def test_app_crosswalk(cw):
    app = pd.read_csv(P_CROSSWALK_APP, dtype={"app_code": str, "code14": str})
    assert set(app.code14) <= set(cw.code14) and not app.duplicated(["app_code", "code14"]).any()
    # a split unit's parts share its counts; below 1 where HCP does not say where the rest went
    assert app.groupby("app_code").weight.sum().le(1.0005).all()
    assert set(app.app_code[app.weight < 1]) == set(app.app_code[app.link == "split"])
    assert app.code14.nunique() >= 1537
    assert set(app.link) == {"exact", "fuzzy", "province_split", "centre", "review", "split"}
    # a centre (milieu digit 3-5) shares its rural commune's link, unless a review moved that commune (the rural
    # remainder renamed when the centre became a municipality)
    review = pd.read_csv(LINK_REVIEW, dtype=str, keep_default_na=False)
    by_code = app[app.link != "split"].set_index("app_code").code14
    centres = app[app.link == "centre"]
    parent = centres.app_code.str[:9] + "2"
    kept = ~parent.isin(review.app_code)
    assert (centres.code14[kept].to_numpy() == parent[kept].map(by_code).to_numpy()).all()
    assert review.evidence.notna().all() and not review.duplicated(["app_code", "code14"]).any()
    linked = set(zip(app.app_code, app.code14))
    placed = review[review.code14 != ""]
    assert all(pair in linked for pair in zip(placed.app_code, placed.code14))
    assert not app.app_code.isin(review.app_code[review.code14 == ""]).any()  # reviewed as unlinked


def test_panel(panel):
    core = panel[panel.level == "commune"]
    assert len(core) == 1538 and (panel.level == "city").sum() == 6
    assert set(panel.src04.dropna()) <= {"direct", "fuzzy", "imputed_cercle", "imputed_province"}
    assert set(panel.src14.dropna()) | set(panel.src24.dropna()) <= {"imputed_cercle", "imputed_province"}
    assert core.idh04.notna().all() and core.mpi2014.notna().all() and core.mpi2024.notna().all()
    assert core.idh04.between(0, 1).all()


def test_city_rows_sum_population(panel):
    city = panel[panel.level == "city"].set_index("code14")
    arr = panel[(panel.level == "commune") & panel.name14.str.contains(r"\(Arrond", na=False)]
    sums = arr.groupby(arr.code14.str[:10]).pop_legal14.sum()
    pd.testing.assert_series_equal(city.pop_legal14.sort_index(), sums.sort_index(), check_names=False)


def test_2024_join_keeps_every_commune():
    cw = pd.read_csv(P_CROSSWALK, dtype=str)
    t24 = pd.read_csv(P_COMMUNES[2024], dtype=str)
    assert set(cw.code24_commune) == set(t24.code24)
    joined = cw.drop_duplicates("code24_commune").merge(t24, left_on="code24_commune", right_on="code24")
    assert len(joined) == 1503
    assert pd.to_numeric(joined.population24).sum() == pd.to_numeric(t24.population24).sum()


def test_panel_keys_are_text_and_unshared():
    p = pd.read_csv(P_PANEL, dtype=str)
    t24 = pd.read_csv(P_COMMUNES[2024], dtype=str)
    assert not p.code24.str.endswith(".0").any()
    city = p[p.level == "city"]
    assert city.code24_commune.isin(t24.code24).all() and city.code24.notna().all()
    # a column shared with the 2014 table must mean the same thing there
    t14 = pd.read_csv(P_COMMUNES[2014], nrows=0)
    assert "population14" not in p.columns and "pop_legal14" in t14.columns


def test_annex_links_are_clean():
    cw = pd.read_csv(P_CROSSWALK, dtype=str)
    labels = pd.read_csv(P_INDICES_2004, dtype=str).label
    assert not labels.str.match(r"(Notation|Vulné|bilité|communaux |de |la )").any()
    assert cw.label04.dropna().isin(labels).all() and cw.label04.dropna().is_unique
    # communes carved out in 2008 have no 2004 annex row of their own
    assert cw.set_index("code14").loc[["04.441.03.05.", "06.385.03.03."], "label04"].isna().all()
    # every annex-linked commune carries its own 2004 values, not an imputation
    p = pd.read_csv(P_PANEL, dtype=str)
    linked = p.code14.isin(cw.code14[cw.label04.notna()])
    assert p.loc[linked, "src04"].isin(["direct", "fuzzy"]).all()


def test_is_urban():
    t14 = pd.read_csv(P_COMMUNES[2014])
    t24 = pd.read_csv(P_COMMUNES[2024])
    assert t14.is_urban.sum() == 256  # 215 municipalities + 41 arrondissements
    assert 150 < t24.is_urban.sum() < 400  # never "every commune"


def test_shares_sum_to_100():
    for y in (2014, 2024):
        assert pd.read_csv(P_COMMUNES[y]).pop_share.sum() == pytest.approx(100)


def test_geometry():
    pts = gpd.read_file(P_POINTS, layer="points")
    assert len(pts) == 1502 and pts.unit.is_unique
    assert set(pts.pt_src) == {"geonames", "wikidata"}  # openly licensed gazetteers only


def test_seed_review():
    review = pd.read_csv(SEED_REVIEW, dtype=str)
    check = pd.read_csv(P_CROSSCHECK, dtype={"unit": str})
    assert review.unit.is_unique and review.source.isin(["geonames", "wikidata"]).all()
    assert set(review.unit) <= set(check.unit[check.flag])  # a review only settles a disagreement
    assert check.loc[check.flag, "decided_by"].isin(["review", "anchor"]).all()
    seeds = pd.read_csv(P_SEEDS, dtype={"unit": str}).set_index("unit")
    assert (seeds.loc[review.unit, "pt_src"].to_numpy() == review.source.to_numpy()).all()


@pytest.mark.parametrize("year,key", [(2014, "code14"), (2024, "code24")])
def test_slices_add_up(year, key):
    pop = f"population{str(year)[2:]}"
    total = pd.read_csv(P_COMMUNES[year], dtype={key: str}).set_index(key)[pop]
    for kind, values in (("milieu", {"urban", "rural"}), ("sex", {"male", "female"})):
        t = pd.read_csv(P_SLICES[year, kind], dtype={key: str})
        assert set(t[kind]) == values and not t.duplicated([key, kind]).any()
        parts = t.groupby(key)[pop].sum()
        assert (parts == total.reindex(parts.index)).all()
    widowed = pd.read_csv(P_SLICES[year, "sex"]).groupby("sex").pct_widowed.median()
    assert widowed["female"] > widowed["male"]


def test_2004_slices():
    t04 = pd.read_csv(P_COMMUNES[2004], dtype={"app_code": str}).set_index("app_code")
    assert t04.milieu04.eq("rural").eq(t04.index.str.endswith("2")).all()
    assert abs(t04.population04[t04.milieu04 == "urban"].sum() / 16463634 - 1) < 0.01  # HCP's 2004 urban total
    sex = pd.read_csv(P_SLICES[2004, "sex"], dtype={"app_code": str})
    assert (sex.groupby("app_code").population04.sum() == t04.population04.reindex(sex.app_code.unique())).all()
    marital = sex[["pct_single", "pct_married", "pct_divorced", "pct_widowed"]].sum(axis=1)
    assert marital[marital > 0].between(99.9, 100.1).all()


def test_seed_names_place_their_units():
    names = pd.read_csv(SEED_NAMES, dtype=str)
    seeds = pd.read_csv(P_SEEDS, dtype={"unit": str}).set_index("unit")
    assert set(names.unit) <= set(seeds.index)


def test_hcp_names_2024():
    t24 = pd.read_csv(P_COMMUNES[2024])
    assert t24.name24_ar.str.startswith("جماعة ").all()
    assert t24.province24.str.match(r"(Province|Préfecture) ").all()
    assert t24.province24_ar.str.match(r"(إقليم|عمالة) ").all()


def test_shares_and_2004_gaps():
    t04 = pd.read_csv(P_COMMUNES[2004])
    t14 = pd.read_csv(P_COMMUNES[2014])
    t24 = pd.read_csv(P_COMMUNES[2024])
    assert t14.pct_female.median() == pytest.approx(49.8, abs=0.5)
    assert t24.pct_female.median() == pytest.approx(49.7, abs=0.5)
    ages = [f"age_{a}_{a + 4}" for a in range(0, 75, 5)] + ["age_75plus"]
    assert t24[ages].sum(axis=1).dropna().between(99, 101).mean() > 0.99
    # construction year is published for urban households only; rural pages must not read as 0%
    rural = t04.dwell_rural > 50
    assert t04.loc[rural, "dwell_age_lt10"].isna().mean() > 0.95
    assert t04.pct_women_divorced.between(0, 100).all()


def test_other_2024_workbooks():
    t24 = pd.read_csv(P_COMMUNES[2024])
    assert t24.n_establishments.sum() == 1304564  # CEE national total, arrondissements summed into cities
    assert t24.n_douars.sum() == 33189
    modes = [c for c in t24 if c.startswith("commute_")]
    assert t24[modes].sum(axis=1).dropna().between(99, 101).mean() > 0.98
    douars = t24[["douar_grouped", "douar_fragmented", "douar_dispersed"]].dropna()
    assert douars.sum(axis=1).between(99.9, 100.1).all()
    assert t24.n_urban_dwellings.notna().sum() == 380


def test_validation_report_matches_tables():
    v = json.loads(P_VALIDATION.read_text())
    cw = pd.read_csv(P_CROSSWALK, dtype=str)
    assert v["linkage"]["linked_all_three"] == (cw.code24.notna() & cw.label04.notna()).sum()
    assert v["linkage"]["linked_2004_profiles"] == pd.read_csv(P_CROSSWALK_APP, dtype=str).code14.nunique()
    assert v["linkage"]["unlinked_2024"] == []
    b = v["backcast_2004"]  # our linked 2004 population against HCP's figures on 2014 boundaries
    parts = [b[k] for k in ("calibrated", "one_to_one", "other_links")]
    assert sum(x["communes"] for x in parts) == b["communes"] == 35
    assert sum(x["within_2pct"] for x in parts) == b["within_2pct"]
    assert len(b["largest_gaps"]) == b["communes"] - b["within_2pct"]
    assert v["seeds"]["placed"] == len(gpd.read_file(P_POINTS, layer="points"))
    for y, n in (("2014", 1538), ("2024", 1503)):
        p = v["population"][y]
        assert p["communes"] == p["in_legal_list"] == n
        assert p["sum_table"] <= p["national_legal"]  # the legal count adds population counted separately
