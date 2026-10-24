#!/usr/bin/env bash
# ============================================================================
# Campagne Lot B (chantier C8) : les 13 suites Playwright CONTRE L'EXÉCUTABLE
# Akuma.exe reconstruit sur la branche operation-100-lot-b (procédure établie
# cycle 63 / cycle 73, rejouée ici pour prouver la compatibilité Windows du
# code du Lot B — défauts de packaging invisibles de la régression uvicorn).
#
# Isolation (mission Lot B : jamais de test concurrent sur une base partagée) :
#   - base JETABLE dédiée quincaillerie_lotbexe (jamais quincaillerie_lotb,
#     jamais quincaillerie_test — Codex), supprimée en fin de script ;
#   - port 8000 (port par défaut du lanceur, vérifié libre avant démarrage) ;
#   - QF_CONFIG vers un fichier éphémère supprimé en fin de script ;
#   - QF_FICHIER_ETAT_SAUVEGARDE : exigence documentée du cycle 63 — en mode
#     figé, RACINE_DEPOT résout vers le dossier de l'exe ; sans cette
#     variable, le voyant sauvegarde chercherait _pgdev/ sous dist/ et la
#     suite exploitation échouerait pour une raison d'installation, pas de
#     code.
#
# À exécuter UNIQUEMENT quand aucune autre campagne ne touche le serveur
# PostgreSQL 5433 (leçon du run 3 : un pg_restore parallèle a fait échouer
# une suite Playwright sur un flake de connexion).
# ============================================================================
set -uo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PSQL="$RACINE/_pgdev/pgsql/bin/psql.exe"
BASE_EXE="${BASE_EXE:-quincaillerie_lotbexe}"
PORT_EXE="${PORT_EXE:-8000}"
DELAI_SUITE_S="${DELAI_SUITE_S:-600}"
EXE="$RACINE/server/fabrication/dist/Akuma.exe"
export PGPASSWORD="${PGPASSWORD:-qf_dev_local}"
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=postgres

if [ ! -f "$EXE" ]; then
    echo "ERREUR : $EXE introuvable (construire d'abord via construire.ps1)."
    exit 1
fi
if netstat -ano | grep -q "LISTENING" && netstat -ano | grep ":${PORT_EXE} " | grep -q LISTENING; then
    echo "ERREUR : le port ${PORT_EXE} est déjà occupé — arrêter le processus avant la campagne."
    exit 1
fi
if tasklist | grep -qi "Akuma.exe"; then
    echo "ERREUR : un Akuma.exe tourne déjà — l'arrêter avant la campagne."
    exit 1
fi

titre() { echo; echo "############################################################"; echo "# $*"; echo "############################################################"; }
ETAPES_KO=0
verdict() {
    if [ "$1" -eq 0 ]; then
        echo ">>> $2 : OK"
    else
        echo ">>> $2 : ÉCHEC (code $1)"
        ETAPES_KO=$((ETAPES_KO + 1))
    fi
}

titre "1. Base jetable ${BASE_EXE} (schéma d'origine + migrations + jeu d'essai)"
"$PSQL" -d postgres -c "DROP DATABASE IF EXISTS ${BASE_EXE};" >/dev/null 2>&1
"$PSQL" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${BASE_EXE};"
verdict $? "création base"
"$PSQL" -d "$BASE_EXE" -v ON_ERROR_STOP=1 -q \
    -f "$RACINE/QuincaillerieFranck_Test/creation_base_donnees.sql"
verdict $? "schéma d'origine"
( cd "$RACINE" && PSQL="$PSQL" PGDATABASE="$BASE_EXE" bash db/outils/migrer.sh appliquer >/dev/null )
verdict $? "migrations"
"$PSQL" -d "$BASE_EXE" -v ON_ERROR_STOP=1 -q -f "$RACINE/db/tests/00_jeu_essai.sql"
verdict $? "jeu d'essai"
"$PSQL" -d "$BASE_EXE" -v ON_ERROR_STOP=1 -q \
    -v mdp="'qf_app_dev_local'" -f "$RACINE/db/outils/definir_mot_de_passe_app.sql"
verdict $? "mot de passe qf_app"

titre "2. Lancement de Akuma.exe --sans-navigateur sur le port ${PORT_EXE}"
CONFIG_TEMP="$(mktemp)"
cat > "$CONFIG_TEMP" <<EOF
[database]
host = 127.0.0.1
port = 5433
dbname = ${BASE_EXE}
user = qf_app
password = qf_app_dev_local

[api]
secret_key = 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
duree_session_minutes = 480
tentatives_max_par_minute = 1000
EOF
JOURNAL_EXE="$RACINE/server/fabrication/dist/campagne_lotb_exe.log"
( cd "$(dirname "$EXE")" && QF_CONFIG="$CONFIG_TEMP" \
    QF_FICHIER_ETAT_SAUVEGARDE="$RACINE/_pgdev/sauvegardes/dernier_etat_sauvegarde.json" \
    ./Akuma.exe --sans-navigateur > "$JOURNAL_EXE" 2>&1 ) &
PID_EXE=$!

PRET=1
for _ in $(seq 1 60); do
    if curl -s -o /dev/null "http://127.0.0.1:${PORT_EXE}/sante"; then PRET=0; break; fi
    sleep 1
done
if [ "$PRET" -ne 0 ]; then
    echo ">>> Akuma.exe n'a jamais répondu sur http://127.0.0.1:${PORT_EXE}/sante"
    echo "--- journal de l'exe ---"; cat "$JOURNAL_EXE"
    rm -f "$CONFIG_TEMP"; taskkill //F //IM Akuma.exe >/dev/null 2>&1
    exit 1
fi
echo ">>> Akuma.exe répond sur :${PORT_EXE}/sante"

nettoyer() {
    taskkill //F //IM Akuma.exe >/dev/null 2>&1
    rm -f "$CONFIG_TEMP"
    "$PSQL" -d postgres -c "DROP DATABASE IF EXISTS ${BASE_EXE};" >/dev/null 2>&1
}
trap nettoyer EXIT

titre "3. Les 13 suites Playwright contre l'exe"
export PGDATABASE_PISTE="$BASE_EXE"
SERVEUR_URL="http://127.0.0.1:${PORT_EXE}"
CODE_PW=0
for suite in routes cablage vente stock rapports inventaire ux comptes caisse rh exploitation echappement roles; do
    ( cd "$RACINE/maquette/verification" && \
      SERVEUR_URL="$SERVEUR_URL" timeout "$DELAI_SUITE_S" npm run "$suite" )
    CODE_SUITE=$?
    if [ "$CODE_SUITE" -eq 124 ]; then
        echo ">>> suite $suite : ÉCHEC (délai de ${DELAI_SUITE_S}s dépassé)"
        ETAPES_KO=$((ETAPES_KO + 1)); CODE_PW=1; continue
    fi
    verdict "$CODE_SUITE" "  suite $suite"
    [ "$CODE_SUITE" -ne 0 ] && CODE_PW=1
done

titre "BILAN"
if [ "$ETAPES_KO" -eq 0 ]; then
    echo "Toutes les étapes sont passées (base ${BASE_EXE}, exe ${PORT_EXE})."
else
    echo "${ETAPES_KO} étape(s) en échec — voir le détail ci-dessus."
fi
echo "Journal de l'exe : $JOURNAL_EXE"
exit "$CODE_PW"
