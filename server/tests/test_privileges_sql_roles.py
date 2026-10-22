"""Privilèges SQL par rôle PostgreSQL (chantier C8, cycle 65).

La matrice API (test_matrice_roles.py) prouve le contrôle applicatif ;
celui-ci prouve le contrôle QUI COMPTE, celui de la base (deps.py, docstring :
« un bug ici ferait au pire répondre 403 à tort — jamais fuiter une donnée
interdite »). On contourne délibérément l'API : connexion de test sous
« postgres » (raccourci d'administration déjà utilisé par
test_cloisonnement_site.py, jamais un chemin emprunté par l'application) puis
``SET LOCAL ROLE`` vers chaque rôle métier — exactement la bascule que fait
``database.connexion_pour()`` en production.

Attendus = GRANT par colonne de la migration 008 et suivantes :
- agent_stock   : JAMAIS de prix (ni achat ni vente) ; quantités oui ;
                  comptages aveugles (quantité attendue jamais lisible) ;
                  clôtures de caisse interdites.
- comptabilité  : prix_vente oui ; prix_achat NON ; quantités NON (ni
                  stocks_sites ni comptages) ; clôtures de caisse NON.
- responsable   : tout sauf le hachage des mots de passe.
"""

from __future__ import annotations

import psycopg

from conftest import PG_ADMIN_DSN


def _sous_role(role: str, sql: str):
    """Exécute sql sous le rôle PostgreSQL indiqué, dans une transaction
    (SET LOCAL). Renvoie (a_reussi, message_erreur)."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(f"SET LOCAL ROLE {role}")
                try:
                    cur.execute(sql)
                    return True, ""
                except psycopg.errors.Error as exc:
                    return False, str(exc)


# --- Agent stock : jamais de prix, quantités oui, caisse interdite ----------

def test_agent_stock_ne_lit_aucun_prix():
    for colonne in ("prix_achat", "prix_vente"):
        ok, _ = _sous_role("qf_agent_stock", f"SELECT {colonne} FROM articles")
        assert not ok, f"qf_agent_stock a pu lire articles.{colonne}"


def test_agent_stock_lit_les_quantites():
    ok, message = _sous_role("qf_agent_stock", "SELECT quantite_stock FROM stocks_sites")
    assert ok, message


def test_agent_stock_ne_lit_pas_la_quantite_attendue_du_comptage():
    # Comptage aveugle (migrations 012/029) : la colonne qui trahirait le
    # stock théorique pendant un inventaire ne lui est jamais lisible.
    ok, _ = _sous_role(
        "qf_agent_stock", "SELECT quantite_attendue FROM comptages_stock"
    )
    assert not ok, "qf_agent_stock a pu lire comptages_stock.quantite_attendue"


def test_agent_stock_ne_lit_pas_les_clotures_de_caisse():
    ok, _ = _sous_role("qf_agent_stock", "SELECT * FROM clotures_caisse")
    assert not ok, "qf_agent_stock a pu lire clotures_caisse"


def test_agent_stock_necrit_pas_directement_les_mouvements_de_vente():
    # Seules les fonctions SECURITY DEFINER (décrément de stock) écrivent
    # côté vente — pas de INSERT direct sous qf_agent_stock.
    ok, _ = _sous_role(
        "qf_agent_stock",
        "INSERT INTO mouvements_stock (article_id, site_id, quantite, type) "
        "VALUES (1, 1, 1, 'vente')",
    )
    assert not ok, "qf_agent_stock a pu insérer un mouvement de vente direct"


# --- Agent comptabilité : prix_vente oui, prix_achat et quantités non -----

def test_compta_lit_le_prix_de_vente_mais_pas_le_prix_dachat():
    ok, message = _sous_role("qf_agent_comptabilite", "SELECT prix_vente FROM articles")
    assert ok, message
    ok, _ = _sous_role("qf_agent_comptabilite", "SELECT prix_achat FROM articles")
    assert not ok, "qf_agent_comptabilite a pu lire articles.prix_achat"


def test_compta_ne_lit_aucune_quantite():
    for table, colonne in (
        ("stocks_sites", "quantite_stock"),
        ("comptages_stock", "quantite"),
    ):
        ok, _ = _sous_role(
            "qf_agent_comptabilite", f"SELECT {colonne} FROM {table}"
        )
        assert not ok, f"qf_agent_comptabilite a pu lire {table}.{colonne}"


def test_compta_ne_lit_pas_les_clotures_de_caisse():
    ok, _ = _sous_role("qf_agent_comptabilite", "SELECT * FROM clotures_caisse")
    assert not ok, "qf_agent_comptabilite a pu lire clotures_caisse"


# --- Responsable : tout sauf le hachage des mots de passe ------------------

def test_responsable_ne_lit_pas_le_hachage_des_mots_de_passe():
    ok, _ = _sous_role(
        "qf_responsable", "SELECT mot_de_passe_hash FROM utilisateurs"
    )
    assert not ok, "qf_responsable a pu lire utilisateurs.mot_de_passe_hash"


def test_responsable_lit_les_colonnes_sensibles_metier():
    for sql in (
        "SELECT prix_achat FROM articles",
        "SELECT quantite_stock FROM stocks_sites",
        "SELECT * FROM clotures_caisse",
    ):
        ok, message = _sous_role("qf_responsable", sql)
        assert ok, f"{sql!r} a échoué : {message}"
