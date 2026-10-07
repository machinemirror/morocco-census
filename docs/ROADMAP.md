# Roadmap

Open work as of release 2026.9.10, roughly in priority order.

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
- **Linkage gaps.** Ait Ali ou Lahcen has no identified parent. Lakhiaita (17,538) and the remainders of Sidi Rahal
  Chatai and Sidi El Mekki went to Had Soualem, Soualem Trifiya and Sahel Oulad H'Riz in unpublished proportions;
  the remainders of Dar Bouazza, Oulad Salah, Ain Dorbane and Lamkansa are also unplaced (65,599 in all).
  HCP's full 2004-2014 commune table (it computed one) or the ministerial boundary arrêtés would settle these.
  Sidi Mohamed Ben Mansour has no seed point (it has its HCP boundary). 24 of the 1,689 2004 profile units have no identified annex row (spelling variants such as "Kahf nsour" /
  "Kahf Nssar"); Ait Sedrate Sahl El Gharbia's 2004 annex values are imputed for that reason.
- **Boundary changes the test set shows.** Of the 87 out-of-sample communes, 23 miss by more than 2%, most on
  one-to-one links: Sidi Abdelkrim, Ain Tizgha, Ziaida (Settat), and Lahraouyine against Sidi Othmane, Tit Mellil
  and Nouaceur (Grand Casablanca). HCP's figures could calibrate these, at the cost of the test; other regional
  directorates may publish the same kind of table (Berrechid's page of the Settat document is an image).
- **Split weights.** Test the 2014-population rule out of sample: recompute HCP-weighted splits from 2014 populations
  and compare with HCP's figures.
- **Harmonised table.** The map's three-census values on the 1,503 units (2004 split-weighted, arrondissements
  combined, with slices) exist only as site JSON; publish them as a long table (`unit, indicator, year, slice,
  value, imputed`).
- **Stricter checks.** Recompute `validation.json` from the tables in a test; assert each extracted column's
  French header against the extraction spec, so a re-issued workbook with shifted columns fails the build.
- **Catalogue headers.** For some 2014 columns the `from` field records a cell value instead of the column header
  (`menages_2014.xlsx col 12: 3.24515407644768`): the header row is read at the wrong offset for those workbooks.
- **National out-of-sample test.** The test set covers Casablanca-Settat only. HCP's other regional directorates may
  publish 2004 populations on 2014 boundaries (as Settat and Grand Casablanca do); harvesting them would make the
  linkage test national.
- **Safer fetches.** Download to `.part` and keep the recorded copy when a checksum differs, rather than replacing it
  and refusing the build; assert that every map unit has a neighbour in the contiguity file.
- **White paper.** Revised against 2026.9.10 after three review rounds. To be posted to Zenodo as its own Preprint
  record, with "Describes" relations to the dataset's concept DOI (10.5281/zenodo.22953567) and the 2026.9.10 version
  DOI (10.5281/zenodo.23033759); once it has a DOI, link it from the README, the About page and CONTRIBUTING, and add
  it to CITATION.cff's references. A data-note version for a journal could follow.

## Site

- The HCP boundary layer (2.9 MB) is the largest remaining file; simplifying it further or tiling it would help
  on slow connections.
