#!/usr/bin/env bash
# ============================================================================
# Suite de non-régression COMPLÈTE, en une seule commande (chantier C13,
# cycle 20).
# ----------------------------------------------------------------------------
# Jusqu'ici, vérifier tout le projet demandait d'enchaîner À LA MAIN trois
# couches (SQL, pytest, Playwright), documenté nulle part comme UNE seule
# procédure — chaque cycle le refaisait par copier-coller de commandes.
# Ce script automatise exactement l'enchaînement suivi depuis le cycle 2 :
#
#   1. suite SQL complète               (db/tests/executer_tests.sh)
#   2. reconstruction de quincaillerie_test (l'étape précédente la supprime
#      délibérément à sa dernière étape, pour comparer le schéma réversible)
#   3. suite pytest du serveur          (server/tests/)
#   4. démarrage temporaire d'uvicorn, puis les suites Playwright de
#      maquette/verification/ qui n'exigent qu'un serveur réel sur
#      SERVEUR_URL (cablage, vente, inventaire, stock, rapports,
#      echappement, rh) — PAS `affichage`/`flux`, qui exigent un second
#      serveur STATIQUE séparé (`py -m http.server 8080`, cycle 1, jamais
#      automatisé, hors périmètre de ce script)
#   5. arrêt du serveur temporaire, jeu d'essai rechargé une dernière fois
#      pour laisser la base dans un état propre
#
# Usage (depuis la racine du dépôt, PostgreSQL de dev déjà démarré — voir
# db/outils/demarrer_pg.ps1) :
#   PSQL=... PG_DUMP=... PGHOST=... PGPORT=... PGUSER=... PGPASSWORD=... \
#   PYTHON=... PORT_SERVEUR=8010 \
#   bash db/outils/verifier_tout.sh
#
# Sort en erreur (code 1) dès qu'une étape échoue ; le serveur temporaire et
# le jeu d'essai sont malgré tout nettoyés (piège trap).
# ============================================================================
set -uo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PSQL="${PSQL:-psql}"
PG_DUMP="${PG_DUMP:-pg_dump}"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5433}"
export PGUSER="${PGUSER:-postgres}"
export PGPASSWORD="${PGPASSWORD:-qf_dev_local}"
export PGCLIENTENCODING="${PGCLIENTENCODING:-UTF8}"

PYTHON="${PYTHON:-$RACINE/server/.venv/Scripts/python.exe}"
PORT_SERVEUR="${PORT_SERVEUR:-8010}"
SERVEUR_URL="http://127.0.0.1:${PORT_SERVEUR}"
BASE_TEST="${BASE_TEST:-quincaillerie_test}"
SCHEMA_ORIGINE="$RACINE/QuincaillerieFranck_Test/creation_base_donnees.sql"

ETAPES_KO=0
PID_SERVEUR=""

titre() { echo; echo "############################################################"; echo "# $1"; echo "############################################################"; }
verdict() {
    if [ "$1" -eq 0 ]; then echo ">>> $2 : OK"
    else echo ">>> $2 : ÉCHEC (code $1)"; ETAPES_KO=$((ETAPES_KO + 1)); fi
}

nettoyer() {
    if [ -n "$PID_SERVEUR" ] && kill -0 "$PID_SERVEUR" 2>/dev/null; then
        kill "$PID_SERVEUR" 2>/dev/null
        wait "$PID_SERVEUR" 2>/dev/null
    fi
}
trap nettoyer EXIT

recreer_base_test() {
    "$PSQL" -d postgres -q \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$BASE_TEST' AND pid <> pg_backend_pid();" \
        -c "DROP DATABASE IF EXISTS $BASE_TEST;" -c "CREATE DATABASE $BASE_TEST;" >/dev/null
    "$PSQL" -d "$BASE_TEST" -q -v ON_ERROR_STOP=1 -f "$SCHEMA_ORIGINE" >/dev/null
    PSQL="$PSQL" PGDATABASE="$BASE_TEST" bash "$RACINE/db/outils/migrer.sh" appliquer >/dev/null 2>&1
    # Piège trouvé en écrivant ce script : l'étape 7 de la suite SQL (aller-
    # retour de réversibilité) DROP les rôles applicatifs (migration 008
    # inverse) — GLOBAUX au serveur, pas propres à une base — puis les
    # recrée sans mot de passe (CREATE ROLE ... LOGIN, sans PASSWORD).
    # `qf_app` retrouve donc un mot de passe VIDE, différent de celui de
    # config.ini : sans cette ligne, pytest ET les suites Playwright
    # échouent en cascade juste après (authentification refusée), pour une
    # raison invisible dans leurs propres messages d'erreur. Le mot de
    # passe est relu dans config.ini plutôt que dupliqué en dur ici.
    MOT_DE_PASSE_QF_APP="$(sed -n 's/^password *= *//p' "$RACINE/server/config.ini" | head -1)"
    "$PSQL" -d postgres -q -c "ALTER ROLE qf_app WITH PASSWORD '${MOT_DE_PASSE_QF_APP}';" >/dev/null
    "$PSQL" -d "$BASE_TEST" -q -v ON_ERROR_STOP=1 -f "$RACINE/db/tests/00_jeu_essai.sql" >/dev/null
}

# ---------------------------------------------------------------------------
titre "1. Suite SQL complète (db/tests/executer_tests.sh)"
PSQL="$PSQL" PG_DUMP="$PG_DUMP" bash "$RACINE/db/tests/executer_tests.sh"
verdict $? "suite SQL"

titre "2. Reconstruction de $BASE_TEST (supprimée par l'étape 7 de la suite SQL)"
recreer_base_test
verdict $? "base reconstruite"

titre "3. Suite pytest du serveur"
( cd "$RACINE/server" && "$PYTHON" -m pytest -q )
verdict $? "pytest"

titre "4. Suites Playwright (serveur réel, cablage/vente/inventaire/stock/rapports/echappement/rh)"
# config.ini de dev limite à 10 connexions/minute (protection anti-force
# brute, voir securite.py) — bien trop bas pour enchaîner 7 suites qui se
# reconnectent chacune plusieurs fois en quelques minutes (trouvé en
# écrivant ce script : les suites 2 et suivantes échouaient toutes avec
# une session nulle, silencieusement rejetées par le serveur). Une copie
# temporaire de config.ini, UNIQUEMENT pour ce process de vérification
# (jamais le vrai config.ini, jamais commitée), relève cette limite au
# même niveau que les tests pytest (conftest.py : 1000/min).
CONFIG_TEMP="$(mktemp)"
sed 's/^tentatives_max_par_minute *=.*/tentatives_max_par_minute = 1000/' \
    "$RACINE/server/config.ini" > "$CONFIG_TEMP"

( cd "$RACINE/server" && QF_CONFIG="$CONFIG_TEMP" "$PYTHON" -m uvicorn app.main:app --app-dir . --port "$PORT_SERVEUR" \
    > "$RACINE/db/outils/.verifier_tout_uvicorn.log" 2>&1 ) &
PID_SERVEUR=$!

PRET=1
for _ in $(seq 1 30); do
    if curl -s -o /dev/null "http://127.0.0.1:${PORT_SERVEUR}/sante"; then PRET=0; break; fi
    sleep 1
done
if [ "$PRET" -ne 0 ]; then
    echo ">>> le serveur temporaire n'a jamais répondu sur ${SERVEUR_URL}/sante"
    verdict 1 "suites Playwright"
else
    CODE_PW=0
    for suite in cablage vente inventaire stock rapports echappement rh exploitation; do
        ( cd "$RACINE/maquette/verification" && SERVEUR_URL="$SERVEUR_URL" npm run "$suite" )
        CODE_SUITE=$?
        verdict "$CODE_SUITE" "  suite $suite"
        [ "$CODE_SUITE" -ne 0 ] && CODE_PW=1
    done
fi

kill "$PID_SERVEUR" 2>/dev/null
wait "$PID_SERVEUR" 2>/dev/null
PID_SERVEUR=""
rm -f "$CONFIG_TEMP"

titre "5. Base laissée propre (jeu d'essai rechargé)"
"$PSQL" -d "$BASE_TEST" -q -v ON_ERROR_STOP=1 -f "$RACINE/db/tests/00_jeu_essai.sql" >/dev/null
verdict $? "jeu d'essai final"

titre "BILAN"
if [ "$ETAPES_KO" -eq 0 ]; then
    echo "Toutes les étapes sont passées."
    exit 0
else
    echo "$ETAPES_KO étape(s) en échec — voir le détail ci-dessus."
    exit 1
fi
