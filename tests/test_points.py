"""The seed-point invariant (geometry.check_points) on the published points, and poisoned copies that must fail it."""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from morocco_census import geometry
from morocco_census.config import P_POINTS, P_SEEDS

LAAYOUNE = "11.321.01.03."


@pytest.fixture(scope="module")
def built():
    return gpd.read_file(P_POINTS, layer="points"), geometry.polygons(), geometry.review_table()


def poisoned(pts, unit, **changes):
    p = pts.copy()
    i = p.index[p.unit == unit][0]
    for k, v in changes.items():
        p.loc[i, k] = v
    return p


def test_published_points_satisfy_the_invariant(built):
    pts, polys, review = built
    assert geometry.check_points(pts, polys, review) == []
    assert len(pts) == len(polys) == 1503
    assert pts.geometry.within(polys.geometry.reindex(pts.unit).set_axis(pts.index)).all()


def test_seeds_file_matches_the_points(built):
    pts = built[0].set_index("unit")
    seeds = pd.read_csv(P_SEEDS, dtype={"unit": str, "source_id": str}).set_index("unit").reindex(pts.index)
    assert (seeds.lon - pts.geometry.x).abs().max() < 1e-5 and (seeds.lat - pts.geometry.y).abs().max() < 1e-5
    assert (seeds.pt_src == pts.pt_src).all() and (seeds.pt_rule == pts.pt_rule).all()


def test_laayoune_is_the_city(built):
    pts = built[0].set_index("unit")
    p = pts.geometry[LAAYOUNE]
    assert pts.feature[LAAYOUNE].startswith("PPL")
    assert geometry.km([p.x], [p.y], [-13.20], [27.15])[0] < 3  # not GeoNames' ADM3 point 14 km east


def test_poison_point_outside_its_polygon(built):
    pts, polys, review = built
    bad = geometry.check_points(poisoned(pts, LAAYOUNE, geometry=Point(-13.06349, 27.18064)), polys, review)
    assert any(b.startswith(LAAYOUNE) and "outside its HCP polygon" in b for b in bad)


def test_poison_point_in_another_province(built):
    # the dissertation-era failure: Chahda (Safi) matched to a namesake 510 km away
    pts, polys, review = built
    unit = "07.431.03.02."
    bad = geometry.check_points(poisoned(pts, unit, geometry=Point(-5.43, 28.0)), polys, review)
    assert any(b.startswith(unit) and "outside its HCP polygon" in b for b in bad)
    assert any(b.startswith(unit) and "nearest point of its province" in b for b in bad)


def test_poison_point_at_province_centroid(built):
    pts, polys, review = built
    unit = "07.431.03.02."
    safi = polys[polys.index.str.startswith("07.431")].to_crs(geometry.UTM).union_all().centroid
    c = gpd.GeoSeries([safi], crs=geometry.UTM).to_crs(4326).iloc[0]
    bad = geometry.check_points(poisoned(pts, unit, geometry=c), polys, review)
    assert any(b.startswith(unit) and "province's centroid" in b for b in bad)


def test_poison_municipality_at_an_admin_feature(built):
    pts, polys, review = built
    bad = geometry.check_points(poisoned(pts, LAAYOUNE, feature="ADM3"), polys, review)
    assert any(b.startswith(LAAYOUNE) and "not an allowed feature" in b for b in bad)


def test_poison_missing_and_shared_points(built):
    pts, polys, review = built
    assert any("units without a point" in b for b in geometry.check_points(pts.iloc[1:], polys, review))
    other = pts.unit.iloc[1]
    twin = poisoned(pts, other, geometry=pts.geometry.iloc[0])
    assert any("sharing coordinates" in b for b in geometry.check_points(twin, polys, review))


def test_reviewed_tolerance_is_the_only_way_outside(built):
    pts, polys, review = built
    unit = pts.unit.iloc[0]
    poly = polys.to_crs(geometry.UTM).geometry[unit]
    edge = poly.exterior if poly.geom_type == "Polygon" else max(poly.geoms, key=lambda g: g.area).exterior
    out = gpd.GeoSeries([edge.interpolate(0).buffer(100).difference(poly).representative_point()], crs=geometry.UTM)
    p = poisoned(pts, unit, geometry=out.to_crs(4326).iloc[0])
    assert any(b.startswith(unit) for b in geometry.check_points(p, polys, review))
    allowed = pd.concat([review, pd.DataFrame({"source": ["geonames"], "max_outside_km": [0.2]}, index=[unit])])
    assert not any(b.startswith(unit) for b in geometry.check_points(p, polys, allowed))
