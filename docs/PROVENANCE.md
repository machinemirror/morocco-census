# Provenance

How every published file is produced, from which HCP source, and what was matched, imputed or
left out. Raw files, with URLs, sizes, sha256 and fetch dates, are listed in
[`data/raw/manifest.json`](../data/raw/manifest.json). `uv run mc fetch` downloads them and
reports any file whose checksum no longer matches (HCP occasionally re-issues files; GeoNames
changes daily).

## Pipeline

| Step | Command / module | Inputs | Output |
|---|---|---|---|
| Fetch | `mc fetch` · `fetch.py` | 20 files (HCP, GADM, GeoNames, Natural Earth) | `data/raw/` |
| 2004 profiles | `mc crawl-2004` · `hcp_app.py` | HCP Maroc en Chiffres app (4 profile pages × 1,689 communes) | `data/raw/2004_app/` |
| 2004 indices | `parse_2004.annex` | HCP 2004 poverty volume, Annexe 2 (PDF) | `commune_indices_2004.csv` |
| 2004 table | `parse_2004.app` | crawled profile pages | `communes_2004.csv` |
| Crosswalk | `crosswalk.communes` | 2014 commune list, 2004 annex, 2004–2014 poverty map, 2025 MPI database | `crosswalk_communes.csv` |
| 2014 and 2024 tables | `extract.py` | HCP 2014 commune workbooks; 2024 indicators workbook | `communes_2014.csv`, `communes_2024.csv` |
| Panel | `panel.py` | crosswalk, annex, poverty map, MPI database, 2014 legal population | `panel_commune.csv` |
| App crosswalk | `crosswalk.app2004` | app commune index, crosswalk | `crosswalk_app2004.csv` |
| Geometry | `mc geometry` · `geometry.py` | crosswalk, GADM 4.1 L4, GeoNames, Natural Earth | `geometry/*` |
| Site | `mc site` · `site.py` | processed tables, catalogue | `site/data/` |

`mc all` runs build, geometry and site. Only `site` runs in CI; everything before it needs the raw files.

## Sources

| Key | Source | URL |
|---|---|---|
| 2004 profiles | HCP, *Maroc en Chiffres* (RGPH 2004 commune profiles; pre-2015 16-region map) | https://applications-web.hcp.ma/hpmc/frmmarocenchiffres.aspx |
| 2004 indices | HCP (2004), *Pauvreté, développement humain et développement social au Maroc*, Annexe 2 | https://www.hcp.ma/file/231444/ |
| Poverty map | HCP, *Cartographie de la pauvreté multidimensionnelle communale 2004 et 2014* | https://www.hcp.ma/file/231434/ |
| MPI database | HCP (May 2025), *Base de données de la cartographie de la pauvreté multidimensionnelle, RGPH 2014 et 2024* | https://www.hcp.ma/file/245096/ |
| 2014 workbooks | HCP, RGPH 2014 indicateurs communaux: Ménages, Individus; Activité; Diplôme | rgph2014.hcp.ma/file/190480, 190479; hcp.ma/file/230028, 230031 |
| 2014 legal population | HCP, RGPH 2014 population légale (12- and 16-region cuts) | rgph2014.hcp.ma/file/166326, 166315 |
| 2024 indicators | HCP, RGPH 2024 indicateurs démographiques et socio-économiques | https://www.hcp.ma/file/242671/ |
| Seed points | GADM 4.1 level 4 (not redistributed); GeoNames MA + EH (CC BY 4.0) | gadm.org; geonames.org |
| Outline | Natural Earth 1:10m admin-0, Morocco + W. Sahara (public domain) | naturalearthdata.com |

The 2014 and 2024 tables carry every both-sexes, both-milieux column of these workbooks (age structure,
marital status, fertility, education, diplomas, languages, employment status, occupations, sectors, housing,
sanitation, cooking fuel, equipment, distance to a paved road). The 2004 profiles are parsed for the concepts that
also appear in 2014 or 2024; the 2004 year of construction is published for urban households only and is left
empty for rural communes. Sex and urban/rural breakdowns (the Masculin/Féminin blocks and the 2024 milieu sheets)
are not yet extracted.

Other 2024 workbooks (transport, urban housing stock, economic establishments, douars, internal
migration) are fetched but not yet extracted.

## Matching

**Spine.** The 2014 commune list: 1,538 rows at code depth 4 with a commune code (communes,
municipalities, 41 arrondissements).

**Crosswalk** (normalized name + province, then unambiguous name-only, then mutual-best fuzzy):

| Link | Matched of 1,538 | Notes |
|---|---|---|
| 2004–2014 poverty map | 1,455 | exact name + province |
| 2025 MPI database (2024 codes) | 1,529 | 36 by fuzzy name with a same-province bonus |
| 2004 annex | 1,473 | 1,405 direct, 68 mutual-best fuzzy (rapidfuzz ≥ 82) |
| All three censuses | 1,466 (95.3%) | the rest are communes created or merged after 2004 |

**2004 app codes** (`crosswalk_app2004.csv`): 1,478 of 1,538, by exact space-insensitive name + province,
then unique name, then province-constrained mutual-best fuzzy (≥ 85).

**Not linked yet.** 4 communes of the 2024 indicators file (My Idriss Zerhoun, Ourtzarh, Kelâat Sraghna,
Sidi Abdellah Ou Belaid) carry codes that differ from the MPI database's.

## Imputation (panel only)

Where a 2014 commune has no 2004, 2014 or 2024 poverty value (it did not exist, or was split), the
value is the population-weighted mean of the other communes in the same cercle (fallback: province),
and the row is flagged:

| Flag | direct | fuzzy | imputed_cercle | imputed_province |
|---|---|---|---|---|
| `src04` | 1,398 | 67 | 72 | 1 |
| `src14` | 1,527 | – | 11 | – |
| `src24` | 1,527 | – | 11 | – |

Robustness checks should drop imputed rows; the flags make that a one-line filter.

## Geometry

- Units: 1,503 (the 41 arrondissements collapse to 6 cities). Seed points: 1,323 from GADM 4.1 level-4
  representative points (computed in UTM 29N), 152 from GeoNames (post-2015 provinces, Western Sahara),
  28 without a point (`points_unmatched.csv`).
- Cells: Voronoi in EPSG:32629, clipped to the Natural Earth outline. Harhoura's seed falls 250 m
  offshore of that coarse coastline; the outline is extended by 1 km around it.
- Weights: queen contiguity on the cells, 1,475 units, mean 5.75 neighbours, no islands.

## Changes from the dissertation-era build

The pipeline was ported from the research repository behind Lehnert (2021) and Lehnert & Smirnov
(2024). Rebuilt from identical raw files, its first version reproduced that repository's tables
byte-for-byte and its tessellation to within 2e-5 m² per cell. Deliberate changes since:

1. `crosswalk_app2004` is built by code; it gains one pair (Sidi Ghanem, Rehamna).
2. The outline is Natural Earth instead of GADM (GADM forbids redistribution); cells along the coast
   and borders differ slightly.
3. `communes_2014` drops the 8 Casablanca *préfectures d'arrondissements* rows, which double-counted
   their arrondissements; `pop_share` is recomputed accordingly.
4. Panel city rows sum population and households (they were population-weighted means).
5. `is_urban`: 2024 flagged every commune urban (all appear in the urban sheet); it is now "no rural
   population". 2014 now counts arrondissements as urban.
