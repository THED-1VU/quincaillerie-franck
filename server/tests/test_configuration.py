"""Logo du client (cycle 28) — prouve par exécution :

  * réservé au responsable au niveau de la REQUÊTE (403 pour un agent, pas
    seulement un bouton caché à l'écran) ;
  * accepté seulement s'il s'agit RÉELLEMENT d'un PNG ou d'un JPEG, vérifié
    sur le contenu du fichier, jamais sur son nom ni le Content-Type déclaré ;
  * un fichier trop volumineux est refusé ;
  * le fichier stocké est réellement récupérable ensuite (GET), et absent
    (404) tant qu'aucun logo n'a été téléversé ;
  * la suppression retombe proprement sur « aucun logo » (jamais un fichier
    orphelin, jamais un 500).
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


@pytest.fixture(autouse=True)
def _dossier_logo_propre(app):
    """Le reset de base (base_reinitialisee, scope function) ne touche pas
    le SYSTÈME DE FICHIERS : sans ce nettoyage, un fichier laissé par un test
    précédent fausserait le suivant (ex. test_aucun_logo_au_depart_renvoie_404
    échouerait si un test antérieur a laissé un logo sur le disque)."""
    from app.routes.configuration import DOSSIER_LOGO
    for f in DOSSIER_LOGO.glob("logo.*"):
        f.unlink()
    yield
    for f in DOSSIER_LOGO.glob("logo.*"):
        f.unlink()


def _png_valide(largeur=10, hauteur=10) -> bytes:
    tampon = io.BytesIO()
    Image.new("RGBA", (largeur, hauteur), (0, 64, 143, 255)).save(tampon, format="PNG")
    return tampon.getvalue()


def _jpeg_valide(largeur=10, hauteur=10) -> bytes:
    tampon = io.BytesIO()
    Image.new("RGB", (largeur, hauteur), (212, 147, 13)).save(tampon, format="JPEG")
    return tampon.getvalue()


def test_aucun_logo_au_depart_renvoie_404(client):
    reponse = client.get("/configuration/logo")
    assert reponse.status_code == 404, reponse.text


def test_agent_comptabilite_ne_peut_pas_televerser(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("logo.png", _png_valide(), "image/png")},
    )
    assert reponse.status_code == 403, reponse.text


def test_agent_stock_ne_peut_pas_televerser(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("logo.png", _png_valide(), "image/png")},
    )
    assert reponse.status_code == 403, reponse.text


def test_responsable_televerse_un_png_reel(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("mon-logo.png", _png_valide(200, 200), "image/png")},
    )
    assert reponse.status_code == 204, reponse.text

    recupere = client.get("/configuration/logo")
    assert recupere.status_code == 200
    assert recupere.headers["content-type"] == "image/png"
    # Réellement une image PNG décodable, pas seulement des octets copiés.
    image = Image.open(io.BytesIO(recupere.content))
    assert image.format == "PNG"
    assert image.size == (200, 200)


def test_responsable_televerse_un_jpeg_reel(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("mon-logo.jpg", _jpeg_valide(150, 150), "image/jpeg")},
    )
    assert reponse.status_code == 204, reponse.text

    recupere = client.get("/configuration/logo")
    assert recupere.status_code == 200
    assert recupere.headers["content-type"] == "image/jpeg"
    image = Image.open(io.BytesIO(recupere.content))
    assert image.format == "JPEG"


def test_second_televersement_remplace_le_premier_meme_format_different(client):
    """Un PNG déjà présent, remplacé par un JPEG : un seul logo à la fois,
    l'ancien fichier ne doit jamais rester orphelin sur le disque."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("premier.png", _png_valide(), "image/png")},
    )
    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("second.jpg", _jpeg_valide(), "image/jpeg")},
    )
    assert reponse.status_code == 204, reponse.text

    recupere = client.get("/configuration/logo")
    assert recupere.headers["content-type"] == "image/jpeg"

    from app.routes.configuration import DOSSIER_LOGO
    fichiers = sorted(p.name for p in DOSSIER_LOGO.glob("logo.*"))
    assert fichiers == ["logo.jpg"], f"un seul fichier logo.* attendu, trouvé {fichiers}"


def test_fichier_texte_renomme_en_png_refuse(client):
    """La signature réelle est absente : l'extension du nom ne suffit pas."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("faux-logo.png", b"ceci n'est pas une image", "image/png")},
    )
    assert reponse.status_code == 422, reponse.text
    assert "reconnu" in reponse.json()["detail"].lower()


def test_png_tronque_corrompu_refuse(client):
    """La signature est correcte, mais le contenu est décodable comme rien —
    ni la signature seule ni le Content-Type ne suffisent, il faut un
    décodage réel."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    png_valide = _png_valide()
    tronque = png_valide[: len(png_valide) // 3]  # coupe en plein milieu des données
    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("logo.png", tronque, "image/png")},
    )
    assert reponse.status_code == 422, reponse.text


def test_fichier_trop_volumineux_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    # Une image réelle, mais dont les octets bruts dépassent la limite —
    # grande résolution, PNG non compressible (bruit aléatoire).
    import random
    tampon = io.BytesIO()
    pixels = bytes(random.getrandbits(8) for _ in range(1200 * 1200 * 3))
    image = Image.frombytes("RGB", (1200, 1200), pixels)
    image.save(tampon, format="PNG", compress_level=0)
    contenu = tampon.getvalue()
    assert len(contenu) > 2 * 1024 * 1024, "le contenu de test doit dépasser 2 Mo pour ce cas"

    reponse = client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("gros-logo.png", contenu, "image/png")},
    )
    assert reponse.status_code == 422, reponse.text
    assert "volumineux" in reponse.json()["detail"].lower()


def test_responsable_supprime_le_logo(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    client.post(
        "/configuration/logo",
        headers=entete_autorisation(session["jeton"]),
        files={"fichier": ("logo.png", _png_valide(), "image/png")},
    )
    assert client.get("/configuration/logo").status_code == 200

    reponse = client.delete(
        "/configuration/logo", headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 204, reponse.text
    assert client.get("/configuration/logo").status_code == 404


def test_agent_ne_peut_pas_supprimer(client):
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    client.post(
        "/configuration/logo",
        headers=entete_autorisation(session_resp["jeton"]),
        files={"fichier": ("logo.png", _png_valide(), "image/png")},
    )
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.delete(
        "/configuration/logo", headers=entete_autorisation(session_agent["jeton"])
    )
    assert reponse.status_code == 403, reponse.text
    # Le logo du responsable doit rester intact après ce refus.
    assert client.get("/configuration/logo").status_code == 200
