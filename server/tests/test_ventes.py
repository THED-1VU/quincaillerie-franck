"""Chantier C5 (ventes) — cycle 6.

Prouve par exécution les trois décisions du propriétaire appliquées dans
``server/app/routes/ventes.py`` (addendum, points b/d/e) :
  * une vente à découvert n'est JAMAIS refusée, l'écart est consigné ;
  * la TVA (19,25 %, régime du réel) est calculée sur des prix TTC, arrondie
    sur le TOTAL de la vente ;
  * le crédit client reste explicitement désactivé.
Et une régression déjà couverte ailleurs (C3) mais qu'une route d'écriture
peut réintroduire : un agent ne peut ni écrire sur l'autre site, ni utiliser
une route hors de son rôle.
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def test_parametres_vente_expose_le_taux_tva_en_vigueur(client):
    """La maquette lit le taux de TVA ici plutôt que de le coder en dur
    (addendum, point d) — vérifié pour les deux rôles autorisés."""
    for identifiant, mdp in (
        ("magasin.compta", MOT_DE_PASSE_AGENT_COMPTA),
        ("resp", MOT_DE_PASSE_RESPONSABLE),
    ):
        session = se_connecter(client, identifiant, mdp)
        reponse = client.get("/ventes/parametres", headers=entete_autorisation(session["jeton"]))
        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {"taux_tva": 19.25}


def test_vente_normale_decremente_le_stock_et_calcule_la_tva(client):
    """Ciment CIM II 50 kg (site 1, stock 30, prix catalogue 6500) : 2 sacs
    négociés à 6000 FCFA (TTC) pièce. Total TTC = 12000 ; à 19,25 %, la TVA
    extraite du total vaut 1937 (12000*19.25/119.25, arrondi arithmétique),
    le HT vaut 10063 — calculé à la main, indépendamment de la route."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "lignes": [{"article_id": 1, "quantite": 2, "prix_unitaire": 6000}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()

    assert corps["total_ttc"] == 12000
    assert corps["montant_tva"] == 1937
    assert corps["sous_total_ht"] == 10063
    assert corps["taux_tva"] == 19.25
    assert corps["ecarts"] == []

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 1")
            assert cur.fetchone()["quantite_stock"] == 28  # 30 - 2

            cur.execute(
                "SELECT type, quantite FROM mouvements_stock WHERE article_id = 1 ORDER BY id DESC LIMIT 1"
            )
            mouvement = cur.fetchone()
            assert mouvement == {"type": "sortie", "quantite": 2}

            cur.execute(
                "SELECT type, montant, vente_id FROM transactions WHERE vente_id = %s",
                (corps["vente_id"],),
            )
            transactions = cur.fetchall()
            assert len(transactions) == 1
            assert transactions[0]["type"] == "recette"
            assert transactions[0]["montant"] == 12000

            cur.execute(
                "SELECT count(*) AS n FROM ecarts_stock_ventes WHERE vente_id = %s",
                (corps["vente_id"],),
            )
            assert cur.fetchone()["n"] == 0


def test_vente_a_decouvert_nest_jamais_refusee_et_consigne_lecart(client):
    """Article rare (site 1, stock 1) : on en vend 5. La vente DOIT quand
    même être enregistrée (addendum, point e — jamais de blocage), le stock
    tombe à 0, jamais négatif, et l'écart de 4 est consigné."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "orange_money",
            "lignes": [{"article_id": 4, "quantite": 5, "prix_unitaire": 2000}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["ecarts"] == [{"article_id": 4, "quantite_manquante": 4}]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 4")
            assert cur.fetchone()["quantite_stock"] == 0  # jamais négatif

            cur.execute(
                "SELECT quantite_manquante FROM ecarts_stock_ventes WHERE vente_id = %s",
                (corps["vente_id"],),
            )
            assert cur.fetchone()["quantite_manquante"] == 4


def test_credit_client_reste_desactive(client):
    """Point b : pas encore de décision complète sur la vente à crédit —
    la route la refuse avec un message clair, pas une erreur SQL brute."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "credit_client",
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422
    assert "crédit" in reponse.json()["detail"].lower()
    assert "addendum" in reponse.json()["detail"].lower()


def test_agent_stock_ne_peut_pas_enregistrer_de_vente(client):
    """Aucun droit sur `ventes` pour l'agent stock (migration 008) : la
    route doit refuser avant même de toucher la base."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 403


def test_agent_comptabilite_ne_peut_pas_vendre_pour_lautre_site(client):
    """Le comptable du Magasin (site 1) tente de vendre le « Clou 5 cm » du
    Comptoir (site 2), y compris en forçant site_id dans le corps : le site
    vient TOUJOURS de sa session, jamais de la requête. La clé étrangère
    composite (migration 002) refuse ensuite l'article hors site."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "site_id": 2,  # ignoré : le comptable a déjà un site en session
            "mode_paiement": "especes",
            "lignes": [{"article_id": 3, "quantite": 1, "prix_unitaire": 800}],
        },
    )
    assert reponse.status_code == 422
    assert "introuvable" in reponse.json()["detail"].lower()

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 3")
            assert cur.fetchone()["quantite_stock"] == 100  # inchangé


def test_responsable_doit_preciser_le_site(client):
    """Le responsable couvre les deux sites (site_id NULL en session) : sans
    site précisé dans la requête, la vente est refusée AVANT toute écriture,
    avec un message explicite plutôt qu'une erreur de contrainte SQL."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422
    assert "site" in reponse.json()["detail"].lower()


def test_responsable_peut_vendre_pour_un_site_precise(client):
    """Le responsable, en précisant le site, peut enregistrer une vente pour
    ce site — la RLS de `ventes`/`ventes_lignes` l'y autorise explicitement
    (`current_user = 'qf_responsable'`, migration 008)."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "site_id": 2,
            "mode_paiement": "mtn_momo",
            "lignes": [{"article_id": 3, "quantite": 1, "prix_unitaire": 800}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["site_id"] == 2
