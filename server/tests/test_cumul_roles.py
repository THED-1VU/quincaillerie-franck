"""Chantier C3 (cycle 41) : cumul de rôles sur un même compte.

Décision du propriétaire (2026-09-22, addendum point h, question 4) : un
compte peut porter plusieurs rôles (petit effectif). La question 3 du point
h (détail des prix ou total seul) reste documentée comme EN ATTENTE.
"""

from __future__ import annotations

import base64
import json

from conftest import (
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


def _creer_agent_cumule(client, session, identifiant, role_principal):
    reponse = client.post(
        "/admin/comptes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "nom_complet": "Agent Cumulé",
            "identifiant": identifiant,
            "mot_de_passe": "CumulAgent123",
            "role": role_principal,
            "site_id": 1,
            "roles": ["agent_stock", "agent_comptabilite"],
        },
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert sorted(corps["roles"]) == ["agent_comptabilite", "agent_stock"]
    return corps


def _roles_du_jeton(jeton: str) -> list:
    corps_b64 = jeton.split(".")[0]
    charge = json.loads(base64.urlsafe_b64decode(corps_b64 + "=" * (-len(corps_b64) % 4)))
    return charge.get("roles", [])


def test_le_jeton_de_connexion_porte_la_liste_des_roles(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _creer_agent_cumule(client, session, "cumul.stock", "agent_stock")

    reponse = client.post(
        "/auth/connexion",
        json={"identifiant": "cumul.stock", "mot_de_passe": "CumulAgent123"},
    )
    assert reponse.status_code == 200, reponse.text
    assert sorted(_roles_du_jeton(reponse.json()["jeton"])) == [
        "agent_comptabilite",
        "agent_stock",
    ]


def test_un_compte_cumule_accede_aux_deux_perimetres(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _creer_agent_cumule(client, session, "cumul.stock", "agent_stock")

    connexion = client.post(
        "/auth/connexion",
        json={"identifiant": "cumul.stock", "mot_de_passe": "CumulAgent123"},
    )
    jeton = connexion.json()["jeton"]

    # Périmètre agent stock : liste à compter (rôle effectif agent_stock).
    reponse_stock = client.get(
        "/inventaire/articles-a-compter?moment=matin",
        headers=entete_autorisation(jeton),
    )
    assert reponse_stock.status_code == 200, reponse_stock.text

    # Périmètre agent comptabilité : paramètres de vente (rôle effectif
    # agent_comptabilite) — la même personne, le même jeton.
    reponse_compta = client.get(
        "/ventes/parametres",
        headers=entete_autorisation(jeton),
    )
    assert reponse_compta.status_code == 200, reponse_compta.text


def test_un_compte_cumule_reste_refuse_hors_de_ses_roles(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _creer_agent_cumule(client, session, "cumul.stock", "agent_stock")

    connexion = client.post(
        "/auth/connexion",
        json={"identifiant": "cumul.stock", "mot_de_passe": "CumulAgent123"},
    )
    jeton = connexion.json()["jeton"]

    reponse = client.get(
        "/admin/comptes",
        headers=entete_autorisation(jeton),
    )
    assert reponse.status_code == 403


def test_un_agent_stock_seul_n_accede_pas_au_perimetre_comptabilite(client):
    session = se_connecter(client, "magasin.stock", "AgentStockTest123")
    reponse = client.get(
        "/ventes/parametres",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 403


def test_creation_cumul_refuse_un_role_principal_hors_liste(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/admin/comptes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "nom_complet": "Agent Incohérent",
            "identifiant": "incoherent.agent",
            "mot_de_passe": "Incoherent123",
            "role": "agent_stock",
            "site_id": 1,
            "roles": ["agent_comptabilite"],
        },
    )
    assert reponse.status_code == 422, reponse.text
