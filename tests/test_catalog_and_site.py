import json

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


def test_map_json(exported):
    d = json.loads((exported / "map.json").read_text())
    n = len(d["units"])
    assert n == 1475
    assert all(len(v) == n for v in d["values"].values())
    for key in d["values"]:
        ind, year = key.split("|")
        assert str(year) in d["indicators"][ind]["vintages"]
    ids = [u["id"] for u in d["units"]]
    city = d["units"][ids.index("06.141.01.")]
    assert city["name"] == "Casablanca"
    hh = d["values"]["hh_size_avg|2014"][ids.index("06.141.01.")]
    assert 3 < hh < 6  # a mean, not a sum over arrondissements


def test_geojson_aligns_with_units(exported):
    g = json.loads((exported / "communes.geojson").read_text())
    assert sorted(f["properties"]["i"] for f in g["features"]) == list(range(1475))


def test_downloads(exported):
    c = json.loads((exported / "catalog.json").read_text())
    names = set(c["sizes"])
    assert any(n.endswith(".zip") for n in names)
    for f in c["files"]:
        assert {f"{f['stem']}.csv", f"{f['stem']}.parquet"} <= names
    assert {"communes.gpkg", "communes_queen.gal", "data_dictionary.csv"} <= names
