"""Fidélité du jeu d'essai (chantier C1, écart C1-04 du REGISTRE_ECARTS_100.md).

Le jeu d'essai TRUNCATE `parametres` puis réinsère une liste figée : toute
clé ajoutée par une migration et oubliée ici fait diverger la base de test
d'une installation réelle par migrations seules. Dérive réelle constatée au
cycle 66 (`seuil_remise_validation_pct`, 037, et `contact_support_technique`,
022, absents), corrigée au cycle 68 avec une note d'audit dans
`db/tests/00_jeu_essai.sql`. Ce test verrouille la couverture complète.
"""

from __future__ import annotations

import psycopg

from conftest import PG_ADMIN_DSN

# Clés insérées par les migrations 006, 019, 022, 032, 037, 040, 045, 048 —
# chacune doit figurer dans le seed, à l'état DÉCIDÉ de sa migration.
CLES_ATTENDUES = {
    "boutique_nom", "boutique_ville", "boutique_telephone",
    "boutique_numero_contribuable", "contact_support_technique",
    "regime_fiscal", "taux_tva", "prix_saisis_ttc", "arrondi_montants",
    "devise", "seuil_alerte_pourcentage", "seuil_alerte_plancher",
    "plafond_vraisemblance_comptage", "tentatives_max_connexion",
    "duree_session_minutes", "seuil_ecart_caisse_tolere",
    "credit_client_actif", "seuil_ecart_prix_vendeur",
    "seuil_remise_validation_pct",
}


def test_parametres_du_seed_couverts_par_les_migrations(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cle, valeur, a_decider FROM parametres")
            lignes = {cle: {"valeur": valeur, "a_decider": a_decider}
                      for cle, valeur, a_decider in cur.fetchall()}

    manquantes = CLES_ATTENDUES - set(lignes)
    assert not manquantes, f"clés de migrations absentes du jeu d'essai : {manquantes}"

    # Seule exception justifiée (note d'audit du seed) : état d'exécution
    # volatile écrit à chaque téléversement/suppression de logo — sans le
    # binaire correspondant, une valeur seed serait incohérente.
    assert "logo_boutique_extension" not in lignes

    # État des deux clés corrigées au cycle 68 : sentinelles à décider,
    # identiques aux migrations 022 et 037.
    assert lignes["seuil_remise_validation_pct"]["valeur"] == "a_definir"
    assert lignes["seuil_remise_validation_pct"]["a_decider"] is True
    assert lignes["contact_support_technique"]["valeur"] == "a_definir"
    assert lignes["contact_support_technique"]["a_decider"] is True
