# Contributing

morocco-census is meant to keep improving through the people who use it. Corrections from anyone who
knows a commune, a source or a variable better than the pipeline does are the most valuable contribution.

## Report a problem

Open an issue with the commune (its `code14` or `code24`), the file and column, what you expected, and
your source. A wrong value, a wrong match between censuses, a misplaced commune or a confusing catalogue
entry are all worth reporting.

## Fix a commune's point on the map

Seed points come from GeoNames, or Wikidata where GeoNames lacks the commune. When the two disagree by
more than 25 km, `catalog/seed_review.csv` records which one is used and why. To correct a point:

1. If the right place is in GeoNames or Wikidata, add or edit a row in `catalog/seed_review.csv`
   (`unit`, `name14`, `prov14`, `source`, `evidence`, `reviewed`) and say what you checked in `evidence`.
2. If neither gazetteer has it right, fix the gazetteer itself: edit the item on
   [Wikidata](https://www.wikidata.org) (commune items are instances of Q17318027 or Q3327862) or
   report it to [GeoNames](https://www.geonames.org). The next release picks the fix up.

Communes without a point are listed in `data/processed/geometry/points_unmatched.csv`; adding their
coordinates to Wikidata is the quickest way to put them on the map.

## Add or correct a variable

Extraction is declared in `src/morocco_census/extract.py` (`SPEC_2014`, `SPEC_2024`: the exact source
column of every variable). Every published column must also appear in `catalog/variables.yaml` with its
English, French and Arabic label, unit, definition and source; the tests fail otherwise. Keep the
French source header in the catalogue so users can trace the column back to HCP's workbook.

## Before a pull request

```sh
uv run mc fetch     # raw inputs, checked against data/raw/manifest.json
uv run mc all       # tables, geometry, validation, site data
uv run pytest -q
uv run ruff check src tests
```

`mc all` regenerates `data/processed/validation.json`; if your change moves its numbers, say why in
the pull request. Describe any change to published values in `docs/PROVENANCE.md` under *Changes*.

## Releases and citation

Releases are tagged `vYYYY.M.N`; each tag publishes a GitHub release with the data bundle. The
white paper in `docs/` describes a named release and is updated with it. Contributors are credited in
the release notes, and substantial contributors in `CITATION.cff`.

By contributing you agree that data contributions are published under CC BY 4.0 and code under MIT.
