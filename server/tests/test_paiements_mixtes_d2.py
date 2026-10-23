"""Décision D2 (cycle 75, 2026-10-23) — paiements mixtes espèces + Mobile
Money sur UNE MÊME vente, traçables par mode (migration 052).

Cas exigés par l'ordre du cycle 75 : composantes séparées par mode, somme
des composantes = encaissé (refus sinon, même par SQL direct — trigger
différé), la part espèces alimente la caisse espèces et la part Mobile
Money son mode (calculer_attendu_caisse), UNE recette de journal seulement
(aucun double comptage), crédit client cohérent (aucune composante, créance
pleine), annulation traçable (dépense = total, composantes conservées,
sortie de l'attendu).
"""

from __future__ import annotations

from datetime import date

import psycopg
from psycopg import errors as erreurs_pg

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def _vente(numero: str, **surcharge) -> dict:
    corps = {
        "site_id": 1,
        "numero_facturier": numero,
        "vendeur_id": 1,
        "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
    }
    corps.update(surcharge)
    return corps


def _lignes_db(vente_id: int) -> tuple[str, list[tuple[str, str]]]:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT mode_paiement FROM ventes WHERE id = %s", (vente_id,))
            mode = cur.fetchone()[0]
            cur.execute(
                "SELECT mode_paiement, montant::text FROM ventes_paiements "
                "WHERE vente_id = %s ORDER BY id",
                (vente_id,),
            )
            return mode, cur.fetchall()


def _recette_journal(vente_id: int) -> list[str]:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT montant::text FROM transactions "
                "WHERE vente_id = %s AND type = 'recette'",
                (vente_id,),
            )
            return [r[0] for r in cur.fetchall()]


def test_vente_mixte_composantes_separees_recette_unique(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A001",
            paiements=[{"mode_paiement": "especes", "montant": 3000},
                       {"mode_paiement": "orange_money", "montant": 3500}],
        ),
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["total_ttc"] == 6500
    assert corps["paiements"] == [
        {"mode_paiement": "especes", "montant": 3000.0},
        {"mode_paiement": "orange_money", "montant": 3500.0},
    ]

    mode, composantes = _lignes_db(corps["vente_id"])
    assert mode == "mixte"
    assert composantes == [("especes", "3000.00"), ("orange_money", "3500.00")]

    # Aucun double comptage : le journal garde UNE recette, du TOTAL —
    # l'attendu de caisse vient des composantes, jamais de transactions.
    assert _recette_journal(corps["vente_id"]) == ["6500.00"]


def test_paiements_un_seul_mode_reprend_le_comportement_historique(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A002",
            paiements=[{"mode_paiement": "mtn_momo", "montant": 6500}],
        ),
    )
    assert reponse.status_code == 201, reponse.text
    mode, composantes = _lignes_db(reponse.json()["vente_id"])
    assert mode == "mtn_momo"
    assert composantes == [("mtn_momo", "6500.00")]


def test_somme_composantes_inexacte_refusee(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A003",
            paiements=[{"mode_paiement": "especes", "montant": 3000},
                       {"mode_paiement": "orange_money", "montant": 3400}],
        ),
    )
    assert reponse.status_code == 422, reponse.text
    assert "6500" in reponse.json()["detail"]
    # Rien n'a été écrit : la vente rejetée ne laisse aucune trace.
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM ventes WHERE numero_facturier = 'MAG-D2A003'"
            )
            assert cur.fetchone()[0] == 0


def test_composante_nulle_refusee(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A004",
            paiements=[{"mode_paiement": "especes", "montant": 0},
                       {"mode_paiement": "orange_money", "montant": 6500}],
        ),
    )
    assert reponse.status_code == 422, reponse.text


def test_mode_duplique_refuse(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A005",
            paiements=[{"mode_paiement": "especes", "montant": 3000},
                       {"mode_paiement": "especes", "montant": 3500}],
        ),
    )
    assert reponse.status_code == 422, reponse.text


def test_mode_paiement_et_paiements_ensemble_refuses(client):
    """Deux façons d'exprimer l'encaissement — jamais les deux à la fois
    (même discipline que les remises globales)."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A006",
            mode_paiement="especes",
            paiements=[{"mode_paiement": "orange_money", "montant": 6500}],
        ),
    )
    assert reponse.status_code == 422, reponse.text


def test_vente_credit_refuse_toute_composante(client):
    """Une vente à crédit n'encaisse RIEN à la vente (045) : aucune
    composante admise, la créance naît pour le total — les règlements
    passent par reglements_creances (047), jamais par un paiement direct.
    Le validateur du schéma refuse mode_paiement + paiements ensemble, donc
    un crédit avec composantes est rejeté avant même la route."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A007",
            mode_paiement="credit_client",
            paiements=[{"mode_paiement": "especes", "montant": 1000}],
        ),
    )
    assert reponse.status_code == 422, reponse.text
    assert any(
        "paiements" in str(erreur).lower() for erreur in reponse.json()["detail"]
    )


def test_vente_mixte_alimente_l_attendu_caisse_par_mode(client):
    """La part espèces va à la caisse espèces, la part Mobile Money à son
    mode : calculer_attendu_caisse somme les COMPOSANTES (migration 052)."""
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entete = entete_autorisation(session_resp["jeton"])
    jour = date.today().isoformat()

    def attendu():
        reponse = client.get(
            "/caisse/attendu",
            headers=entete,
            params={"site_id": 1, "date_cloture": jour},
        )
        assert reponse.status_code == 200, reponse.text
        return reponse.json()

    avant = attendu()
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A008",
            paiements=[{"mode_paiement": "especes", "montant": 3000},
                       {"mode_paiement": "mtn_momo", "montant": 3500}],
        ),
    )
    assert reponse.status_code == 201, reponse.text
    apres = attendu()

    assert round(float(apres["attendu_especes"]) - float(avant["attendu_especes"]), 2) == 3000
    assert round(float(apres["attendu_mtn_momo"]) - float(avant["attendu_mtn_momo"]), 2) == 3500
    assert round(float(apres["attendu_orange_money"]) - float(avant["attendu_orange_money"]), 2) == 0
    assert round(float(apres["attendu_autre"]) - float(avant["attendu_autre"]), 2) == 0


def test_annulation_vente_mixte_tracee(client):
    """L'annulation (017) contrapasse le TOTAL par UNE dépense, garde les
    composantes en base (trace de ce qui avait été réellement réglé, par
    mode) et fait sortir la vente de l'attendu (statut annulee)."""
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entete = entete_autorisation(session_resp["jeton"])
    jour = date.today().isoformat()

    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-D2A009",
            paiements=[{"mode_paiement": "especes", "montant": 3000},
                       {"mode_paiement": "orange_money", "montant": 3500}],
        ),
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]

    def attendu():
        r = client.get(
            "/caisse/attendu", headers=entete, params={"site_id": 1, "date_cloture": jour}
        )
        assert r.status_code == 200, r.text
        return r.json()

    avant = attendu()
    annulation = client.post(
        f"/ventes/{vente_id}/annuler",
        headers=entete,
        json={"motif": "test D2 : annulation d'une vente mixte"},
    )
    assert annulation.status_code == 200, annulation.text
    assert annulation.json()["montant_ttc"] == 6500

    apres = attendu()
    assert round(float(apres["attendu_especes"]) - float(avant["attendu_especes"]), 2) == -3000
    assert (
        round(float(apres["attendu_orange_money"]) - float(avant["attendu_orange_money"]), 2)
        == -3500
    )

    mode, composantes = _lignes_db(vente_id)
    assert mode == "mixte"
    assert composantes == [("especes", "3000.00"), ("orange_money", "3500.00")]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT montant::text FROM transactions "
                "WHERE vente_id = %s AND type = 'depense'",
                (vente_id,),
            )
            assert cur.fetchone()[0] == "6500.00"


def test_invariant_somme_verifie_par_la_base_meme_par_sql_direct():
    """Contournement : un INSERT SQL direct qui triche sur la somme est
    rejeté À COMMIT par le trigger de contrainte différé (migration 052) —
    l'invariant appartient à la base, pas à l'application."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ventes (site_id, utilisateur_id, statut, mode_paiement,
                                    utilisateur_caisse_id, sous_total_ht, taux_tva,
                                    montant_tva, total_ttc, date_encaissement,
                                    numero_facturier, vendeur_id)
                VALUES (1, 1, 'payee', 'mixte', 1, 100, 0, 0, 100, NOW(), 'MAG-D2SQL01', 1)
                RETURNING id
                """
            )
            vente_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO ventes_paiements (vente_id, mode_paiement, montant) "
                "VALUES (%s, 'especes', 90)",
                (vente_id,),
            )
            commite = False
            try:
                conn.commit()
                commite = True
            except erreurs_pg.CheckViolation:
                conn.rollback()
            assert not commite, (
                "Le COMMIT aurait dû échouer : somme des composantes (90) "
                "ne correspond pas au total encaissé (100)."
            )
        # La transaction rejetée n'a rien laissé.
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM ventes WHERE id = %s", (vente_id,))
            assert cur.fetchone()[0] == 0
