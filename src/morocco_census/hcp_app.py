"""Crawl HCP's Maroc-en-Chiffres app (RGPH 2004 commune profiles) -> data/raw/2004_app/html/.

The app is an ASP.NET WebForms page with cascading dropdowns (lRE region -> lPR province ->
lCMA commune) on the pre-2015 16-region scheme. For each commune all four profile pages
(d=démographie, s=socio-culturel, e=économie, h=habitat) are cached as
html/<commune_code>_<profil>.html; existing files are skipped, so the crawl is resumable.
Also writes data/raw/2004_app/communes_index.csv. Takes several hours at a 0.35 s delay.
"""

import csv
import time

import requests
from bs4 import BeautifulSoup

from .config import R_APP_HTML, R_APP_INDEX

URL = "https://applications-web.hcp.ma/hpmc/frmmarocenchiffres.aspx"
UA = {"User-Agent": "Mozilla/5.0 (research crawl; +https://github.com/machinemirror/morocco-census)"}
PROFILES = ("d", "s", "e", "h")


def state(soup: BeautifulSoup) -> dict:
    d = {}
    for el in soup.find("form").find_all("input", {"type": "hidden"}):
        d[el.get("name")] = el.get("value", "")
    d["typeProfil"] = "d"  # a profile radio must be selected
    return d


def options(soup: BeautifulSoup, name: str) -> list[tuple[str, str]]:
    sel = soup.find("select", {"name": name})
    if not sel:
        return []
    return [(o.get("value", ""), o.get_text(strip=True)) for o in sel.find_all("option")]


def post(s: requests.Session, soup: BeautifulSoup, target: str, values: dict) -> BeautifulSoup:
    # omit selects that currently have no options: event validation rejects them
    data = state(soup) | {"__EVENTTARGET": target, "__EVENTARGUMENT": "", "__LASTFOCUS": ""} | values
    r = s.post(URL, data=data, headers=UA, timeout=60)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def fresh(s: requests.Session) -> BeautifulSoup:
    return BeautifulSoup(s.get(URL, headers=UA, timeout=60).text, "lxml")


def main() -> None:
    R_APP_HTML.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    soup = fresh(s)
    regions = [(v, t) for v, t in options(soup, "lRE") if not t.startswith("(")]
    index = []
    n_fetched = n_cached = 0
    for rv, rt in regions:
        soup = fresh(s)
        soup = post(s, soup, "lRE", {"lRE": rv})
        provs = [(v, t) for v, t in options(soup, "lPR") if not t.startswith("(")]
        for pv, pt in provs:
            soup_p = post(s, soup, "lPR", {"lRE": rv, "lPR": pv})
            coms = [(v, t) for v, t in options(soup_p, "lCMA") if not t.startswith("(")]
            for cv, ct in coms:
                index.append(
                    {
                        "region_code": rv,
                        "region": rt,
                        "prov_code": pv,
                        "province": pt,
                        "commune_code": cv,
                        "commune": ct,
                    }
                )
                for profil in PROFILES:
                    f = R_APP_HTML / f"{cv}_{profil}.html"
                    if f.exists() and f.stat().st_size > 5000:
                        n_cached += 1
                        continue
                    data = state(soup_p) | {
                        "__EVENTTARGET": "lCMA",
                        "__EVENTARGUMENT": "",
                        "__LASTFOCUS": "",
                        "lRE": rv,
                        "lPR": pv,
                        "lCMA": cv,
                        "typeProfil": profil,
                    }
                    for attempt in range(3):
                        try:
                            r = s.post(URL, data=data, headers=UA, timeout=90)
                            if r.status_code == 200 and len(r.text) > 5000:
                                f.write_text(r.text)
                                n_fetched += 1
                                break
                        except requests.RequestException:
                            time.sleep(5 * (attempt + 1))
                            soup_p = post(s, post(s, fresh(s), "lRE", {"lRE": rv}), "lPR", {"lRE": rv, "lPR": pv})
                            data = state(soup_p) | {
                                k: data[k]
                                for k in (
                                    "__EVENTTARGET",
                                    "__EVENTARGUMENT",
                                    "__LASTFOCUS",
                                    "lRE",
                                    "lPR",
                                    "lCMA",
                                    "typeProfil",
                                )
                            }
                    time.sleep(0.35)
            print(f"[{rt} / {pt}] {len(coms)} communes done (fetched {n_fetched}, cached {n_cached})", flush=True)
    with open(R_APP_INDEX, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(index[0].keys()))
        w.writeheader()
        w.writerows(index)
    print(f"DONE: {len(index)} communes, fetched {n_fetched}, cached {n_cached}")
