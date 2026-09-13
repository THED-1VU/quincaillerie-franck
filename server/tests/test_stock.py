"""Chantier C4 (articles et stock) — cycle 9 : réception, transfert,
casse, retours. Addendum, points a et f.
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_AGENT_STOCK_COMPTOIR,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def _seuil_et_stock(article_id: int) -> dict:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock, seuil_alerte FROM articles WHERE id = %s", (article_id,))
            return cur.fetchone()


# ---------------------------------------------------------------------------
# Réception (recalcule le seuil — cycle 2, exposée par une route ce cycle)
# ---------------------------------------------------------------------------

def test_reception_recalcule_le_seuil(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/entrees",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "quantite": 50, "motif": "Livraison Cimenterie"},
    )
    assert reponse.status_code == 201, reponse.text
    avant_apres = _seuil_et_stock(1)
    assert avant_apres["quantite_stock"] == 80  # 30 + 50
    assert avant_apres["seuil_alerte"] == 10    # 20 % de 50


def test_reception_refusee_pour_un_article_de_lautre_site(client):
    """Trouvé lors du contrôle de boucle sur ce cycle : enregistrer_entree_
    stock() n'avait jamais été exposée par une route avant, et ne vérifiait
    aucun site."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/entrees",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 3, "quantite": 10, "motif": "essai cross-site"},
    )
    assert reponse.status_code == 403


# ---------------------------------------------------------------------------
# Transfert inter-sites (addendum, point a)
# ---------------------------------------------------------------------------

def test_transfert_normal_ne_recalcule_pas_le_seuil(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    avant = _seuil_et_stock(3)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id_origine": 1, "article_id_destination": 3, "quantite": 5, "motif": "réassort comptoir"},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["quantite_stock_origine"] == 25   # 30 - 5
    assert corps["quantite_stock_destination"] == 105  # 100 + 5
    apres = _seuil_et_stock(3)
    assert apres["seuil_alerte"] == avant["seuil_alerte"], "le seuil ne doit JAMAIS bouger sur un transfert"


def test_transfert_motif_blanc_refuse_par_la_base(client):
    """Pydantic bloque déjà une chaîne vide (min_length=1) ; un motif
    blanc (espaces) passe la validation applicative mais doit être
    refusé par la base — défense en profondeur, vérifiée ici."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id_origine": 1, "article_id_destination": 3, "quantite": 1, "motif": "   "},
    )
    assert reponse.status_code == 422
    assert "motif" in reponse.json()["detail"].lower()


def test_transfert_stock_insuffisant_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id_origine": 4, "article_id_destination": 3, "quantite": 100, "motif": "trop"},
    )
    assert reponse.status_code == 422
    assert "insuffisant" in reponse.json()["detail"].lower()


def test_transfert_vers_le_meme_site_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id_origine": 1, "article_id_destination": 2, "quantite": 1, "motif": "même site"},
    )
    assert reponse.status_code == 422
    assert "site" in reponse.json()["detail"].lower()


def test_agent_stock_ne_transfere_que_depuis_son_site(client):
    session_comptoir = se_connecter(client, "comptoir.stock", MOT_DE_PASSE_AGENT_STOCK_COMPTOIR)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session_comptoir["jeton"]),
        json={"article_id_origine": 1, "article_id_destination": 3, "quantite": 1, "motif": "depuis comptoir, interdit"},
    )
    assert reponse.status_code == 403

    session_magasin = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse2 = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session_magasin["jeton"]),
        json={"article_id_origine": 1, "article_id_destination": 3, "quantite": 1, "motif": "depuis magasin, autorisé"},
    )
    assert reponse2.status_code == 201, reponse2.text


# ---------------------------------------------------------------------------
# Casse (addendum, point f) — réservée au responsable
# ---------------------------------------------------------------------------

def test_casse_reservee_au_responsable(client):
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/casse",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "quantite": 1, "motif": "sac éventré"},
    )
    assert reponse.status_code == 403

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    avant = _seuil_et_stock(1)
    reponse2 = client.post(
        "/stock/casse",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"article_id": 1, "quantite": 3, "motif": "sac éventré"},
    )
    assert reponse2.status_code == 201, reponse2.text
    assert reponse2.json()["quantite_stock"] == avant["quantite_stock"] - 3
    apres = _seuil_et_stock(1)
    assert apres["seuil_alerte"] == avant["seuil_alerte"]


# ---------------------------------------------------------------------------
# Retour client (addendum, point f)
# ---------------------------------------------------------------------------

def test_retour_client_rattache_a_la_vente(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "lignes": [{"article_id": 1, "quantite": 2, "prix_unitaire": 6500}]},
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    vente_id = reponse_vente.json()["vente_id"]

    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    avant = _seuil_et_stock(1)
    reponse = client.post(
        "/stock/retours-client",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1, "motif": "produit non conforme"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["quantite_stock"] == avant["quantite_stock"] + 1
    apres = _seuil_et_stock(1)
    assert apres["seuil_alerte"] == avant["seuil_alerte"]


def test_retour_client_vente_inexistante_refuse(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/retours-client",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "vente_id": 999999, "quantite": 1},
    )
    assert reponse.status_code == 422
    assert "introuvable" in reponse.json()["detail"].lower()


def test_agent_stock_ne_traite_un_retour_client_que_pour_son_site(client):
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"mode_paiement": "especes", "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}]},
    )
    vente_id = reponse_vente.json()["vente_id"]

    session_comptoir = se_connecter(client, "comptoir.stock", MOT_DE_PASSE_AGENT_STOCK_COMPTOIR)
    reponse = client.post(
        "/stock/retours-client",
        headers=entete_autorisation(session_comptoir["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1},
    )
    assert reponse.status_code == 403


# ---------------------------------------------------------------------------
# Retour fournisseur (addendum, point f)
# ---------------------------------------------------------------------------

def test_retour_fournisseur_sur_une_vraie_reception(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse_reception = client.post(
        "/stock/entrees",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "quantite": 20, "motif": "Livraison test"},
    )
    assert reponse_reception.status_code == 201, reponse_reception.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT id FROM mouvements_stock WHERE article_id = 1 AND categorie = 'reception_fournisseur' ORDER BY id DESC LIMIT 1"
            )
            mouvement_id = cur.fetchone()["id"]

    avant = _seuil_et_stock(1)
    reponse = client.post(
        "/stock/retours-fournisseur",
        headers=entete_autorisation(session["jeton"]),
        json={"mouvement_origine_id": mouvement_id, "quantite": 5, "motif": "sacs abîmés à réception"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["article_id"] == 1
    assert reponse.json()["quantite_stock"] == avant["quantite_stock"] - 5


def test_retour_fournisseur_sur_un_mouvement_qui_nest_pas_une_reception(client):
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"mode_paiement": "especes", "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}]},
    )
    assert reponse_vente.status_code == 201, reponse_vente.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT id FROM mouvements_stock WHERE article_id = 1 AND categorie = 'vente' ORDER BY id DESC LIMIT 1"
            )
            mouvement_id = cur.fetchone()["id"]

    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/retours-fournisseur",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"mouvement_origine_id": mouvement_id, "quantite": 1},
    )
    assert reponse.status_code == 422
    assert "réception" in reponse.json()["detail"].lower()
