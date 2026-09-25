# Provenance

How every published file is produced, from which HCP source, and what was matched, imputed or
left out. Raw files, with URLs, sizes, sha256 and fetch dates, are listed in
[`data/raw/manifest.json`](../data/raw/manifest.json). `uv run mc fetch` downloads them and
reports any file whose checksum no longer matches (HCP occasionally re-issues files; GeoNames
changes daily).

## Pipeline

| Step | Command / module | Inputs | Output |
|---|---|---|---|
| Fetch | `mc fetch` · `fetch.py` | 95 files (HCP workbooks and PDF, 75 HCP boundary files, GeoNames, Wikidata, Natural Earth) | `data/raw/` |
| 2004 profiles | `mc crawl-2004` · `hcp_app.py` | HCP Maroc en Chiffres app (4 profile pages × 1,689 communes) | `data/raw/2004_app/` |
| 2004 indices | `parse_2004.annex` | HCP 2004 poverty volume, Annexe 2 (PDF) | `commune_indices_2004.csv` |
| 2004 table | `parse_2004.app` | crawled profile pages | `communes_2004.csv`, `communes_2004_sex.csv` |
| Crosswalk | `crosswalk.communes` | 2014 commune list, 2004 annex, 2004–2014 poverty map, 2025 MPI database | `crosswalk_communes.csv` |
| 2014 and 2024 tables | `extract.py` | HCP 2014 commune workbooks; 2024 indicators and other workbooks; 2024 legal population (names) | `communes_2014.csv`, `communes_2024.csv`, `communes_{2014,2024}_{milieu,sex}.csv` |
| Panel | `panel.py` | crosswalk, annex, poverty map, MPI database, 2014 legal population | `panel_commune.csv` |
| App crosswalk | `crosswalk.app2004` | app commune index, crosswalk, `catalog/link_review.csv`, 2014 population | `crosswalk_app2004.csv` |
| Geometry | `mc geometry` · `geometry.py` | crosswalk, GeoNames, Wikidata, `catalog/seed_review.csv`, `catalog/seed_names.csv`, Natural Earth, HCP boundary files | `geometry/*` (commune points, HCP boundaries and their queen weights) |
| Validate | `mc validate` · `validate.py` | tables, legal population 2014 and 2024, `catalog/hcp_2004_on_2014.csv` | `validation.json` |
| Site | `mc site` · `site.py` | processed tables, catalogue | `site/data/` (map index and values by theme and breakdown, class breaks, geometry, downloads) |

`mc all` runs build, geometry, validate and site. Only `site` runs in CI; everything before it needs the raw files.

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
| 2024 commuting | HCP, RGPH 2024 mode de transport domicile-lieu de travail | https://www.hcp.ma/file/248301/ |
| 2024 urban housing stock | HCP, RGPH 2024 indicateurs communaux du parc logement urbain | https://www.hcp.ma/file/246208/ |
| 2024 establishments | HCP, RGPH 2024 cartographie des établissements économiques (CEE) | https://www.hcp.ma/file/242672/ |
| 2024 douars | HCP, RGPH 2024 population et ménages par douars | https://www.hcp.ma/file/245768/ |
| 2024 migration | HCP, RGPH 2024 base de données de la migration interne | https://www.hcp.ma/file/245650/ |
| 2024 legal population | HCP, RGPH 2024 population légale (commune and province names in French and Arabic) | https://www.hcp.ma/file/242341/ |
| Boundaries and 2024 labels | HCP, RGPH 2024 results platform: 75 per-province commune boundary files (2014 census cartography); bilingual indicator menu (chart 667) and concept definitions | https://resultats2024.rgphapps.ma |
| 2004 on 2014 boundaries | HCP regional monographs and notes (Berrechid, Grand Casablanca, Settat, Rabat-Salé-Kénitra, Salé, M'Diq-Fnideq), each cited in `catalog/hcp_2004_on_2014.csv` | hcp.ma regional sites |
| Commune decrees | Décret n° 2-08-520 (BO 5684, 2008) and n° 2-09-320 (BO 5744, 2009): lists of communes, consulted for the 2009 reorganisation | sgg.gov.ma (via the Internet Archive) |
| Seed points | GeoNames MA + EH (CC BY 4.0); Wikidata rural and urban communes of Morocco, SPARQL query in `fetch.py` (CC0) | geonames.org; query.wikidata.org |
| Outline | Natural Earth 1:10m admin-0, Morocco + W. Sahara (public domain) | naturalearthdata.com |

The 2014 and 2024 tables carry every both-sexes, both-milieux column of these workbooks (age structure,
marital status, fertility, education, diplomas, languages, employment status, occupations, sectors, housing,
sanitation, cooking fuel, equipment, distance to a paved road). The 2004 profiles are parsed for the concepts that
also appear in 2014 or 2024; the 2004 year of construction is published for urban households only and is left
empty for rural communes. Urban/rural and male/female breakdowns are separate tables (see *Urban/rural and
male/female breakdowns* below).

The five other 2024 workbooks are joined to `communes_2024.csv` on `code24`:

- **Commuting, urban housing stock, migration**: commune rows keyed by `code24` as in the indicators file.
  The urban housing stock covers the 380 urban communes and counts dwellings, occupied or not.
- **Establishments (CEE)**: codes are 2024 codes written as dotted segments (region, province, cercle,
  commune); province, cercle and commune give the last 7 digits of `code24`. The 41 arrondissement rows are
  summed into their city before shares and per-1,000 rates are computed.
- **Douars**: 33,189 douar rows. The douar code is province (3 digits, leading zero dropped), cercle (2),
  commune (2), milieu (1), fraction (2), douar (3), so the commune is the last 7 digits of `code24`; all 1,279
  rural communes with douars match. People-based shares are population-weighted over douars; dwelling types
  and distances are household-weighted.

## Matching

**Spine.** The 2014 commune list: 1,538 rows at code depth 4 with a commune code (communes,
municipalities, 41 arrondissements).

**Crosswalk** (normalized name + province, then unambiguous name-only, then mutual-best fuzzy):

| Link | Matched of 1,538 | Notes |
|---|---|---|
| 2004–2014 poverty map | 1,455 | exact name + province |
| 2025 MPI database (2024 codes) | 1,538 | 36 by fuzzy name with a same-province bonus, 9 by identical code (a 2024 code is usually the 2014 code without dots) |
| 2004 annex | 1,473 | 1,405 direct, 68 mutual-best fuzzy (rapidfuzz ≥ 82) |
| All three censuses | 1,473 (95.8%) | the rest are communes created or merged after 2004 |

**2004 app codes** (`crosswalk_app2004.csv`): 1,537 of 1,538 communes, one row per app unit and 2014 commune, with its
`link` type and `weight`.

- The app reports a rural commune (code ending 2) apart from its autonomous centres (3-5, same first 9 digits): disjoint
  populations (all app units sum to the 2004 national total) that HCP's 2014 commune covers together. A centre named
  like its commune is not matched on its own; every centre left unmatched is linked with its commune (147,
  `centre`). Before this, 125 linked communes carried the rural part's values only.
- Matching: exact space-insensitive name + province, then unique name (1,467 `exact`); province-constrained
  mutual-best fuzzy ≥ 85 (31 `fuzzy`); for provinces created after 2004 (Driouch, Fquih Ben Salah, Sidi Slimane...),
  mutual-best fuzzy within the 2004 provinces their linked communes came from (13 `province_split`).
- `catalog/link_review.csv` (29 `review`, 8 `split`): merges (Ain Johra + Sidi Boukhalkhal, Ain Nzagh + Tamadroust), renames
  (Lkhaloua → Had Al Gharbia), rural remainders renamed when their centre became a municipality (Driouch → Mtalssa,
  Tahannaout → Aghouatim, Sidi Bou Othmane → Jbilate, Sidi Bouknadel → Ameur) and absorptions (Amalou Ighriben into
  Khenifra), and Soualem, whose rural remainder kept its commune number as Soualem Trifiya while its centre became Had
  Soualem. Each is decided on 2004-2014 population and on where the GeoNames point of the 2004 unit falls in HCP's
  commune polygons, and states its evidence.
- Splits: an app unit listed more than once in the review was divided after 2004. Each part carries the unit's 2004
  rates; its counts are shared by `weight`, taken from HCP's 2004 populations on 2014 boundaries where a regional
  publication gives them (`catalog/hcp_2004_on_2014.csv`, 35 communes: Berrechid, Nouaceur, Settat, Kénitra, Sidi
  Slimane, Salé, M'Diq-Fnideq), else from the parts' 2014 population. Examples: rural Deroua (25,239) gave 11,421 to
  Deroua (Mun.) and the rest to Oulad Ziyane (HCP: 14,151); Ain Dorbane, abolished in 2008, went mostly to Ben Ahmed
  (7,132) and Ain Dorbane-Lahlaf (878); Oulad Azzouz (26,103) was carved from Dar Bouazza. Where HCP accounts for only
  part of a unit, its weights sum below 1 and the rest is left unplaced (Sidi Rahal Chatai, Sidi El Mekki, Dar
  Bouazza, Oulad Salah, Ain Dorbane). Lamkansa, which HCP leaves out of Bouskoura, is unlinked.
- The 2008-2009 decrees (n° 2-08-520, BO 5684; n° 2-09-320, BO 5744) list communes by province, cercle and caïdat
  but not what each was carved from; boundaries were set by ministerial arrêtés that are not published online. HCP
  says it computed 2004-2014 growth for every commune but has published it only in some regional documents.
- `validation.json` (`backcast_2004`) compares each 2014 commune's linked 2004 population with HCP's figure: 27 of 35
  within 2%. The gaps are in Berrechid, where Had Soualem, Soualem Trifiya and Sahel Oulad H'Riz gained from
  Lakhiaita and the unplaced parts of Sidi Rahal Chatai and Sidi El Mekki in proportions HCP does not publish.
- Several app units sharing a 2014 commune are combined like arrondissements into cities: sums for counts,
  population- or household-weighted means for rates.
- Not linked: Ait Ali ou Lahcen (Khémisset), with no published parent; the app units Lakhiaita and Lamkansa.

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

- Units: 1,503 (the 41 arrondissements collapse to 6 cities). Seed points: 1,448 from GeoNames (1,431 by
  exact name, 17 by fuzzy name), 54 from Wikidata (49 exact, 5 fuzzy), 1 without a point
  (`points_unmatched.csv`: Sidi Mohamed Ben Mansour, which neither gazetteer has as a commune). Five communes are
  matched under a gazetteer spelling recorded in `catalog/seed_names.csv` (Mtalssa as Metalsa, Rmilat as Ermilate...),
  each checked to fall inside the commune's HCP polygon. Every point, its source identifier (geonameid or QID), feature class and match
  type is in `points_seeds.csv`.
- GeoNames matching: commune-level admin features (ADM3/ADM4) before populated places, primary names before
  alternate names; cercles and higher units are excluded. Candidates must lie within a province radius of
  the province anchor, the median of units with a single unambiguous candidate (3 × the 75th-percentile
  anchor distance, clipped to 0.5°–3°). Fuzzy matches (rapidfuzz ≥ 88, a clear margin, every word agreeing)
  are tried only within that radius.
- Wikidata: items with several coordinates are used only if these agree within ~15 km (their median is
  taken); the item's stated province (P131) must match.
- Cross-check (`points_crosscheck.csv`): 1,371 units are placed by both gazetteers, median 3.3 km apart,
  90th percentile 9.8 km. 37 disagree by more than 25 km. 35 are settled in `catalog/seed_review.csv`
  by comparison with an OpenStreetMap Nominatim lookup (used for review only; no OSM data is published),
  2 without an OSM result by distance to the province anchor. The pattern: GeoNames admin points for
  municipalities and for Saharan communes are often off; for rural northern communes Wikidata is.
- Output: `geometry/communes_points.gpkg` (layer `points`). The Natural Earth outline bounds the gazetteer search and
  draws the map's coast and neighbouring countries.
- Thiessen cells around these points, clipped to Natural Earth, were the map's alternative layer and a download
  (with queen weights) until release 2026.9.6; with HCP's boundaries published they were retired.

## Validation

`mc validate` writes `data/processed/validation.json` (tracked); `uv run pytest` checks it against the
published tables.

- **Population against the legal count.** HCP publishes each census's legal population per commune
  separately from the indicator workbooks. In 2014, 992 of 1,534 comparable communes match exactly and the
  median absolute difference is 0.0% (4 Oued Ed-Dahab communes carry "pm" in the legal list); in 2024, 639 of
  1,503 match exactly, median 0.012%. The commune tables sum to 33,610,084 (2014) and 36,490,591 (2024)
  against legal totals of 33,848,242 and 36,828,330. Legal population includes the *population comptée à part*
  — people living collectively: military in barracks and camps, detainees, long-stay patients, boarders
  ([HCP definitions](https://www.hcp.ma/region-meknes/Concepts-et-definitions-utilisees-dans-le-Recensement-General-de-la-Population-et-de-l-Habitat-2014_a124.html)).
  The largest shortfalls are consistent with that: Saharan communes (Al Mahbass 582 against 19,139 in
  2024) and large cities. Use the legal population, not `population14`/`population24`, as a denominator
  where institutional population matters.
- **Linkage and imputation**: the counts in *Matching* and *Imputation* above, recomputed.
- **Seed points**: the gazetteer cross-check in *Geometry* above.

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
6. Seed points no longer derive from GADM (release 2026.9.2). GADM's licence bars redistribution
   without permission, and derived seed coordinates were arguably covered. GeoNames and Wikidata replace it;
   22 more units get a cell (1,497), and the previous release's point for Lagouira, about 1,700 km from the
   town, is corrected. Against the 1,473 units placed in both releases the median shift is 3.0 km;
   12 move more than 50 km, all Saharan communes, reviewed disagreements or corrected errors.
7. 2004 profile links rebuilt (2026.9.3 to 2026.9.5): autonomous centres join their rural commune (125
   communes had carried the rural part's values only); provinces created after 2004 are matched within their 2004
   provinces; reviewed merges, renames, absorptions and splits, calibrated to HCP's 2004 populations on 2014
   boundaries where published. Links grow from 1,478 to 1,537 communes; `crosswalk_app2004` gains `link` and
   `weight` and is keyed by `app_code` and `code14`.
8. 2024 links: 9 rows linked by identical code (2026.9.3); 1,538 of 1,538.
9. Seed points: five communes placed under gazetteer spellings (`catalog/seed_names.csv`); 1,502 units.
10. French and Arabic (2026.9.3): the AI-assisted translations of definitions, notes, descriptions and pages are
    removed; French and Arabic labels are HCP's own wording, for the map's indicators and place names only.
11. HCP's commune boundaries are redistributed and are the map's default layer, with their own weights (2026.9.4).
12. Urban/rural and male/female tables added for all three censuses; `communes_2004` gains `milieu04`,
    `communes_2024` gains HCP's Arabic commune names and province names (2026.9.3 to 2026.9.4).
13. The map shows only indicators observed in all three censuses (50), with class breaks chosen per indicator and
    pooled over the censuses; its data is split into an index and one file per theme and breakdown.
14. Thiessen cells and their weights are retired (2026.9.6): the map draws HCP's boundaries only, and the download
    bundle carries the commune points (`communes_points.gpkg`, `.geojson`) instead of `communes.gpkg`,
    `communes_queen.gal`, `communes_thiessen.geojson` and `boundary_mar_esh.gpkg`.

## HCP commune boundaries (the map's layer)

HCP's RGPH 2024 results platform (https://resultats2024.rgphapps.ma, Apache Superset) draws commune boundaries from 75
per-province GeoJSON files served as static assets. `mc fetch` finds their current hashed names in the platform's
country-map bundle and records each file in the manifest. The files declare CRS84 but carry Web Mercator metres.

- Features carry an ISO-style code `MA-RR-PPP-CCccM` that is the **2014** commune code (region, province, cercle,
  commune) plus a milieu digit (1 municipality or arrondissement, 2 rural commune, 3-5 urban centre inside a rural
  commune). The urban centres are drawn as the 2014 census delimited them. So although the 2024 platform serves them,
  these look like HCP's 2014 census cartography; HCP does not say whether lines were redrawn for 2024. The commune
  set is the same in both censuses (1,497 communes and municipalities one to one, 2014's 41 arrondissements being
  2024's 6 city communes), so the layer serves both; the files keep the name `hcp_communes_2024` for stability. All 1,538 communes of the 2014 spine match; Sebta and Melilla features have no census data and are dropped.
- `geometry.hcp_boundaries()` dissolves centres into their rural commune and arrondissements into their city, giving
  1,503 map units, coverage-simplified at 100 m, in
  `geometry/hcp_communes_2024.gpkg`.
- Redistributed in the download bundle (GeoPackage, GeoJSON) with attribution to HCP, whose terms allow reuse with
  attribution.
- Weights (`geometry/hcp_communes_2024_queen.gal`): queen contiguity with a 50 m tolerance, since the per-province
  files leave hairline gaps along province borders (strict queen isolates 12 communes); 1,503 units, mean 5.63
  neighbours, no islands.
- Reliability by census on these boundaries: 2014 exact (same codes); 2024 through the crosswalk (every commune,
  cities from their arrondissements); 2004 through the app crosswalk (1,537 communes; rural communes with their
  centres, reviewed merges, renames and splits as above). 2004-2014 population growth across linked communes has a median
  ratio of 1.02; the largest drops are Saharan communes, whose census coverage differs between rounds.

## Urban/rural and male/female breakdowns

- 2014 (`communes_2014_milieu.csv`, `communes_2014_sex.csv`): the `Indic.Urbain` and `Indic.Rural` sheets of the four
  workbooks repeat the `Indic.Ensemble` layout; the individus, activité and diplôme workbooks repeat their both-sexes
  columns in a male then a female block (offsets 54, 20 and 15 columns). Household variables have no sex breakdown;
  fertility is female by definition and stays in `communes_2014.csv`. The four Oued Ed-Dahab communes HCP gives as
  "pm" have no sex rows.
- 2024 (`communes_2024_milieu.csv`, `communes_2024_sex.csv`): `Population_Urbaine`/`Population_Rurale` and
  `Ménages_Urbains`/`Ménages_Ruraux` repeat the layout of the both-milieux sheets. The male and female blocks of the
  Population sheet omit some columns (fertility is female-only), so each both-sexes column is matched to its block
  column by group and category header, in order. The other 2024 workbooks are not broken down.
- 2004: urban/rural from the app units (`milieu04` in `communes_2004.csv`): rural communes (code ending 2) are rural;
  municipalities, arrondissements and autonomous centres are urban, 16,339,561 people against HCP's 2004 urban total of
  16,463,634 (99.2%). Male/female (`communes_2004_sex.csv`) from the female counts under each category: each section's
  base is the sum of its categories by sex (marital status 15+, education 25+, status in employment), ages are shares
  of each sex's population, and male youth illiteracy (15-24) follows from HCP's total and female rates and the 15-24
  population by sex. Spoken languages and activity have no female counts in a usable base.
- Checks (`validation.json`, `slices`): urban + rural and male + female populations equal each commune's population
  in every commune with data.
- The map offers a breakdown for an indicator only where all three censuses have it: urban/rural for 49 of the 50
  (road distance is rural only), male/female for 25.

## Names and labels in French and Arabic

- Commune and province names: HCP's 2024 legal population list (`poplegale_2024.xlsx`), which names every commune
  (`جماعة ...`) and province in both languages; published as `name24_ar`, `province24`, `province24_ar` in
  `communes_2024.csv`. The map drops the `Commune de` / `جماعة` prefix.
- Indicator labels (`fr`, `ar`, `label_source` in the catalogue) for the 50 map indicators: HCP's own wording, from the
  RGPH 2024 results platform's bilingual indicator menu (chart 667) and concept definitions, the bilingual headers of
  the 2024 douar workbook, the 2024 and 2014 indicator workbooks, and HCP's Chichaoua 2024 provincial note for Arabic
  category names the platform lacks (age groups, local languages, employment status). Where HCP gives a variable
  and a category, the label joins them with a colon as HCP's Arabic does ("Type de logement : Villa" /
  "نوع المسكن: فيلا"). Two indicators have no HCP wording (65 and over; divorced women) and stay in English.
- Map groups (`map_groups`): the platform menu's headings (Démographie, Conditions d'habitat...).
- Everything else (definitions, notes, dataset descriptions, the other pages) is English; earlier AI-assisted French
  and Arabic versions were removed pending review by fluent speakers.
