import json

import numpy as np
import pytest

from morocco_census import catalog, site


def test_catalogue_matches_tables():
    assert catalog.problems(catalog.load()) == []


def test_every_indicator_is_used():
    cat = catalog.load()
    used = {spec["indicator"] for ds in cat["datasets"] for spec in ds["columns"].values() if "indicator" in spec}
    assert used == set(cat["indicators"])


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    mp = pytest.MonkeyPatch()
    mp.setattr(site, "SITE", out)
    site.main()
    mp.undo()
    return out / "data"


def test_map_data(exported):
    d = json.loads((exported / "map" / "index.json").read_text())
    ids = d["units"]["id"]
    n = len(ids)
    assert n == 1503
    assert all(len(col) == n for col in d["units"].values())
    cat = catalog.load()
    assert set(d["indicators"]) == catalog.on_map(cat) and len(d["indicators"]) == 50
    for ind in d["indicators"].values():
        assert set(ind["vintages"]) == {2004, 2014, 2024} or set(ind["vintages"]) == {"2004", "2014", "2024"}
    values = {}
    for f in (exported / "map").glob("*.json"):
        if f.name != "index.json" and f.name.count(".") == 1:
            values |= json.loads(f.read_text())
    assert {ind["group"] for ind in d["indicators"].values()} == set(d["groups"])
    assert sum(1 for ind in d["indicators"].values() if ind.get("fr") and ind.get("ar")) == 48
    assert all(len(v) == n for v in values.values())
    assert {k.split("|")[0] for k in values} == set(d["indicators"])
    i = ids.index("06.141.01.")
    assert d["units"]["name"][i] == "Casablanca" and d["units"]["name_ar"][i] == "الدار البيضاء"
    assert d["provinces"][d["units"]["prov"][i]]["fr"] == "Préfecture de Casablanca"
    assert all(d["units"]["name_fr"]) and all(d["units"]["name_ar"])
    hh = values["hh_size_avg|2014"][i]
    assert 3 < hh < 6  # a mean, not a sum over arrondissements
    for ind in d["indicators"].values():
        for b in ind["breaks"].values():
            assert b["edges"] == sorted(set(b["edges"])) and 1 <= len(b["edges"]) <= 6
    assert d["indicators"]["lang_hassania"]["breaks"]["all"]["method"].endswith("+zero")
    slices = {ind: set(x["slices"]) for ind, x in d["indicators"].items()}
    assert slices["pct_electricity"] == {"urban", "rural"}
    assert slices["pct_married"] == {"urban", "rural", "male", "female"}
    for ind, sls in slices.items():
        for sl in sls:
            v = json.loads((exported / "map" / f"{d['indicators'][ind]['theme']}.{sl}.json").read_text())
            assert all(len(v[f"{ind}|{y}"]) == n for y in (2004, 2014, 2024))


def test_level_breaks():
    rng = np.random.default_rng(0)
    skewed = rng.lognormal(8, 1.5, 3000)  # like population: Jenks on logs, not a class for the three largest
    edges, method = site.level_breaks(skewed)
    classes = np.searchsorted(edges, skewed, side="left")
    assert np.bincount(classes).min() / len(skewed) >= site.MIN_CLASS
    zeros = np.concatenate([np.zeros(2000), rng.uniform(0, 100, 1000)])  # like a regional language
    edges, method = site.level_breaks(zeros)
    assert edges[0] == 0 and method.endswith("+zero")
    assert np.allclose(site.fisher_jenks(np.array([1, 1, 2, 2, 10, 11, 12, 50, 51.0]), 3), [2, 12])


def test_boundaries_align_with_units(exported):
    g = json.loads((exported / "communes_hcp2024.geojson").read_text())
    assert sorted(f["properties"]["i"] for f in g["features"]) == list(range(1503))


def test_downloads(exported):
    c = json.loads((exported / "catalog.json").read_text())
    names = set(c["sizes"])
    assert any(n.endswith(".zip") for n in names)
    for f in c["files"]:
        assert {f"{f['stem']}.csv", f"{f['stem']}.parquet"} <= names
    assert {"communes_points.gpkg", "communes_points.geojson", "data_dictionary.csv"} <= names
    assert not {"communes.gpkg", "communes_queen.gal", "communes_thiessen.geojson"} & names
    assert {"hcp_communes_2024.gpkg", "hcp_communes_2024.geojson", "hcp_communes_2024_queen.gal"} <= names


def test_every_column_needs_a_source():
    cat = catalog.load()
    assert catalog.problems(cat) == []
    ds = next(d for d in cat["datasets"] if d["id"] == "crosswalk_communes")
    del ds["source"]
    assert "crosswalk_communes.code14: no source" in catalog.problems(cat)
