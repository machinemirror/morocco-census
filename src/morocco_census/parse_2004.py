"""RGPH 2004 parsers.

annex(): Annexe 2 of HCP's Sept-2004 'Pauvreté, développement humain et développement social'
PDF -> commune_indices_2004.csv. Each row after pypdf extraction is a commune label then six
French-decimal numbers: taux_pauvrete, vulnerabilite, severite, inegalite, idh, ids. Region
comes from the page header; the province column is vertically merged in the PDF, so labels
carry a 'Province Commune' prefix that the crosswalk splits later.

app(): the crawled Maroc-en-Chiffres commune profiles -> communes_2004.csv. '%' column
preferred; effectifs kept where they serve as weights.
"""

import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .config import P_COMMUNES, P_INDICES_2004, R_ANNEX_2004, R_APP_HTML

NUM = r"\d{1,3},\d{1,3}"
# four numeric columns, then IDH and IDS which may be missing ("-")
ROW = re.compile(rf"^(?P<label>.*?)\s*(?P<n>({NUM}\s+){{4}}(?:{NUM}|-)\s+(?:{NUM}|-))\s*$")
SKIP = re.compile(
    r"Indices|développement|Pauvreté|Vulnéra|bilité|Sévérité|pauvreté|Inégalité|Humain|Social|Commune|Province"
    r"|R[ée]gion|Taux|Indice|^\d{1,3}\s*$|^\s*$"
)


def annex(src: Path = R_ANNEX_2004, out: Path = P_INDICES_2004) -> pd.DataFrame:
    rows = []
    for i, p in enumerate(PdfReader(src).pages, start=1):
        text = p.extract_text() or ""
        if not re.search(r"Indices\s+communaux", text):
            continue
        m = re.search(r"R[ée]gion\s*:?\s*([A-ZÉÈÀ' \-–]+)", text)
        region = m.group(1).strip() if m else ""
        pending = ""
        for line in text.split("\n"):
            line = line.strip()
            mm = ROW.match(line)
            if not mm:
                if line and not SKIP.search(line):
                    pending = (pending + " " + line).strip()  # wrapped label fragment
                continue
            label = (pending + " " + mm.group("label")).strip()
            label = re.sub(
                r"^(communaux|de|la|développement|Indices|d)(\s+(de|la|développement|communaux|d))*\s+", "", label
            )
            label = re.sub(r"\s{2,}", " ", label)
            pending = ""
            nums = [None if x == "-" else float(x.replace(",", ".")) for x in mm.group("n").split()]
            rows.append(
                {
                    "page": i,
                    "region": region,
                    "label": label,
                    "taux_pauvrete": nums[0],
                    "vulnerabilite": nums[1],
                    "severite": nums[2],
                    "inegalite": nums[3],
                    "idh": nums[4],
                    "ids": nums[5],
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    print(
        f"2004 annex: {len(df)} rows -> {out.name} (idh missing {df.idh.isna().sum()}, ids missing {df.ids.isna().sum()})"
    )
    return df


def num(x: str) -> float | None:
    x = x.replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


def rows_of(path: Path) -> list[list[str]]:
    soup = BeautifulSoup(path.read_text(), "lxml")
    t = soup.find_all("table")[-1]
    out = []
    for tr in t.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if cells and any(cells):
            out.append(cells)
    return out


def grab(rows, label, col=2, startswith=False, after=None):
    """Value from the row whose first cell matches label; col 1=effectif, 2=%.
    `after`: only match rows appearing after the given section header."""
    seen = after is None
    for r in rows:
        if not seen:
            if r[0].strip().upper().startswith(after.upper()):
                seen = True
            continue
        ok = r[0].strip().lower().startswith(label.lower()) if startswith else r[0].strip().lower() == label.lower()
        if ok and len(r) > col:
            return num(r[col])
    return None


def parse_commune(code: str, html: Path = R_APP_HTML) -> dict | None:
    files = {p: html / f"{code}_{p}.html" for p in "dseh"}
    if not all(f.exists() for f in files.values()):
        return None
    d, s, e, h = (rows_of(files[p]) for p in "dseh")
    out = {"app_code": code}
    out["population04"] = grab(d, "Population totale", 1)
    out["pct_female"] = grab(d, "Féminin", 2, after="SEXE")
    out["age_0_4"] = grab(d, "Moins de 5 ans", 2)
    out["age_5_9"] = grab(d, "5 à 9 ans", 2)
    out["age_10_14"] = grab(d, "10 à 14 ans", 2)
    out["isf"] = grab(d, "Indice synthétique de fécondité", 1)
    out["birth_rate"] = grab(d, "Taux de natalité", 1, startswith=True)
    out["infant_mortality"] = grab(d, "Taux de mortalité infantil", 1, startswith=True)
    out["hh_size_avg"] = grab(d, "Taille moyenne du ménage", 1)
    out["n_households"] = grab(d, "Ménages total", 1)
    out["pct_no_education"] = grab(s, "Néant", 2, after="NIVEAU")
    out["pct_illiterate"] = grab(s, "Taux d'analphabétisme", 1, startswith=True)
    out["pct_no_lang_written"] = grab(s, "Aucune", 2, after="LANGUES PARLEES ET ECRITES")
    out["pct_women_divorced"] = grab(s, "Divorcé", 2, startswith=True, after="ETAT MATRIMONIAL")
    out["pct_migrant_since99"] = grab(s, "Commune différente", 2, after="RESIDENCE EN 1999")
    out["activity_rate"] = grab(e, "Actifs", 2, startswith=True)
    out["pct_agriculture"] = grab(e, "Agriculture", 2, startswith=True)
    out["pct_owner"] = grab(h, "Ménages propriétaires", 2)
    out["pct_renter"] = grab(h, "Ménages locataires", 2)
    out["pct_electricity"] = grab(h, "Electricité", 2, after="ELEMENT DE CONFORT")
    out["pct_water"] = grab(h, "Eau courante", 2, after="ELEMENT DE CONFORT")
    out["pct_cellphone"] = grab(h, "Portable", 2, startswith=True, after="EQUIPEMENT DOMESTIQUE")
    out["pct_tv"] = grab(h, "Télévision", 2, after="EQUIPEMENT DOMESTIQUE")
    out["pct_slum"] = grab(h, "Maison sommaire ou bidonville", 2)
    return out


def app(html: Path = R_APP_HTML, out: Path = P_COMMUNES[2004]) -> pd.DataFrame:
    codes = sorted({f.name.split("_")[0] for f in html.glob("*_d.html")})
    df = pd.DataFrame([r for c in codes if (r := parse_commune(c, html))])
    df.to_csv(out, index=False)
    print(f"2004 app: {len(df)} communes -> {out.name}")
    return df
