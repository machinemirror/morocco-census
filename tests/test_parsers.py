from morocco_census.crosswalk import norm, norm_app
from morocco_census.extract import to_num
from morocco_census.parse_2004 import ROW, grab, num


def test_num_handles_french_formatting():
    assert num("1\xa0234,5") == 1234.5
    assert num("n.d.") is None


def test_grab_respects_section():
    rows = [
        ["SEXE", "", ""],
        ["Masculin", "10", "48,0"],
        ["Féminin", "11", "52,0"],
        ["ETAT MATRIMONIAL", "", ""],
        ["Divorcé(e)", "3", "1,5"],
    ]
    assert grab(rows, "Féminin", 2, after="SEXE") == 52.0
    assert grab(rows, "Divorcé", 2, startswith=True, after="ETAT MATRIMONIAL") == 1.5
    assert grab(rows, "Divorcé", 2, after="ETAT MATRIMONIAL") is None


def test_annex_row_regex():
    m = ROW.match("Aousserd Zoug 13,28 17,68 1,46 38,93 0,622 0,966")
    assert m and m.group("label") == "Aousserd Zoug"
    m = ROW.match("Casablanca Anfa (AR) 2,10 5,30 0,20 35,10 0,780 -")
    assert m and m.group("n").split()[-1] == "-"


def test_norm():
    assert norm("Bni Bouayach (Mun.)") == norm("Commune de Bni Bouayach") == "bnibouayach"
    assert norm("Aîn-Sebaâ (Arrond.)") == "ainsebaa"
    assert norm_app("CR-Sidi Youssef Ben Ahmed") == "sidi youssef ben ahmed"


def test_to_num_tokens():
    import pandas as pd

    assert to_num(pd.Series(["pm", "-", "12.5", " .. "])).isna().tolist() == [True, True, False, True]
