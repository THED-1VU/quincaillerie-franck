"""Chantier C4 (articles et stock) — cycle 9 : création d'articles.

Un article naît TOUJOURS à quantite_stock = 0 (le chargement du stock
initial dépend du point j de l'addendum, non tranché) ; le prix n'est
accepté que pour un responsable.
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def test_responsable_cree_un_article_avec_prix(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Marteau 500g", "unite": "pièce", "site_id": 1, "prix_achat": 1500, "prix_vente": 2500},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["nom"] == "Marteau 500g"
    assert corps["site_id"] == 1

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT quantite_stock, seuil_alerte, prix_achat, prix_vente FROM articles WHERE id = %s",
                (corps["article_id"],),
            )
            ligne = cur.fetchone()
            assert ligne["quantite_stock"] == 0, "un article naît toujours sans stock (point j non tranché)"
            assert float(ligne["prix_achat"]) == 1500
            assert float(ligne["prix_vente"]) == 2500


def test_agent_stock_cree_un_article_sans_prix(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Scie à métaux", "unite": "pièce"},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["site_id"] == 1  # toujours son propre site, jamais un paramètre

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT prix_vente, quantite_stock FROM articles WHERE id = %s", (corps["article_id"],))
            ligne = cur.fetchone()
            assert float(ligne["prix_vente"]) == 0
            assert ligne["quantite_stock"] == 0


def test_agent_stock_ne_peut_pas_choisir_un_autre_site(client):
    """Le site vient TOUJOURS de la session pour un agent — un site_id
    fourni dans le corps est ignoré, jamais utilisé."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Essai site forcé", "unite": "pièce", "site_id": 2},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["site_id"] == 1


def test_responsable_doit_preciser_un_site(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Sans site", "unite": "pièce"},
    )
    assert reponse.status_code == 422
    assert "site" in reponse.json()["detail"].lower()


def test_agent_comptabilite_ne_peut_pas_creer_darticle(client):
    from conftest import MOT_DE_PASSE_AGENT_COMPTA

    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Interdit", "unite": "pièce"},
    )
    assert reponse.status_code == 403
