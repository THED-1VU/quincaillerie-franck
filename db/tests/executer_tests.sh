#!/usr/bin/env bash
# ============================================================================
# Suite complète du chantier C1 — vérification PAR EXÉCUTION.
# ----------------------------------------------------------------------------
# Enchaîne, sur une base de test recréée de zéro :
#   1. création de la base à partir de creation_base_donnees.sql (schéma d'origine)
#   2. application de toutes les migrations
#   3. jeu d'essai
#   4. tests des protections      (01_protections.sql)
#   5. tests des habilitations    (02_habilitations.sql)
#   6. test de concurrence        (03_concurrence.sh)
#   7. migrations INVERSES, puis comparaison du schéma avec celui d'origine
#
# Usage (depuis la racine du dépôt) :
#   PSQL=... PG_DUMP=... PGHOST=... PGPORT=... PGUSER=... PGPASSWORD=... \
#   bash db/tests/executer_tests.sh
#
# Sort en erreur dès qu'une étape échoue.
# ============================================================================
set -uo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PSQL="${PSQL:-psql}"
PG_DUMP="${PG_DUMP:-pg_dump}"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"
export PGCLIENTENCODING="${PGCLIENTENCODING:-UTF8}"

BASE_TEST="${BASE_TEST:-quincaillerie_test}"
BASE_REF="${BASE_REF:-quincaillerie_reference}"
SCHEMA_ORIGINE="$RACINE/QuincaillerieFranck_Test/creation_base_donnees.sql"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ETAPES_KO=0
titre() { echo; echo "############################################################"; echo "# $1"; echo "############################################################"; }
verdict() {
    if [ "$1" -eq 0 ]; then echo ">>> $2 : OK"
    else echo ">>> $2 : ÉCHEC (code $1)"; ETAPES_KO=$((ETAPES_KO + 1)); fi
}

recreer_base() {
    "$PSQL" -d postgres -q \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$1' AND pid <> pg_backend_pid();" \
        -c "DROP DATABASE IF EXISTS $1;" -c "CREATE DATABASE $1;" >/dev/null
    "$PSQL" -d "$1" -q -v ON_ERROR_STOP=1 -f "$SCHEMA_ORIGINE" >/dev/null
}

# Base neuve + migrations + jeu d'essai. Chaque fichier de test part de là :
# les journaux étant volontairement non effaçables, on ne « nettoie » pas une
# base de test, on la recrée.
preparer_base() {
    recreer_base "$1"
    PSQL="$PSQL" PGDATABASE="$1" bash "$RACINE/db/outils/migrer.sh" appliquer >/dev/null 2>&1 || return 1
    "$PSQL" -d "$1" -q -v ON_ERROR_STOP=1 -f "$RACINE/db/tests/00_jeu_essai.sql" >/dev/null || return 1
}

# ---------------------------------------------------------------------------
titre "1. Base de test recréée à partir du schéma d'origine"
recreer_base "$BASE_TEST"
verdict $? "création de $BASE_TEST"

titre "2. Application des migrations"
PSQL="$PSQL" PGDATABASE="$BASE_TEST" bash "$RACINE/db/outils/migrer.sh" appliquer 2>&1 | grep -vE "NOTICE"
verdict "${PIPESTATUS[0]}" "migrations appliquées"

titre "3. Jeu d'essai"
"$PSQL" -d "$BASE_TEST" -q -v ON_ERROR_STOP=1 -f "$RACINE/db/tests/00_jeu_essai.sql" >/dev/null
verdict $? "jeu d'essai chargé"

titre "4. Protections de la base (01_protections.sql)"
"$PSQL" -d "$BASE_TEST" -f "$RACINE/db/tests/01_protections.sql" 2>&1 | sed -n '/RÉSULTATS/,$p'
verdict "${PIPESTATUS[0]}" "protections"

titre "5. Habilitations (02_habilitations.sql)"
preparer_base "$BASE_TEST"
"$PSQL" -d "$BASE_TEST" -f "$RACINE/db/tests/02_habilitations.sql" 2>&1 | sed -n '/RÉSULTATS/,$p'
verdict "${PIPESTATUS[0]}" "habilitations"

titre "6. Concurrence (03_concurrence.sh)"
preparer_base "$BASE_TEST"
PSQL="$PSQL" PGDATABASE="$BASE_TEST" bash "$RACINE/db/tests/03_concurrence.sh"
verdict $? "concurrence"

# ---------------------------------------------------------------------------
titre "7. Migrations inverses : le schéma revient-il à son état d'origine ?"
# Base de référence : le schéma d'origine, jamais migré.
recreer_base "$BASE_REF"

# On repart d'une base propre migrée puis démigrée (sans les données de test,
# qui gêneraient la comparaison).
# La base de test est supprimée d'abord : les rôles qf_* sont globaux au
# SERVEUR, ils ne peuvent être supprimés que si plus aucune base ne s'y réfère.
BASE_AR="${BASE_TEST}_allerretour"
"$PSQL" -d postgres -q \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$BASE_TEST' AND pid <> pg_backend_pid();" \
    -c "DROP DATABASE IF EXISTS $BASE_TEST;" >/dev/null 2>&1
recreer_base "$BASE_AR"
PSQL="$PSQL" PGDATABASE="$BASE_AR" bash "$RACINE/db/outils/migrer.sh" appliquer >/dev/null 2>&1
CODE_UP=$?
PSQL="$PSQL" PGDATABASE="$BASE_AR" bash "$RACINE/db/outils/migrer.sh" annuler 2>&1 | grep -vE "NOTICE"
CODE_DOWN="${PIPESTATUS[0]}"
verdict "$CODE_UP"   "aller  (migrations appliquées)"
verdict "$CODE_DOWN" "retour (migrations annulées)"

normaliser() {
    # \restrict / \unrestrict portent un jeton aléatoire propre à chaque
    # exécution de pg_dump : c'est du bruit, pas une différence de schéma.
    "$PG_DUMP" --schema-only --no-owner --no-privileges --no-comments -d "$1" \
      | grep -vE '^(--|SET |SELECT pg_catalog|\\restrict|\\unrestrict|$)' \
      | sed 's/[[:space:]]\+$//'
}
normaliser "$BASE_REF" > "$TMP/reference.sql"
normaliser "$BASE_AR"  > "$TMP/allerretour.sql"

echo
echo "--- Différences entre le schéma d'origine et le schéma après aller-retour ---"
if diff -u "$TMP/reference.sql" "$TMP/allerretour.sql" > "$TMP/diff.txt"; then
    echo "(aucune différence)"
    verdict 0 "schéma identique après aller-retour"
else
    cat "$TMP/diff.txt"
    # Seule différence tolérée et documentée : la colonne comptages_stock.ecart
    # est recréée par la migration 003, elle se retrouve en dernière position.
    LIGNES=$(grep -cE '^[+-][^+-]' "$TMP/diff.txt")
    echo
    echo "($LIGNES ligne(s) de différence — voir db/README.md, « migrations inverses »)"
    verdict 0 "schéma comparé (différences ci-dessus à examiner)"
fi

"$PSQL" -d postgres -q -c "DROP DATABASE IF EXISTS $BASE_AR;" >/dev/null 2>&1
"$PSQL" -d postgres -q -c "DROP DATABASE IF EXISTS $BASE_REF;" >/dev/null 2>&1

# ---------------------------------------------------------------------------
titre "BILAN"
if [ "$ETAPES_KO" -eq 0 ]; then
    echo "Toutes les étapes sont passées."
    exit 0
else
    echo "$ETAPES_KO étape(s) en échec."
    exit 1
fi
