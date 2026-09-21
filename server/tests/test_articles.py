"""Chantier C4 (articles et stock) — cycle 9, révisé cycle 35 (13b).

Depuis la décision 2026-09-19, un article est une FICHE sans site ; le stock
vit dans ``stocks_sites``. La création d'une fiche ne prend plus de site, le
prix n'est accepté que pour un responsable, et le catalogue est commun aux
deux sites (seule la quantité est cloisonnée).
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
        json={"nom": "Marteau 500g", "unite": "pièce", "prix_achat": 1500, "prix_vente": 2500},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["nom"] == "Marteau 500g"

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT prix_achat, prix_vente FROM articles WHERE id = %s",
                (corps["article_id"],),
            )
            ligne = cur.fetchone()
            assert float(ligne["prix_achat"]) == 1500
            assert float(ligne["prix_vente"]) == 2500

            cur.execute(
                "SELECT count(*) AS n FROM stocks_sites WHERE article_id = %s",
                (corps["article_id"],),
            )
            assert cur.fetchone()["n"] == 0, "une fiche naît sans aucune ligne de stock"


def test_agent_stock_cree_un_article_sans_prix(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Scie à métaux", "unite": "pièce"},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT prix_vente FROM articles WHERE id = %s", (corps["article_id"],))
            assert float(cur.fetchone()["prix_vente"]) == 0


def test_agent_stock_cree_une_fiche_sans_site(client):
    """La fiche n'a plus de site : un ``site_id`` envoyé par un agent est
    simplement ignoré (le schéma n'en veut plus du tout)."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Essai sans site", "unite": "pièce", "site_id": 2},
    )
    assert reponse.status_code == 201, reponse.text
    assert "site_id" not in reponse.json()


def test_responsable_cree_une_fiche_sans_site(client):
    """Le responsable non plus n'a plus à préciser de site : la fiche est
    unique, le stock viendra par les fonctions de mouvement."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Sans site", "unite": "pièce"},
    )
    assert reponse.status_code == 201, reponse.text


def test_agent_comptabilite_ne_peut_pas_creer_darticle(client):
    from conftest import MOT_DE_PASSE_AGENT_COMPTA

    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Interdit", "unite": "pièce"},
    )
    assert reponse.status_code == 403


# ---------------------------------------------------------------------------
# Modification (PUT /articles/{id}, cycle 11)
# ---------------------------------------------------------------------------

def test_responsable_modifie_le_nom_et_le_prix(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.put(
        "/articles/1",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Ciment CIM II 50 kg (renommé)", "prix_vente": 7000},
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["nom"] == "Ciment CIM II 50 kg (renommé)"
    assert corps["prix_vente"] == 7000

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT champ, ancienne_valeur, nouvelle_valeur FROM historique_modifications_articles"
                " WHERE article_id = 1 ORDER BY id DESC LIMIT 1"
            )
            ligne = cur.fetchone()
            assert ligne["champ"] == "nom"
            assert ligne["nouvelle_valeur"] == "Ciment CIM II 50 kg (renommé)"

            cur.execute(
                "SELECT ancien_prix_vente, nouveau_prix_vente FROM historique_prix_articles"
                " WHERE article_id = 1 ORDER BY id DESC LIMIT 1"
            )
            prix = cur.fetchone()
            assert float(prix["nouveau_prix_vente"]) == 7000


def test_agent_stock_modifie_le_nom_mais_pas_le_prix(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.put(
        "/articles/1",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Ciment renommé par l'agent", "prix_vente": 99999},
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["nom"] == "Ciment renommé par l'agent"
    assert corps["prix_vente"] is None  # jamais relu pour un agent stock

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT prix_vente FROM articles WHERE id = 1")
            assert float(cur.fetchone()["prix_vente"]) == 6500, "prix inchangé, ignoré silencieusement"


def test_agent_stock_peut_modifier_une_fiche_du_catalogue_commun(client):
    """Le catalogue est commun aux deux sites : la fiche « Clou 5 cm » (dont
    le stock est au Comptoir) est modifiable par un agent du Magasin — la
    quantité, elle, reste cloisonnée dans stocks_sites."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.put(
        "/articles/3",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Clou 5 cm (commun)"},
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["nom"] == "Clou 5 cm (commun)"


def test_modification_article_inexistant_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.put(
        "/articles/999999",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Fantôme"},
    )
    assert reponse.status_code == 404, reponse.text


def test_modification_sans_aucun_champ_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.put(
        "/articles/1", headers=entete_autorisation(session["jeton"]), json={}
    )
    assert reponse.status_code == 422, reponse.text


def test_modification_fournisseur_invalide_refusee_proprement(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.put(
        "/articles/1",
        headers=entete_autorisation(session["jeton"]),
        json={"fournisseur_id": 999999},
    )
    assert reponse.status_code == 422, reponse.text
    assert "erreur interne" not in reponse.json()["detail"].lower()


def test_modification_prix_identique_ne_trace_rien(client):
    """Constat n°3 (contrôle de boucle après le cycle 11) : le formulaire de
    stock.html pré-remplit toujours les prix — soumettre le même prix
    (typiquement en corrigeant seulement le nom) ne doit PAS créer de ligne
    dans historique_prix_articles."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT count(*) AS n FROM historique_prix_articles WHERE article_id = 1")
            avant = cur.fetchone()["n"]

    reponse = client.put(
        "/articles/1",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Ciment renommé, prix inchangé", "prix_achat": 5000, "prix_vente": 6500},
    )
    assert reponse.status_code == 200, reponse.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT count(*) AS n FROM historique_prix_articles WHERE article_id = 1")
            apres = cur.fetchone()["n"]
    assert apres == avant, "aucune ligne d'historique de prix pour un prix soumis identique à l'actuel"

    # Un vrai changement, lui, doit toujours être tracé.
    reponse = client.put(
        "/articles/1",
        headers=entete_autorisation(session["jeton"]),
        json={"prix_vente": 6600},
    )
    assert reponse.status_code == 200, reponse.text
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT count(*) AS n FROM historique_prix_articles WHERE article_id = 1")
            apres_vrai_changement = cur.fetchone()["n"]
    assert apres_vrai_changement == avant + 1, "un vrai changement de prix reste tracé"


# ---------------------------------------------------------------------------
# Catalogue commun (GET /articles, décision 2026-09-19) — l'ancien
# GET /articles/autre-site n'existe plus.
# ---------------------------------------------------------------------------

def test_agent_stock_voit_tout_le_catalogue_sans_prix(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get("/articles", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [a["nom"] for a in reponse.json()["articles"]]
    assert "Ciment CIM II 50 kg" in noms  # fiche dont le stock est au Magasin
    assert "Clou 5 cm" in noms  # fiche dont le stock est au Comptoir — catalogue commun
    assert not any("prix_vente" in a for a in reponse.json()["articles"])


def test_agent_stock_ne_voit_que_la_quantite_de_son_site(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get("/articles", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    clou = [a for a in reponse.json()["articles"] if a["nom"] == "Clou 5 cm"][0]
    # Le stock du Clou (100) vit au Comptoir : l'agent du Magasin voit 0.
    assert clou["quantite_stock"] == 0
    assert clou["site_id"] == 1


def test_responsable_voit_une_ligne_par_article_et_site(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/articles", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    articles = reponse.json()["articles"]
    sites = {a["site_id"] for a in articles}
    assert sites == {1, 2}
    assert all("prix_vente" in a and "quantite_stock" in a for a in articles)
