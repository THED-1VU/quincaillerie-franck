#!/usr/bin/env bash
# ============================================================================
# TEST DE CONCURRENCE — deux ventes du même article, au même instant
# ----------------------------------------------------------------------------
# Le scénario du dossier de recette : un article à stock = 1, deux postes qui
# valident presque simultanément. Ce test se fait forcément avec DEUX sessions
# distinctes : une seule session ne peut pas se concurrencer elle-même.
#
# Mis à jour au cycle 6 (chantier C5) : le propriétaire a tranché le point e
# de l'addendum — une vente déjà encaissée n'est JAMAIS bloquée pour cause de
# stock insuffisant (voir db/migrations/011_ventes_fiscalite_anti_survente.sql
# et ADDENDUM_CAHIER_DES_CHARGES.md, « Ce que devient le test de concurrence »).
# Ce qui reste vérifié, et qui ne dépend d'AUCUNE décision métier :
#   * le décrément est toujours SÉRIALISÉ (verrou de ligne) : les deux
#     sessions ne peuvent pas lire le même stock et l'écrire toutes les deux ;
#   * le stock ne devient JAMAIS négatif ;
#   * AUCUNE marchandise n'est inventée : un seul mouvement de sortie réel
#     (1 unité, celle qui existait vraiment), le reste est un ÉCART consigné,
#     jamais une seconde sortie fictive.
# Ce qui est NOUVEAU par rapport au cycle 2 : les DEUX ventes réussissent
# (plus de « perdante ») ; celle qui arrive après que le stock est tombé à 0
# produit un écart de 1 unité, rattaché à sa propre vente — pas un refus.
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

echo "===== Préparation : article 4 « Article rare », stock ramené à 1, deux ventes-test créées ====="
"$PSQL" -q -c "UPDATE articles SET quantite_stock = 1 WHERE id = 4;"
VENTE_A=$("$PSQL" -q -At -c "INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc) VALUES (1, 4, 'en_attente', 0, 0, 0, 0) RETURNING id;")
VENTE_B=$("$PSQL" -q -At -c "INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc) VALUES (1, 4, 'en_attente', 0, 0, 0, 0) RETURNING id;")
echo "vente-test A (id=$VENTE_A), vente-test B (id=$VENTE_B)"

# Les scripts sont passés par FICHIER (-f) et non par entrée standard :
# sous Git Bash, un « document en ligne » vers un processus d'arrière-plan
# n'est pas fiable. Double-quoté (pas '...') : $VENTE_A/$VENTE_B doivent être
# substitués par bash avant l'écriture du fichier.
cat > "$TMP/poste_a.sql" <<SQL
BEGIN;
SELECT * FROM decrementer_stock_vente(4, 1, 4, $VENTE_A, 'vente poste A') AS resultat_a;
SELECT pg_sleep(3);   -- garde le verrou : simule la saisie du poste A
COMMIT;
SQL

cat > "$TMP/poste_b.sql" <<SQL
BEGIN;
SELECT * FROM decrementer_stock_vente(4, 1, 4, $VENTE_B, 'vente poste B') AS resultat_b;
COMMIT;
SQL

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
NB_ECARTS=$("$PSQL" -At -c "SELECT count(*) FROM ecarts_stock_ventes WHERE vente_id IN ($VENTE_A, $VENTE_B);")
SOMME_ECARTS=$("$PSQL" -At -c "SELECT COALESCE(sum(quantite_manquante), 0) FROM ecarts_stock_ventes WHERE vente_id IN ($VENTE_A, $VENTE_B);")

echo
echo "===================== BILAN ====================="
echo "stock final                  : $STOCK_FINAL"
echo "mouvements de sortie ajoutés : $NB_SORTIES"
echo "écarts consignés             : $NB_ECARTS (soit $SOMME_ECARTS unité(s))"
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

verifier "les DEUX ventes réussissent (plus de blocage, addendum point e)" \
         "$( [ "$CODE_A" -eq 0 ] && [ "$CODE_B" -eq 0 ] && echo oui || echo non )" "oui"
verifier "le stock n'est jamais négatif, il tombe à 0" "$STOCK_FINAL" "0"
verifier "une seule marchandise réelle n'est sortie qu'une fois (1 mouvement)" "$NB_SORTIES" "1"
verifier "un seul écart consigné, pour la vente arrivée après coup"          "$NB_ECARTS"   "1"
verifier "l'écart consigné vaut exactement 1 unité (rien d'inventé)"        "$SOMME_ECARTS" "1"
verifier "aucun message de refus : la saisie n'est jamais bloquée" \
         "$(grep -qi 'stock insuffisant' "$TMP/a.out" "$TMP/b.out" && echo trouve || echo absent)" "absent"

echo
if [ "$ECHECS" -eq 0 ]; then
    echo "Concurrence : 6/6 — aucune survente possible, aucun blocage (point e)."
    exit 0
else
    echo "Concurrence : $ECHECS contrôle(s) en échec."
    exit 1
fi
