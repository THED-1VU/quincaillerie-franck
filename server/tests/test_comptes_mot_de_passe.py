"""Chantier C2 (cycle 38) : durée de session définitive et réinitialisation
du mot de passe d'un agent par le responsable.

Décisions du propriétaire (2026-09-22) :
- durée de session : 8 heures (480 minutes) — valeur DÉCIDÉE en base ;
- réinitialisation : le responsable saisit le nouveau mot de passe
  (>= 8 caractères), jamais restitué, changement forcé à la première
  connexion.
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    _executer_sql_admin,
    entete_autorisation,
    se_connecter,
)


def _reinitialiser(client, session, compte_id, mot_de_passe):
    return client.patch(
        f"/admin/comptes/{compte_id}/mot-de-passe",
        headers=entete_autorisation(session["jeton"]),
        json={"mot_de_passe": mot_de_passe},
    )


def test_responsable_reinitialise_le_mot_de_passe_dun_agent(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _reinitialiser(client, session, 2, "NouveauMdp123")
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["compte_id"] == 2
    assert corps["doit_changer_mot_de_passe"] is True

    # L'ancien mot de passe est refusé, le nouveau accepté avec changement forcé.
    ancien = client.post(
        "/auth/connexion",
        json={"identifiant": "magasin.stock", "mot_de_passe": MOT_DE_PASSE_AGENT_STOCK},
    )
    assert ancien.status_code == 401

    nouveau = client.post(
        "/auth/connexion",
        json={"identifiant": "magasin.stock", "mot_de_passe": "NouveauMdp123"},
    )
    assert nouveau.status_code == 200, nouveau.text
    assert nouveau.json()["doit_changer_mot_de_passe"] is True


def test_mot_de_passe_trop_court_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _reinitialiser(client, session, 2, "court")
    assert reponse.status_code == 422, reponse.text


def test_reinitialisation_refusee_pour_un_compte_responsable(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _reinitialiser(client, session, 1, "NouveauMdp123")
    assert reponse.status_code == 422, reponse.text
    assert "agent" in reponse.json()["detail"].lower()


def test_agent_stock_ne_peut_pas_reinitialiser(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = _reinitialiser(client, session, 2, "NouveauMdp123")
    assert reponse.status_code == 403


def test_reinitialisation_tracee_dans_journal_comptes(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = _reinitialiser(client, session, 2, "NouveauMdp123")
    assert reponse.status_code == 200, reponse.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT utilisateur_cible_id, action, utilisateur_auteur_id"
                " FROM journal_comptes WHERE action = 'reinitialisation_mot_de_passe'"
                " ORDER BY id DESC LIMIT 1"
            )
            ligne = cur.fetchone()
            assert ligne["utilisateur_cible_id"] == 2
            assert ligne["utilisateur_auteur_id"] == 1


def test_duree_session_lue_depuis_la_base(client):
    """La durée décidée (480 min) est lue en base à la connexion — le
    config.ini n'est qu'un repli."""
    reponse = client.post(
        "/auth/connexion",
        json={"identifiant": "magasin.stock", "mot_de_passe": MOT_DE_PASSE_AGENT_STOCK},
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["expire_dans_secondes"] == 480 * 60

    # Et si le paramètre change en base, la réponse suit immédiatement.
    _executer_sql_admin(
        "UPDATE parametres SET valeur = '60', utilisateur_id = 1, a_decider = FALSE"
        " WHERE cle = 'duree_session_minutes'"
    )
    try:
        reponse = client.post(
            "/auth/connexion",
            json={"identifiant": "magasin.stock", "mot_de_passe": MOT_DE_PASSE_AGENT_STOCK},
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["expire_dans_secondes"] == 60 * 60
    finally:
        _executer_sql_admin(
            "UPDATE parametres SET valeur = '480', utilisateur_id = 1, a_decider = FALSE"
            " WHERE cle = 'duree_session_minutes'"
        )
