import argparse
import sys

from .config import PROCESSED


def build() -> None:
    from . import crosswalk, extract, panel, parse_2004

    PROCESSED.mkdir(parents=True, exist_ok=True)
    parse_2004.annex()
    parse_2004.app()
    crosswalk.communes()
    extract.main()
    panel.main()
    crosswalk.app2004()


def geometry(outline: str | None = None) -> None:
    from . import geometry as g

    g.main(outline)


def site() -> None:
    from . import site as s

    s.main()


def main() -> int:
    ap = argparse.ArgumentParser(prog="mc", description="Build the morocco-census data and site")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download raw HCP, GeoNames, Wikidata and Natural Earth files into data/raw")
    sub.add_parser("crawl-2004", help="crawl the 2004 Maroc-en-Chiffres commune profiles (hours)")
    sub.add_parser("build", help="raw -> data/processed tables")
    gp = sub.add_parser("geometry", help="seed points, Thiessen cells and queen weights")
    gp.add_argument("--outline", help="clip to this outline instead of Natural Earth MAR+SAH")
    sub.add_parser("site", help="export site/data and catalog.json")
    sub.add_parser("all", help="build, geometry, site")
    a = ap.parse_args()

    if a.cmd == "fetch":
        from . import fetch

        return fetch.main()
    if a.cmd == "crawl-2004":
        from . import hcp_app

        hcp_app.main()
    if a.cmd in ("build", "all"):
        build()
    if a.cmd in ("geometry", "all"):
        geometry(getattr(a, "outline", None))
    if a.cmd in ("site", "all"):
        site()
    return 0


if __name__ == "__main__":
    sys.exit(main())
