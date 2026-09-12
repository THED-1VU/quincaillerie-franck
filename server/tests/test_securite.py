"""Sécurité applicative (chantier C11)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import MOT_DE_PASSE_RESPONSABLE, entete_autorisation, se_connecter

MOTIF_HACHAGE_BCRYPT = re.compile(r"\$2[aby]\$\d{2}\$")


def test_reponse_de_connexion_ne_contient_jamais_de_hachage(client):
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE}
    )
    assert reponse.status_code == 200
    assert MOTIF_HACHAGE_BCRYPT.search(reponse.text) is None


def test_reponses_articles_et_profil_ne_contiennent_jamais_de_hachage(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes = entete_autorisation(session["jeton"])
    for chemin in ("/articles", "/moi", "/ventes/synthese-jour"):
        reponse = client.get(chemin, headers=entetes)
        assert MOTIF_HACHAGE_BCRYPT.search(reponse.text) is None, (
            f"{chemin} a laissé fuiter un hachage : {reponse.text}"
        )


def test_config_refuse_le_compte_superutilisateur(tmp_path):
    from app.config import ErreurConfiguration, charger_config

    chemin = tmp_path / "config.ini"
    chemin.write_text(
        "[database]\n"
        "host = 127.0.0.1\nport = 5433\ndbname = quincaillerie_test\n"
        "user = postgres\npassword = peu_importe\n"
        "[api]\nsecret_key = " + "0" * 64 + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ErreurConfiguration, match="superutilisateur"):
        charger_config(chemin)


def test_config_refuse_la_cle_secrete_exemple(tmp_path):
    from app.config import ErreurConfiguration, charger_config

    chemin = tmp_path / "config.ini"
    chemin.write_text(
        "[database]\n"
        "host = 127.0.0.1\nport = 5433\ndbname = quincaillerie_test\n"
        "user = qf_app\npassword = peu_importe\n"
        "[api]\nsecret_key = A_GENERER_python_-c_import_secrets_print_secrets.token_hex_32\n",
        encoding="utf-8",
    )
    with pytest.raises(ErreurConfiguration, match="secret_key"):
        charger_config(chemin)


def test_mot_de_passe_en_clair_jamais_ecrit_dans_le_code_serveur():
    """Recherche grossière mais utile : aucun mot de passe de compte
    applicatif ni aucune clé ne doit apparaître en dur dans le code du
    serveur (le vrai config.ini, lui, n'est jamais dans le dépôt — voir
    .gitignore)."""
    racine_app = Path(__file__).resolve().parent.parent / "app"
    motifs_interdits = ("qf_app_dev_local", "postgres123", "motdepasse123")
    for fichier in racine_app.rglob("*.py"):
        contenu = fichier.read_text(encoding="utf-8").lower()
        for motif in motifs_interdits:
            assert motif.lower() not in contenu, f"{fichier} contient '{motif}'"


def test_hachage_genere_par_le_serveur_est_verifiable_par_pgcrypto():
    """Non-régression du piège documenté dans la migration 009 : le serveur
    DOIT générer des hachages au format $2a$, jamais $2b$ (défaut de la
    bibliothèque bcrypt), sous peine que verifier_connexion() rejette
    systématiquement un mot de passe pourtant correct."""
    from app.securite import hacher_mot_de_passe

    hachage = hacher_mot_de_passe("PeuImporte1234")
    assert hachage.startswith("$2a$"), (
        f"préfixe {hachage[:4]!r} : pgcrypto ne le validera pas, voir "
        "db/migrations/009_authentification.sql"
    )


def test_jeton_expire_est_refuse():
    from app.securite import GestionnaireSessions

    gestionnaire = GestionnaireSessions(secret_key="cle-de-test", duree_minutes=0)
    jeton = gestionnaire.emettre(
        utilisateur_id=1, role="responsable", site_id=None,
        nom_complet="Test", doit_changer_mot_de_passe=False,
    )
    import time

    time.sleep(1.1)  # la durée de session est de 0 minute : déjà expiré
    from app.securite import JetonInvalide

    with pytest.raises(JetonInvalide, match="expiré"):
        gestionnaire.verifier(jeton)


def test_jeton_signe_avec_une_autre_cle_est_refuse():
    from app.securite import GestionnaireSessions, JetonInvalide

    emetteur = GestionnaireSessions(secret_key="cle-a", duree_minutes=30)
    verificateur = GestionnaireSessions(secret_key="cle-b", duree_minutes=30)
    jeton = emetteur.emettre(
        utilisateur_id=1, role="responsable", site_id=None,
        nom_complet="Test", doit_changer_mot_de_passe=False,
    )
    with pytest.raises(JetonInvalide, match="[Ss]ignature"):
        verificateur.verifier(jeton)


def test_injection_sql_dans_lidentifiant_ne_casse_rien(client):
    charges_malveillantes = [
        "' OR '1'='1",
        "resp'--",
        "'; DROP TABLE utilisateurs; --",
        "\" OR \"\"=\"",
    ]
    for identifiant in charges_malveillantes:
        reponse = client.post(
            "/auth/connexion", json={"identifiant": identifiant, "mot_de_passe": "peu importe"}
        )
        assert reponse.status_code == 401
        assert reponse.json()["detail"] == "Identifiant ou mot de passe incorrect."

    # La table existe toujours et le compte responsable fonctionne encore.
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE}
    )
    assert reponse.status_code == 200
