#!/usr/bin/env bash
# ============================================================================
# Applique (ou annule) les migrations de schéma, dans l'ordre.
# ----------------------------------------------------------------------------
# Usage :
#   db/outils/migrer.sh appliquer            # 000 -> la plus récente
#   db/outils/migrer.sh annuler              # la plus récente -> 000
#   db/outils/migrer.sh etat                 # ce qui est appliqué
#
# Connexion : variables d'environnement PostgreSQL habituelles.
#   PGHOST (défaut 127.0.0.1), PGPORT (5432), PGUSER (postgres),
#   PGDATABASE (quincaillerie_test), PGPASSWORD.
#   PSQL permet de pointer un binaire psql qui n'est pas dans le PATH.
#
# Chaque fichier est exécuté dans UNE transaction, avec ON_ERROR_STOP :
# une migration passe en entier, ou pas du tout.
# ============================================================================
set -euo pipefail

ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS="$(cd "$ICI/../migrations" && pwd)"

PSQL="${PSQL:-psql}"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"
export PGDATABASE="${PGDATABASE:-quincaillerie_test}"
export PGCLIENTENCODING="${PGCLIENTENCODING:-UTF8}"

executer() {
    "$PSQL" -v ON_ERROR_STOP=1 --single-transaction -q -f "$1"
}

case "${1:-}" in
  appliquer)
    echo "== Application des migrations sur $PGDATABASE ($PGHOST:$PGPORT) =="
    # État figé avant la boucle : les deux fichiers historiques 040 doivent
    # tous deux tourner sur base vierge, sans rejouer les versions livrées.
    plancher=-1
    versions_appliquees=''
    existe=$("$PSQL" -v ON_ERROR_STOP=1 -Atqc "SELECT to_regclass('public.schema_migrations') IS NOT NULL")
    existe=${existe//$'\r'/}
    if [ "$existe" = t ]; then
        plancher=$("$PSQL" -v ON_ERROR_STOP=1 -Atqc "SELECT COALESCE(MAX(version::integer),-1) FROM schema_migrations")
        versions_appliquees=$("$PSQL" -v ON_ERROR_STOP=1 -Atqc "SELECT version FROM schema_migrations")
        plancher=${plancher//$'\r'/}
        versions_appliquees=${versions_appliquees//$'\r'/}
    fi
    for f in "$MIGRATIONS"/[0-9][0-9][0-9]_*.sql; do
        case "$f" in *_inverse.sql) continue ;; esac
        nom=$(basename "$f")
        version=${nom:0:3}
        if (( 10#$version <= plancher )); then
            case $'\n'"$versions_appliquees"$'\n' in
                *$'\n'"$version"$'\n'*) continue ;;
                *) echo "Historique incomplet : version $version absente avant $plancher. Diagnostic requis." >&2; exit 1 ;;
            esac
        fi
        echo "-- $(basename "$f")"
        executer "$f"
    done
    echo "== Terminé =="
    "$PSQL" -q -c "SELECT version, nom, applique_le FROM schema_migrations ORDER BY version;"
    ;;

  annuler)
    echo "== Annulation des migrations sur $PGDATABASE ($PGHOST:$PGPORT) =="
    # Tableau + parcours à rebours : le chemin du dépôt contient un espace
    # (« THED CONNECT »), un $(ls) serait découpé en morceaux.
    fichiers=( "$MIGRATIONS"/[0-9][0-9][0-9]_*_inverse.sql )
    for (( i=${#fichiers[@]}-1 ; i>=0 ; i-- )); do
        echo "-- $(basename "${fichiers[i]}")"
        executer "${fichiers[i]}"
    done
    echo "== Terminé (schéma revenu à son état d'origine) =="
    ;;

  etat)
    "$PSQL" -q -c "SELECT version, nom, applique_le, applique_par FROM schema_migrations ORDER BY version;"
    ;;

  *)
    echo "Usage : $(basename "$0") {appliquer|annuler|etat}" >&2
    exit 2
    ;;
esac
