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


def test_lister_employes_refuse_a_lagent_stock(client):
    """L'agent stock n'a jamais eu besoin de choisir un employé (aucune
    déclaration ne le lui demande) — reste refusé, contrairement à l'agent
    comptabilité depuis le chantier A."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get("/rh/employes", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 403


def test_responsable_liste_tous_les_employes_toutes_colonnes(client):
    """Comportement inchangé (cycle 16) : tous les sites, toutes les
    colonnes, actifs ou non."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/rh/employes", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    employes = reponse.json()["employes"]
    assert len(employes) >= 1
    ligne = employes[0]
    assert "salaire_mensuel" in ligne
    assert "telephone" in ligne
    assert "type_contrat" in ligne


def test_agent_comptabilite_liste_les_employes_actifs_de_son_site_colonnes_restreintes(client):
    """Chantier A (point f) : nécessaire pour choisir l'employé qui a
    offert un article — jamais le salaire ni le téléphone (§3.5 du CDC,
    « jamais gérer les fiches »), jamais un employé inactif ou d'un autre
    site (la déclaration l'aurait de toute façon refusé, migration 039)."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get("/rh/employes", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    employes = reponse.json()["employes"]
    assert len(employes) >= 1
    for ligne in employes:
        assert ligne["site_id"] == 1
        assert ligne["actif"] is True
        assert "salaire_mensuel" not in ligne
        assert "telephone" not in ligne
        assert "type_contrat" not in ligne
        assert "date_embauche" not in ligne


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
