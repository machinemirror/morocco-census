import json

import geopandas as gpd
import pandas as pd
import pytest

from morocco_census.config import (
    P_COMMUNES,
    P_CROSSCHECK,
    P_CROSSWALK,
    P_CROSSWALK_APP,
    P_GPKG,
    P_INDICES_2004,
    P_PANEL,
    P_SEEDS,
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


def test_app_crosswalk_is_one_to_one(cw):
    app = pd.read_csv(P_CROSSWALK_APP, dtype=str)
    assert len(app) >= 1478
    assert app.code14.is_unique and app.app_code.is_unique
    assert set(app.code14) <= set(cw.code14)


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
    sums = arr.groupby(arr.code14.str[:10]).population14.sum()
    pd.testing.assert_series_equal(city.population14.sort_index(), sums.sort_index(), check_names=False)


def test_is_urban():
    t14 = pd.read_csv(P_COMMUNES[2014])
    t24 = pd.read_csv(P_COMMUNES[2024])
    assert t14.is_urban.sum() == 256  # 215 municipalities + 41 arrondissements
    assert 150 < t24.is_urban.sum() < 400  # never "every commune"


def test_shares_sum_to_100():
    for y in (2014, 2024):
        assert pd.read_csv(P_COMMUNES[y]).pop_share.sum() == pytest.approx(100)


def test_geometry():
    cells = gpd.read_file(P_GPKG, layer="thiessen")
    pts = gpd.read_file(P_GPKG, layer="points")
    assert len(cells) == len(pts) == 1497
    assert cells.unit.is_unique and set(cells.unit) == set(pts.unit)
    assert cells.geometry.is_valid.all()
    assert set(pts.pt_src) == {"geonames", "wikidata"}  # openly licensed gazetteers only


def test_seed_review():
    review = pd.read_csv(SEED_REVIEW, dtype=str)
    check = pd.read_csv(P_CROSSCHECK, dtype={"unit": str})
    assert review.unit.is_unique and review.source.isin(["geonames", "wikidata"]).all()
    assert set(review.unit) <= set(check.unit[check.flag])  # a review only settles a disagreement
    assert check.loc[check.flag, "decided_by"].isin(["review", "anchor"]).all()
    seeds = pd.read_csv(P_SEEDS, dtype={"unit": str}).set_index("unit")
    assert (seeds.loc[review.unit, "pt_src"].to_numpy() == review.source.to_numpy()).all()


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
    assert v["seeds"]["placed"] == len(gpd.read_file(P_GPKG, layer="points"))
    for y, n in (("2014", 1538), ("2024", 1503)):
        p = v["population"][y]
        assert p["communes"] == p["in_legal_list"] == n
        assert p["sum_table"] <= p["national_legal"]  # the legal count adds population counted separately
