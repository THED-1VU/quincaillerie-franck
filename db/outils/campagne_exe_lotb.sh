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
PSQL="${PSQL:-$RACINE/_pgdev/pgsql/bin/psql.exe}"
BASE_EXE="${BASE_EXE:-quincaillerie_lotbexe}"
PORT_EXE="${PORT_EXE:-8000}"
DELAI_SUITE_S="${DELAI_SUITE_S:-600}"
EXE="$RACINE/server/fabrication/dist/Akuma.exe"
export PGPASSWORD="${PGPASSWORD:-qf_dev_local}"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5433}"
export PGUSER="${PGUSER:-postgres}"

# Toute campagne dont une dependance manque doit s'arreter AVANT la moindre
# action destructive (revue #103, R1 complement) : sinon la suppression de la
# base jetable et le rapport final partiraient d'un environnement incomplet.
if [ ! -f "$EXE" ]; then
    echo "ERREUR : $EXE introuvable (construire d'abord via construire.ps1)."
    exit 1
fi
for dependance in \
    "$PSQL" \
    "$RACINE/db/outils/migrer.sh" \
    "$RACINE/db/outils/definir_mot_de_passe_app.sql" \
    "$RACINE/db/tests/00_jeu_essai.sql" \
    "$RACINE/QuincaillerieFranck_Test/creation_base_donnees.sql"; do
    if [ ! -f "$dependance" ]; then
        echo "ERREUR : dépendance manquante : $dependance — campagne annulée avant toute action."
        exit 1
    fi
done
for outil in curl npm; do
    if ! command -v "$outil" >/dev/null 2>&1; then
        echo "ERREUR : dépendance manquante : $outil introuvable dans le PATH — campagne annulée avant toute action."
        exit 1
    fi
done
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
CONFIG_TEMP=""
DB_CREEE=0
BASE_NETTOYEE=0
NETTOYAGE_KO=0

# Le nettoyage de la base est aussi un verdict : une base jetable qui survit
# a la campagne est un echec, jamais un detail (revue #103, R1 complement).
nettoyer_base() {
    if [ "$BASE_NETTOYEE" -eq 1 ] || [ "$DB_CREEE" -eq 0 ]; then
        BASE_NETTOYEE=1
        return 0
    fi
    if "$PSQL" -d postgres -c "DROP DATABASE IF EXISTS ${BASE_EXE};" >/dev/null 2>&1; then
        DB_CREEE=0
        BASE_NETTOYEE=1
        return 0
    fi
    NETTOYAGE_KO=1
    return 1
}

# Installe AVANT toute creation : une sortie anticipee (preparation en echec,
# EXE muet) doit laisser le poste propre — base jetable supprimee, config
# temporaire effacee, Akuma arrete.
nettoyer() {
    taskkill //F //IM Akuma.exe >/dev/null 2>&1
    rm -f "$CONFIG_TEMP"
    nettoyer_base || true
}
trap nettoyer EXIT

verdict() {
    if [ "$1" -eq 0 ]; then
        echo ">>> $2 : OK"
    else
        echo ">>> $2 : ÉCHEC (code $1)"
        ETAPES_KO=$((ETAPES_KO + 1))
    fi
}

# La preparation est un prealable : poursuivre apres son premier echec
# produirait des suites jouees sur une base incomplete, donc un verdict sans
# valeur. On s'arrete et on rend un code non nul (revue #103, R1).
verdict_preparation() {
    if [ "$1" -eq 0 ]; then
        echo ">>> $2 : OK"
        return 0
    fi
    echo ">>> $2 : ÉCHEC (code $1)"
    echo ">>> Campagne interrompue : la préparation a échoué ; aucun résultat de suite ne serait fiable."
    ETAPES_KO=$((ETAPES_KO + 1))
    exit 1
}

titre "1. Base jetable ${BASE_EXE} (schéma d'origine + migrations + jeu d'essai)"
"$PSQL" -d postgres -c "DROP DATABASE IF EXISTS ${BASE_EXE};" >/dev/null 2>&1
verdict_preparation $? "suppression base précédente"
"$PSQL" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${BASE_EXE};"
verdict_preparation $? "création base"
DB_CREEE=1
"$PSQL" -d "$BASE_EXE" -v ON_ERROR_STOP=1 -q \
    -f "$RACINE/QuincaillerieFranck_Test/creation_base_donnees.sql"
verdict_preparation $? "schéma d'origine"
( cd "$RACINE" && PSQL="$PSQL" PGDATABASE="$BASE_EXE" bash db/outils/migrer.sh appliquer >/dev/null )
verdict_preparation $? "migrations"
"$PSQL" -d "$BASE_EXE" -v ON_ERROR_STOP=1 -q -f "$RACINE/db/tests/00_jeu_essai.sql"
verdict_preparation $? "jeu d'essai"
"$PSQL" -d "$BASE_EXE" -v ON_ERROR_STOP=1 -q \
    -v mdp="'qf_app_dev_local'" -f "$RACINE/db/outils/definir_mot_de_passe_app.sql"
verdict_preparation $? "mot de passe qf_app"

titre "2. Lancement de Akuma.exe --sans-navigateur sur le port ${PORT_EXE}"
CONFIG_TEMP="$(mktemp)" || { echo "ERREUR : création du fichier de configuration temporaire impossible."; exit 1; }
cat > "$CONFIG_TEMP" <<EOF
[database]
host = ${PGHOST}
port = ${PGPORT}
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
    exit 1
fi
echo ">>> Akuma.exe répond sur :${PORT_EXE}/sante"

titre "3. Les 13 suites Playwright contre l'exe"
export PGDATABASE_PISTE="$BASE_EXE"
SERVEUR_URL="http://127.0.0.1:${PORT_EXE}"
for suite in routes cablage vente stock rapports inventaire ux comptes caisse rh exploitation echappement roles; do
    ( cd "$RACINE/maquette/verification" && \
      SERVEUR_URL="$SERVEUR_URL" timeout "$DELAI_SUITE_S" npm run "$suite" )
    CODE_SUITE=$?
    if [ "$CODE_SUITE" -eq 124 ]; then
        echo ">>> suite $suite : ÉCHEC (délai de ${DELAI_SUITE_S}s dépassé)"
        ETAPES_KO=$((ETAPES_KO + 1)); continue
    fi
    verdict "$CODE_SUITE" "  suite $suite"
done

titre "Nettoyage de la base jetable"
if nettoyer_base; then
    echo ">>> nettoyage : OK"
else
    echo ">>> nettoyage : ÉCHEC — la base ${BASE_EXE} n'a pas pu être supprimée."
    ETAPES_KO=$((ETAPES_KO + 1))
fi

titre "BILAN"
echo "Journal de l'exe : $JOURNAL_EXE"
if [ "$ETAPES_KO" -eq 0 ]; then
    echo "Toutes les étapes sont passées (base ${BASE_EXE}, exe ${PORT_EXE})."
    exit 0
else
    echo "${ETAPES_KO} étape(s) en échec — voir le détail ci-dessus."
    exit 1
fi
