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
        if f.name != "index.json":
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


def test_geojson_aligns_with_units(exported):
    g = json.loads((exported / "communes.geojson").read_text())
    assert sorted(f["properties"]["i"] for f in g["features"]) == list(range(1502))


def test_downloads(exported):
    c = json.loads((exported / "catalog.json").read_text())
    names = set(c["sizes"])
    assert any(n.endswith(".zip") for n in names)
    for f in c["files"]:
        assert {f"{f['stem']}.csv", f"{f['stem']}.parquet"} <= names
    assert {"communes.gpkg", "communes_queen.gal", "data_dictionary.csv"} <= names


def test_hcp_boundary_layer(exported):
    g = json.loads((exported / "communes_hcp2024.geojson").read_text())
    ids = sorted(f["properties"]["i"] for f in g["features"])
    assert ids == list(range(1503))  # every map unit, including those without a Thiessen cell
