#!/usr/bin/env bash
# ============================================================================
# Exécute les 12 suites Playwright « serveur réel » avec un délai maximal par
# suite, et conserve un journal par suite (cycle 62, CI Playwright).
#
# Pourquoi ce script existe : en CI, une suite qui se bloque (constat du
# cycle 61 : navigateur jamais fermé, processus vivant après 26/26 contrôles)
# ne doit pas immobiliser le job jusqu'au timeout global sans indiquer LAQUELLE
# a échoué. Chaque suite reçoit donc son propre délai et son propre journal.
#
# `affichage` et `flux` sont volontairement EXCLUS : suites héritées du mode
# statique, inutilisables sur écrans connectés (backend requis, limite
# documentée depuis le cycle 59).
#
# Prérequis : serveur sur SERVEUR_URL et PostgreSQL joignables via `psql`
# (sur le PATH en CI, via _pgdev sur le poste Windows).
# Usage : bash maquette/verification/executer_suites_reelles.sh [dossier_journaux]
# ============================================================================
set -uo pipefail

ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOURNAUX="${1:-${JOURNAUX_PLAYWRIGHT:-$ICI/rapports-playwright}}"
DELAI="${DELAI_SUITE_S:-600}"

mkdir -p "$JOURNAUX"
RESUME="$JOURNAUX/synthese.txt"
: > "$RESUME"

# Ordre identique à la régression du cycle 61, pour des preuves comparables.
SUITES=(
  "routes:verifier-routes-appelees.mjs"
  "cablage:verifier-cablage.mjs"
  "vente:verifier-vente-reelle.mjs"
  "stock:verifier-stock-reel.mjs"
  "rapports:verifier-rapports-reel.mjs"
  "inventaire:verifier-inventaire-reel.mjs"
  "ux:verifier-ux-corrections.mjs"
  "comptes:verifier-comptes-reel.mjs"
  "caisse:verifier-caisse-reel.mjs"
  "rh:verifier-rh-reel.mjs"
  "exploitation:verifier-exploitation-reel.mjs"
  "echappement:verifier-echappement-html.mjs"
)

TOTAL=0
ECHECS=0

for entree in "${SUITES[@]}"; do
  NOM="${entree%%:*}"
  FICHIER="${entree#*:}"
  JOURNAL="$JOURNAUX/$NOM.log"
  echo "=== suite $NOM ($FICHIER) ==="
  timeout "$DELAI" node "$ICI/$FICHIER" > "$JOURNAL" 2>&1
  CODE=$?
  TOTAL=$((TOTAL + 1))
  DETAIL="$(grep -E '^(== [0-9]+/[0-9]+ contrôles réussis ==|Total : [0-9]+ contrôles, [0-9]+ échec\(s\)\.)$' "$JOURNAL" | tail -1)"
  if [ "$CODE" -eq 0 ]; then
    echo "OK    $NOM  ${DETAIL}" | tee -a "$RESUME"
  else
    if [ "$CODE" -eq 124 ]; then
      MESSAGE="délai de ${DELAI} s dépassé"
    else
      MESSAGE="code ${CODE}"
    fi
    echo "KO    $NOM  (${MESSAGE})  ${DETAIL}" | tee -a "$RESUME"
    echo "--- 40 dernières lignes de $JOURNAL ---" >&2
    tail -40 "$JOURNAL" >&2
    ECHECS=$((ECHECS + 1))
  fi
done

echo
echo "$((TOTAL - ECHECS))/$TOTAL suites réussies — journaux : $JOURNAUX"
[ "$ECHECS" -eq 0 ]
