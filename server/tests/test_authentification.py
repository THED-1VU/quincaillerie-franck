"""Tests d'authentification (chantier C2) — vérification par exécution réelle
contre PostgreSQL (aucun mock de la base : conftest.py pointe vers la vraie
instance de développement, _pgdev/).
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


def test_connexion_reussie(client):
    reponse = client.post(
        "/auth/connexion",
        json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE},
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["role"] == "responsable"
    assert corps["site_id"] is None
    assert corps["utilisateur_id"] == 1
    assert corps["jeton"]
    assert corps["expire_dans_secondes"] == 480 * 60
    # Le hachage ne doit JAMAIS apparaître nulle part dans la réponse.
    assert "hash" not in reponse.text.lower()
    assert "$2a$" not in reponse.text


def test_connexion_mot_de_passe_incorrect(client):
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": "mauvais"}
    )
    assert reponse.status_code == 401
    assert reponse.json()["detail"] == "Identifiant ou mot de passe incorrect."


def test_connexion_identifiant_inconnu(client):
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "fantome", "mot_de_passe": "peu importe"}
    )
    assert reponse.status_code == 401
    # Même message que "mauvais mot de passe" : on ne révèle pas quels
    # identifiants existent.
    assert reponse.json()["detail"] == "Identifiant ou mot de passe incorrect."


def test_verrouillage_apres_echecs_repetes(client):
    # Le seuil (parametres.tentatives_max_connexion) vaut 5 dans le jeu d'essai.
    for _ in range(4):
        reponse = client.post(
            "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": "mauvais"}
        )
        assert reponse.status_code == 401
        assert reponse.json()["detail"] == "Identifiant ou mot de passe incorrect."

    # 5e échec : la réponse doit annoncer le verrouillage.
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": "mauvais"}
    )
    assert reponse.status_code == 401
    assert "verrouillé" in reponse.json()["detail"]

    # Même avec le BON mot de passe, le compte reste verrouillé.
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE}
    )
    assert reponse.status_code == 401
    assert "verrouillé" in reponse.json()["detail"]


def test_compte_desactive_ne_peut_pas_se_connecter(client, base_reinitialisee):
    import psycopg

    from conftest import PG_ADMIN_DSN

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute("UPDATE utilisateurs SET actif = FALSE WHERE identifiant = 'resp'")
        conn.commit()

    reponse = client.post(
        "/auth/connexion",
        json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE},
    )
    assert reponse.status_code == 401
    assert "désactivé" in reponse.json()["detail"]


def test_deverrouillage_par_le_responsable(client):
    # On verrouille le compte de l'agent stock.
    for _ in range(5):
        client.post(
            "/auth/connexion", json={"identifiant": "magasin.stock", "mot_de_passe": "mauvais"}
        )
    reponse = client.post(
        "/auth/connexion",
        json={"identifiant": "magasin.stock", "mot_de_passe": MOT_DE_PASSE_AGENT_STOCK},
    )
    assert reponse.status_code == 401
    assert "verrouillé" in reponse.json()["detail"]

    # Le responsable se connecte et déverrouille le compte (id=2).
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/admin/comptes/2/deverrouiller", headers=entete_autorisation(session_resp["jeton"])
    )
    assert reponse.status_code == 200
    assert reponse.json()["tentatives_echouees"] == 0

    # L'agent stock peut de nouveau se connecter avec son BON mot de passe.
    reponse = client.post(
        "/auth/connexion",
        json={"identifiant": "magasin.stock", "mot_de_passe": MOT_DE_PASSE_AGENT_STOCK},
    )
    assert reponse.status_code == 200


def test_deverrouillage_refuse_a_un_agent(client):
    """Seul le responsable déverrouille — un agent ne le peut pas, même sur
    lui-même. Vérifié au niveau de la route (403) : le rôle applicatif
    qf_agent_stock, lui, n'a de toute façon aucun droit UPDATE sur
    utilisateurs.tentatives_echouees (migration 008) — double barrière."""
    session_stock = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/admin/comptes/2/deverrouiller", headers=entete_autorisation(session_stock["jeton"])
    )
    assert reponse.status_code == 403


def test_limitation_de_debit_sur_la_connexion(app):
    """La limitation de débit est indépendante du verrouillage de compte
    (base de données) : elle coupe court AVANT même d'interroger la base,
    dès qu'un identifiant est tenté trop souvent trop vite."""
    from fastapi.testclient import TestClient

    from app.securite import LimiteurDebit

    app.state.limiteur_connexion = LimiteurDebit(max_essais=3, fenetre_secondes=60)
    client = TestClient(app)

    for _ in range(3):
        reponse = client.post(
            "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": "mauvais"}
        )
        assert reponse.status_code == 401

    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": "mauvais"}
    )
    assert reponse.status_code == 429


def test_changement_mot_de_passe_a_la_premiere_connexion(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    assert session["doit_changer_mot_de_passe"] is True

    reponse = client.post(
        "/auth/changer-mot-de-passe",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mot_de_passe_actuel": MOT_DE_PASSE_RESPONSABLE,
            "nouveau_mot_de_passe": "NouveauMotDePasse456",
        },
    )
    assert reponse.status_code == 204

    # L'ancien mot de passe ne fonctionne plus.
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE}
    )
    assert reponse.status_code == 401

    # Le nouveau fonctionne, et doit_changer_mot_de_passe est retombé à faux.
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": "NouveauMotDePasse456"}
    )
    assert reponse.status_code == 200
    assert reponse.json()["doit_changer_mot_de_passe"] is False


def test_changement_mot_de_passe_refuse_si_actuel_incorrect(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/auth/changer-mot-de-passe",
        headers=entete_autorisation(session["jeton"]),
        json={"mot_de_passe_actuel": "faux", "nouveau_mot_de_passe": "PeuImporte1234"},
    )
    assert reponse.status_code == 401

    # Et l'ancien mot de passe fonctionne toujours.
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE}
    )
    assert reponse.status_code == 200


def test_un_agent_ne_peut_changer_que_son_propre_mot_de_passe(client):
    """Le libre-service ne prend aucun identifiant de compte cible en
    paramètre : il n'y a tout simplement AUCUN moyen, via cette route, de
    viser le compte d'un tiers."""
    session_stock = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/auth/changer-mot-de-passe",
        headers=entete_autorisation(session_stock["jeton"]),
        json={
            "mot_de_passe_actuel": MOT_DE_PASSE_AGENT_STOCK,
            "nouveau_mot_de_passe": "NouveauMdpAgent123",
        },
    )
    assert reponse.status_code == 204

    # Le compte du RESPONSABLE, lui, n'a pas bougé.
    reponse = client.post(
        "/auth/connexion", json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE}
    )
    assert reponse.status_code == 200
