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
#   4. démarrage temporaire d'uvicorn, puis les 13 suites Playwright de
#      maquette/verification/ qui n'exigent qu'un serveur réel sur
#      SERVEUR_URL (routes, cablage, vente, stock, rapports, inventaire, ux,
#      comptes, caisse, rh, exploitation, echappement, roles — cycle 71,
#      écart C13-02 : la liste était restée à 8 suites alors que 13
#      existent ; la correspondance complète suites↔chantiers est dans
#      maquette/verification/SUITES_CHANTIERS.md) — PAS `affichage`/`flux`,
#      suites héritées du mode statique, inutilisables sur écrans connectés
#      (backend requis, limite documentée depuis le cycle 59)
#   5. arrêt du serveur temporaire, jeu d'essai rechargé une dernière fois
#      pour laisser la base dans un état propre
#
# Usage (depuis la racine du dépôt, PostgreSQL de dev déjà démarré — voir
# db/outils/demarrer_pg.ps1) :
#   PSQL=... PG_DUMP=... PGHOST=... PGPORT=... PGUSER=... PGPASSWORD=... \
#   PYTHON=... PORT_SERVEUR=8010 \
#   bash db/outils/verifier_tout.sh
#
# Vérification de cible seule (aucune suite lancée, aucun fichier créé) :
#   PGHOST=... PGPORT=... BASE_TEST=quincaillerie_... \
#   bash db/outils/verifier_tout.sh --verifier-cible
#
# Sort en erreur (code 1) dès qu'une étape échoue ; le serveur temporaire et
# le jeu d'essai sont malgré tout nettoyés (piège trap).
# ============================================================================
set -uo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PSQL="${PSQL:-psql}"
PG_DUMP="${PG_DUMP:-pg_dump}"

# Cycle 73 : un PSQL/PG_DUMP relatif hérité de l'appelant casse les suites
# Playwright — `npm run` exécute chaque suite depuis maquette/verification/
# et les suites utilisent la variable telle quelle (spawnSync ENOENT sur
# 11 suites, constat réel du cycle 73). Absolutisation de tout chemin
# relatif existant depuis la racine ; sous Git Bash, conversion au format
# Windows (les suites Node n'interprètent pas les chemins /c/...). Sur la
# CI (psql dans le PATH, fichier inexistant relativement à la racine), la
# valeur est inchangée.
absolutiser_pour_node() {
    local valeur="$1"
    case "$valeur" in
        /*|[A-Za-z]:[\\/]*) : ;;
        *) if [ -f "$RACINE/$valeur" ]; then
               valeur="$RACINE/$valeur"
               command -v cygpath >/dev/null 2>&1 && valeur="$(cygpath -w "$valeur")"
           fi ;;
    esac
    printf '%s' "$valeur"
}
PSQL="$(absolutiser_pour_node "$PSQL")"
PG_DUMP="$(absolutiser_pour_node "$PG_DUMP")"
export PSQL PG_DUMP
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5433}"
export PGUSER="${PGUSER:-postgres}"
export PGPASSWORD="${PGPASSWORD:-qf_dev_local}"
export PGCLIENTENCODING="${PGCLIENTENCODING:-UTF8}"

PYTHON="${PYTHON:-$RACINE/server/.venv/Scripts/python.exe}"
PORT_SERVEUR="${PORT_SERVEUR:-8010}"
SERVEUR_URL="http://127.0.0.1:${PORT_SERVEUR}"
REPERTOIRE_TEMPORAIRE="${TEMP:-${TMPDIR:-/tmp}}"
BASE_TEST="${BASE_TEST:-quincaillerie_test}"
SCHEMA_ORIGINE="$RACINE/QuincaillerieFranck_Test/creation_base_donnees.sql"

# ---------------------------------------------------------------------------
# Garde-fous de cible (revue #103, R2).
#
# Cette suite est DESTRUCTIVE : elle recrée BASE_TEST, recharge le jeu d'essai
# et l'étape 7 de la suite SQL supprime/recrée des rôles GLOBAUX au serveur.
# Elle doit donc refuser toute cible qui n'est pas une base de test locale :
#   - nom « quincaillerie_<suffixe> » (la production documentée est
#     « quincaillerie », sans suffixe) ;
#   - hôte loopback uniquement ;
#   - hôte, port ET nom réellement atteints vérifiés par le serveur lui-même,
#     pas seulement supposés depuis l'environnement.
# ---------------------------------------------------------------------------
valider_nom_base_test() {
    if [[ ! "$BASE_TEST" =~ ^quincaillerie_[a-z0-9][a-z0-9_]*$ ]]; then
        echo "ERREUR : '$BASE_TEST' n'est pas une base de test attendue" >&2
        echo "         (nom requis : quincaillerie_<suffixe> ; la base de production 'quincaillerie' est refusée)." >&2
        exit 1
    fi
}

valider_parametres_cible() {
    if [[ ! "$PGPORT" =~ ^[0-9]+$ ]] || (( PGPORT < 1 || PGPORT > 65535 )); then
        echo "ERREUR : port PostgreSQL invalide : '$PGPORT'." >&2
        exit 1
    fi
    case "$PGHOST" in
        127.0.0.1|localhost|::1) : ;;
        *)
            echo "ERREUR : hôte PostgreSQL '$PGHOST' refusé : les tests destructifs" >&2
            echo "         ne s'exécutent que sur une instance locale (loopback)." >&2
            exit 1
            ;;
    esac
}

# Vérifiée AVANT l'étape 1 (destructive) : l'instance annoncée doit être
# celle qui répond réellement, sur le bon port et en local. Une configuration
# ambiguë (PGPORT ignoré par un service, redirection, mauvaise instance) doit
# arrêter avant toute suppression ou recréation de base.
verifier_identite_serveur() {
    valider_parametres_cible

    local identite
    if ! identite="$("$PSQL" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -tAc \
        "SELECT current_database() || '|' || COALESCE(host(inet_server_addr()), 'local') || '|' || inet_server_port();" 2>&1)"; then
        echo "ERREUR : instance PostgreSQL injoignable ($PGHOST:$PGPORT) :" >&2
        echo "$identite" >&2
        exit 1
    fi

    local base_effective hote_effectif port_effectif
    IFS='|' read -r base_effective hote_effectif port_effectif <<< "$identite"
    if [ "$base_effective" != "postgres" ] || [ "$port_effectif" != "$PGPORT" ]; then
        echo "ERREUR : identité de l'instance incohérente." >&2
        echo "         demandé : instance locale sur $PGHOST:$PGPORT" >&2
        echo "         atteint : $base_effective sur $hote_effectif:$port_effectif" >&2
        exit 1
    fi
    case "$hote_effectif" in
        127.0.0.1|::1|local) : ;;
        *)
            echo "ERREUR : l'instance joignable ($hote_effectif) n'est pas locale." >&2
            exit 1
            ;;
    esac
    echo ">>> instance de test vérifiée : $hote_effectif:$port_effectif"
}

verifier_identite_cible() {
    valider_parametres_cible

    local identite
    if ! identite="$("$PSQL" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$BASE_TEST" -tAc \
        "SELECT current_database() || '|' || COALESCE(host(inet_server_addr()), 'local') || '|' || inet_server_port();" 2>&1)"; then
        echo "ERREUR : cible de test injoignable ($PGHOST:$PGPORT/$BASE_TEST) :" >&2
        echo "$identite" >&2
        exit 1
    fi

    local base_effective hote_effectif port_effectif
    IFS='|' read -r base_effective hote_effectif port_effectif <<< "$identite"
    if [ "$base_effective" != "$BASE_TEST" ] || [ "$port_effectif" != "$PGPORT" ]; then
        echo "ERREUR : identité de la cible incohérente." >&2
        echo "         demandé : $BASE_TEST sur $PGHOST:$PGPORT" >&2
        echo "         atteint : $base_effective sur $hote_effectif:$port_effectif" >&2
        exit 1
    fi
    case "$hote_effectif" in
        127.0.0.1|::1|local) : ;;
        *)
            echo "ERREUR : l'instance joignable ($hote_effectif) n'est pas locale." >&2
            exit 1
            ;;
    esac
    echo ">>> cible de test vérifiée : $base_effective sur $hote_effectif:$port_effectif"
}

if [ "${1:-}" = "--verifier-cible" ]; then
    valider_nom_base_test
    verifier_identite_serveur
    verifier_identite_cible
    exit 0
fi
valider_nom_base_test
verifier_identite_serveur

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
    [ -n "${CONFIG_TEMP:-}" ] && rm -f "$CONFIG_TEMP"
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
    # config.ini est gitignoré : s'il est absent du checkout (worktree
    # propre), repli sur la valeur de développement par défaut (celle des
    # tests conftest/CI) plutôt qu'un mot de passe VIDE (trou trouvé le
    # 2026-10-23, opération 100 % Lot B).
    MOT_DE_PASSE_QF_APP="$(sed -n 's/^password *= *//p' "$RACINE/server/config.ini" 2>/dev/null | head -1)"
    if [ -z "$MOT_DE_PASSE_QF_APP" ]; then
        MOT_DE_PASSE_QF_APP="qf_app_dev_local"
    fi
    "$PSQL" -d postgres -q -c "ALTER ROLE qf_app WITH PASSWORD '${MOT_DE_PASSE_QF_APP}';" >/dev/null
    "$PSQL" -d "$BASE_TEST" -q -v ON_ERROR_STOP=1 -f "$RACINE/db/tests/00_jeu_essai.sql" >/dev/null
}

# ---------------------------------------------------------------------------
titre "1. Suite SQL complète (db/tests/executer_tests.sh)"
# BASE_TEST : executer_tests.sh retombe sinon sur son défaut quincaillerie_test
# et recréerait une AUTRE base que celle vérifiée ici (trou d'isolation de la
# revue #103, R2).
BASE_TEST="$BASE_TEST" PSQL="$PSQL" PG_DUMP="$PG_DUMP" bash "$RACINE/db/tests/executer_tests.sh"
verdict $? "suite SQL"

titre "2. Reconstruction de $BASE_TEST (supprimée par l'étape 7 de la suite SQL)"
recreer_base_test
verdict $? "base reconstruite"
# La base vient d'être recréée : on vérifie MAINTENANT que l'hôte, le port et
# le nom effectivement atteints sont ceux annoncés, avant que pytest et les
# suites Playwright ne la modifient.
verifier_identite_cible

# ---------------------------------------------------------------------------
# Configuration éphémère commune aux étapes 3 (pytest) et 4 (uvicorn) :
# UNIQUEMENT pour ce process de vérification — jamais le vrai config.ini,
# jamais commitée.
#
# config.ini de dev limite à 10 connexions/minute (protection anti-force
# brute, voir securite.py) — bien trop bas pour enchaîner 13 suites qui se
# reconnectent chacune plusieurs fois en quelques minutes (trouvé en
# écrivant ce script : les suites 2 et suivantes échouaient toutes avec
# une session nulle, silencieusement rejetées par le serveur). La limite
# est relevée au même niveau que les tests pytest (conftest.py : 1000/min).
#
# dbname : le serveur doit viser BASE_TEST, pas la base écrite en dur
# dans config.ini — même trou d'isolation que QF_TEST_DBNAME ci-dessous
# (2026-10-23, opération 100 % Lot B). Le vrai config.ini peut même être
# absent du checkout (gitignoré) : le modèle est reconstruit depuis les
# valeurs par défaut du script, pas copié.
#
# QF_CONFIG sert AUSSI à pytest : importer app.main exécute
# `app = creer_application()` AU NIVEAU DU MODULE (app/main.py, gestion du
# point d'entrée uvicorn), qui appelle charger_config() — dans un worktree
# propre sans config.ini (gitignoré), l'import échoue et TOUT test utilisant
# la fixture `app` sort en ERROR. Trouvé par exécution le 2026-10-23
# (opération 100 % Lot B) : 55 passed / 314 errors, dont 313 ne sont que la
# cascade interne de pytest (AssertionError dans fixtures.py) après la
# première ErreurConfiguration — le mur d'erreurs n'a qu'une seule cause.
MOT_DE_PASSE_QF_APP="${MOT_DE_PASSE_QF_APP:-qf_app_dev_local}"
if [ -f "$RACINE/server/config.ini" ]; then
    MOT_DE_PASSE_QF_APP="$(sed -n 's/^password *= *//p' "$RACINE/server/config.ini" | head -1)"
fi
CONFIG_TEMP="$(mktemp)"
# secret_key factice de test, celle-là même que la CI écrit dans son
# config.ini éphémère (voir .github/workflows/ci.yml) — les jetons ne
# vivent que le temps de ce process de vérification.
cat > "$CONFIG_TEMP" <<EOF
[database]
host = ${PGHOST}
port = ${PGPORT}
dbname = ${BASE_TEST}
user = qf_app
password = ${MOT_DE_PASSE_QF_APP}

[api]
secret_key = ${SECRET_KEY_TEST:-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef}
duree_session_minutes = 480
tentatives_max_par_minute = 1000
EOF

titre "3. Suite pytest du serveur"
# --basetemp : le dossier par défaut %TEMP%\pytest-of-USER\pytest-current
# contient un symlink résiduel inaccessibles sans élévation (constat du
# cycle 56, BLOCKED_TECHNICAL signalé au propriétaire) — pytest crashe en
# nettoyage de fin de session avec PermissionError et rend un code 1 alors
# que les tests passent. Le basetemp dédié contourne ce défaut d'environnement,
# comme chaque cycle le fait depuis le cycle 57.
# QF_TEST_DBNAME : conftest.py lit cette variable pour choisir SA base
# (défaut quincaillerie_test) — sans cet export, l'étape pytest viserait
# la base par défaut même quand BASE_TEST est surchargé, et deux agents
# travaillant en parallèle s'écraseraient mutuellement leurs données de
# test (trou d'isolation trouvé par exécution le 2026-10-23, opération
# 100 % Lot B).
# QF_TEST_PGPORT/QF_TEST_PGHOST (revue #103, R2) : conftest.py lit SON port
# dans QF_TEST_PGPORT (défaut 5433), indépendamment de PGPORT. Sans ces
# exports, un PGPORT=5558 configuré ici faisait viser 5433 aux
# réinitialisations pytest, alors que le serveur applicatif visait 5558.
( cd "$RACINE/server" && QF_TEST_DBNAME="$BASE_TEST" QF_TEST_PGHOST="$PGHOST" \
    QF_TEST_PGPORT="$PGPORT" QF_CONFIG="$CONFIG_TEMP" \
    "$PYTHON" -m pytest -q --basetemp "$REPERTOIRE_TEMPORAIRE/verifier_tout_pytest" )
verdict $? "pytest"

titre "4. Suites Playwright (serveur réel, 13 suites — SUITES_CHANTIERS.md)"
titre "4. Suites Playwright (serveur réel, 13 suites — SUITES_CHANTIERS.md)"
# Le serveur temporaire reçoit la configuration éphémère commune créée
# avant l'étape 3 (base BASE_TEST, limite de débit relevée à 1000/min).
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
    # PGDATABASE_PISTE : les suites réinitialisent le jeu d'essai elles-
    # mêmes (chaque fichier .mjs le documente dans son en-tête) et tombent
    # par défaut sur quincaillerie_test ; l'exporter ici lie les réinitialisations
    # à BASE_TEST si un appelant surcharge cette dernière.
    # Délai maximal par suite (DELAI_SUITE_S, défaut 600 s) : une suite qui
    # se bloque ne doit pas immobiliser la régression — constat réel du
    # cycle 71, la suite comptes, terminée mais sans navigateur.close()
    # (défaut corrigé), a rendu son code de sortie jamais : 20 minutes
    # d'attente avant intervention manuelle. Même philosophie que
    # executer_suites_reelles.sh (PR #79, cycle 62). Code 124 = délai dépassé.
    CODE_PW=0
    DELAI_SUITE_S="${DELAI_SUITE_S:-600}"
    export PGDATABASE_PISTE="$BASE_TEST"
    for suite in routes cablage vente stock rapports inventaire ux comptes caisse rh exploitation echappement roles; do
        ( cd "$RACINE/maquette/verification" && \
          SERVEUR_URL="$SERVEUR_URL" timeout "$DELAI_SUITE_S" npm run "$suite" )
        CODE_SUITE=$?
        if [ "$CODE_SUITE" -eq 124 ]; then
            echo ">>> suite $suite : ÉCHEC (délai de ${DELAI_SUITE_S}s dépassé, processus tué)"
            ETAPES_KO=$((ETAPES_KO + 1))
            CODE_PW=1
            continue
        fi
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
