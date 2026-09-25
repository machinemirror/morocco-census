import hashlib

import pytest

from morocco_census import cli, fetch
from morocco_census.crosswalk import norm, norm_app
from morocco_census.extract import to_num
from morocco_census.fetch import changed
from morocco_census.parse_2004 import HEADER_SPILL, ROW, grab, num


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


def test_annex_label_drops_header_spill():
    assert HEADER_SPILL.sub("", "Vulné- de la Boulemane Enjil") == "Boulemane Enjil"
    assert HEADER_SPILL.sub("", "Notation : Dans ce tableau ... monde rural. communaux de de la Laayoune Tah") == "Laayoune Tah"
    assert HEADER_SPILL.sub("", "Laayoune Dcheira El Jihadia") == "Laayoune Dcheira El Jihadia"


def test_fetch_flags_changed_files():
    manifest = {"a.xlsx": {"sha256": "0" * 64}}
    assert changed(manifest, "a.xlsx", "1" * 64, accept=False)
    assert not changed(manifest, "a.xlsx", "1" * 64, accept=True)
    assert not changed(manifest, "a.xlsx", "0" * 64, accept=False)
    assert not changed(manifest, "new.xlsx", "1" * 64, accept=False)


def test_norm():
    assert norm("Bni Bouayach (Mun.)") == norm("Commune de Bni Bouayach") == "bnibouayach"
    assert norm("Aîn-Sebaâ (Arrond.)") == "ainsebaa"
    assert norm_app("CR-Sidi Youssef Ben Ahmed") == "sidi youssef ben ahmed"


def test_to_num_tokens():
    import pandas as pd

    assert to_num(pd.Series(["pm", "-", "12.5", " .. "])).isna().tolist() == [True, True, False, True]


def test_verify_flags_tampered_and_missing_files(tmp_path):
    (tmp_path / "a.xlsx").write_bytes(b"original")
    manifest = {
        "a.xlsx": {"sha256": hashlib.sha256(b"original").hexdigest()},
        "gone.pdf": {"sha256": "0" * 64},
    }
    assert fetch.verify(manifest, raw=tmp_path) == ["gone.pdf: missing"]
    (tmp_path / "a.xlsx").write_bytes(b"re-issued")
    assert [b.split(":")[0] for b in fetch.verify(manifest, raw=tmp_path)] == ["a.xlsx", "gone.pdf"]


def test_build_refuses_changed_raw_files(monkeypatch):
    monkeypatch.setattr(fetch, "verify", lambda: ["a.xlsx: sha256 1, manifest 0"])
    with pytest.raises(SystemExit, match="differ from data/raw/manifest.json"):
        cli.build()
