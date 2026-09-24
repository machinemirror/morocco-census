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

from .config import P_COMMUNES, P_INDICES_2004, P_SLICES, R_ANNEX_2004, R_APP_HTML

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


def total(*vals):
    return None if all(v is None for v in vals) else sum(v or 0 for v in vals)


def fem(rows, label, after):
    """Female count (effectif) from the 'Féminin' row that follows `label` within section `after`."""
    seen = False
    for i, r in enumerate(rows):
        if not seen:
            seen = r[0].strip().upper().startswith(after.upper())
            continue
        if r[0].strip().lower() == label.lower():
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            if nxt and nxt[0].strip() == "Féminin":
                return num(nxt[1]) or 0.0 if len(nxt) > 1 else 0.0
            return None
    return None


def share(part, *whole):
    tot = total(*whole)
    return None if part is None or not tot else 100 * part / tot


def parse_commune(code: str, html: Path = R_APP_HTML) -> dict | None:
    files = {p: html / f"{code}_{p}.html" for p in "dseh"}
    if not all(f.exists() for f in files.values()):
        return None
    d, s, e, h = (rows_of(files[p]) for p in "dseh")
    # the app's rural communes end in 2; municipalities, arrondissements and autonomous centres are urban
    out = {"app_code": code, "milieu04": "rural" if code.endswith("2") else "urban"}
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
    out["pct_women_divorced"] = share(
        fem(s, "Divorcé", "ETAT MATRIMONIAL"),
        *[fem(s, x, "ETAT MATRIMONIAL") for x in ("Célibataire", "Marié", "Veuf", "Divorcé")],
    )
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
    out["age_15_19"] = grab(d, "15 à 19 ans", 2)
    out["age_20_24"] = grab(d, "20 à 24 ans", 2)
    out["age_75plus"] = total(grab(d, "75 à 84 ans", 2), grab(d, "85 ans et plus", 2))
    out["age_60plus"] = grab(d, "60 ans et plus", 2)
    out["age_65plus"] = total(grab(d, "65 à 74 ans", 2), grab(d, "75 à 84 ans", 2), grab(d, "85 ans et plus", 2))
    out["pct_single"] = grab(s, "Célibataire", 2, after="ETAT MATRIMONIAL")
    out["pct_married"] = grab(s, "Marié", 2, after="ETAT MATRIMONIAL")
    out["pct_divorced"] = grab(s, "Divorcé", 2, after="ETAT MATRIMONIAL")
    out["pct_widowed"] = grab(s, "Veuf", 2, after="ETAT MATRIMONIAL")
    out["edu_primary"] = grab(s, "Primaire", 2, after="NIVEAU")
    out["edu_lower_secondary"] = grab(s, "Collégial", 2, after="NIVEAU")
    out["edu_upper_secondary"] = grab(s, "Secondaire", 2, after="NIVEAU")
    out["edu_higher"] = grab(s, "Universitaire", 2, after="NIVEAU")
    out["lang_darija"] = grab(s, "Arabe dialectal", 2, after="LANGUES PARLEES")
    out["lang_tachelhit"] = grab(s, "Tashlhit", 2, after="LANGUES PARLEES")
    out["lang_tamazight"] = grab(s, "Tamazight", 2, after="LANGUES PARLEES")
    out["lang_tarifit"] = grab(s, "Tarifit", 2, after="LANGUES PARLEES")
    out["lang_hassania"] = grab(s, "Hsaynia", 2, after="LANGUES PARLEES")
    out["lit_arabic_only"] = grab(s, "Arabe seul", 2, after="LANGUES PARLEES ET ECRITES")
    out["lit_arabic_french"] = grab(s, "Arabe et Français seuls", 2, after="LANGUES PARLEES ET ECRITES")
    out["pct_employer"] = grab(e, "Employeur", 2, after="SITUATION DANS LA PROFESSION")
    out["pct_self_employed"] = grab(e, "Indépendant", 2, after="SITUATION DANS LA PROFESSION")
    out["pct_public_employee"] = grab(e, "Salariés publiques", 2, after="SITUATION DANS LA PROFESSION")
    out["pct_private_employee"] = grab(e, "Salariés privés", 2, after="SITUATION DANS LA PROFESSION")
    out["pct_family_worker"] = grab(e, "Aide familiale", 2, after="SITUATION DANS LA PROFESSION")
    out["pct_apprentice"] = grab(e, "Apprentie", 2, after="SITUATION DANS LA PROFESSION")
    out["sec_industry"] = total(grab(e, "Mines", 2, after="BRANCHES"), grab(e, "Industrie", 2, after="BRANCHES"))
    out["sec_utilities"] = grab(e, "Eau électricité et énergie", 2, after="BRANCHES")
    out["sec_construction"] = grab(e, "B.T.P", 2, after="BRANCHES")
    out["sec_trade"] = grab(e, "Commerce", 2, after="BRANCHES")
    out["sec_transport"] = grab(e, "Transport et communication", 2, after="BRANCHES")
    out["sec_services"] = grab(e, "Services", 2, after="BRANCHES")
    out["sec_public"] = grab(e, "Administration", 2, after="BRANCHES")
    out["sec_other"] = grab(e, "Activité exercée hors du Maroc", 2, startswith=True, after="BRANCHES")
    out["dwell_villa"] = grab(h, "Villa, niveau de villa", 2)
    out["dwell_apartment"] = grab(h, "Appartement", 2)
    out["dwell_moroccan"] = total(grab(h, "Maison marocaine traditionnelle", 2), grab(h, "Maison marocaine moderne", 2))
    out["dwell_rural"] = grab(h, "Habitation de type rural", 2)
    out["dwell_other"] = grab(h, "Autres", 2, after="TYPES D'HABITATS")
    # year of construction is published for urban households only: rural pages show empty counts and 0%
    built = [grab(h, x, 1) for x in ("1995 à septembre 2004", "1975 à 1994", "1955 à 1974", "1954 ou avant")]
    out["dwell_age_lt10"] = grab(h, "1995 à septembre 2004", 2) if total(*built) else None
    out["pct_kitchen"] = grab(h, "Cuisine", 2, after="ELEMENT DE CONFORT")
    out["pct_toilet"] = grab(h, "W.C.", 2, after="ELEMENT DE CONFORT")
    out["road_distance"] = grab(h, "Distance moyenne (km)", 1) if grab(h, "Ménages ruraux", 1) else None
    out["pct_landline"] = grab(h, "Téléphone Fixe", 2, after="EQUIPEMENT DOMESTIQUE")
    out["pct_satellite"] = grab(h, "Parabole", 2, after="EQUIPEMENT DOMESTIQUE")
    return out


# Male and female rates, from the female counts ('Féminin' rows) the pages give under each category.
# {variable: (page, section, categories summed)}; each section's base is the sum of its categories.
SEX_SECTIONS_2004 = {
    "ETAT MATRIMONIAL": ("s", {"pct_single": ["Célibataire"], "pct_married": ["Marié"], "pct_widowed": ["Veuf"],
                               "pct_divorced": ["Divorcé"]}),
    "NIVEAU": ("s", {"pct_no_education": ["Néant"], "edu_primary": ["Primaire"], "edu_lower_secondary": ["Collégial"],
                     "edu_upper_secondary": ["Secondaire"], "edu_higher": ["Universitaire"]}),
    "SITUATION DANS LA PROFESSION": ("e", {"pct_employer": ["Employeur"], "pct_self_employed": ["Indépendant"],
                                           "pct_public_employee": ["Salariés publiques"],
                                           "pct_private_employee": ["Salariés privés"],
                                           "pct_family_worker": ["Aide familiale"], "pct_apprentice": ["Apprentie"]}),
}
AGES_2004 = {
    "age_0_4": ["Moins de 5 ans"], "age_5_9": ["5 à 9 ans"], "age_10_14": ["10 à 14 ans"], "age_15_19": ["15 à 19 ans"],
    "age_20_24": ["20 à 24 ans"], "age_60plus": ["60 ans et plus"],
    "age_65plus": ["65 à 74 ans", "75 à 84 ans", "85 ans et plus"], "age_75plus": ["75 à 84 ans", "85 ans et plus"],
}


def parse_commune_sex(code: str, html: Path = R_APP_HTML) -> list[dict]:
    pages = {p: rows_of(html / f"{code}_{p}.html") for p in "dse"}
    d = pages["d"]
    pop = {"all": grab(d, "Population totale", 1), "female": grab(d, "Féminin", 1, after="SEXE")}
    counts = {}  # variable -> (all, female, base all, base female)

    def section(rows, after, cats):
        tot = {k: [grab(rows, x, 1, after=after) for x in v] for k, v in cats.items()}
        fm = {k: [fem(rows, x, after) for x in v] for k, v in cats.items()}
        base = total(*[x for v in tot.values() for x in v]), total(*[x for v in fm.values() for x in v])
        for k in cats:
            counts[k] = (total(*tot[k]), total(*fm[k]), *base)

    for after, (page, cats) in SEX_SECTIONS_2004.items():
        section(pages[page], after, cats)
    for k, v in AGES_2004.items():
        counts[k] = (total(*[grab(d, x, 1, after="AGE") for x in v]), total(*[fem(d, x, "AGE") for x in v]),
                     pop["all"], pop["female"])
    rows = []
    for sex in ("male", "female"):
        r = {"app_code": code, "sex": sex}
        n = pop["female"] if sex == "female" else total(pop["all"], -(pop["female"] or 0))
        r["population04"] = n
        for k, (a, f, ba, bf) in counts.items():
            if None in (a, ba) or f is None or bf is None:
                r[k] = None
                continue
            part, base = (f, bf) if sex == "female" else (a - f, ba - bf)
            r[k] = 100 * part / base if base else None
        # youth illiteracy (15-24) is given as a rate with a female rate below it; the male rate follows from the
        # 15-24 population by sex
        s_rows = pages["s"]
        i = next((j for j, x in enumerate(s_rows) if x[0].startswith("Taux d'analphabétisme")), None)
        rate, frate = (num(s_rows[i][1]), num(s_rows[i + 1][1])) if i is not None and i + 1 < len(s_rows) else (None, None)
        y_all, y_f = counts["age_15_19"][0] + counts["age_20_24"][0], counts["age_15_19"][1] + counts["age_20_24"][1]
        if sex == "female":
            r["pct_illiterate"] = frate
        elif None not in (rate, frate) and y_all - y_f > 0:
            r["pct_illiterate"] = (rate * y_all - frate * y_f) / (y_all - y_f)
        else:
            r["pct_illiterate"] = None
        rows.append(r)
    return rows


def app(html: Path = R_APP_HTML, out: Path = P_COMMUNES[2004]) -> pd.DataFrame:
    codes = sorted({f.name.split("_")[0] for f in html.glob("*_d.html")})
    df = pd.DataFrame([r for c in codes if (r := parse_commune(c, html))])
    df.to_csv(out, index=False)
    sex = pd.DataFrame([r for c in df.app_code for r in parse_commune_sex(c, html)])
    sex.to_csv(P_SLICES[2004, "sex"], index=False)
    print(f"2004 app: {len(df)} communes -> {out.name}; {len(sex)} male/female rows")
    return df
