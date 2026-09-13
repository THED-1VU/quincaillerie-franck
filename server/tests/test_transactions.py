"""Chantier C6 (comptabilité et RH) — cycle 16 : recettes et dépenses hors
vente. La clôture de caisse (addendum, point g) n'est pas traitée ici,
volontairement — voir ADDENDUM_CAHIER_DES_CHARGES.md.
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


def test_responsable_enregistre_une_recette(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        json={"type": "recette", "montant": 5000, "description": "Vente de chutes", "site_id": 1},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["type"] == "recette"
    assert corps["site_id"] == 1


def test_responsable_enregistre_une_depense_rattachee_a_un_employe(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        json={"type": "depense", "montant": 60000, "description": "Salaire", "employe_id": 1, "site_id": 1},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["employe_id"] == 1


def test_agent_comptabilite_enregistre_sur_son_site(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        json={"type": "depense", "montant": 3000, "description": "Fournitures"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["site_id"] == 1  # toujours son propre site, jamais un paramètre


def test_agent_stock_ne_peut_pas_enregistrer_de_transaction(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        json={"type": "recette", "montant": 1000, "site_id": 1},
    )
    assert reponse.status_code == 403


def test_transaction_employe_invalide_refusee_proprement(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        json={"type": "depense", "montant": 1000, "employe_id": 999999, "site_id": 1},
    )
    assert reponse.status_code == 422, reponse.text
    assert "erreur interne" not in reponse.json()["detail"].lower()


def test_responsable_doit_preciser_un_site_pour_une_transaction(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        json={"type": "recette", "montant": 1000},
    )
    assert reponse.status_code == 422
    assert "site" in reponse.json()["detail"].lower()


def test_lister_transactions_filtre_par_periode(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    client.post(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        json={"type": "recette", "montant": 2500, "site_id": 1},
    )

    aujourdhui = client.get(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        params={"date_debut": "2000-01-01", "date_fin": "2999-12-31"},
    )
    assert aujourdhui.status_code == 200, aujourdhui.text
    assert any(t["montant"] == 2500 for t in aujourdhui.json()["transactions"])

    hors_periode = client.get(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        params={"date_debut": "2000-01-01", "date_fin": "2000-01-02"},
    )
    assert hors_periode.status_code == 200, hors_periode.text
    assert hors_periode.json()["transactions"] == []


def test_lister_transactions_date_invalide_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/transactions",
        headers=entete_autorisation(session["jeton"]),
        params={"date_debut": "pas-une-date", "date_fin": "2026-09-13"},
    )
    assert reponse.status_code == 422
