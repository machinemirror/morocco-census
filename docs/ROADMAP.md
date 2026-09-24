# Roadmap

Open work as of release 2026.9.2, roughly in priority order.

## Decisions for the maintainer

- **HCP 2024 boundaries.** Ask HCP for explicit permission to redistribute the commune geometry of its RGPH 2024
  results platform. With it, add `hcp_communes_2024.gpkg` to the download bundle and consider making it the default
  map layer (and deriving queen weights from it). Without it, the layer stays optional and out of the bundle.
- **Western Sahara wording** in the French and Arabic About pages ("Sahara occidental", الصحراء الغربية) is a literal
  rendering of the English; official Moroccan usage differs (e.g. الأقاليم الجنوبية). HCP's boundary files also carry
  Sebta and Melilla features, which the pipeline drops.

## Translation review

The French and Arabic definitions, notes and About pages were translated with AI assistance and not yet reviewed.
Terms worth a native speaker's check:

- Arabic: indicateur conjoncturel de fécondité (المؤشر الظرفي للخصوبة), âge moyen singulier au mariage, descendance
  finale (الخصوبة المكتملة), vocational "initiation" (الاستئناس المهني), occupation group labels, georeferenced
  (المرجعة جغرافيا), unfit/fit dwellings (غير لائقة / لائقة).
- French: the housing-deficit definition (insalubres / salubres), FGT2 wording, "livret d'état civil de la famille".

## Data

- **Sex and urban/rural breakdowns.** Male and female blocks of the 2014 workbooks and the 2024 Population sheet, the
  2014 `Indic.Urbain` / `Indic.Rural` sheets, the 2024 milieu sheets and the sex blocks of the commuting workbook.
  Roughly triples the series; the map would need a sex / milieu selector.
- **Linkage gaps.** 6 communes without a seed point (`points_unmatched.csv`); 4 communes of the 2024 indicators file
  not linked to the 2014 list; 60 2014 communes with no 2004 link, which population change suggests are mostly
  matching misses rather than post-2004 creations and could be recovered.
- **White paper.** CONTRIBUTING refers to one in `docs/`; it does not exist yet.

## Site

- `map.json` is about 3.5 MB (0.9 MB compressed). Loading values per indicator on demand would cut the first load.
