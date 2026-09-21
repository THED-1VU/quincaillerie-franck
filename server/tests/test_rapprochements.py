"""Chantier 13a (cycle 34) : rapprochement des fiches articles homonymes.

Décision du propriétaire (2026-09-20) : la suggestion est automatique (même
``nom`` strict après ``btrim``, sites différents), la décision est humaine,
article par article, jamais une fusion automatique.

Ces tests vérifient, par exécution SQL réelle :

- la liste des candidats : vide sur le jeu d'essai (aucun homonyme), une
  paire exacte après injection synthétique, pas de candidat pour deux
  articles de même nom sur le MÊME site ;
- l'enregistrement d'une décision ``fusionner``/``distincts`` via la
  fonction SECURITY DEFINER ``enregistrer_rapprochement()`` (seul qf_app a
  EXECUTE), le retrait de la paire de la liste, et le refus de toute
  re-décision ;
- les refus : paire non homonyme, décision invalide, ordre d'identifiants
  invalide.
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import PG_ADMIN_DSN, PG_HOST, PG_PORT, PG_TEST_DBNAME, _executer_sql_admin

QF_APP_DSN = (
    f"host={PG_HOST} port={PG_PORT} dbname={PG_TEST_DBNAME} "
    f"user=qf_app password=qf_app_dev_local"
)

NOM_TEST = "Homonyme Test 13a"


def _inserer_article(nom, site_id):
    """Crée une FICHE (modèle multi-site, cycle 35) et sa ligne de stock au
    site demandé."""
    _executer_sql_admin(
        "INSERT INTO articles (nom, categorie, unite, prix_achat, prix_vente, fournisseur_id) "
        f"VALUES ({_litteral(nom)}, 'Divers', 'piece', 100, 200, NULL)"
    )
    _executer_sql_admin(
        "INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte) "
        f"VALUES ((SELECT max(id) FROM articles), {site_id}, 5, 1)"
    )


def _litteral(texte):
    return "'" + texte.replace("'", "''") + "'"


def _ids_candidats_qf_app():
    with psycopg.connect(QF_APP_DSN) as conn:
        lignes = conn.execute(
            "SELECT article_id_1, article_id_2, nom, site_id_1, site_id_2 "
            "FROM candidats_rapprochement() ORDER BY article_id_1, article_id_2"
        ).fetchall()
    return lignes


def _dernier_id_articles():
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute("SELECT max(id) FROM articles").fetchone()[0]


def test_jeu_essai_sans_homonyme(base_reinitialisee):
    assert _ids_candidats_qf_app() == []


def test_injection_paire_homonyme_listee(base_reinitialisee):
    _inserer_article(NOM_TEST, 1)
    _inserer_article(NOM_TEST, 2)
    max_id = _dernier_id_articles()
    candidats = _ids_candidats_qf_app()
    assert len(candidats) == 1
    article1, article2, nom, site1, site2 = candidats[0]
    assert (article1, article2) == (max_id - 1, max_id)
    assert nom == NOM_TEST
    assert (site1, site2) == (1, 2)


def test_btrim_est_applique_au_critere(base_reinitialisee):
    _inserer_article("  " + NOM_TEST + "  ", 1)
    _inserer_article(NOM_TEST, 2)
    assert len(_ids_candidats_qf_app()) == 1


def test_meme_nom_meme_site_non_candidat(base_reinitialisee):
    _inserer_article(NOM_TEST, 1)
    _inserer_article(NOM_TEST, 1)
    assert _ids_candidats_qf_app() == []


def test_enregistrer_fusionner_retire_la_paire(base_reinitialisee):
    _inserer_article(NOM_TEST, 1)
    _inserer_article(NOM_TEST, 2)
    max_id = _dernier_id_articles()
    id1, id2 = max_id - 1, max_id

    with psycopg.connect(QF_APP_DSN) as conn:
        conn.execute(
            "SELECT enregistrer_rapprochement(%s, %s, 'fusionner', 'Test 13a')",
            (id1, id2),
        )

    assert _ids_candidats_qf_app() == []
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        ligne = conn.execute(
            "SELECT decision, decide_par FROM rapprochements_articles "
            "WHERE article_id_1 = %s AND article_id_2 = %s",
            (id1, id2),
        ).fetchone()
    assert ligne == ("fusionner", "Test 13a")


def test_redecision_refusee(base_reinitialisee):
    _inserer_article(NOM_TEST, 1)
    _inserer_article(NOM_TEST, 2)
    max_id = _dernier_id_articles()
    id1, id2 = max_id - 1, max_id
    with psycopg.connect(QF_APP_DSN) as conn:
        conn.execute(
            "SELECT enregistrer_rapprochement(%s, %s, 'distincts', 'Test')",
            (id1, id2),
        )
        with pytest.raises(psycopg.errors.UniqueViolation, match="déjà enregistrée"):
            conn.execute(
                "SELECT enregistrer_rapprochement(%s, %s, 'fusionner', 'Test')",
                (id1, id2),
            )


def test_paire_non_homonyme_refusee(base_reinitialisee):
    # Les articles 1 et 3 du jeu d'essai ont des noms différents.
    with psycopg.connect(QF_APP_DSN) as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="paire homonyme"):
            conn.execute(
                "SELECT enregistrer_rapprochement(1, 3, 'fusionner', 'Test')"
            )


def test_decision_invalide_refusee(base_reinitialisee):
    _inserer_article(NOM_TEST, 1)
    _inserer_article(NOM_TEST, 2)
    max_id = _dernier_id_articles()
    with psycopg.connect(QF_APP_DSN) as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="fusionner ou distincts"):
            conn.execute(
                "SELECT enregistrer_rapprochement(%s, %s, 'peut-etre', 'Test')",
                (max_id - 1, max_id),
            )


def test_ordre_identifiants_invalide_refuse(base_reinitialisee):
    _inserer_article(NOM_TEST, 1)
    _inserer_article(NOM_TEST, 2)
    max_id = _dernier_id_articles()
    with psycopg.connect(QF_APP_DSN) as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="ordonnés"):
            conn.execute(
                "SELECT enregistrer_rapprochement(%s, %s, 'fusionner', 'Test')",
                (max_id, max_id - 1),
            )


def test_privileges_execute(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        def privilege(role):
            return conn.execute(
                "SELECT has_function_privilege(%s, "
                "'enregistrer_rapprochement(INTEGER,INTEGER,VARCHAR,VARCHAR)', "
                "'EXECUTE')",
                (role,),
            ).fetchone()[0]

        assert privilege("qf_app") is True
        assert privilege("qf_responsable") is False
        assert privilege("qf_agent_stock") is False
        assert privilege("qf_agent_comptabilite") is False
