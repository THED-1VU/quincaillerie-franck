"""Crédit client (addendum, point b, décidé le 2026-09-25) — migration 045.

Couvre : CRUD client (réservé au responsable, lecture ouverte à l'agent
comptabilité), une vente à crédit (créance, jamais une recette encaissée,
plafond respecté), le règlement (FIFO, refus d'un dépassement d'encours), et
la désactivation du paramètre credit_client_actif.
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


def _creer_client_admin(nom="Client Test", plafond=100000, telephone=None):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO clients (nom, telephone, plafond_credit) VALUES (%s, %s, %s) RETURNING id",
                (nom, telephone, plafond),
            )
            return cur.fetchone()[0]


def _encours(client_id: int) -> float:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return float(conn.execute("SELECT encours_client(%s)", (client_id,)).fetchone()[0])


# ---------------------------------------------------------------------------
# CRUD client
# ---------------------------------------------------------------------------

def test_responsable_cree_un_client(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/clients",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Nouveau Client", "telephone": "699111222"},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["nom"] == "Nouveau Client"
    assert corps["plafond_credit"] == 100000  # défaut
    assert corps["encours"] == 0


def test_agent_comptabilite_ne_peut_pas_creer_de_client(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/clients",
        headers=entete_autorisation(session["jeton"]),
        json={"nom": "Interdit"},
    )
    assert reponse.status_code == 403


def test_agent_comptabilite_peut_lister_les_clients(client):
    _creer_client_admin("Client Listé")
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get("/clients", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [c["nom"] for c in reponse.json()]
    assert "Client Listé" in noms


def test_agent_stock_na_aucun_acces_aux_clients(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get("/clients", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 403


def test_desactivation_client_naffecte_pas_lencours(client):
    client_id = _creer_client_admin("Client À Désactiver")
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.patch(
        f"/clients/{client_id}/actif",
        headers=entete_autorisation(session["jeton"]),
        json={"actif": False},
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["actif"] is False


# ---------------------------------------------------------------------------
# Vente à crédit
# ---------------------------------------------------------------------------

def test_vente_a_credit_cree_une_creance_pas_une_recette(client):
    client_id = _creer_client_admin("Client Crédit A", plafond=1000000)
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-9001",
            "vendeur_id": 1,
            "client_id": client_id,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]
    total_ttc = reponse.json()["total_ttc"]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT count(*) AS n FROM transactions WHERE vente_id = %s", (vente_id,))
            assert cur.fetchone()["n"] == 0, "aucune recette pour une vente à crédit"
            cur.execute(
                "SELECT montant FROM creances WHERE vente_id = %s", (vente_id,)
            )
            creance = cur.fetchone()
            assert creance is not None
            assert float(creance["montant"]) == total_ttc

    assert _encours(client_id) == total_ttc


def test_vente_a_credit_sans_client_refusee(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-9002",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert reponse.status_code == 422
    assert "client" in reponse.json()["detail"].lower()


def test_vente_a_credit_client_inactif_refusee(client):
    client_id = _creer_client_admin("Client Inactif")
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute("UPDATE clients SET actif = FALSE WHERE id = %s", (client_id,))
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-9003",
            "vendeur_id": 1,
            "client_id": client_id,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert reponse.status_code == 422
    assert "actif" in reponse.json()["detail"].lower()


def test_vente_a_credit_depassant_le_plafond_refusee(client):
    client_id = _creer_client_admin("Client Plafond Bas", plafond=100)
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-9004",
            "vendeur_id": 1,
            "client_id": client_id,
            # article 1 (Ciment), prix catalogue 6500 FCFA >> plafond 100.
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert reponse.status_code == 422
    assert "plafond" in reponse.json()["detail"].lower()
    assert _encours(client_id) == 0  # aucune créance créée


def test_vente_a_credit_desactivee_pour_la_boutique_refusee(client):
    client_id = _creer_client_admin("Client Feature Off")
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute("UPDATE parametres SET valeur = 'non' WHERE cle = 'credit_client_actif'")
    try:
        session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
        reponse = client.post(
            "/ventes",
            headers=entete_autorisation(session["jeton"]),
            json={
                "mode_paiement": "credit_client",
                "numero_facturier": "MAG-9005",
                "vendeur_id": 1,
                "client_id": client_id,
                "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
            },
        )
        assert reponse.status_code == 422
        assert "activée" in reponse.json()["detail"].lower()
    finally:
        with psycopg.connect(PG_ADMIN_DSN) as conn:
            conn.execute("UPDATE parametres SET valeur = 'oui' WHERE cle = 'credit_client_actif'")


def test_vente_a_credit_nimpacte_pas_lattendu_de_caisse(client):
    """Vérifie ce que migration 019 promettait déjà (calculer_attendu_caisse
    exclut credit_client des 4 totaux) tient bout en bout avec la vraie
    route de vente, pas seulement en SQL direct."""
    client_id = _creer_client_admin("Client Caisse", plafond=1000000)
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-9006",
            "vendeur_id": 1,
            "client_id": client_id,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert reponse.status_code == 201, reponse.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT * FROM calculer_attendu_caisse(1, CURRENT_DATE)"
            )
            attendu = cur.fetchone()
    assert attendu["especes"] == 0
    assert attendu["orange_money"] == 0
    assert attendu["mtn_momo"] == 0
    assert attendu["autre"] == 0


# ---------------------------------------------------------------------------
# Règlement (FIFO, plafond de l'encours)
# ---------------------------------------------------------------------------

def test_reglement_fifo_eteint_la_creance_la_plus_ancienne(client):
    client_id = _creer_client_admin("Client FIFO", plafond=1000000)
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute(
            "INSERT INTO creances (client_id, site_id, montant, utilisateur_id, date_creance) "
            "VALUES (%s, 1, 10000, 1, NOW() - INTERVAL '40 days'), "
            "       (%s, 1, 20000, 1, NOW() - INTERVAL '5 days')",
            (client_id, client_id),
        )
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/clients/{client_id}/reglements",
        headers=entete_autorisation(session["jeton"]),
        json={"montant": 10000, "motif": "paiement partiel"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["encours"] == 20000

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT tranche, montant FROM vieillissement_creances()")
            tranches = {t["tranche"]: float(t["montant"]) for t in cur.fetchall()}
    assert "31-60" not in tranches  # entièrement éteinte par le FIFO
    assert tranches.get("0-30") == 20000


def test_reglement_depassant_lencours_refuse(client):
    client_id = _creer_client_admin("Client Encours Bas")
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute(
            "INSERT INTO creances (client_id, site_id, montant, utilisateur_id) VALUES (%s, 1, 5000, 1)",
            (client_id,),
        )
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/clients/{client_id}/reglements",
        headers=entete_autorisation(session["jeton"]),
        json={"montant": 999999},
    )
    assert reponse.status_code == 422
    assert "encours" in reponse.json()["detail"].lower()


def test_agent_stock_ne_peut_pas_enregistrer_de_reglement(client):
    client_id = _creer_client_admin("Client Reglement Interdit")
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        f"/clients/{client_id}/reglements",
        headers=entete_autorisation(session["jeton"]),
        json={"montant": 100},
    )
    assert reponse.status_code == 403


# ---------------------------------------------------------------------------
# Annulation d'une vente à crédit (trouvé par exécution en écrivant ce
# cycle : annuler_vente(), migration 017, contre-passait INCONDITIONNELLEMENT
# une recette par une dépense — une vente à crédit n'en a jamais créé,
# corrigé migration 045 : la créance est annulée à la place)
# ---------------------------------------------------------------------------

def test_annulation_vente_credit_non_reglee_annule_la_creance(client):
    client_id = _creer_client_admin("Client Annulation A", plafond=1000000)
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    vente = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-9101",
            "vendeur_id": 1,
            "client_id": client_id,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert vente.status_code == 201, vente.text
    vente_id = vente.json()["vente_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    annulation = client.post(
        f"/ventes/{vente_id}/annuler",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"motif": "erreur de saisie"},
    )
    assert annulation.status_code == 200, annulation.text

    assert _encours(client_id) == 0
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT annulee FROM creances WHERE vente_id = %s", (vente_id,))
            assert cur.fetchone()["annulee"] is True
            cur.execute("SELECT count(*) AS n FROM transactions WHERE vente_id = %s", (vente_id,))
            assert cur.fetchone()["n"] == 0, "aucune dépense fantôme pour une vente à crédit annulée"


def test_annulation_vente_credit_deja_reglee_refusee(client):
    client_id = _creer_client_admin("Client Annulation B", plafond=1000000)
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    vente = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-9102",
            "vendeur_id": 1,
            "client_id": client_id,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert vente.status_code == 201, vente.text
    vente_id = vente.json()["vente_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reglement = client.post(
        f"/clients/{client_id}/reglements",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"montant": 1000},
    )
    assert reglement.status_code == 201, reglement.text

    annulation = client.post(
        f"/ventes/{vente_id}/annuler",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"motif": "trop tard"},
    )
    assert annulation.status_code == 422
    assert "règlement" in annulation.json()["detail"].lower()
