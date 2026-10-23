# CYCLE 77 — REVALIDATION DE LA PR #103 SUR `main` (2026-10-24)

Ordre du propriétaire : « QODER — CYCLE 77 : REVALIDATION DE #103 ET
CLÔTURE DU LOT B ». Ce document consigne la revalidation de la PR #103
(Lot B, C5/C8/C12) sur l'état combiné de `main` après les fusions #100,
#101 et #102, la correction des documents de suivi et l'analyse séparée
des PR #92 et #60. Contraintes tenues : aucune fusion, aucun push sur
`main`, `db/outils/sauvegarder.ps1` jamais exécuté ni restauré, aucun
import réel, aucune décision métier inventée, aucune contrainte SQL
affaiblie.

---

## 1. État de référence et synchronisation

- `main` = **`d745ead`** (vérifié sur GitHub par Claude in Chrome) :
  #100 → `335eb91` (cycle 75 complet), #101 → `75aaae0` (Codex C2/C3,
  migration 053), #102 → `d745ead` (Codex C1, migration 054).
- Migrations sur `main` : **000 à 054**. Aucune migration ajoutée par le
  Lot B ; le prochain numéro libre est **055** (non réservé, non utilisé).
- Branche revalidée : `operation-100-lot-b` (worktree
  `QuincaillerieFranck_Test_LotB`), tête avant alignement `54ffea5`.
- Synchronisation : `git fetch origin --prune`, `origin/main` = `d745ead`.

## 2. Fusion d'alignement

`origin/main` (`d745ead`) fusionné dans `operation-100-lot-b` par merge
commit **`76f3d5e`** (« Lot B : alignement sur main d745ead »),
**sans aucun conflit** : 54 fichiers, **+2 663 / −31**. Apports intégrés :
migrations `053_sessions_serveur` et `054_integrite_paiements` (+ inverses),
`conftest.py` de Codex (`QF_TEST_PGPORT`), correction de la migration 052,
authentification/sécurité/schémas, trois suites de la maquette ajustées,
`CONTRAT_INTERFACE_LOTS_A_B.md`, `test_sessions_serveur.py`,
`test_integrite_paiements_sql.py` et rapports Codex.

## 3. Passe unique locale (base isolée, migrations 000–054)

Invocation (worktree Lot B, venv partagé, base dédiée, port 8020) :

```
PYTHON=.../QuincaillerieFranck_Test/server/.venv/Scripts/python.exe \
PORT_SERVEUR=8020 BASE_TEST=quincaillerie_lotb \
bash db/outils/verifier_tout.sh
```

Résultats de la passe :

| Étape | Résultat |
|---|---|
| 1. Suite SQL complète (schéma d'origine, protections, habilitations, concurrence, aller-retour des migrations) | **OK** — toutes les étapes |
| 2. Reconstruction de `quincaillerie_lotb` (000 → 054 + jeu d'essai) | **OK** |
| 3. Suite pytest complète | **396 passed**, 75 warnings, 854,25 s (14 min 14 s) — **0 échec** |
| 4. 13 suites Playwright (serveur réel, 5 largeurs) | **13/13 OK, 505 contrôles, 0 échec** |
| 5. Base laissée propre (jeu d'essai rechargé) | **OK** |
| **BILAN** | **« Toutes les étapes sont passées. » — exit 0** |

Détail des suites Playwright : routes 65, câblage 101, vente 63, stock 49,
rapports 52, inventaire 17, ux 26, comptes 24, caisse 21, RH 14,
exploitation 11, échappement 11, rôles 35 — **505 contrôles, 0 échec**.

## 4. Échec pytest du 2026-10-24 : défaut du test, corrigé

Au run précédent (interrompu après ~36 % pour diagnostic), un seul test
échouait, en position 49 de la collecte (ordre déterministe, aucun greffon
de randomisation) : `test_campagne_fcfa_c5.py::test_journee_boutique_fcfa`.

**Symptôme reproduit** en isolation avec la configuration exacte de
l'orchestrateur : `assert attendu["attendu_especes"] == 21850` →
`assert 0 == 21850` sur `GET /caisse/attendu`.

**Cause racine** : le test figeait le jour avec `date.today()` (horloge du
POSTE), alors que PostgreSQL date les transactions avec SA propre date.
Au moment du run, le poste était au **2026-10-24 00:17** et la base
(`TimeZone = Africa/Douala`) encore au **2026-10-23 23:17** : le test
interrogeait la clôture du 24, la base n'avait que des transactions du 23.
Ce n'est pas un défaut de l'application ni de la migration 053/054, et
aucune contrainte SQL n'a été touchée.

**Correctif (dans les tests uniquement)** : les deux fichiers concernés
lisent désormais le jour sur la base (`SELECT current_date`), source de
vérité des transactions —
`test_campagne_fcfa_c5.py` (helper `_jour_bd`, utilisé pour l'attendu et la
clôture) et `test_paiements_mixtes_d2.py` (mêmes deux tests d'attendu par
mode). Aucun code applicatif modifié, aucune migration ajoutée.

**Preuve** : rejeu ciblé des deux fichiers **dans la fenêtre de divergence
d'horloges** → **12/12** ; puis passe complète ci-dessus → **396/396** et
**13/13 suites**. Le run antérieur vert (396/396) n'est pas nié : il a été
obtenu avant la bascule d'horloge du poste ; le correctif rend le test
indépendant de ce décalage.

## 5. CI sur l'état combiné

- Branche poussée : `operation-100-lot-b`, `54ffea5..835e0fb` (le commit
  `835e0fb` a pour parent le merge d'alignement `76f3d5e`).
- Run **40035602067** (« CI — pytest et Playwright ») sur **`835e0fb`** :
  **succès** — job `pytest` **succès**, job `playwright` **succès**.
- Run **40037134895** sur **`51035b8`** (commit de consignation, documents
  seuls) : job `pytest` **succès**, job `playwright` **échec** — une seule
  suite en échec, `caisse` : « attendu réel : espèces attendues = 0 (vente
  réelle = 6500) ». **Défaut du TEST, aucun défaut applicatif** : la suite
  capturait l'aperçu déclenché par le changement de SITE, parti avec la date
  par défaut du NAVIGATEUR (23/10, runner en UTC) alors que la base date les
  ventes du 24/10 (`Africa/Douala`) — le run a démarré à 23 h 00 UTC, soit
  minuit passé à Douala. Le `POST /caisse` du même scénario réussissait avec
  écart 0, ce qui exclut un défaut serveur ; l'écran affichait bien 6 500
  (deuxième `GET`), seule la réponse capturée était périmée.
- **Correctif (test uniquement, même famille que l'échec pytest de la
  section 4)** : `verifier-caisse-reel.mjs` attend désormais précisément
  l'URL `site_id=<site>&date_cloture=<jour lu en base>` (helper
  `chargerAttenduExact`) et que l'ÉCRAN affiche le montant du jour avant
  lecture. Preuve A/B sous conditions reproduites (fuseau navigateur forcé
  à UTC-11 + 400 ms de latence sur l'aperçu) : version d'avant = échec
  identique au CI (1/24), version corrigée = 24/24 ; suite réelle ensuite
  24/24. Aucun code applicatif ni contrainte SQL touchés.
- La PR #103 pointe sur la tête de `operation-100-lot-b` ; la fusion
  reste à la main du propriétaire (Claude in Chrome), merge commit uniquement.

## 6. Analyse séparée des PR #92 et #60 (aucune décision)

**PR #92** (`cycle-74-arbitrage`, tête `c3dd4ae`, base `37b7b79`) :
- Apporte **3 documents uniques** absents de `main` :
  `CYCLE_74_CAMPAGNES_CALENDRIER.md` (170 lignes),
  `CYCLE_74_D11_KASPERSKY_PROCEDURE.md` (101 lignes),
  `CYCLE_74_PILOTAGE_CHANTIERS.md` (53 lignes).
- Modifie aussi `loop-state.md` (+39 lignes) pour ajouter une section
  « Cycle 74 » **en doublon** de celle déjà présente sur `main` (issue de
  #91, qui a par ailleurs déjà apporté `CYCLE_74_ARBITRAGE.md`).
- État GitHub : **CONFLICTING / DIRTY** (le journal a évolué sur `main`
  depuis sa base).
- Options (à trancher par le propriétaire) : rafraîchir la branche sur
  `main` en conservant les 3 documents et en retirant le delta de journal
  redondant ; ou fermer la PR si la documentation du cycle 74 est jugée
  déjà couverte sur `main`.

**PR #60** (`doc-chantier-c-deja-livre`, tête `fc2db6e`, base `d00a499`) :
- Ajoute au `ADDENDUM_CAHIER_DES_CHARGES.md` un bloc « Livré (cycles
  34-35) » et met à jour la ligne du point a (+32/−1).
- Ce contenu est **absent de `main`** (vérifié : aucune occurrence du bloc ;
  ligne 1234 de `main` toujours dans son état ancien).
- État GitHub : **MERGEABLE / CLEAN** ; `main` a modifié l'addendum depuis
  la base de la PR (+53 lignes) mais dans des régions distinctes.
- Options : fusionner telle quelle, ou fermer si la mise à jour est jugée
  obsolète. Aucune décision prise.

## 7. Nommage C0–C14 et divergences signalées (non corrigées)

Le nommage officiel est celui de `REGISTRE_ECARTS_100.md` :
C0 Infrastructure et dépôt ; C1 Base de données et intégrité ;
C2 Authentification et comptes ; C3 Habilitations et cloisonnement ;
C4 Articles et stock ; C5 Ventes et facturation ; C6 Clôture de caisse et
paiements ; C7 Inventaire et comptage ; C8 Interfaces et parcours ;
C9 Tests et recette ; C10 Qualité et non-régression ; C11 Sécurité ;
C12 Sauvegarde et reprise ; C13 Intégration continue ; C14 Dossier de
recette et mise en production.

Divergences relevées, **signalées sans correction** :

1. **Scores** : le REGISTRE affiche encore les valeurs du cycle 75
   (C5 88, C8 86, C12 97), tandis que le rapport Lot B revendique les
   valeurs du cycle 76 (C5 97, C8 95, C12 98). Aucun score n'a été reporté
   dans le REGISTRE ni inventé ; l'arbitrage revient au propriétaire.
2. **Intitulés** : d'éventuels tableaux de suivi employant d'autres
   libellés pour C6, C9, C10, C11, C13 ou C14 divergent du REGISTRE ;
   c'est le REGISTRE qui fait foi (le rapport Lot B et `loop-state.md`
   suivent ses intitulés).
3. Aucun autre écart de statut de PR n'a été trouvé après les corrections
   documentaires du cycle 77 (#100/#101/#102 fusionnées, `main` =
   `d745ead`, chaîne « #92 → #100 » retirée).

## 8. Ce qui reste à la main du propriétaire

- **Fusion de la PR #103** (Claude in Chrome) : CI sur l'état combiné
  (section 5 : run 40035602067 vert ; la course de test révélée par le run
  40037134895 est corrigée et re-prouvée localement).
- **Kaspersky** : procédure S1-S6 (restauration/exclusion de
  `sauvegarder.ps1`), décision propriétaire.
- **Second PC** : épreuve physique P1-P9 (reprise, RTO ≤ 2 h).
- **Comptable** : réponses Q1-Q6 (politique TTC, D5).
- **Campagnes humaines** : R1/R2/R5 et H1-H4 (C5/C8/C12), non automatisables.
- **Sort des PR #92 et #60** (analyse ci-dessus, décision propriétaire).

Aucun 100 % n'est déclaré : les maillons humains et les décisions
ci-dessus restent ouverts.
