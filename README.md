# morocco-census

Commune-level data from Morocco's three most recent censuses (RGPH 2004, 2014 and 2024),
harmonized on one commune key, with approximate commune shapes, a catalogue of every variable,
and an interactive map (226 indicators, 385 indicator-census series; the map shows the 50 observed in all three
censuses, readable in English, French or Arabic with HCP's own place names and labels).

**Site:** https://machinemirror.github.io/morocco-census/ — map, catalogue, downloads.

| | 2004 | 2014 | 2024 |
|---|---|---|---|
| Communes in HCP's tables | 1,689 | 1,538 | 1,503 |
| Commune variables | 69 | 132 | 166 |
| Poverty / development indices | IDH, IDS, poverty, MPI (poverty map) | MPI (both series) | MPI |
| Linked to the 2014 list | 1,473 (annex) · 1,528 (profiles) | spine | 1,538 |

1,528 of the 1,538 2014 communes have 2004 profile values and all have 2024 values; the other 10 were created after
2004 from part of another commune. 1,473 (95.8%) are also matched to the 2004 poverty annex. Imputed values are
flagged, never silent.

## Data

Everything published is in [`data/processed/`](data/processed) and described column by column in
[`catalog/variables.yaml`](catalog/variables.yaml) (also on the site's Catalogue page and as
`data_dictionary.csv` in the download bundle).

| File | Rows | Key | What |
|---|---|---|---|
| `communes_2004.csv` | 1,689 | `app_code` | RGPH 2004 commune profiles (HCP Maroc en Chiffres) |
| `communes_2014.csv` | 1,538 | `code14` | RGPH 2014 commune indicators |
| `communes_2024.csv` | 1,503 | `code24` | RGPH 2024 commune indicators |
| `commune_indices_2004.csv` | 1,677 | `label` | 2004 poverty, vulnerability, IDH, IDS |
| `panel_commune.csv` | 1,544 | `code14` | three-census poverty/development panel, with provenance flags |
| `crosswalk_communes.csv` | 1,538 | `code14` | 2014 ↔ 2004 annex ↔ poverty map ↔ 2024 codes |
| `crosswalk_app2004.csv` | 1,685 | `app_code` | 2004 profile codes → 2014 communes (1,528), with link type |
| `geometry/communes.gpkg` | 1,502 | `unit` | Thiessen cells + seed points (approximate, see below) |
| `geometry/communes_queen.gal` | 1,502 | | queen-contiguity weights |
| `geometry/hcp_communes_2024.gpkg` | 1,503 | `unit` | HCP's own 2024 boundaries (optional map layer; not in the download bundle) |
| `validation.json` | | | populations against HCP's legal population, linkage and seed-point checks |

Read codes as text: `app_code` has leading zeros and `code14` ends with a dot.

```python
import pandas as pd
base = "https://raw.githubusercontent.com/machinemirror/morocco-census/main/data/processed/"
panel = pd.read_csv(base + "panel_commune.csv", dtype={"code14": str})
```

### Commune shapes are approximate

HCP does not distribute commune boundaries as a dataset (its RGPH 2024 results platform draws them; the site offers
them as an optional layer, not in the downloads, as their reuse licence is not stated). Each commune gets one seed point (GeoNames, else Wikidata) and
the country is split into Thiessen cells around them. The cells show where a commune is, not its
extent: do not compute areas or densities from them.

## Rebuild

Requires [uv](https://docs.astral.sh/uv/) and Python ≥ 3.12.

```sh
uv run mc fetch        # download raw files into data/raw, check sha256 against the manifest
uv run mc crawl-2004   # 2004 commune profiles from HCP's app (several hours, resumable)
uv run mc all          # tables -> geometry -> site/data
python -m http.server -d site
```

`uv run pytest` checks the published tables, the catalogue and the site export; it needs no raw data.
Corrections and additions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).
[`docs/PROVENANCE.md`](docs/PROVENANCE.md) documents every step, match rate and imputation.
Open work is listed in [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Licence and citation

Code: [MIT](LICENSE). Derived data, catalogue and geometry: [CC BY 4.0](LICENSE-DATA). The statistics
are the Haut-Commissariat au Plan's; raw HCP files are not redistributed.

> Lehnert, M. R. (2026). *morocco-census: commune-level RGPH 2004, 2014 and 2024.*
> https://github.com/machinemirror/morocco-census

Source statistics: Haut-Commissariat au Plan, *Recensement Général de la Population et de l'Habitat*
2004, 2014, 2024. The harmonization began with Lehnert (2021, Ph.D. dissertation, University of
Toledo) and Lehnert & Smirnov (2024), *African Geographical Review* 43(1):60–79,
[doi:10.1080/19376812.2022.2107547](https://doi.org/10.1080/19376812.2022.2107547).

Western Sahara communes are included as HCP reports them; this implies no position on the
territory's status.
