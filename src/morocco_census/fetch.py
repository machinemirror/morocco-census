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

from .config import RAW

MANIFEST_PATH = RAW / "manifest.json"

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


def fetch_hcp_boundaries(manifest: dict) -> list:
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
        return [(HCP_BOUNDARIES, HCP_PLATFORM, f"expected 75 province files, found {len(files)}")]
    failures = []
    for key, h in sorted(files.items()):
        rel, url = f"{HCP_BOUNDARIES}/{key}.geojson", f"{HCP_PLATFORM}/static/assets/{h}.geojson"
        out = RAW / rel
        if not out.exists():
            ok, err = curl_fetch(url, out)
            if not ok:
                failures.append((rel, url, err))
                continue
        manifest[rel] = {
            "url": url,
            "description": f"HCP RGPH 2024 results platform, commune boundaries of province {key[-6:]}",
            "size_bytes": out.stat().st_size,
            "sha256": sha256_of(out),
            "fetch_date": manifest.get(rel, {}).get("fetch_date") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    print(f"HCP boundaries: {len(files) - len(failures)}/75 province files")
    return failures


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    failures = []

    for rel, url, desc in FILES:
        dest = RAW / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 0:
            digest = sha256_of(dest)
            known = manifest.get(rel, {}).get("sha256")
            flag = "" if known in (None, digest) else "  (sha256 differs from manifest)"
            print(f"[skip] {rel}{flag}")
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
            known = manifest.get(rel, {}).get("sha256")
            if known and known != digest:
                print(f"  NOTE: sha256 {digest[:12]} differs from manifest {known[:12]} (upstream changed)")
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

    failures += fetch_hcp_boundaries(manifest)
    save_manifest(manifest)
    print(f"\n{len(FILES) - len(failures)}/{len(FILES)} files present.")
    for rel, url, err in failures:
        print(f"  FAILED {rel} <- {url}: {err}")
    return 1 if failures else 0
