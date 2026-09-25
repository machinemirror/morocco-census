# Roadmap

Open work as of release 2026.9.8, roughly in priority order.

## Decisions for the maintainer

- **Western Sahara wording**, should the About page be translated: official Moroccan usage (e.g. الأقاليم الجنوبية)
  differs from a literal rendering of the English. HCP's boundary files also carry Sebta and Melilla features, which
  the pipeline drops.

## Translation

Only the map's place names and indicator labels are in French and Arabic, all HCP's own wording. Definitions, notes
and the other pages are English, each with a French and Arabic call for fluent translators (GitHub issues labelled
`translation`). HCP's Arabic spelling varies between its documents (تمازيغت / تمزيغت, تريفت / تريفيت); the catalogue
cites the one used.

## Data

- **More breakdowns.** Urban/rural and male/female cover the indicators workbooks. The commuting workbook has milieu
  and sex blocks, the other 2024 workbooks milieu sheets; sex × milieu is not extracted.
- **Linkage gaps.** Ait Ali ou Lahcen has no identified parent. In Berrechid, Lakhiaita and parts of Sidi Rahal
  Chatai and Sidi El Mekki went to Had Soualem, Soualem Trifiya and Sahel Oulad H'Riz in unpublished proportions.
  HCP's full 2004-2014 commune table (it computed one) or the ministerial boundary arrêtés would settle these, and
  HCP's regional monographs for other provinces may give more 2004 figures on 2014 boundaries.
  Sidi Mohamed Ben Mansour has no seed point (it has its HCP boundary). Tah (Tarfaya) has a clean annex label
  ("Laayoune Tah") since 2026.9.8 but its three-letter name is below the matching rules' minimum.
- **Split weights.** Test the 2014-population rule out of sample: recompute the 16 HCP-weighted splits from 2014
  populations and compare with HCP's figures. Publish each commune's weight basis (HCP, 2014 population, none).
- **Harmonised table.** The map's three-census values on the 1,503 units (2004 split-weighted, arrondissements
  combined, with slices) exist only as site JSON; publish them as a long table (`unit, indicator, year, slice,
  value, imputed`).
- **Stricter checks.** Recompute `validation.json` from the tables in a test; assert each extracted column's
  French header against the extraction spec, so a re-issued workbook with shifted columns fails the build.
- **White paper.** Drafted and under review (round 1); to cite the dataset's concept DOI (10.5281/zenodo.22953567), and could go
  to a data journal as a data note.

## Site

- The HCP boundary layer (2.9 MB) is the largest remaining file; simplifying it further or tiling it would help
  on slow connections.
