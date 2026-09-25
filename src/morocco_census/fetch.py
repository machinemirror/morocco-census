"""Idempotent downloader for every raw input. Records url, sha256, size and fetch date in
data/raw/manifest.json (tracked, so anyone can check their copy against ours).

The 2004 commune profiles are not a file download: they come from crawling HCP's
Maroc-en-Chiffres app (`mc crawl-2004`, ~7k requests, several hours).
"""

import hashlib
import json
import subprocess
import time
import urllib.parse
import zipfile
from pathlib import Path

from .config import R_APP_HTML, R_APP_INDEX, RAW

MANIFEST_PATH = RAW / "manifest.json"
# per-page sha256 of the 2004 crawl (tracked); the manifest holds one digest over this list
APP_PAGES_PATH = RAW / "2004_app_pages.sha256"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Rural (Q17318027) and urban (Q3327862) communes of Morocco with coordinates. Wikidata changes
# continuously; the snapshot's sha256 and fetch date in the manifest pin what a build used.
WIKIDATA_QUERY = """SELECT ?item ?cls ?label ?fr ?coord ?admLabel WHERE {
  VALUES ?cls { wd:Q17318027 wd:Q3327862 }
  ?item wdt:P31 ?cls; wdt:P625 ?coord.
  OPTIONAL { ?item rdfs:label ?label FILTER(lang(?label) = "en") }
  OPTIONAL { ?item rdfs:label ?fr FILTER(lang(?fr) = "fr") }
  OPTIONAL { ?item wdt:P131 ?adm. ?adm rdfs:label ?admLabel FILTER(lang(?admLabel) = "en") }
} ORDER BY ?item ?coord"""
WIKIDATA_URL = "https://query.wikidata.org/sparql?query=" + urllib.parse.quote(WIKIDATA_QUERY)

# the Wikidata Query Service asks for a descriptive agent and needs Accept to choose CSV
HEADERS = {
    "geometry/wikidata_communes.csv": [
        "-A",
        "morocco-census/1 (https://github.com/machinemirror/morocco-census)",
        "-H",
        "Accept: text/csv",
    ]
}

# (path under data/raw, url, description)
FILES = [
    # --- RGPH 2004 ---
    (
        "2004/pauvrete_developpement_2004.pdf",
        "https://www.hcp.ma/file/231444/",
        "HCP (2004) Pauvrete, developpement humain et developpement social au Maroc; Annexe 2 = commune indices",
    ),
    (
        "2004/population_legale_2004_settat.pdf",
        "https://www.hcp.ma/reg-chaouia/docs/Publications/Population%20legale_2004.pdf",
        "HCP Direction provinciale de Settat: population legale 2004 by region, and by commune on post-2009 codes",
    ),
    (
        "2014/grand_casablanca_note_premiers_resultats_2014.pdf",
        "https://www.hcp.ma/reg-casablanca/docs/docs/rgph2014__region_grand_casablanca_note_de_presentation_des_premiers_resultats.pdf",
        "HCP Grand Casablanca: note on the first RGPH 2014 results, 2004 and 2014 population by commune on 2014 boundaries",
    ),
    (
        "2004/carto_pauvrete_communale_2004_2014.xlsx",
        "https://www.hcp.ma/file/231434/",
        "HCP cartographie de la pauvrete multidimensionnelle communale 2004 et 2014",
    ),
    # --- RGPH 2014 ---
    ("menages_2014.xlsx", "https://rgph2014.hcp.ma/file/190480/", "RGPH 2014 - Indicateurs communaux - Menages"),
    ("individus_2014.xlsx", "https://rgph2014.hcp.ma/file/190479/", "RGPH 2014 - Indicateurs communaux - Individus"),
    (
        "activite_2014.xlsx",
        "https://www.hcp.ma/file/230028/",
        "RGPH 2014 - La Profession et l'Activite Economique - Niveau Communal",
    ),
    ("diplome_2014.xlsx", "https://www.hcp.ma/file/230031/", "RGPH 2014 - Le Diplome - Niveau Communal"),
    (
        "poplegale_2014_16reg.xlsx",
        "https://rgph2014.hcp.ma/file/166315/",
        "RGPH 2014 - Population legale par regions/provinces/communes (16 regions cut)",
    ),
    (
        "poplegale_2014_12reg.xlsx",
        "https://rgph2014.hcp.ma/file/166326/",
        "RGPH 2014 - Population legale par regions/provinces/communes (12 regions cut)",
    ),
    # --- RGPH 2024 ---
    (
        "poplegale_2024.xlsx",
        "https://www.hcp.ma/file/242341/",
        "RGPH 2024 - Population legale par regions/provinces/prefectures/communes",
    ),
    (
        "indicateurs_demo_socioeco_2024.xlsx",
        "https://www.hcp.ma/file/242671/",
        "RGPH 2024 - Indicateurs demographiques et socioeconomiques du Royaume",
    ),
    (
        "transport_domicile_travail_2024.xlsx",
        "https://www.hcp.ma/file/248301/",
        "RGPH 2024 - Indicateurs communaux - Mode de transport domicile-lieu de travail",
    ),
    (
        "parc_logement_urbain_2024.xlsx",
        "https://www.hcp.ma/file/246208/",
        "RGPH 2024 - Indicateurs communaux du parc logement urbain",
    ),
    (
        "cee_etablissements_eco_2024.xlsx",
        "https://www.hcp.ma/file/242672/",
        "RGPH 2024 - Cartographie des Etablissements Economiques (CEE), par commune",
    ),
    (
        "population_menages_douars_2024.xlsx",
        "https://www.hcp.ma/file/245768/",
        "RGPH 2024 - Population et menages par douars",
    ),
    (
        "migration_interne_2024.xlsx",
        "https://www.hcp.ma/file/245650/",
        "RGPH 2024 - Base de donnees de la migration interne",
    ),
    (
        "2024/mpi_communes_2014_2024.xls",
        "https://www.hcp.ma/file/245096/",
        "HCP (May 2025) base de donnees de la cartographie de la pauvrete multidimensionnelle, 2014 et 2024",
    ),
    # --- Geometry ---
    (
        "geometry/MA.zip",
        "https://download.geonames.org/export/dump/MA.zip",
        "GeoNames gazetteer, Morocco (CC BY 4.0; updated daily upstream)",
    ),
    (
        "geometry/EH.zip",
        "https://download.geonames.org/export/dump/EH.zip",
        "GeoNames gazetteer, Western Sahara (CC BY 4.0; updated daily upstream)",
    ),
    (
        "geometry/ne_10m_admin_0_countries.zip",
        "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip",
        "Natural Earth 1:10m admin-0 countries (public domain); outline for clipping",
    ),
    (
        "geometry/wikidata_communes.csv",
        WIKIDATA_URL,
        "Wikidata rural and urban communes of Morocco with coordinates (CC0; changes continuously upstream)",
    ),
]

UNZIP = {
    "geometry/MA.zip": "geometry",
    "geometry/EH.zip": "geometry",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def curl_fetch(url: str, dest: Path, headers: list[str] | None = None) -> tuple[bool, str]:
    cmd = [
        "curl",
        "-sSL",
        "--fail",
        *(headers or ["-A", USER_AGENT, "-H", "Accept: */*"]),
        "--connect-timeout",
        "20",
        "--max-time",
        "600",
        "-o",
        str(dest),
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return False, proc.stderr.strip()[-500:]
    return True, ""


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


# HCP draws commune boundaries in its RGPH 2024 results platform (Apache Superset); the per-province
# GeoJSON files are static assets whose hashed names are listed in the country-map bundle, so they are
# discovered from the live bundle rather than pinned.
HCP_PLATFORM = "https://resultats2024.rgphapps.ma"
HCP_BOUNDARIES = "hcp_boundaries_2024"


def changed(manifest: dict, rel: str, digest: str, accept: bool) -> bool:
    """True when rel's digest differs from the manifest and the change is not accepted."""
    known = manifest.get(rel, {}).get("sha256")
    if known in (None, digest):
        return False
    print(f"  CHANGED: {rel} sha256 {digest[:12]}, manifest {known[:12]}" + ("" if accept else " (--accept-changes to record)"))
    return not accept


def fetch_hcp_boundaries(manifest: dict, accept: bool) -> tuple[list, list]:
    import re
    import urllib.request

    def get(url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        return urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "ignore")

    dest = RAW / HCP_BOUNDARIES
    dest.mkdir(parents=True, exist_ok=True)
    page = get(HCP_PLATFORM + "/")
    files = {}
    for js in re.findall(r'src="(/static/assets/[\w.]+\.entry\.js)"', page):
        src = get(HCP_PLATFORM + js)
        if "morocco_01_051" not in src:
            continue
        head = src[: src.index("morocco:")]
        assigned = dict(re.findall(r'[,\s;]([A-Za-z_$]{1,2})=\w+\.p\+"([0-9a-f]{20})\.geojson"', head[-20000:]))
        block = src[src.index("morocco:") : src.index("palestine:")]
        for key, ref in re.findall(r"(morocco_\d\d_\d{3}):([^,}]+)", block):
            h = re.search(r"([0-9a-f]{20})\.geojson", ref)
            files[key] = h.group(1) if h else assigned.get(ref.strip())
    if len(files) != 75 or None in files.values():
        return [(HCP_BOUNDARIES, HCP_PLATFORM, f"expected 75 province files, found {len(files)}")], []
    failures, mismatches = [], []
    for key, h in sorted(files.items()):
        rel, url = f"{HCP_BOUNDARIES}/{key}.geojson", f"{HCP_PLATFORM}/static/assets/{h}.geojson"
        out = RAW / rel
        if not out.exists():
            ok, err = curl_fetch(url, out)
            if not ok:
                failures.append((rel, url, err))
                continue
        digest = sha256_of(out)
        if changed(manifest, rel, digest, accept):
            mismatches.append(rel)
            continue
        manifest[rel] = {
            "url": url,
            "description": f"HCP RGPH 2024 results platform, commune boundaries of province {key[-6:]}",
            "size_bytes": out.stat().st_size,
            "sha256": digest,
            "fetch_date": manifest.get(rel, {}).get("fetch_date") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    print(f"HCP boundaries: {len(files) - len(failures)}/75 province files")
    return failures, mismatches


def app_digests() -> dict[str, tuple[str, str]]:
    """manifest key -> (sha256, description) for the 2004 crawl, and the per-page list its digest covers."""
    pages = "".join(f"{sha256_of(f)}  {f.name}\n" for f in sorted(R_APP_HTML.glob("*.html")))
    return {
        "2004_app/communes_index.csv": (sha256_of(R_APP_INDEX), "communes listed by the 2004 app crawl"),
        "2004_app/html": (
            hashlib.sha256(pages.encode()).hexdigest(),
            f"the crawl's {pages.count(chr(10))} profile pages; digest of {APP_PAGES_PATH.name}",
        ),
    }, pages


def record_2004_app(manifest: dict, accept: bool) -> list:
    """Check the 2004 crawl (communes_index.csv and the cached pages) against the manifest, or record it."""
    if not R_APP_INDEX.exists():
        print("[skip] 2004_app: not crawled (mc crawl-2004)")
        return []
    digests, pages = app_digests()
    mismatches = []
    for rel, (digest, desc) in digests.items():
        if changed(manifest, rel, digest, accept):
            mismatches.append(rel)
            continue
        size = R_APP_INDEX.stat().st_size if rel.endswith(".csv") else None
        manifest[rel] = (
            manifest.get(rel, {})
            | {"url": "https://applications-web.hcp.ma/hpmc/frmmarocenchiffres.aspx", "description": desc, "sha256": digest}
            | ({"size_bytes": size} if size else {})
        )
    if not mismatches:
        APP_PAGES_PATH.write_text(pages)
    print(f"2004_app: {pages.count(chr(10))} pages" + (f", {len(mismatches)} changed" if mismatches else ""))
    return mismatches


def verify(manifest: dict | None = None, raw: Path = RAW) -> list[str]:
    """Raw inputs that are missing or differ from the manifest; `mc build` refuses to run while any do."""
    manifest = load_manifest() if manifest is None else manifest
    app = app_digests()[0] if (raw / "2004_app" / "communes_index.csv").exists() else {}
    bad = []
    for rel, entry in manifest.items():
        path = raw / rel
        if rel in app:
            digest = app[rel][0]
        elif path.is_file():
            digest = sha256_of(path)
        else:
            bad.append(f"{rel}: missing")
            continue
        if digest != entry.get("sha256"):
            bad.append(f"{rel}: sha256 {digest[:12]}, manifest {str(entry.get('sha256'))[:12]}")
    return bad


def main(accept: bool = False) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    failures, mismatches = [], []

    for rel, url, desc in FILES:
        dest = RAW / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 0:
            digest = sha256_of(dest)
            print(f"[skip] {rel}")
            if changed(manifest, rel, digest, accept):
                mismatches.append(rel)
            elif accept:
                manifest.get(rel, {})["sha256"] = digest
            manifest.setdefault(
                rel,
                {
                    "url": url,
                    "description": desc,
                    "size_bytes": dest.stat().st_size,
                    "sha256": digest,
                    "fetch_date": None,
                },
            )
        else:
            print(f"[fetch] {rel} <- {url}")
            tmp = dest.with_suffix(dest.suffix + ".part")
            ok, err = curl_fetch(url, tmp, HEADERS.get(rel))
            if ok and tmp.stat().st_size < 200:
                ok, err = False, f"suspiciously small response ({tmp.stat().st_size} bytes)"
            if not ok:
                print(f"  FAILED: {err}")
                failures.append((rel, url, err))
                tmp.unlink(missing_ok=True)
                continue
            tmp.rename(dest)
            digest = sha256_of(dest)
            if changed(manifest, rel, digest, accept):
                mismatches.append(rel)
                continue
            manifest[rel] = {
                "url": url,
                "description": desc,
                "size_bytes": dest.stat().st_size,
                "sha256": digest,
                "fetch_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            print(f"  OK: {dest.stat().st_size} bytes, sha256={digest[:12]}...")
        if rel in UNZIP:
            with zipfile.ZipFile(dest) as z:
                z.extractall(RAW / UNZIP[rel])
        save_manifest(manifest)

    f, m = fetch_hcp_boundaries(manifest, accept)
    failures += f
    mismatches += m + record_2004_app(manifest, accept)
    save_manifest(manifest)
    print(f"\n{len(FILES) - len(failures)}/{len(FILES)} files present.")
    for rel, url, err in failures:
        print(f"  FAILED {rel} <- {url}: {err}")
    for rel in mismatches:
        print(f"  CHANGED {rel}: differs from the manifest; rerun with --accept-changes to record it")
    return 1 if failures or mismatches else 0
