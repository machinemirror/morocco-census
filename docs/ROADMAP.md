# Roadmap

Open work as of release 2026.9.3, roughly in priority order.

## Decisions for the maintainer

- **HCP 2024 boundaries.** Ask HCP for explicit permission to redistribute the commune geometry of its RGPH 2024
  results platform. With it, add `hcp_communes_2024.gpkg` to the download bundle and consider making it the default
  map layer (and deriving queen weights from it). Without it, the layer stays optional and out of the bundle.
- **Western Sahara wording**, should the About page be translated: official Moroccan usage (e.g. الأقاليم الجنوبية)
  differs from a literal rendering of the English. HCP's boundary files also carry Sebta and Melilla features, which
  the pipeline drops.

## Translation

Only the map's place names and indicator labels are in French and Arabic, all HCP's own wording. Definitions, notes
and the other pages are English, each with a French and Arabic call for fluent translators (GitHub issues labelled
`translation`). HCP's Arabic spelling varies between its documents (تمازيغت / تمزيغت, تريفت / تريفيت); the catalogue
cites the one used.

## Data

- **Sex and urban/rural breakdowns.** Male and female blocks of the 2014 workbooks and the 2024 Population sheet, the
  2014 `Indic.Urbain` / `Indic.Rural` sheets, the 2024 milieu sheets and the sex blocks of the commuting workbook.
  Roughly triples the series; the map would need a sex / milieu selector.
- **Linkage gaps.** Sidi Mohamed Ben Mansour has no seed point. 10 communes created after 2004 from part of another
  have no 2004 values; three 2004 units (Ain Dorbane, Lakhiaita, Soualem) split between 2014 communes are unlinked.
  Apportioning them (e.g. by 2014 population) would recover 2004 values under a stated assumption.
- **White paper.** CONTRIBUTING refers to one in `docs/`; it does not exist yet.

## Site

- The HCP 2024 boundary layer (2.9 MB) is the largest remaining file; simplifying it further or tiling it would help
  on slow connections.
