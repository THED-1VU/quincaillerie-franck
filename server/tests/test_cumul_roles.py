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
    fixer_drapeau_changement_mdp,
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
    # Compte « en poste » (cycle 65 : un compte créé par l'API a l'obligation
    # de changement de mot de passe, qui bloquerait toute route métier avant
    # même la question du cumul — ces tests portent sur les rôles, pas sur
    # cette obligation ; le 403 du second test doit être un refus de RÔLE).
    fixer_drapeau_changement_mdp(identifiant, False)
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


# ---------------------------------------------------------------------------
# D7 (validée le 2026-10-23) : l'union à l'écran — /moi porte la liste
# complète, /articles sert les DEUX familles de colonnes à un cumul
# stock + comptabilité, via le rôle PG de chaque famille.
# ---------------------------------------------------------------------------

def test_moi_renvoie_la_liste_complete_des_roles(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _creer_agent_cumule(client, session, "cumul.stock", "agent_stock")

    connexion = client.post(
        "/auth/connexion",
        json={"identifiant": "cumul.stock", "mot_de_passe": "CumulAgent123"},
    )
    jeton = connexion.json()["jeton"]

    reponse = client.get("/moi", headers=entete_autorisation(jeton))
    assert reponse.status_code == 200, reponse.text
    profil = reponse.json()
    assert profil["role"] == "agent_stock"
    assert sorted(profil["roles"]) == ["agent_comptabilite", "agent_stock"]


def test_moi_d_un_compte_simple_ne_porte_qu_un_role(client):
    reponse = client.get(
        "/moi",
        headers=entete_autorisation(
            se_connecter(client, "magasin.stock", "AgentStockTest123")["jeton"]
        ),
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["roles"] == ["agent_stock"]


def test_articles_cumul_porte_prix_et_quantites(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _creer_agent_cumule(client, session, "cumul.stock", "agent_stock")
    jeton = client.post(
        "/auth/connexion",
        json={"identifiant": "cumul.stock", "mot_de_passe": "CumulAgent123"},
    ).json()["jeton"]

    reponse = client.get("/articles", headers=entete_autorisation(jeton))
    assert reponse.status_code == 200, reponse.text
    articles = reponse.json()["articles"]
    assert articles, "le catalogue ne doit pas être vide"
    ciment = next(a for a in articles if a["id"] == 1)
    # Les deux familles de colonnes, sur la même ligne : le cumul vend ET
    # compte, sans jamais voir le prix d'achat (réservé au responsable).
    assert float(ciment["prix_vente"]) == 6500.0
    assert ciment["site_id"] == 1
    assert "quantite_stock" in ciment
    assert "prix_achat" not in ciment


def test_articles_roles_simples_inchanges(client):
    # agent stock seul : quantités, aucun prix (comportement historique).
    stock = client.get(
        "/articles",
        headers=entete_autorisation(
            se_connecter(client, "magasin.stock", "AgentStockTest123")["jeton"]
        ),
    ).json()["articles"]
    assert stock, "le catalogue ne doit pas être vide"
    assert "quantite_stock" in stock[0]
    assert "prix_vente" not in stock[0]

    # agent comptabilité seul : prix, aucune quantité (comportement historique).
    compta = client.get(
        "/articles",
        headers=entete_autorisation(
            se_connecter(client, "magasin.compta", "AgentComptaTest123")["jeton"]
        ),
    ).json()["articles"]
    assert compta, "le catalogue ne doit pas être vide"
    assert "prix_vente" in compta[0]
    assert "quantite_stock" not in compta[0]
