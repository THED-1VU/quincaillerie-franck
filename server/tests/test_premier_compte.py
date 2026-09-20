"""Chantier C0-C (cycle 31) : création du premier compte responsable.

La fonction ``creer_premier_responsable()`` (migration 023) est appelée par
l'outil console ``db/outils/creer_compte_responsable.ps1`` — elle n'a pas de
route HTTP. Ces tests vérifient, par exécution SQL réelle :

- le chemin de refus, connecté en tant que ``qf_app`` (le rôle de
  l'application, seul détenteur du droit EXECUTE) : le jeu d'essai contient
  déjà un responsable, et les contrôles d'entrée s'appliquent ;
- le privilège EXECUTE : ``qf_app`` oui, les rôles métier non ;
- le chemin de succès dans une transaction annulée (le jeu d'essai n'est
  jamais modifié) : compte créé, hachage au format ``$2a$``, ``actif`` et
  ``doit_changer_mot_de_passe`` à ``TRUE``, journal ``creation`` écrit.

Le parcours complet « base neuve -> script -> connexion réelle » est prouvé
hors pytest par l'exécution réelle de ``creer_compte_responsable.ps1`` sur
une base vierge (voir loop-state.md, cycle 31).
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import PG_ADMIN_DSN, PG_HOST, PG_PORT, PG_TEST_DBNAME

QF_APP_DSN = (
    f"host={PG_HOST} port={PG_PORT} dbname={PG_TEST_DBNAME} "
    f"user=qf_app password=qf_app_dev_local"
)


def _creer_en_tant_que_qf_app(nom, identifiant, mot_de_passe):
    with psycopg.connect(QF_APP_DSN) as conn:
        conn.execute(
            "SELECT creer_premier_responsable(%s, %s, %s)",
            (nom, identifiant, mot_de_passe),
        )
        return conn.execute("SELECT 1").fetchone()  # pragma: no cover - jamais atteint en succès ici


def test_qf_app_a_execute_et_les_roles_metier_non(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        def privilegie(role):
            return conn.execute(
                "SELECT has_function_privilege(%s, "
                "'creer_premier_responsable(VARCHAR,VARCHAR,TEXT)', 'EXECUTE')",
                (role,),
            ).fetchone()[0]

        assert privilegie("qf_app") is True
        assert privilegie("qf_responsable") is False
        assert privilegie("qf_agent_stock") is False
        assert privilegie("qf_agent_comptabilite") is False


def test_refuse_identifiant_vide(base_reinitialisee):
    with pytest.raises(psycopg.errors.RaiseException, match="identifiant est obligatoire"):
        _creer_en_tant_que_qf_app("Nouveau Responsable", "   ", "MotDePasse123")


def test_refuse_nom_vide(base_reinitialisee):
    with pytest.raises(psycopg.errors.RaiseException, match="nom complet est obligatoire"):
        _creer_en_tant_que_qf_app("   ", "nouveau.resp", "MotDePasse123")


def test_refuse_mot_de_passe_court(base_reinitialisee):
    with pytest.raises(psycopg.errors.RaiseException, match="au moins 8"):
        _creer_en_tant_que_qf_app("Nouveau Responsable", "nouveau.resp", "court")


def test_refuse_identifiant_deja_pris(base_reinitialisee):
    with pytest.raises(psycopg.errors.RaiseException, match="déjà utilisé"):
        _creer_en_tant_que_qf_app("Nouveau Responsable", "resp", "MotDePasse123")


def test_refuse_si_responsable_existe(base_reinitialisee):
    with pytest.raises(psycopg.errors.RaiseException, match="responsable existe déjà"):
        _creer_en_tant_que_qf_app("Nouveau Responsable", "nouveau.resp", "MotDePasse123")


def test_succes_dans_transaction_annulee(base_reinitialisee):
    """Le succès est prouvé dans une transaction annulée : le jeu d'essai
    (qui contient déjà un responsable) n'est jamais modifié durablement."""
    with psycopg.connect(PG_ADMIN_DSN, row_factory=psycopg.rows.dict_row) as conn:
        conn.execute("BEGIN")
        try:
            # Simule une base neuve : le responsable du jeu d'essai devient
            # temporairement un agent (la contrainte rôle/site est respectée).
            conn.execute(
                "UPDATE utilisateurs SET role = 'agent_stock', site_id = 1 "
                "WHERE role = 'responsable'"
            )
            nouveau_id = conn.execute(
                "SELECT creer_premier_responsable('Nouveau Responsable', "
                "'premier.resp', 'MotDePasse123')"
            ).fetchone()["creer_premier_responsable"]

            ligne = conn.execute(
                "SELECT identifiant, role, site_id, actif, "
                "doit_changer_mot_de_passe, mot_de_passe_hash "
                "FROM utilisateurs WHERE id = %s",
                (nouveau_id,),
            ).fetchone()
            assert ligne["identifiant"] == "premier.resp"
            assert ligne["role"] == "responsable"
            assert ligne["site_id"] is None
            assert ligne["actif"] is True
            assert ligne["doit_changer_mot_de_passe"] is True
            assert ligne["mot_de_passe_hash"].startswith("$2a$")

            trace = conn.execute(
                "SELECT action FROM journal_comptes WHERE utilisateur_cible_id = %s",
                (nouveau_id,),
            ).fetchone()
            assert trace is not None and trace["action"] == "creation"
        finally:
            conn.rollback()
