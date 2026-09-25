# morocco-census

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22953567.svg)](https://doi.org/10.5281/zenodo.22953567)

Commune-level data from Morocco's three most recent censuses (RGPH 2004, 2014 and 2024),
harmonized on one commune key, with HCP's commune boundaries, urban/rural and male/female breakdowns, a catalogue
of every variable, and an interactive map (227 indicators, 387 indicator-census series; the map shows the 50
observed in all three censuses, by urban/rural for 49 and by sex for 25, readable in English, French or Arabic with
HCP's own place names and labels).

**Site:** https://machinemirror.github.io/morocco-census/ — map, catalogue, downloads.

| | 2004 | 2014 | 2024 |
|---|---|---|---|
| Communes in HCP's tables | 1,689 | 1,538 | 1,503 |
| Commune variables | 69 | 133 | 164 |
| Poverty / development indices | IDH, IDS, poverty, MPI (poverty map) | MPI (both series) | MPI |
| Linked to the 2014 list | 1,492 (annex) · 1,537 (profiles) | spine | 1,538 |

1,537 of the 1,538 2014 communes have 2004 profile values and all have 2024 values; 1,492 (97.0%) are also matched
to the 2004 poverty annex. Imputed values are flagged, never silent. Against HCP's own 2004 populations on 2014
boundaries for 87 communes that set no weight (Settat, Benslimane, Grand Casablanca), the links are within 2% for 64;
the misses are boundary changes and 65,599 people of 2004 left unplaced, which `pop04_basis` and `unplaced04_nearby`
flag per commune (see [PROVENANCE](docs/PROVENANCE.md#matching)).

## Data

Everything published is in [`data/processed/`](data/processed) and described column by column in
[`catalog/variables.yaml`](catalog/variables.yaml) (also on the site's Catalogue page and as
`data_dictionary.csv` in the download bundle).

| File | Rows | Key | What |
|---|---|---|---|
| `communes_2004.csv` | 1,689 | `app_code` | RGPH 2004 commune profiles (HCP Maroc en Chiffres) |
| `communes_2014.csv` | 1,538 | `code14` | RGPH 2014 commune indicators |
| `communes_2024.csv` | 1,503 | `code24` | RGPH 2024 commune indicators, with HCP's French and Arabic names |
| `communes_2004_sex.csv` | 3,378 | `app_code`, `sex` | 2004 profiles by sex, from the pages' female counts |
| `communes_2014_milieu.csv`, `communes_2024_milieu.csv` | 1,680 · 1,663 | code, `milieu` | urban and rural parts of each commune (HCP's milieu sheets) |
| `communes_2014_sex.csv`, `communes_2024_sex.csv` | 3,066 · 2,997 | code, `sex` | individual-level indicators by sex |
| `commune_indices_2004.csv` | 1,677 | `label` | 2004 poverty, vulnerability, IDH, IDS |
| `panel_commune.csv` | 1,544 | `code14` | three-census poverty/development panel, with provenance flags; 6 city rows (`level = city`) to drop before summing |
| `crosswalk_communes.csv` | 1,538 | `code14` | 2014 ↔ 2004 annex ↔ poverty map ↔ 2024 commune (`code24_commune`) ↔ map unit (`unit`) |
| `crosswalk_app2004.csv` | 1,696 | `app_code`, `code14` | 2004 profile codes → 2014 communes (1,537), with link type and split weight |
| `geometry/hcp_communes_2024.gpkg` | 1,503 | `unit` | HCP's commune boundaries, the communes of 2014 and 2024 (the map's default layer) |
| `geometry/hcp_communes_2024_queen.gal` | 1,503 | | queen-contiguity weights on HCP's boundaries |
| `geometry/communes_points.gpkg` | 1,502 | `unit` | one point per commune from GeoNames or Wikidata (openly licensed) |
| `validation.json` | | | populations against HCP's legal population, linkage and seed-point checks |

`geometry/` also holds build intermediates, tracked so the checks can be audited: the Natural Earth outline
(`boundary_mar_esh.gpkg`) and neighbouring countries (`context_countries.gpkg`) the map draws, and the seed-point
review files: `points_seeds.csv` (each point's gazetteer match), `points_crosscheck.csv` (GeoNames against
Wikidata), `points_unmatched.csv` (communes without a point) and `points_duplicate.csv` (units dropped for sharing
coordinates; currently none).

Read codes as text: `app_code` has leading zeros and `code14` ends with a dot. Join 2024 tables through the
crosswalk's `code24_commune`, not `code24`: the 41 arrondissements of 2014 are the six city communes of 2024. The
boundaries and points are keyed by `unit` (the commune, or the city for an arrondissement). `population14` and
`population24` are HCP's municipal population, the base of the rates; `pop_legal14` and `pop_legal24` add the
population living collectively (barracks, prisons, boarding schools) and are the resident count for per-capita
totals, notably in garrison and Saharan communes.

```python
import pandas as pd
base = "https://raw.githubusercontent.com/machinemirror/morocco-census/main/data/processed/"
cw = pd.read_csv(base + "crosswalk_communes.csv", dtype=str)
c14 = pd.read_csv(base + "communes_2014.csv", dtype={"code14": str})
c24 = pd.read_csv(base + "communes_2024.csv", dtype={"code24": str})

# 2014 and 2024 on the 1,503 communes of 2024 (arrondissements summed into their city)
pop14 = c14.merge(cw[["code14", "code24_commune"]], on="code14").groupby("code24_commune").population14.sum()
both = c24.set_index("code24")[["name24", "population24"]].join(pop14)
```

### Commune shapes

The boundaries are HCP's own, redistributed with attribution to HCP. Its RGPH 2024 results platform serves them, but
they are keyed by the 2014 commune code and drawn on the 2014 census base; the communes are the same in 2014 and 2024
(2014's 41 arrondissements are 2024's 6 city communes), and 2004 values reach them through the crosswalk. A point per commune from the
GeoNames and Wikidata gazetteers is published alongside, for uses that need locations rather than polygons.

## Rebuild

Requires [uv](https://docs.astral.sh/uv/) and Python ≥ 3.12.

```sh
uv run mc fetch        # download raw files into data/raw; exits non-zero if one differs from the manifest
uv run mc crawl-2004   # 2004 commune profiles from HCP's app (several hours, resumable)
uv run mc all          # tables -> geometry -> validation.json -> site/data; refuses raw files that differ from the manifest
python -m http.server -d site
```

GeoNames and Wikidata change daily, so a fresh `mc fetch` reports them as changed; `mc fetch --accept-changes`
records the new checksums, and the rebuilt points may then differ slightly from the release.
`uv run pytest` checks the published tables, the catalogue and the site export; it needs no raw data.
Corrections and additions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).
[`docs/PROVENANCE.md`](docs/PROVENANCE.md) documents every step, match rate and imputation.
Open work is listed in [`docs/ROADMAP.md`](docs/ROADMAP.md).

## AI assistance

The pipeline, tests, site and documentation were developed with AI coding assistants (Anthropic's Claude Code
and OpenAI's Codex) under the author's direction. The statistics are HCP's; each linkage and placement decision is
recorded with its evidence in `catalog/link_review.csv` and `catalog/seed_review.csv`, and every published number
is regenerated from HCP's files and checked by the tests and `validation.json`, so the results can be audited
without relying on how the code was written. Commits made with an assistant name it in an `Assisted-by:` line.

## Licence and citation

Code: [MIT](LICENSE). Derived data, catalogue and geometry: [CC BY 4.0](LICENSE-DATA). The statistics
are the Haut-Commissariat au Plan's; raw HCP files are not redistributed, except HCP's commune boundaries
(processed, with attribution to HCP).

Cite the dataset (APA 7):

> Lehnert, M. R. (2026). *morocco-census: Commune-level RGPH 2004, 2014 and 2024* [Data set]. Zenodo.
> https://doi.org/10.5281/zenodo.22953567

That DOI always resolves to the latest release. To cite the exact version used, add it after the title,
e.g. *(Version 2026.9.8)*, and use that release's own DOI from the [Zenodo record](https://doi.org/10.5281/zenodo.22953567).

Cite HCP as the source of the statistics:

> Haut-Commissariat au Plan. (2004). *Recensement général de la population et de l'habitat 2004* [Data set].
> https://www.hcp.ma
>
> Haut-Commissariat au Plan. (2014). *Recensement général de la population et de l'habitat 2014* [Data set].
> https://rgph2014.hcp.ma
>
> Haut-Commissariat au Plan. (2024). *Recensement général de la population et de l'habitat 2024* [Data set].
> https://www.hcp.ma

The harmonization began with:

> Lehnert, M. R. (2021). *Spatial data science: Theory and methods with applications to human development in
> Morocco* [Doctoral dissertation, University of Toledo]. OhioLINK Electronic Theses and Dissertations Center.
> http://rave.ohiolink.edu/etdc/view?acc_num=toledo1620381248329514
>
> Lehnert, M. R., & Smirnov, O. (2024). Human development in Morocco: Out-of-sample prediction using spatial
> econometrics and RandomForest. *African Geographical Review, 43*(1), 60–79. https://doi.org/10.1080/19376812.2022.2107547

Western Sahara communes are included as HCP reports them; this implies no position on the
territory's status.
