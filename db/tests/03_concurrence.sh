#!/usr/bin/env bash
# ============================================================================
# TEST DE CONCURRENCE — deux ventes du même article, au même instant
# ----------------------------------------------------------------------------
# Le scénario du dossier de recette : un article à stock = 1, deux postes qui
# valident presque simultanément. Ce test se fait forcément avec DEUX sessions
# distinctes : une seule session ne peut pas se concurrencer elle-même.
#
# Ce qui est vérifié (et qui est déjà tranché) :
#   * le décrément est SÉRIALISÉ : les deux sessions ne peuvent pas lire le même
#     stock et l'écrire toutes les deux ;
#   * le stock ne devient JAMAIS négatif ;
#   * il ne reste qu'UN seul mouvement de sortie ;
#   * la session perdante reçoit un message explicite.
#
# Ce qui n'est PAS tranché et n'est donc PAS testé ici : ce que l'application
# doit faire de la seconde vente, puisqu'elle a déjà été encaissée au comptoir
# (refus, ou saisie autorisée avec écart à régulariser) — ADDENDUM, point e.
# La base se contente de garantir qu'aucune marchandise n'est inventée.
#
# Usage (depuis la racine du dépôt) :
#   PSQL=... PGHOST=... PGPORT=... PGUSER=... PGDATABASE=... \
#   bash db/tests/03_concurrence.sh
# ============================================================================
set -uo pipefail

PSQL="${PSQL:-psql}"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"
export PGDATABASE="${PGDATABASE:-quincaillerie_test}"
export PGCLIENTENCODING="${PGCLIENTENCODING:-UTF8}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Les scripts sont passés par FICHIER (-f) et non par entrée standard :
# sous Git Bash, un « document en ligne » vers un processus d'arrière-plan
# n'est pas fiable.
cat > "$TMP/poste_a.sql" <<'SQL'
BEGIN;
SELECT decrementer_stock_vente(4, 1, 4, 'vente poste A') AS stock_apres_A;
SELECT pg_sleep(3);   -- garde le verrou : simule la saisie du poste A
COMMIT;
SQL

cat > "$TMP/poste_b.sql" <<'SQL'
BEGIN;
SELECT decrementer_stock_vente(4, 1, 4, 'vente poste B') AS stock_apres_B;
COMMIT;
SQL

echo "===== Préparation : article 4 « Article rare », stock ramené à 1 ====="
"$PSQL" -q -c "UPDATE articles SET quantite_stock = 1 WHERE id = 4;"
AVANT_MVT=$("$PSQL" -At -c "SELECT count(*) FROM mouvements_stock WHERE article_id = 4;")
echo "stock initial                : $("$PSQL" -At -c 'SELECT quantite_stock FROM articles WHERE id = 4;')"
echo "mouvements déjà présents     : $AVANT_MVT"
echo

# --- Poste A : démarre, prend le verrou et le garde 3 secondes --------------
"$PSQL" -v ON_ERROR_STOP=1 -f "$TMP/poste_a.sql" > "$TMP/a.out" 2>&1 &
PID_A=$!

sleep 1   # laisse au poste A le temps de prendre le verrou

# --- Poste B : demande le même article pendant que A tient le verrou -------
"$PSQL" -v ON_ERROR_STOP=1 -f "$TMP/poste_b.sql" > "$TMP/b.out" 2>&1
CODE_B=$?

wait "$PID_A"
CODE_A=$?

echo "----- Poste A (code de sortie $CODE_A) -----"
cat "$TMP/a.out"
echo "----- Poste B (code de sortie $CODE_B) -----"
cat "$TMP/b.out"

STOCK_FINAL=$("$PSQL" -At -c "SELECT quantite_stock FROM articles WHERE id = 4;")
APRES_MVT=$("$PSQL" -At -c "SELECT count(*) FROM mouvements_stock WHERE article_id = 4;")
NB_SORTIES=$((APRES_MVT - AVANT_MVT))

echo
echo "===================== BILAN ====================="
echo "stock final                  : $STOCK_FINAL"
echo "mouvements de sortie ajoutés : $NB_SORTIES"
echo

ECHECS=0
verifier() {
    if [ "$2" = "$3" ]; then
        echo "[ok]    $1 (= $2)"
    else
        echo "[ÉCHEC] $1 : obtenu « $2 », attendu « $3 »"
        ECHECS=$((ECHECS + 1))
    fi
}

verifier "une seule des deux ventes aboutit" \
         "$( [ "$CODE_A" -eq 0 ] && [ "$CODE_B" -ne 0 ] && echo oui || echo non )" "oui"
verifier "le stock n'est jamais négatif, il tombe à 0" "$STOCK_FINAL" "0"
verifier "un seul mouvement de sortie enregistré"      "$NB_SORTIES"  "1"
verifier "la session perdante reçoit « stock insuffisant »" \
         "$(grep -qi 'stock insuffisant' "$TMP/b.out" && echo oui || echo non)" "oui"

echo
if [ "$ECHECS" -eq 0 ]; then
    echo "Concurrence : 4/4 — aucune survente possible."
    exit 0
else
    echo "Concurrence : $ECHECS contrôle(s) en échec."
    exit 1
fi
