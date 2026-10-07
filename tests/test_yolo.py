"""Tests de la preparation du jeu d'images au format YOLO."""
import cv2
import numpy as np

from jeu_de_donnees.yolo import ligne_yolo, preparer, repartir

VARIANTES = ["propre", "flou1", "flou2", "flou3", "occ1", "occ2", "occ3"]


def fabriquer(tmp_path, n_codes=20):
    dossier = tmp_path / "images"
    dossier.mkdir()
    lignes = []
    for i in range(n_codes):
        numero = f"SERIE{i:03d}"
        for v in VARIANTES:
            cv2.imwrite(str(dossier / f"{numero}_{v}.png"), np.zeros((60, 80, 3), np.uint8))
            lignes.append({"fichier": f"{numero}_{v}.png", "numeroSerie": numero, "x": "20", "y": "10",
                           "largeur": "40", "hauteur": "30", "largeurImage": "80", "hauteurImage": "60"})
    return lignes, dossier


def test_l_etiquette_yolo_est_normalisee_et_centree():
    ligne = {"x": "127", "y": "171", "largeur": "303", "hauteur": "303", "largeurImage": "800", "hauteurImage": "600"}
    classe, xc, yc, w, h = ligne_yolo(ligne).split()
    assert classe == "0"
    assert float(xc) == round((127 + 151.5) / 800, 6) and float(yc) == round((171 + 151.5) / 600, 6)
    assert float(w) == round(303 / 800, 6) and float(h) == round(303 / 600, 6)
    assert all(0 < float(v) < 1 for v in (xc, yc, w, h))


def test_la_repartition_respecte_les_proportions_et_est_reproductible():
    numeros = [f"S{i:03d}" for i in range(100)]
    groupes = repartir(numeros, 34)
    assert sorted(set(groupes.values())) == ["test", "train", "val"]
    assert list(groupes.values()).count("train") == 70
    assert list(groupes.values()).count("val") == 15 and list(groupes.values()).count("test") == 15
    assert repartir(numeros, 34) == groupes
    assert repartir(numeros, 35) != groupes


def test_les_variantes_d_un_meme_code_restent_dans_le_meme_groupe(tmp_path):
    lignes, dossier = fabriquer(tmp_path)
    sortie = tmp_path / "yolo"
    groupes = preparer(lignes, dossier, sortie, 34)
    for numero, groupe in groupes.items():
        for v in VARIANTES:
            assert (sortie / "images" / groupe / f"{numero}_{v}.png").exists()
            assert (sortie / "labels" / groupe / f"{numero}_{v}.txt").exists()
            for autre in ("train", "val", "test"):
                if autre != groupe:
                    assert not (sortie / "images" / autre / f"{numero}_{v}.png").exists()


def test_chaque_image_a_une_etiquette_et_le_fichier_de_configuration_existe(tmp_path):
    lignes, dossier = fabriquer(tmp_path, 10)
    sortie = tmp_path / "yolo"
    preparer(lignes, dossier, sortie, 34)
    for groupe in ("train", "val", "test"):
        images = sorted(p.stem for p in (sortie / "images" / groupe).glob("*.png"))
        etiquettes = sorted(p.stem for p in (sortie / "labels" / groupe).glob("*.txt"))
        assert images == etiquettes
    assert "datamatrix" in (sortie / "data.yaml").read_text(encoding="utf-8")