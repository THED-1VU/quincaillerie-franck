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


def test_site_invalide_refuse_proprement(client):
    """Trouvé au contrôle de boucle après le cycle 9 : remontait en 500
    générique avant ce correctif (cycle 11)."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/articles",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Site invalide", "unite": "pièce", "site_id": 999},
    )
    assert reponse.status_code == 422, reponse.text
    assert "erreur interne" not in reponse.json()["detail"].lower()


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


def test_agent_stock_ne_modifie_pas_un_article_de_lautre_site(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.put(
        "/articles/3",  # Clou 5 cm, site 2 (Comptoir)
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Essai"},
    )
    assert reponse.status_code == 404, reponse.text


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


# ---------------------------------------------------------------------------
# Articles de l'autre site (GET /articles/autre-site, cycle 11)
# ---------------------------------------------------------------------------

def test_agent_stock_voit_les_articles_de_lautre_site_sans_prix(client):
    from conftest import MOT_DE_PASSE_AGENT_STOCK_COMPTOIR

    session = se_connecter(client, "comptoir.stock", MOT_DE_PASSE_AGENT_STOCK_COMPTOIR)
    reponse = client.get("/articles/autre-site", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [a["nom"] for a in reponse.json()]
    assert "Ciment CIM II 50 kg" in noms  # site 1 (Magasin)
    assert not any("prix" in a for a in reponse.json())


def test_agent_stock_ne_voit_pas_son_propre_site_dans_lautre_site(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get("/articles/autre-site", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [a["nom"] for a in reponse.json()]
    assert "Ciment CIM II 50 kg" not in noms  # son propre site (Magasin), exclu
    assert "Clou 5 cm" in noms  # Comptoir


def test_responsable_ne_peut_pas_appeler_articles_autre_site(client):
    """Réservée à un agent stock — un responsable n'en a pas besoin (GET
    /articles lui montre déjà les deux sites)."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/articles/autre-site", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 403
