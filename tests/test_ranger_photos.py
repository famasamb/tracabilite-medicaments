"""Rangement des photos reelles dans l'ordre de la planche (etape 55)."""
from pathlib import Path

import pytest

from jeu_de_donnees import ranger_photos as rp

SERIES = [f"S{i:02d}" for i in range(1, 13)]


def test_chaque_photo_prend_le_numero_de_serie_de_sa_place_sur_la_planche():
    photos = [Path(f"IMG_{i:03d}.jpg") for i in range(12)]
    plan = rp.associer(photos, SERIES)
    assert [(s, n) for _, s, n in plan] == [(s, 1) for s in SERIES]


def test_plusieurs_passages_sont_numerotes():
    photos = [Path(f"IMG_{i:03d}.jpg") for i in range(24)]
    plan = rp.associer(photos, SERIES)
    assert [n for _, _, n in plan] == [1] * 12 + [2] * 12
    assert plan[12][1] == "S01" and plan[23][1] == "S12"


@pytest.mark.parametrize("nombre", [0, 11, 13, 25])
def test_un_nombre_de_photos_incomplet_est_refuse(nombre):
    with pytest.raises(ValueError):
        rp.associer([Path(f"IMG_{i}.jpg") for i in range(nombre)], SERIES)


def test_le_rangement_copie_les_photos_sans_toucher_aux_originales(tmp_path, monkeypatch):
    source = tmp_path / "telephone"; source.mkdir()
    for i in range(12):
        (source / f"PXL_{i:03d}.jpg").write_bytes(b"x" * (i + 1))
    monkeypatch.setattr(rp, "DOSSIER", tmp_path)
    monkeypatch.setattr(rp, "PHOTOS", tmp_path / "photos_reelles")
    (tmp_path / "planche_codes.csv").write_text(
        "ordre,numeroSerie,produit,lot,groupe\n" + "".join(f"{i},{s},p,l,test\n" for i, s in enumerate(SERIES, start=1)),
        encoding="utf-8")
    rp.main([str(source), "normal"])
    assert (tmp_path / "photos_reelles" / "normal" / "S01__1.jpg").read_bytes() == b"x"
    assert (tmp_path / "photos_reelles" / "normal" / "S12__1.jpg").read_bytes() == b"x" * 12
    assert len(list(source.iterdir())) == 12      # originales intactes


def test_sans_planche_codes_csv_le_message_dit_quoi_faire(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "DOSSIER", tmp_path)
    with pytest.raises(SystemExit, match="generer_planche"):
        rp.ordre_de_la_planche()
