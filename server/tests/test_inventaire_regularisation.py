"""Chantier C7 (cycle 36) : régularisation d'un écart de comptage et plafond
de vraisemblance.

Décisions du propriétaire (2026-09-22) :
- 4 types de résolution, motif obligatoire sauf `erreur_de_comptage` ;
- traçabilité PURE : la régularisation ne modifie JAMAIS le stock ;
- plafond de vraisemblance : paramètre `a_definir` — aucun comptage refusé
  tant que le propriétaire ne fixe pas de valeur.
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import (
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    _executer_sql_admin,
    entete_autorisation,
    se_connecter,
)


def _inserer_comptage(article_id, site_id, moment, quantite_comptee):
    _executer_sql_admin(
        "INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment, quantite_comptee)"
        f" VALUES ({article_id}, {site_id}, 2, '{moment}', {quantite_comptee})"
    )
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT max(id) FROM comptages_stock"
        ).fetchone()[0]


def test_responsable_regularise_un_ecart_de_comptage(client):
    comptage_id = _inserer_comptage(1, 1, "matin", 25)  # attendu 30 -> écart -5
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "erreur_de_comptage"},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["comptage_id"] == comptage_id
    assert corps["type_resolution"] == "erreur_de_comptage"
    assert corps["motif"] is None

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT comptage_id, type_resolution, decide_par_id"
                " FROM regularisations_ecarts_comptage WHERE comptage_id = %s",
                (comptage_id,),
            )
            ligne = cur.fetchone()
            assert ligne["type_resolution"] == "erreur_de_comptage"
            assert ligne["decide_par_id"] == 1  # le responsable du jeu d'essai


def test_re_regularisation_du_meme_comptage_refusee(client):
    comptage_id = _inserer_comptage(1, 1, "matin", 25)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    premier = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "erreur_de_comptage"},
    )
    assert premier.status_code == 201, premier.text

    second = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "retrouve", "motif": "retrouvé en réserve"},
    )
    assert second.status_code == 422, second.text
    assert "déjà" in second.json()["detail"].lower()


def test_vol_presume_sans_motif_refuse(client):
    comptage_id = _inserer_comptage(1, 1, "matin", 25)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "vol_presume"},
    )
    assert reponse.status_code == 422, reponse.text
    assert "motif" in reponse.json()["detail"].lower()


def test_type_de_resolution_invalide_refuse_par_le_schema(client):
    comptage_id = _inserer_comptage(1, 1, "matin", 25)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "nimporte_quoi"},
    )
    assert reponse.status_code == 422


def test_comptage_sans_ecart_refuse(client):
    comptage_id = _inserer_comptage(1, 1, "matin", 30)  # attendu 30 -> écart 0
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "erreur_de_comptage"},
    )
    assert reponse.status_code == 422, reponse.text
    assert "aucun écart" in reponse.json()["detail"].lower()


def test_ecart_regularise_disparait_de_la_liste_du_jour(client):
    comptage_id = _inserer_comptage(1, 1, "matin", 25)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    avant = client.get("/inventaire/ecarts", headers=entete_autorisation(session["jeton"]))
    assert any(e["id"] == comptage_id for e in avant.json()["ecarts"])

    reponse = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "erreur_de_comptage"},
    )
    assert reponse.status_code == 201, reponse.text

    apres = client.get("/inventaire/ecarts", headers=entete_autorisation(session["jeton"]))
    assert not any(e["id"] == comptage_id for e in apres.json()["ecarts"]), (
        "un écart régularisé ne doit plus apparaître dans la liste à traiter"
    )


def test_agent_stock_ne_peut_pas_regulariser(client):
    comptage_id = _inserer_comptage(1, 1, "matin", 25)
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        f"/inventaire/ecarts/{comptage_id}/regulariser",
        headers=entete_autorisation(session["jeton"]),
        json={"type_resolution": "erreur_de_comptage"},
    )
    assert reponse.status_code == 403


def test_plafond_inactif_tant_que_non_fixe(client):
    """Décision 2026-09-22 : tant que `plafond_vraisemblance_comptage` est
    `a_definir`, AUCUN comptage n'est refusé pour vraisemblance."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/inventaire/comptages",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 2, "moment": "matin", "quantite_comptee": 999999},
    )
    assert reponse.status_code == 201, reponse.text


def test_plafond_refuse_quand_le_proprietaire_le_fixe(client):
    """La mécanique est prête : dès que le paramètre est fixé, elle refuse."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    _executer_sql_admin(
        "UPDATE parametres SET valeur = '1000', a_decider = FALSE"
        " WHERE cle = 'plafond_vraisemblance_comptage'"
    )
    try:
        reponse = client.post(
            "/inventaire/comptages",
            headers=entete_autorisation(session["jeton"]),
            json={"article_id": 2, "moment": "soir", "quantite_comptee": 1001},
        )
        assert reponse.status_code == 422, reponse.text
        assert "invraisemblable" in reponse.json()["detail"].lower()

        acceptable = client.post(
            "/inventaire/comptages",
            headers=entete_autorisation(session["jeton"]),
            json={"article_id": 4, "moment": "soir", "quantite_comptee": 1000},
        )
        assert acceptable.status_code == 201, acceptable.text
    finally:
        _executer_sql_admin(
            "UPDATE parametres SET valeur = 'a_definir', a_decider = TRUE"
            " WHERE cle = 'plafond_vraisemblance_comptage'"
        )
