"""Commune crosswalks.

communes(): 2004 <-> 2014 <-> 2024 -> crosswalk_communes.csv. Spine: the RGPH 2014 commune list
(dotted geographic codes, names, provinces) from menages_2014.xlsx. Joined to the HCP 2004-2014
poverty-map workbook (name + province), the parsed 2004 annex ('Province Commune' label), and the
May-2025 MPI database (2024 codes; province from the 4-digit prefix). Matching is normalized
name + province, then unambiguous name-only, then mutual-best province-constrained fuzzy.

app2004(): Maroc-en-Chiffres app codes (2004 profiles) <-> 2014 spine -> crosswalk_app2004.csv.
"""

import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz, process

from .config import (
    LINK_REVIEW,
    P_COMMUNES,
    P_CROSSWALK,
    P_CROSSWALK_APP,
    P_INDICES_2004,
    R_APP_INDEX,
    R_CARTO,
    R_MPI,
    RAW,
)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((mun|m|c|ac|cu|arr|arrond)\.?\)", "", s)
    s = re.sub(r"\bcentre\b", "", s)
    s = re.sub(
        r"^(commune( urbaine| rurale)?|arrondissement|municipalite|province|prefecture)( d'| de | des | du | )", "", s
    )
    return re.sub(r"[^a-z0-9]", "", s)


def load_2014() -> pd.DataFrame:
    df = pd.read_excel(RAW / "menages_2014.xlsx", sheet_name="Indic.Ensemble", header=None)
    df = df.rename(columns={0: "reg", 1: "pro", 2: "cer", 3: "prefarr", 4: "com", 6: "code", 7: "name"})
    prov = None
    rows = []
    for _, r in df.iterrows():
        code = str(r["code"]) if pd.notna(r["code"]) else ""
        name = str(r["name"]) if pd.notna(r["name"]) else ""
        if name.startswith(("Province", "Prefecture", "Préfecture")):
            prov = re.sub(r"^[^:]*:\s*", "", name).strip()
            continue
        # depth 4 with COM set = commune / municipality / arrondissement (excludes préfectures d'arrondissements)
        if code.count(".") == 4 and pd.notna(r["com"]):
            rows.append({"code14": code, "name14": name.strip(), "prov14": prov})
    out = pd.DataFrame(rows).drop_duplicates("code14")
    out["k_name"] = out.name14.map(norm)
    out["k_prov"] = out.prov14.map(norm)
    return out


def load_carto() -> pd.DataFrame:
    x = pd.ExcelFile(R_CARTO)
    frames = []
    for s in x.sheet_names:
        if s == "Ensemble":
            continue
        df = x.parse(s, header=None, skiprows=5)
        df = df.rename(columns={0: "prov", 1: "commune", 2: "centre"})
        # rows carrying a libellé_centre are sub-commune centres
        df = df[df.commune.notna() & df.prov.notna() & df.centre.isna()][["prov", "commune"]]
        frames.append(df)
    out = pd.concat(frames).drop_duplicates().reset_index(drop=True)
    out["k_name"] = out.commune.map(norm)
    out["k_prov"] = out.prov.map(norm)
    return out.rename(columns={"prov": "prov_carto", "commune": "name_carto"})


def load_2024() -> pd.DataFrame:
    df = pd.read_excel(R_MPI, sheet_name="Ensemble", header=None, skiprows=6)
    df = df.rename(columns={0: "label", 1: "code", 2: "level", 3: "year"})
    df["code"] = pd.to_numeric(df["code"], errors="coerce").astype("Int64")
    prov = df[df.level.astype(str).str.contains("province", case=False, na=False)].drop_duplicates("code")
    prov_map = {
        str(c): re.sub(r"^(Province|Préfecture)( d'| de | des | du )", "", lab).strip()
        for c, lab in zip(prov.code, prov.label)
    }
    com = df[df.level.isin(["commune", "commune casa"])].drop_duplicates("code").copy()
    com["prov24"] = com.code.astype(str).str[:4].map(prov_map)
    # préfectures d'arrondissements carry 7-digit codes; map their communes too
    pref = df[
        df.level.astype(str).str.contains("arrondissement", case=False, na=False) & (df.code.astype(str).str.len() == 7)
    ]
    pref_map = {str(c)[:4]: lab for c, lab in zip(pref.code, pref.label)}
    com.loc[com.prov24.isna(), "prov24"] = com.loc[com.prov24.isna()].code.astype(str).str[:4].map(pref_map)
    com = com.rename(columns={"label": "name24", "code": "code24"})[["code24", "name24", "prov24"]]
    com["k_name"] = com.name24.map(norm)
    com["k_prov"] = com.prov24.map(norm)
    return com.reset_index(drop=True)


CONTAMINATION = re.compile(
    r"^(Notation :.*?rural\.\s*|Vulné-\s*|bilité\s*|(communaux |de |la |développement )+)", re.IGNORECASE
)


def load_2004() -> pd.DataFrame:
    df = pd.read_csv(P_INDICES_2004)
    df["label"] = df.label.str.replace(CONTAMINATION, "", regex=True).str.strip()
    df["k_label"] = df.label.map(norm)
    return df


def match(spine: pd.DataFrame, other: pd.DataFrame, tag: str) -> pd.Series:
    """Other-row index aligned to spine: exact name+prov, then unambiguous name-only."""
    o = other.reset_index()
    by_np = o.drop_duplicates(["k_name", "k_prov"]).set_index(["k_name", "k_prov"])["index"]
    res = spine.set_index(["k_name", "k_prov"]).index.map(by_np)
    counts = o.k_name.value_counts()
    uniq = o[o.k_name.map(counts) == 1].set_index("k_name")["index"]
    out = pd.Series(res, index=spine.index).fillna(spine.k_name.map(uniq))
    n_np = pd.Series(res).notna().sum()
    print(
        f"{tag}: name+prov {n_np}, +name-only {int(out.notna().sum() - n_np)}, total {out.notna().sum()}/{len(spine)}"
    )
    return out


def communes(out_path=P_CROSSWALK) -> pd.DataFrame:
    spine = load_2014()
    carto, c24, d04 = load_carto(), load_2024(), load_2004()
    spine["i_carto"] = match(spine, carto, "carto 2004-2014")
    spine["i_2024"] = match(spine, c24, "MPI 2024")

    # 2004 annex label is 'Province Commune ...', possibly truncated: match on an 18-char suffix
    d04r = d04.reset_index()
    suffix = {}
    for _, r in d04r.iterrows():
        suffix.setdefault(norm(r.label)[-18:], []).append(r["index"])

    def m04(row):
        k = (row.k_prov + row.k_name)[-18:] if row.k_prov else row.k_name[-18:]
        cand = suffix.get(k, [])
        return cand[0] if len(cand) == 1 else None

    spine["i_2004"] = spine.apply(m04, axis=1)
    # fallback: 2004 label ends with the commune name, unambiguously
    ends = {}
    for _, r in d04r.iterrows():
        ends.setdefault(r.k_label, r["index"])

    def m04b(row):
        if pd.notna(row.i_2004):
            return row.i_2004
        hits = [i for kl, i in ends.items() if kl.endswith(row.k_name) and len(row.k_name) >= 5]
        return hits[0] if len(hits) == 1 else None

    spine["i_2004"] = spine.apply(m04b, axis=1)
    spine["src04"] = spine.i_2004.notna().map({True: "direct", False: None})

    # mutual-best fuzzy among still-unmatched 2004 rows, province-prefixed
    un_sp = spine[spine.i_2004.isna()]
    un_04 = d04r[~d04r["index"].isin(set(spine.i_2004.dropna()))]
    best_sp, best_04 = {}, {}
    for si, srow in un_sp.iterrows():
        key = norm(str(srow.k_prov)) + srow.k_name
        for _, orow in un_04.iterrows():
            sc = fuzz.ratio(key, orow.k_label)
            if sc > best_sp.get(si, (0, None))[0]:
                best_sp[si] = (sc, orow["index"])
            if sc > best_04.get(orow["index"], (0, None))[0]:
                best_04[orow["index"]] = (sc, si)
    n_f = 0
    for si, (sc, oi) in best_sp.items():
        if sc >= 82 and best_04.get(oi, (0, None))[1] == si:
            spine.loc[si, "i_2004"] = oi
            spine.loc[si, "src04"] = "fuzzy"
            n_f += 1
    print(f"2004 mutual-best fuzzy added: {n_f}; 2004 annex matched {spine.i_2004.notna().sum()}/{len(spine)}")

    # best fuzzy (with a same-province bonus) among unmatched 2024 rows
    un_sp2 = spine[spine.i_2024.isna()]
    un_24 = c24[~c24.index.isin(set(spine.i_2024.dropna()))]
    add2 = 0
    for si, srow in un_sp2.iterrows():
        scored = sorted(
            ((fuzz.ratio(srow.k_name, r.k_name) + 20 * (srow.k_prov == r.k_prov), i) for i, r in un_24.iterrows()),
            reverse=True,
        )
        if scored and scored[0][0] >= 105:
            spine.loc[si, "i_2024"] = scored[0][1]
            add2 += 1
    # most 2024 codes are the 2014 code without dots (cercles were renumbered in places): Ourtzarh/Ouartzagh
    by_code = pd.Series(c24.index, c24.code24.astype(str))
    by_code = by_code[~by_code.isin(set(spine.i_2024.dropna()))]
    same = spine.code14.str.replace(".", "").str.lstrip("0").map(by_code)
    add3 = int((spine.i_2024.isna() & same.notna()).sum())
    spine["i_2024"] = spine.i_2024.fillna(same)
    print(f"2024 fuzzy added: {add2}, same code: {add3}; total {spine.i_2024.notna().sum()}/{len(spine)}")

    out = spine[["code14", "name14", "prov14"]].copy()
    out["name_carto"] = spine.i_carto.map(carto.name_carto)
    out["code24"] = spine.i_2024.map(c24.code24)
    out["name24"] = spine.i_2024.map(c24.name24)
    out["label04"] = spine.i_2004.map(d04.label)
    out["idh04"] = spine.i_2004.map(d04.idh)
    out["src04"] = spine.src04
    out.to_csv(out_path, index=False)
    full = out.dropna(subset=["code24", "label04"])
    print(f"crosswalk: {len(out)} spine rows; full three-census matches {len(full)} ({len(full) / len(out):.1%})")
    return out


APP_PREFIX = re.compile(r"^(MU|CR|AC|AR)\s*-\s*", re.IGNORECASE)


def norm_app(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = APP_PREFIX.sub("", s)
    s = re.sub(r"\(.*?\)", " ", s.lower())
    s = re.sub(r"\b(arrond|arrondissement|ac|mun|municipalite|centre)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def app2004(threshold: int = 85, out_path=P_CROSSWALK_APP) -> pd.DataFrame:
    idx = pd.read_csv(R_APP_INDEX, dtype=str)
    spine = pd.read_csv(P_CROSSWALK, dtype={"code14": str})
    idx["k"], idx["p"] = idx.commune.map(norm_app), idx.province.map(norm_app)
    spine["k"], spine["p"] = spine.name14.map(norm_app), spine.prov14.fillna("").map(norm_app)

    # app labels often glue words ("CR-ElAtef" vs "El Atef"), so exact tiers compare space-free keys
    idx["kx"], idx["px"] = idx.commune.str.replace(APP_PREFIX, "", regex=True).map(norm), idx.province.map(norm)
    spine["kx"], spine["px"] = spine.name14.map(norm), spine.prov14.fillna("").map(norm)

    # The app reports a rural commune (last digit 2) apart from its autonomous centres (3-5, same first 9 digits):
    # disjoint populations that the 2014 commune covers together. A centre named like its commune is not matched
    # on its own; every centre left unmatched is linked with its commune.
    base, milieu = idx.commune_code.str[:9], idx.commune_code.str[-1]
    centre = milieu.isin(["3", "4", "5"])
    idx["parent"] = base.map(idx.commune_code[milieu == "2"].set_axis(base[milieu == "2"])).where(centre)
    parent_k = idx.parent.map(idx.set_index("commune_code").k)
    twin = centre & pd.Series(
        [fuzz.token_sort_ratio(a, b) >= 90 for a, b in zip(idx.k, parent_k.fillna(""))], idx.index
    )
    units = idx[~twin]

    # tier 1: exact name + province, unique on both sides; tier 2: name unique on both sides
    pairs = []
    for keys in (["kx", "px"], ["kx"]):
        a = units[~units.commune_code.isin({c for _, c in pairs})]
        b = spine[~spine.code14.isin({c for c, _ in pairs})]
        a = a[~a.duplicated(keys, keep=False)]
        b = b[~b.duplicated(keys, keep=False)]
        m = b.merge(a, on=keys)
        pairs += list(zip(m.code14, m.commune_code))
    n_exact = len(pairs)

    def mutual_best(g14: pd.DataFrame, pool: pd.DataFrame) -> list[tuple[str, str]]:
        fwd, back = {}, {}
        for _, r in g14.iterrows():
            h = process.extractOne(r.k, pool.k.tolist(), scorer=fuzz.token_sort_ratio, score_cutoff=threshold)
            if h:
                fwd[r.code14] = pool.commune_code.iloc[h[2]]
        for _, r in pool.iterrows():
            h = process.extractOne(r.k, g14.k.tolist(), scorer=fuzz.token_sort_ratio, score_cutoff=threshold)
            if h:
                back[r.commune_code] = g14.code14.iloc[h[2]]
        return [(c14, a) for c14, a in fwd.items() if back.get(a) == c14]

    # tier 3: province-constrained mutual-best fuzzy
    rest = units[~units.commune_code.isin({c for _, c in pairs})]
    sp = spine[~spine.code14.isin({c for c, _ in pairs})]
    for p, g14 in sp.groupby("p"):
        # province names drift between the 2004 app and the 2014 spine (renamed post-2009): allow a fuzzy link
        pool = rest[rest.p == p]
        if pool.empty:
            hit = process.extractOne(p, rest.p.unique(), scorer=fuzz.token_sort_ratio, score_cutoff=88)
            if hit is None:
                continue
            pool = rest[rest.p == hit[0]]
        pairs += mutual_best(g14, pool)
    n_fuzzy = len(pairs) - n_exact

    # tier 4: provinces created after 2004 (Driouch, Ouezzane, Rehamna...) draw on the 2004 provinces their
    # already-linked communes came from
    lk = pd.DataFrame(pairs, columns=["code14", "app_code"])
    origin = (
        lk.code14.map(spine.set_index("code14").p)
        .to_frame("p14")
        .assign(p04=lk.app_code.map(idx.set_index("commune_code").p))
    )
    rest = units[~units.commune_code.isin(lk.app_code)]
    sp = spine[~spine.code14.isin(lk.code14)]
    for p, g14 in sp.groupby("p"):
        pool = rest[rest.p.isin(set(origin.p04[origin.p14 == p]))]
        if len(pool):
            pairs += mutual_best(g14, pool)
    n_split = len(pairs) - n_exact - n_fuzzy

    out = pd.DataFrame(pairs, columns=["code14", "app_code"])
    out["link"] = ["exact"] * n_exact + ["fuzzy"] * n_fuzzy + ["province_split"] * n_split
    by_parent = out.set_index("app_code").code14
    extra = idx[centre & ~idx.commune_code.isin(out.app_code) & idx.parent.isin(by_parent.index)]
    out = pd.concat(
        [out, pd.DataFrame({"code14": extra.parent.map(by_parent), "app_code": extra.commune_code, "link": "centre"})],
        ignore_index=True,
    )
    # merges, renames and absorptions after 2004, decided on population and GeoNames location
    # an app unit listed more than once was split after 2004: its counts are shared by 2014 population, its rates
    # are carried to every part
    review = pd.read_csv(LINK_REVIEW, dtype=str)
    pop14 = pd.read_csv(P_COMMUNES[2014], dtype={"code14": str}).set_index("code14").population14
    review["weight"] = review.code14.map(pop14) / review.groupby("app_code").code14.transform(lambda c: pop14[c].sum())
    split = review.app_code.duplicated(keep=False)
    out = pd.concat(
        [
            out[~out.app_code.isin(review.app_code)].assign(weight=1.0),
            review[["code14", "app_code", "weight"]].assign(link=split.map({True: "split", False: "review"})),
        ],
        ignore_index=True,
    )
    out["weight"] = out.weight.round(4)
    assert out.groupby("app_code").weight.sum().round(3).eq(1).all() and out.code14.isin(spine.code14).all()
    out.to_csv(out_path, index=False)
    print(
        f"app2004: exact {n_exact} + fuzzy {n_fuzzy} + province split {n_split} + centres {len(extra)}, "
        f"{(~split).sum()} reviewed, {split.sum()} split rows; {out.code14.nunique()}/{len(spine)} communes linked"
    )
    return out
