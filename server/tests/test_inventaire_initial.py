"""Point j (migration 041) : chargement du stock initial réel.

Décision du propriétaire (2026-09-19, ADDENDUM_CAHIER_DES_CHARGES.md, point j
; convention des 20 % validée le 2026-09-25) : le chargement initial est un
mouvement ``inventaire_initial`` daté, tracé, jamais confondu avec une
réception fournisseur. Pas de route HTTP dédiée (outil console,
``db/outils/importer_stock_initial.py``) : ces tests appellent la fonction
SECURITY DEFINER ``enregistrer_inventaire_initial()`` directement, comme
``test_rapprochements.py`` le fait pour ``enregistrer_rapprochement()``.

``enregistrer_inventaire_initial()`` est réservée à qf_responsable (pas
qf_app, contrairement au rapprochement) : qf_app s'y connecte puis bascule
avec ``SET ROLE``, exactement comme le fait le serveur
(``database.py::connexion_pour``).
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import PG_ADMIN_DSN, PG_HOST, PG_PORT, PG_TEST_DBNAME, _executer_sql_admin

QF_APP_DSN = (
    f"host={PG_HOST} port={PG_PORT} dbname={PG_TEST_DBNAME} "
    f"user=qf_app password=qf_app_dev_local"
)


def _connexion_responsable():
    conn = psycopg.connect(QF_APP_DSN)
    conn.execute("SET ROLE qf_responsable")
    return conn


def _stock(article_id, site_id):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT quantite_stock, seuil_alerte FROM stocks_sites "
            "WHERE article_id = %s AND site_id = %s",
            (article_id, site_id),
        ).fetchone()


def test_cree_la_ligne_de_stock_si_absente(base_reinitialisee):
    # Article 4 (jeu d'essai) n'a pas de ligne au site 2.
    _executer_sql_admin("DELETE FROM stocks_sites WHERE article_id = 4 AND site_id = 2")
    with _connexion_responsable() as conn:
        total = conn.execute(
            "SELECT enregistrer_inventaire_initial(4, 2, 50, 2, 'zone A')"
        ).fetchone()[0]
    assert total == 50
    quantite, seuil = _stock(4, 2)
    assert (quantite, seuil) == (50, 10)


def test_second_chargement_additionne(base_reinitialisee):
    _executer_sql_admin("DELETE FROM stocks_sites WHERE article_id = 4 AND site_id = 2")
    with _connexion_responsable() as conn:
        conn.execute("SELECT enregistrer_inventaire_initial(4, 2, 50, 2, 'zone A')")
        conn.commit()
        conn.execute("SELECT enregistrer_inventaire_initial(4, 2, 30, 2, 'zone B')")
    quantite, seuil = _stock(4, 2)
    assert (quantite, seuil) == (80, 16)


def test_mouvement_categorise_inventaire_initial(base_reinitialisee):
    _executer_sql_admin("DELETE FROM stocks_sites WHERE article_id = 4 AND site_id = 2")
    with _connexion_responsable() as conn:
        conn.execute("SELECT enregistrer_inventaire_initial(4, 2, 50, 2, 'zone A')")
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        categorie, type_mvt = conn.execute(
            "SELECT categorie, type FROM mouvements_stock "
            "WHERE article_id = 4 AND site_id = 2 ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert (categorie, type_mvt) == ("inventaire_initial", "entree")


def test_seuil_arrondi_a_lentier_pour_article_non_decimal(base_reinitialisee):
    # Trouvé par exécution en testant l'outil d'import : 13 x 20 % = 2.6, un
    # article qui n'autorise pas les décimales (défaut) refuserait un seuil
    # décimal sans l'arrondi ajouté dans la fonction.
    with _connexion_responsable() as conn:
        conn.execute("SELECT enregistrer_inventaire_initial(3, 1, 13, 2, 'zone C')")
    quantite, seuil = _stock(3, 1)
    assert (quantite, seuil) == (13, 3)


def test_quantite_nulle_refusee(base_reinitialisee):
    with _connexion_responsable() as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="Quantité invalide"):
            conn.execute("SELECT enregistrer_inventaire_initial(4, 1, 0, 2, 'zone A')")


def test_quantite_negative_refusee(base_reinitialisee):
    with _connexion_responsable() as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="Quantité invalide"):
            conn.execute("SELECT enregistrer_inventaire_initial(4, 1, -5, 2, 'zone A')")


def test_motif_vide_refuse(base_reinitialisee):
    with _connexion_responsable() as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="Motif obligatoire"):
            conn.execute("SELECT enregistrer_inventaire_initial(4, 1, 10, 2, '')")


def test_motif_null_refuse(base_reinitialisee):
    with _connexion_responsable() as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="Motif obligatoire"):
            conn.execute(
                "SELECT enregistrer_inventaire_initial(4, 1, 10, 2, %s)", (None,)
            )


def test_article_introuvable_refuse(base_reinitialisee):
    with _connexion_responsable() as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation, match="introuvable"):
            conn.execute("SELECT enregistrer_inventaire_initial(999999, 1, 10, 2, 'zone A')")


def test_privileges_execute(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        def privilege(role):
            return conn.execute(
                "SELECT has_function_privilege(%s, "
                "'enregistrer_inventaire_initial(INTEGER,INTEGER,NUMERIC,INTEGER,VARCHAR)', "
                "'EXECUTE')",
                (role,),
            ).fetchone()[0]

        assert privilege("qf_responsable") is True
        assert privilege("qf_app") is False
        assert privilege("qf_agent_stock") is False
        assert privilege("qf_agent_comptabilite") is False
