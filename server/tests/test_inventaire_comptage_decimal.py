"""Comptage d'une quantité décimale sur un article en quantités entières
(chantier C7) : refus lisible 422, jamais « Erreur interne » (500).

Constat de l'audit indépendant du 2026-10-23 : le garde-fou de la base
(migration 034, `verifier_decimale_comptages_stock`) refusait bien la saisie,
mais la route ne traduisait pas cette erreur — l'agent stock qui tapait 2,5
pour un article vendu au sac voyait « Erreur interne. ».
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_STOCK,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)

ARTICLE_ENTIER = 2  # « Fer à béton 8 mm », unité barre, quantités entières


def _nb_comptages(article_id: int) -> int:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT count(*) FROM comptages_stock WHERE article_id = %s", (article_id,)
        ).fetchone()[0]


def test_comptage_decimal_sur_article_entier_est_un_422_lisible(client):
    jeton = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)["jeton"]
    avant = _nb_comptages(ARTICLE_ENTIER)

    reponse = client.post(
        "/inventaire/comptages",
        headers=entete_autorisation(jeton),
        json={"article_id": ARTICLE_ENTIER, "moment": "matin", "quantite_comptee": 2.5},
    )

    assert reponse.status_code == 422, reponse.text
    detail = reponse.json()["detail"]
    assert "entières" in detail
    assert "violates" not in detail  # règle C11 : aucun détail SQL côté client
    assert _nb_comptages(ARTICLE_ENTIER) == avant  # rien n'a été enregistré


def test_comptage_entier_sur_le_meme_article_reste_accepte(client):
    jeton = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)["jeton"]
    reponse = client.post(
        "/inventaire/comptages",
        headers=entete_autorisation(jeton),
        json={"article_id": ARTICLE_ENTIER, "moment": "matin", "quantite_comptee": 40},
    )
    assert reponse.status_code == 201, reponse.text
