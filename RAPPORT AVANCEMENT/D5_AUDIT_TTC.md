# D5 — Audit de la politique TTC (cycle 75-G, 2026-10-23)

Décision du propriétaire validée le 2026-10-23 : « les prix saisis sont TTC ;
le traitement fiscal est à confirmer avec le comptable avant tout import
réel ». Le présent audit établit ce que le code fait RÉELLEMENT aujourd'hui
(chaque point pointé dans le code et couvert par les tests d'exécution), puis
liste les questions à soumettre au comptable. AUCUN taux de TVA, AUCUNE règle
fiscale n'a été inventé ; la saisie TTC est conservée.

## 1. Ce que le code fait aujourd'hui (prouvé, pas supposé)

1. **Prix saisis TTC partout.** La saisie (écran `vente.html`, API `POST
   /ventes`) et le stockage considèrent `prix_unitaire` comme un prix TTC :
   le total de la vente est la somme des `prix_unitaire × quantité`, moins
   les remises (`server/app/routes/ventes.py:335-337`, remises
   `:344-361`). Aucun prix HT n'est jamais saisi ni déduit ligne à ligne.
2. **La TVA est extraite sur le TOTAL de la vente, jamais ligne à ligne.**
   `montant_tva = total_ttc × t / (100 + t)` arrondi au franc
   (ROUND_HALF_UP), puis `sous_total_ht = total_ttc − montant_tva`
   (`ventes.py:378-384`). Une seule extraction par vente — c'est ce qui
   évite les écarts d'un franc entre lignes (exigence addendum, commentée
   en tête du bloc `:334`).
3. **Aucun taux inventé — le taux vient de la base ou vaut zéro.**
   `taux_tva` est un paramètre PostgreSQL (migration 006) : valeur par
   défaut `0` (= aucune TVA appliquée, fonctionnement valide par
   construction), lu à chaque vente et à `GET /ventes/parametres`
   (`ventes.py:94-95, 185-186`). La fonction `parametre_numerique()` REFUSE
   la valeur sentinelle `a_definir` : l'application s'arrête franchement au
   lieu d'appliquer en silence une règle inventée (en-tête de la migration
   006). Sont également à l'état sentinelle `a_definir` + `a_decider =
   TRUE` : `regime_fiscal`, `prix_saisis_ttc`,
   `boutique_numero_contribuable`, `arrondi_montants`.
4. **Reçu et rapports n'exposent que des valeurs déduites, jamais saisies.**
   `sous_total_ht`, `taux_tva`, `montant_tva`, `total_ttc` sont calculés à
   l'encaissement et écrits dans `ventes` (`ventes.py:432-440`) ; le reçu
   PDF (`ventes.py:543-552`) et l'export ventes (`rapports.py:280`)
   réaffichent ces valeurs stockées. Personne ne saisit de valeur fiscale à
   la main.

## 2. Questions à faire confirmer par le comptable AVANT tout import réel

| # | Question | Paramètre concerné |
|---|---|---|
| Q1 | Régime fiscal réel de la quincaillerie : impôt libératoire, simplifié ou réel (assujetti TVA) ? | `regime_fiscal` (a_definir) |
| Q2 | Si assujetti : le taux de TVA applicable et sa valeur exacte (aujourd'hui : 0 = aucune TVA appliquée) | `taux_tva` (0) |
| Q3 | Les prix négociés avec le client sont-ils bien TTC ? (hypothèse de travail depuis le cycle 6, jamais confirmée par le comptable) | `prix_saisis_ttc` (a_definir) |
| Q4 | Les documents (reçu/facture, exports) doivent-ils présenter une ventilation HT **ligne à ligne**, ou la ventilation globale actuelle (HT / TVA / TTC de la vente) suffit-elle ? | présentation — écart C1-02 |
| Q5 | Le numéro de contribuable doit-il figurer sur les factures, et quelles mentions fiscales obligatoires s'attachent à la numérotation ? | `boutique_numero_contribuable` (a_definir) |
| Q6 | Méthode d'arrondi au franc CFA retenue (aujourd'hui : ROUND_HALF_UP appliqué à la TVA extraite du total) | `arrondi_montants` (a_definir) |

## 3. Conséquences d'un changement (pour arbitrer en connaissance de cause)

- **Changer le taux** : simple mise à jour du paramètre en base — pris en
  compte à l'encaissement SUIVANT ; les ventes déjà enregistrées conservent
  leurs valeurs d'origine (immutabilité, migrations 004/005).
- **Passer d'une saisie TTC à une saisie HT** : migration de données +
  réécriture des écrans et des reçus — c'est précisément pourquoi la
  décision D5 exige la confirmation du comptable AVANT tout import réel du
  stock.
- **Ventilation ligne à ligne** : pur ajout de PRÉSENTATION (colonne HT par
  ligne recalculée et affichée) — aucune règle fiscale nouvelle, aucun
  recalcul des montants stockés.

## 4. Ce que ce cycle n'a PAS fait (limites assumées)

- Aucun taux de TVA ni aucune règle fiscale inventés ; aucune valeur
  `a_definir` basculée — les migrations et le seed restent à l'état
  sentinelle (les 5 lignes `a_decider = TRUE` de C6-01 attendent leurs
  arbitrages, dont D5).
- Aucun import de données réelles (limite §7 du cycle 75).
- Aucune modification d'écran ni de calcul : l'audit constate, il ne tranche
  pas.
