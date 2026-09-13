"""Chantier C8 (tableaux de bord et rapports) — cycle 10.

Alertes de stock faible (dernière carte encore simulée de
``tableau-bord.html``) et historique des comptages filtrable par période.
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


def test_alertes_stock_liste_larticle_sous_seuil(client):
    """« Article rare » (jeu d'essai) est à 1 unité pour un seuil de 1 —
    déjà en alerte sans aucune préparation supplémentaire."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/tableau-bord/alertes-stock", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [a["nom"] for a in reponse.json()["alertes"]]
    assert "Article rare" in noms


def test_alertes_stock_narticle_au_dessus_du_seuil_absent(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/tableau-bord/alertes-stock", headers=entete_autorisation(session["jeton"]))
    noms = [a["nom"] for a in reponse.json()["alertes"]]
    assert "Ciment CIM II 50 kg" not in noms  # 30 en stock, seuil 6


def test_alertes_stock_reservee_au_responsable(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get("/tableau-bord/alertes-stock", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 403, reponse.text


def test_historique_comptages_filtre_par_periode(client):
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/inventaire/comptages",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "moment": "matin", "quantite_comptee": 25},
    )
    assert reponse.status_code == 201, reponse.text

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    aujourdhui = client.get(
        "/inventaire/historique-comptages",
        headers=entete_autorisation(session_resp["jeton"]),
        params={"date_debut": "2000-01-01", "date_fin": "2999-12-31"},
    )
    assert aujourdhui.status_code == 200, aujourdhui.text
    articles_comptes = [c["article_nom"] for c in aujourdhui.json()["comptages"]]
    assert "Ciment CIM II 50 kg" in articles_comptes

    hors_periode = client.get(
        "/inventaire/historique-comptages",
        headers=entete_autorisation(session_resp["jeton"]),
        params={"date_debut": "2000-01-01", "date_fin": "2000-01-02"},
    )
    assert hors_periode.status_code == 200, hors_periode.text
    assert hors_periode.json()["comptages"] == []


def test_historique_comptages_date_invalide_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/inventaire/historique-comptages",
        headers=entete_autorisation(session["jeton"]),
        params={"date_debut": "pas-une-date", "date_fin": "2026-09-13"},
    )
    assert reponse.status_code == 422, reponse.text


def test_historique_comptages_reserve_au_responsable(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/inventaire/historique-comptages",
        headers=entete_autorisation(session["jeton"]),
        params={"date_debut": "2000-01-01", "date_fin": "2999-12-31"},
    )
    assert reponse.status_code == 403, reponse.text
