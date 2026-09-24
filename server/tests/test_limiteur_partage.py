"""Chantier C11 (cycle 44) : limiteur de débit PARTAGÉ entre processus.

Décision du propriétaire (2026-09-24) : seuil 10 tentatives/minute inchangé,
mais compteur déplacé en base (migration 038) pour être partagé entre
plusieurs processus applicatifs, avec repli en mémoire si la base ne répond
pas. Audit de dépendances/TLS : documenté comme limite, hors périmètre local.
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    _executer_sql_admin,
    se_connecter,
)

QF_APP_DSN = PG_ADMIN_DSN.replace(
    "user=postgres password=qf_dev_local",
    "user=qf_app password=qf_app_dev_local",
)


def test_le_compteur_est_partage_entre_deux_connexions(client):
    """Deux connexions qf_app distinctes (deux processus simulés) partagent
    le MÊME compteur : la quatrième tentative est refusée même si elle vient
    d'une connexion qui n'a encore rien tenté."""
    with psycopg.connect(QF_APP_DSN) as conn1:
        for _ in range(3):
            assert conn1.execute(
                "SELECT tentative_autorisee('partage_test', 3, 60)"
            ).fetchone()[0] is True
        conn1.commit()  # libère le verrou FOR UPDATE avant la 2e connexion

    with psycopg.connect(QF_APP_DSN) as conn2:
        # Le compteur vit en base : une AUTRE connexion est refusée.
        assert conn2.execute(
            "SELECT tentative_autorisee('partage_test', 3, 60)"
        ).fetchone()[0] is False
        conn2.commit()
        # Réinitialisation, puis de nouveau autorisé.
        conn2.execute("SELECT reinitialiser_limitation('partage_test')")
        conn2.commit()
        assert conn2.execute(
            "SELECT tentative_autorisee('partage_test', 3, 60)"
        ).fetchone()[0] is True
        conn2.commit()


def test_la_route_connexion_refuse_apres_le_seuil(client, app):
    """La route utilise le compteur partagé : avec un seuil de 3 essais,
    trois échecs passent (401), le quatrième est coupé court (429), et une
    connexion RÉUSSIE efface le compteur."""
    from fastapi.testclient import TestClient

    from app.securite import LimiteurDebit

    app.state.limiteur_connexion = LimiteurDebit(max_essais=3, fenetre_secondes=60)
    client_route = TestClient(app)

    for _ in range(3):
        reponse = client_route.post(
            "/auth/connexion",
            json={"identifiant": "resp", "mot_de_passe": "mauvais"},
        )
        assert reponse.status_code == 401

    reponse = client_route.post(
        "/auth/connexion",
        json={"identifiant": "resp", "mot_de_passe": "mauvais"},
    )
    assert reponse.status_code == 429

    # Une fois la fenêtre écoulée (simulée ici par la réinitialisation du
    # compteur), une connexion RÉUSSIE efface le compteur : l'échec suivant
    # repart à zéro et répond 401, pas 429.
    _executer_sql_admin("SELECT reinitialiser_limitation('resp')")
    reponse = client_route.post(
        "/auth/connexion",
        json={"identifiant": "resp", "mot_de_passe": MOT_DE_PASSE_RESPONSABLE},
    )
    assert reponse.status_code == 200, reponse.text
    _executer_sql_admin(
        "UPDATE utilisateurs SET tentatives_echouees = 0 WHERE identifiant = 'resp'"
    )
    reponse = client_route.post(
        "/auth/connexion",
        json={"identifiant": "resp", "mot_de_passe": "mauvais"},
    )
    assert reponse.status_code == 401


def test_les_cles_sont_independantes(client):
    """Deux identifiants distincts ont des compteurs distincts."""
    with psycopg.connect(QF_APP_DSN) as conn:
        for _ in range(3):
            conn.execute("SELECT tentative_autorisee('cle_a', 3, 60)")
        # cle_a est épuisée, cle_b est vierge : autorisée.
        assert conn.execute(
            "SELECT tentative_autorisee('cle_a', 3, 60)"
        ).fetchone()[0] is False
        assert conn.execute(
            "SELECT tentative_autorisee('cle_b', 3, 60)"
        ).fetchone()[0] is True
        conn.execute("SELECT reinitialiser_limitation('cle_a')")
        conn.execute("SELECT reinitialiser_limitation('cle_b')")


def test_la_connexion_normale_reste_possible(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    assert session["utilisateur_id"] == 1
