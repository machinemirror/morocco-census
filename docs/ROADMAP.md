# Roadmap

Open work as of release 2026.9.3, roughly in priority order.

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
- **Linkage gaps.** Ain Chair, Ait Ali ou Lahcen, Oulad Ziyane and Oulad Azzouz (Nouaceur) have no identified parent;
  Ain Dorbane and Lakhiaita have conflicting evidence. HCP's decrees creating the 2009 communes would settle them.
  Sidi Mohamed Ben Mansour has no seed point (it has its HCP boundary).
- **White paper.** CONTRIBUTING refers to one in `docs/`; it does not exist yet.

## Site

- The HCP 2024 boundary layer (2.9 MB) is the largest remaining file; simplifying it further or tiling it would help
  on slow connections.
