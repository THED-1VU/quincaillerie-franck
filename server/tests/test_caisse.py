"""Chantier C6 — clôture de caisse quotidienne, PAR SITE (addendum, point g,
décidé le 2026-09-13). Couvre les critères de sortie du cycle :

  * le total ATTENDU par mode de paiement est calculé PAR LE SERVEUR à partir
    des ventes `payee` du jour, jamais saisi ni recalculé côté client ;
  * l'ÉCART (compté − attendu) est calculé par la fonction PostgreSQL
    ``cloturer_caisse()``, jamais par l'application ;
  * une clôture est FIGÉE après création : aucune modification directe,
    prouvé en la tentant directement en SQL et en observant le refus de
    la base (pas seulement un refus de l'API) ;
  * un commentaire devient obligatoire si l'écart dépasse
    ``seuil_ecart_caisse_tolere`` (table ``parametres``) — amorcé à la
    sentinelle ``a_definir`` (addendum, question 5 non tranchée) :
    ``cloturer_caisse()`` applique alors une tolérance NULLE (jamais un
    chiffre inventé). Un test dédié vérifie aussi que si le propriétaire
    fixe un jour une vraie valeur, elle s'applique sans changement de code.
  * cloisonnement par RÔLE (responsable seul) prouvé à la fois par l'API
    (403) et en SQL DIRECT, en contournant complètement l'API — même
    patron que ``test_cloisonnement_site.py``.
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def _creer_vente_payee(client, prix_unitaire=6500, quantite=1, mode_paiement="especes"):
    """Vente réelle au Magasin (site 1), encaissée immédiatement (POST
    /ventes prend déjà le mode de paiement — saisie a posteriori, cahier des
    charges). Renvoie (vente_id, date_encaissement AAAA-MM-JJ, total_ttc) :
    la date vient d'une lecture directe de la ligne créée, jamais recalculée
    côté test, pour ne dépendre d'aucune hypothèse de fuseau horaire entre la
    machine de test et la base (Africa/Douala, migration 013)."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": mode_paiement,
            "lignes": [{"article_id": 1, "quantite": quantite, "prix_unitaire": prix_unitaire}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]
    total_ttc = reponse.json()["total_ttc"]
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT date_encaissement::date FROM ventes WHERE id = %s", (vente_id,))
            jour = cur.fetchone()[0]
    return vente_id, jour.isoformat(), total_ttc


# ---------------------------------------------------------------------------
# Calcul serveur : attendu et écart, jamais côté client
# ---------------------------------------------------------------------------

def test_attendu_previsualise_correspond_aux_ventes_payees_du_jour(client):
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/caisse/attendu",
        headers=entete_autorisation(session["jeton"]),
        params={"site_id": 1, "date_cloture": jour},
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["attendu_especes"] == total
    assert corps["attendu_orange_money"] == 0
    assert corps["attendu_mtn_momo"] == 0
    assert corps["attendu_autre"] == 0


def test_cloture_exacte_ecart_nul_sans_commentaire(client):
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["attendu_especes"] == total
    assert corps["ecart_especes"] == 0.0
    assert corps["commentaire"] is None


def test_ecart_calcule_par_la_fonction_jamais_par_lapplication(client):
    """Le client n'envoie JAMAIS d'écart ni d'attendu — seul le compté. La
    réponse doit pourtant contenir l'écart exact (compté - attendu),
    forcément calculé côté serveur puisqu'absent de la requête."""
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={
            "site_id": 1, "date_cloture": jour, "espece_comptee": total - 500,
            "commentaire": "500 FCFA manquants, à vérifier",
        },
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    # Le corps envoyé ci-dessus ne contient ni "ecart" ni "attendu" (voir
    # DemandeClotureCaisse, server/app/schemas.py) : la valeur qui revient
    # ne peut donc venir que du calcul serveur.
    assert corps["ecart_especes"] == -500.0
    assert corps["attendu_especes"] == total


# ---------------------------------------------------------------------------
# Seuil de commentaire obligatoire (addendum, question 5)
# ---------------------------------------------------------------------------

def test_seuil_a_definir_impose_un_commentaire_pour_tout_ecart_non_nul(client):
    """seuil_ecart_caisse_tolere vaut 'a_definir' dans le jeu d'essai (comme
    dans la migration 019) : cloturer_caisse() applique alors une tolérance
    NULLE, jamais un chiffre inventé. Documenté ici plutôt que deviné."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT valeur FROM parametres WHERE cle = 'seuil_ecart_caisse_tolere'")
            assert cur.fetchone()[0] == "a_definir"

    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total - 1},
    )
    assert reponse.status_code == 422, reponse.text
    assert "commentaire" in reponse.json()["detail"].lower()


def test_seuil_reellement_fixe_par_le_proprietaire_est_applique(client):
    """Si le propriétaire fixe un jour une vraie valeur, elle s'applique
    SANS changement de code : on la simule ici en écrivant directement le
    paramètre (comme le ferait une future route d'administration)."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE parametres SET valeur = '1000' WHERE cle = 'seuil_ecart_caisse_tolere'"
            )
        conn.commit()

    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)

    # Écart de 500 FCFA, sous le seuil de 1000 : PAS de commentaire exigé.
    dans_le_seuil = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total - 500},
    )
    assert dans_le_seuil.status_code == 201, dans_le_seuil.text
    assert dans_le_seuil.json()["ecart_especes"] == -500.0


# ---------------------------------------------------------------------------
# Immutabilité : figée après création (prouvé en SQL DIRECT, en contournant
# entièrement l'API — même exigence que ventes/journaux, migrations 004/005)
# ---------------------------------------------------------------------------

def test_cloture_figee_update_direct_refuse(client):
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total},
    )
    cloture_id = reponse.json()["cloture_id"]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RestrictViolation) as exc_info:
                cur.execute(
                    "UPDATE clotures_caisse SET compte_especes = 999999 WHERE id = %s",
                    (cloture_id,),
                )
        assert "figée" in str(exc_info.value)
        conn.rollback()


def test_cloture_ne_se_supprime_pas_meme_en_sql_direct(client):
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total},
    )
    cloture_id = reponse.json()["cloture_id"]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.RestrictViolation) as exc_info:
                cur.execute("DELETE FROM clotures_caisse WHERE id = %s", (cloture_id,))
        assert "journal" in str(exc_info.value)
        conn.rollback()


def test_insertion_directe_hors_fonction_refusee_meme_pour_le_role_responsable(client):
    """Seule ``cloturer_caisse()`` écrit dans la table : même le rôle
    responsable, qui peut LIRE la table (GRANT SELECT), ne peut pas y écrire
    directement — aucun GRANT INSERT ne lui a été donné."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_responsable")
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute(
                        """
                        INSERT INTO clotures_caisse
                          (site_id, date_cloture, attendu_especes, attendu_orange_money,
                           attendu_mtn_momo, attendu_autre, compte_especes,
                           ecart_especes, utilisateur_id)
                        VALUES (1, CURRENT_DATE, 0, 0, 0, 0, 0, 0, 1)
                        """
                    )


# ---------------------------------------------------------------------------
# Unicité par (site, jour) et clôture rectificative
# ---------------------------------------------------------------------------

def test_deuxieme_cloture_originale_meme_site_jour_refusee(client):
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    premiere = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total},
    )
    assert premiere.status_code == 201, premiere.text

    deuxieme = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total},
    )
    assert deuxieme.status_code == 422, deuxieme.text
    assert "rectificative" in deuxieme.json()["detail"].lower()


def test_cloture_rectificative_autorisee_et_tracee(client):
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    premiere = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"site_id": 1, "date_cloture": jour, "espece_comptee": total},
    )
    premiere_id = premiere.json()["cloture_id"]

    rectificative = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={
            "site_id": 1, "date_cloture": jour, "espece_comptee": total - 200,
            "commentaire": "200 FCFA retrouvés manquants après coup",
            "cloture_rectificative_de": premiere_id,
        },
    )
    assert rectificative.status_code == 201, rectificative.text
    corps = rectificative.json()
    assert corps["cloture_rectificative_de"] == premiere_id
    assert corps["cloture_id"] != premiere_id

    historique = client.get("/caisse", headers=entete_autorisation(session["jeton"]))
    assert historique.status_code == 200
    ids = {c["cloture_id"] for c in historique.json()["clotures"]}
    assert {premiere_id, corps["cloture_id"]} <= ids


def test_cloture_rectificative_reference_invalide_refusee(client):
    _, jour, total = _creer_vente_payee(client, prix_unitaire=6500)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={
            "site_id": 1, "date_cloture": jour, "espece_comptee": total,
            "cloture_rectificative_de": 999999,
        },
    )
    assert reponse.status_code == 422, reponse.text


def test_site_obligatoire_pour_le_responsable(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session["jeton"]),
        json={"date_cloture": "2026-09-16", "espece_comptee": 1000},
    )
    assert reponse.status_code == 422
    assert "site" in reponse.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Cloisonnement par RÔLE — au niveau API (403)
# ---------------------------------------------------------------------------

def test_agent_comptabilite_ne_peut_ni_lire_ni_ecrire_via_lapi(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])
    assert client.get("/caisse", headers=entetes).status_code == 403
    assert client.get(
        "/caisse/attendu", headers=entetes, params={"site_id": 1, "date_cloture": "2026-09-16"}
    ).status_code == 403
    assert client.post(
        "/caisse", headers=entetes,
        json={"site_id": 1, "date_cloture": "2026-09-16", "espece_comptee": 1000},
    ).status_code == 403


def test_agent_stock_ne_peut_ni_lire_ni_ecrire_via_lapi(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])
    assert client.get("/caisse", headers=entetes).status_code == 403
    assert client.get(
        "/caisse/attendu", headers=entetes, params={"site_id": 1, "date_cloture": "2026-09-16"}
    ).status_code == 403
    assert client.post(
        "/caisse", headers=entetes,
        json={"site_id": 1, "date_cloture": "2026-09-16", "espece_comptee": 1000},
    ).status_code == 403


# ---------------------------------------------------------------------------
# Cloisonnement par RÔLE — en SQL DIRECT, en contournant complètement l'API
# (preuve la plus forte : ne dépend d'aucune ligne de code applicatif — même
# patron que test_cloisonnement_site.py)
# ---------------------------------------------------------------------------

def test_rls_bloque_completement_la_lecture_pour_agent_stock_en_sql_direct(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_agent_stock")
                cur.execute("SELECT set_config('qf.site_id', '1', true)")
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT * FROM clotures_caisse")


def test_rls_bloque_completement_la_lecture_pour_agent_comptabilite_en_sql_direct(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_agent_comptabilite")
                cur.execute("SELECT set_config('qf.site_id', '1', true)")
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT * FROM clotures_caisse")


def test_execution_cloturer_caisse_refusee_pour_agent_stock_en_sql_direct(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_agent_stock")
                cur.execute("SELECT set_config('qf.site_id', '1', true)")
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT * FROM cloturer_caisse(1, CURRENT_DATE, 1000, 2)")


def test_execution_cloturer_caisse_refusee_pour_agent_comptabilite_en_sql_direct(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_agent_comptabilite")
                cur.execute("SELECT set_config('qf.site_id', '1', true)")
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT * FROM cloturer_caisse(1, CURRENT_DATE, 1000, 4)")


def test_rls_laisse_le_responsable_voir_les_deux_sites_en_sql_direct(base_reinitialisee):
    """Contre-épreuve (même principe que test_cloisonnement_site.py) : la
    même politique RLS ne bride PAS le responsable — cloisonnement PAR
    RÔLE, pas une restriction générale de la table."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO clotures_caisse
                      (site_id, date_cloture, attendu_especes, attendu_orange_money,
                       attendu_mtn_momo, attendu_autre, compte_especes,
                       ecart_especes, utilisateur_id)
                    VALUES (1, CURRENT_DATE, 0, 0, 0, 0, 0, 0, 1)
                    """
                )
                cur.execute(
                    """
                    INSERT INTO clotures_caisse
                      (site_id, date_cloture, attendu_especes, attendu_orange_money,
                       attendu_mtn_momo, attendu_autre, compte_especes,
                       ecart_especes, utilisateur_id)
                    VALUES (2, CURRENT_DATE, 0, 0, 0, 0, 0, 0, 1)
                    """
                )
        conn.commit()

        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_responsable")
                cur.execute("SELECT DISTINCT site_id FROM clotures_caisse ORDER BY site_id")
                assert {r[0] for r in cur.fetchall()} == {1, 2}
