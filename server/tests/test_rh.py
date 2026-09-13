"""Chantier C6 (comptabilité et RH) — cycle 16 : gestion des employés,
absences/congés et avances sur salaire — réservée au responsable (CDC
§3.5).
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


def test_responsable_cree_un_employe(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/rh/employes",
        headers=entete_autorisation(session["jeton"]),
        json={"nom_complet": "Nouvel Employé", "poste": "Vendeur", "salaire_mensuel": 50000, "site_id": 1},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["actif"] is True
    assert corps["type_contrat"] == "permanent"


def test_agent_comptabilite_ne_peut_pas_creer_employe(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/rh/employes",
        headers=entete_autorisation(session["jeton"]),
        json={"nom_complet": "Interdit", "salaire_mensuel": 10000},
    )
    assert reponse.status_code == 403


def test_lister_employes_reserve_au_responsable(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get("/rh/employes", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 403


def test_responsable_cree_une_absence_conge(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/rh/absences-conges",
        headers=entete_autorisation(session["jeton"]),
        json={"employe_id": 1, "type": "conge", "date_debut": "2026-10-01", "date_fin": "2026-10-05"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["employe_id"] == 1


def test_absence_conge_employe_invalide_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/rh/absences-conges",
        headers=entete_autorisation(session["jeton"]),
        json={"employe_id": 999999, "type": "absence", "date_debut": "2026-10-01", "date_fin": "2026-10-01"},
    )
    assert reponse.status_code == 422, reponse.text
    assert "erreur interne" not in reponse.json()["detail"].lower()


def test_absence_periode_incoherente_refusee(client):
    """chk_absences_periode_coherente (cycle 1) : la fin ne peut pas
    précéder le début."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/rh/absences-conges",
        headers=entete_autorisation(session["jeton"]),
        json={"employe_id": 1, "type": "absence", "date_debut": "2026-10-05", "date_fin": "2026-10-01"},
    )
    assert reponse.status_code == 422, reponse.text
    assert "erreur interne" not in reponse.json()["detail"].lower()


def test_responsable_cree_une_avance_salaire(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/rh/avances-salaire",
        headers=entete_autorisation(session["jeton"]),
        json={"employe_id": 1, "montant": 15000, "motif": "urgence familiale"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["remboursee"] is False


def test_rembourser_avance_salaire(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    creation = client.post(
        "/rh/avances-salaire",
        headers=entete_autorisation(session["jeton"]),
        json={"employe_id": 1, "montant": 10000},
    )
    avance_id = creation.json()["id"]

    reponse = client.post(
        f"/rh/avances-salaire/{avance_id}/rembourser",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 204, reponse.text

    liste = client.get("/rh/avances-salaire", headers=entete_autorisation(session["jeton"]))
    ligne = next(a for a in liste.json()["avances_salaire"] if a["id"] == avance_id)
    assert ligne["remboursee"] is True


def test_rembourser_avance_deja_remboursee_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    creation = client.post(
        "/rh/avances-salaire",
        headers=entete_autorisation(session["jeton"]),
        json={"employe_id": 1, "montant": 5000},
    )
    avance_id = creation.json()["id"]
    client.post(f"/rh/avances-salaire/{avance_id}/rembourser", headers=entete_autorisation(session["jeton"]))

    deuxieme = client.post(
        f"/rh/avances-salaire/{avance_id}/rembourser", headers=entete_autorisation(session["jeton"])
    )
    assert deuxieme.status_code == 404


def test_rembourser_avance_inexistante_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/rh/avances-salaire/999999/rembourser", headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 404
