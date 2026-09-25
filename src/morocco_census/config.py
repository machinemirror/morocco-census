import os
from pathlib import Path

ROOT = Path(os.environ.get("MC_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
GEOMETRY = PROCESSED / "geometry"
INTERIM = DATA / "interim"
SITE = ROOT / "site"
CATALOG = ROOT / "catalog" / "variables.yaml"
SEED_REVIEW = ROOT / "catalog" / "seed_review.csv"
LINK_REVIEW = ROOT / "catalog" / "link_review.csv"
# HCP's 2004 populations on 2014 commune boundaries, where its regional publications give them
HCP_2004_ON_2014 = ROOT / "catalog" / "hcp_2004_on_2014.csv"
SEED_NAMES = ROOT / "catalog" / "seed_names.csv"

# raw inputs, relative to RAW (names chosen by fetch.py)
R_ANNEX_2004 = RAW / "2004" / "pauvrete_developpement_2004.pdf"
R_CARTO = RAW / "2004" / "carto_pauvrete_communale_2004_2014.xlsx"
R_APP_HTML = RAW / "2004_app" / "html"
R_APP_INDEX = RAW / "2004_app" / "communes_index.csv"
R_MPI = RAW / "2024" / "mpi_communes_2014_2024.xls"
R_GEONAMES = [RAW / "geometry" / "MA.txt", RAW / "geometry" / "EH.txt"]
R_NATURAL_EARTH = RAW / "geometry" / "ne_10m_admin_0_countries.zip"
R_WIKIDATA = RAW / "geometry" / "wikidata_communes.csv"

# processed outputs (tracked)
P_INDICES_2004 = PROCESSED / "commune_indices_2004.csv"
P_COMMUNES = {y: PROCESSED / f"communes_{y}.csv" for y in (2004, 2014, 2024)}
# urban/rural and male/female slices of the commune tables, one row per commune and slice
P_SLICES = {(y, k): PROCESSED / f"communes_{y}_{k}.csv" for y in (2004, 2014, 2024) for k in ("milieu", "sex")}
P_CROSSWALK = PROCESSED / "crosswalk_communes.csv"
P_CROSSWALK_APP = PROCESSED / "crosswalk_app2004.csv"
P_PANEL = PROCESSED / "panel_commune.csv"
# one point per commune from openly licensed gazetteers (GeoNames, Wikidata)
P_POINTS = GEOMETRY / "communes_points.gpkg"
# HCP's commune boundaries, served by its RGPH 2024 platform on 2014 codes (same communes in 2014 and 2024)
P_HCP_GPKG = GEOMETRY / "hcp_communes_2024.gpkg"
P_HCP_GAL = GEOMETRY / "hcp_communes_2024_queen.gal"
R_HCP_BOUNDARIES = RAW / "hcp_boundaries_2024"
P_UNMATCHED = GEOMETRY / "points_unmatched.csv"
P_DUP_POINTS = GEOMETRY / "points_duplicate.csv"
P_SEEDS = GEOMETRY / "points_seeds.csv"
P_CROSSCHECK = GEOMETRY / "points_crosscheck.csv"
P_BOUNDARY = GEOMETRY / "boundary_mar_esh.gpkg"
P_CONTEXT = GEOMETRY / "context_countries.gpkg"


# the six arrondissement cities: one map unit each (the 2014 cercle code), one commune each in 2024
CITIES = {
    "01.511.01.": ("Tanger", 1511010),
    "03.231.01.": ("Fès", 3231010),
    "04.421.01.": ("Rabat", 4421010),
    "04.441.01.": ("Salé", 4441010),
    "06.141.01.": ("Casablanca", 6141010),
    "07.351.01.": ("Marrakech", 7351010),
}
