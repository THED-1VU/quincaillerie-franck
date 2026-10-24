# REGISTRE DES ÉCARTS — OBJECTIF 100 % (cycle 66)

**Date de l'audit :** 2026-10-21 (cycle 66, branche `cycle-66-audit-ecarts`)
**Périmètre :** les 15 chantiers C0–C14, du code tel que versé dans les branches
ouvertes (#78 → #82) + `main` à `c1784c6` (merge PR #77).
**Méthode :** aucun écart repris sur parole — chaque ligne cite sa preuve
(fichier:ligne, requête exécutée, PR, document). Base d'audit fraîche
`quincaillerie_c66` reconstruite de zéro (schéma d'origine + migrations 000–050
+ jeu d'essai) le 2026-10-21 à 00:09, détruite après capture des preuves.

**Gravité :**
- **P0** — intégrité / comptabilité / sécurité compromise, ou blocage total de la mise en production. *Aucun P0 identifié dans cet audit (voir § synthèse).*
- **P1** — indispensable avant le GO : décision métier bloquante ou recette bloquante.
- **P2** — important : correctif planifiable ou confirmation propriétaire nécessaire.
- **P3** — hygiène / documentation / fidélité des environnements de test.

**Statuts :** `OUVERT` (correctif faisable par le développement) · `EN_COURS`
(livré dans une PR ouverte) · `BLOQUE_PROPRIETAIRE` (décision ou action réservée)
· `BLOQUE_TEST_HUMAIN` (validation humaine requise) · `CLOS` (vérifié ce cycle).

---

## Synthèse de pilotage

40 écarts recensés, dont **20 clôturés par vérification, livraison ou
décision** (C4-01 et C8-02 vérifiés au cycle 66 ; C4-02 livré au cycle 67 ;
C1-04, C7-02 et C7-03 livrés au cycle 68 ; C8-01 soldé au cycle 69 ; C0-04
reconstruit au cycle 70 ; C14-03 livré au cycle 72 ; **C0-01, C13-01, C13-02
et C14-01 acquittés au cycle 73 par l'intégration des PR #78→#89 (+ #90) dans
`main`** ; **au cycle 75 sur les décisions du propriétaire du 2026-10-23 :
C5-01 et C5-02 (D9, D4), C1-01 (D2), C2-02 (D10), C3-02 (D8), C3-03 (D7),
C12-02 (alerte sauvegarde)**).
20 écarts ouverts :

| Gravité | Total | Détail | Actionnable par le développement |
|---------|:-----:|--------|:--------------------------------:|
| P0 | **0** | aucun écart d'intégrité, de comptabilité ou de sécurité | — |
| P1 | **13** | 7 BLOQUE_PROPRIETAIRE + 6 BLOQUE_TEST_HUMAIN | 0 |
| P2 | **7** | 4 BLOQUE_PROPRIETAIRE · 1 TEST HUMAIN · 2 EN_COURS/OUVERT | 2 |
| P3 | **0** | les derniers P3 (C3-02, C3-03) sont clos au cycle 75 | — |
| **Total ouverts** | **20** | 11 BLOQUE_PROPRIETAIRE · 7 BLOQUE_TEST_HUMAIN · 2 EN_COURS/OUVERT | **2** |

Lecture (mise à jour cycle 75, clôture) : **aucun écart d'intégrité** et
**aucun P3 restant** — les **neuf décisions validées le 2026-10-23** (D2, D4,
D5, D6, D7, D8, D9, D10, C12-02) sont toutes **implémentées et testées**,
chacune sur preuve d'exécution réelle (PR #93→#100, en attente de fusion par
le propriétaire). Le chemin vers 99–100 % passe désormais par : (1) les
décisions et actions restant au propriétaire — D1 (confirmation du statu quo
prix caissier), D3 (fond de caisse/seuil d'écart), C6-02, C7-01
(confirmations de paramètres), D11 (exclusion Kaspersky sur son poste), le
sort des PR #60 et #92, les fusions #93→#100, et les réponses du comptable
Q1-Q6 (D5, avant tout import réel) ; (2) les validations humaines (campagnes
UX — fiches prêtes dans `RAPPORT AVANCEMENT/CYCLE_73_FICHES_RECETTE.md`,
impression, 2ᵉ poste). Le développement garde **2 écarts actionnables**
(C12-03, C11-02) — tous deux suspendus à l'installation réelle, donc
reportables au jour J.

**Rattrapage d'en-têtes de score (cycle 71)** — les en-têtes de sections
suivent désormais les scores prouvés par cycle : C4 77→**78** (cycle 67),
C7 65→**67** (cycle 68), C8 85→**86** (cycle 69), C13 76→**77** (cycle 71,
C13-02), C5 81→**88** (cycle 75, C5-01 et C5-02 résorbés sur décisions D9 et
D4 — seul C5-03, test humain, reste ouvert), C1 92→**96** (cycle 75, C1-01
livré sur décision D2 — restent C1-02 et C1-03, suspendus à D5 et à
l'installation réelle). **Cycle 75, clôture** : C2 82→**90** (C2-02 clos par
décision D10 — 7 mesures compensatoires prouvées ; moitié de C2-01 résorbée
par D6 — reste la confirmation `tentatives_max_connexion`), C3 77→**88**
(C3-02 clos par décision D8, C3-03 clos par décision D7 et livraison de
l'union des écrans — reste C3-01/D1), C12 95→**97** (C12-02 livré et testé
en échec simulé). Aucune de ces corrections n'est un
score nouveau : ce sont des
reportages de preuves déjà établies.

---

## C0 — Infrastructure et dépôt (90 %)

### C0-01 — Fusions des PR #78 → #82 en attente
- **Exigence source :** PROMPT MAÎTRE (« fusion des PR = propriétaire uniquement ») + D13.
- **État :** *acquitté (cycle 73)* — l'intégration des 12 PR #78→#89 a été
  exécutée dans l'ordre des dépendances, sous l'autorisation explicite du
  propriétaire (mission 1 du cycle 73) : base et dépendances vérifiées avant
  chaque fusion, protections et CI GitHub vertes à chaque étape, aucun conflit
  masqué (fusion refusée ou reportée sinon), fusions `--merge` sans force-push
  ni rebase. L'incident de fusion de la PR #89 dans sa base empilée (retarget
  omis) a été corrigé sans réécriture d'historique par la PR #90 → `main`
  = `d0fa264` contient les cycles 61-72.
- **Preuve (exécutée cycle 73) :** registre des fusions #78→fd707b5, #79→13c1338,
  #80→b8d82f8, #81→b809cc4, #82→0b29f04, #83→56eb6c7, #84→9cca716, #85→b7c547d,
  #86→3b73d6e, #87→36812ff, #88→c4e0e9b, #89→2eb36ba, #90→d0fa264 ; CI verte
  sur chaque PR (ex. run 39894259707 : playwright 8 min 39 s + pytest 8 min 57 s)
  ; `main` = d0fa264 (parents c4e0e9b + 805d479) ; régression complète fraîche
  sur le nouveau `main` (journal du cycle 73).
- **Gravité / risque métier :** P1 — levé.
- **Correction :** exécutée (voir §État).
- **Dépendances :** — **Responsable :** développement (autorisé mission 1 du cycle 73).
- **Critère d'acceptation :** `main` contient tous les cycles 61-72, CI verte, aucun conflit masqué, historique sans force-push — **atteint**.
- **Tests requis :** régression complète sur le nouveau `main` — faite au cycle 73.
- **Statut :** CLOS (cycle 73).

### C0-02 — Enregistrement PostgreSQL en service + tâche de sauvegarde planifiée (poste cible)
- **Exigence source :** chantier C0/C12 (livraison poste client) ; ordre permanent « aucune installation réelle sans autorisation ».
- **État :** outils livrés (`db/outils/enregistrer_service_pg.ps1`, `planifier_sauvegarde.ps1`) mais jamais exécutés sur un poste cible réel.
- **Preuve :** dossier cycle 64 (PR #81) ; base `quincaillerie_c66` prouve que le service local 5433 tourne **en session développeur**, pas en service enregistré.
- **Gravité / risque métier :** P1 — sans service, PostgreSQL ne survit pas à un redémarrage du poste ; sans tâche planifiée, pas de sauvegarde automatique (RTO 2 h non tenable).
- **Correction :** exécuter les deux scripts sur le poste cible lors de l'installation réelle, tracer le résultat.
- **Dépendances :** autorisation d'installation (propriétaire), poste cible disponible. **Responsable :** PROPRIÉTAIRE (+ opérateur).
- **Critère d'acceptation :** service PostgreSQL présent après redémarrage du poste ; sauvegarde chiffrée produite à l'heure planifiée ; `restaurer.ps1` rejoué avec succès.
- **Tests requis :** redémarrage réel du poste + restauration réelle (recette C12).
- **Statut :** BLOQUE_PROPRIETAIRE.

### C0-03 — Installation réelle testée sur un 2ᵉ poste
- **Exigence source :** cycle 12 / C12 — « restauration testée sur un deuxième poste ».
- **État :** non exécuté ; seul le poste de développement a porté l'exécutable (cycle 63).
- **Preuve :** `RAPPORT AVANCEMENT/loop-state.md`, chantier C12 « reste ».
- **Gravité / risque métier :** P1 — l'auto-portabilité de `Akuma.exe` est prouvée sur une machine, pas sur deux configurations distinctes.
- **Correction :** installer sur 2ᵉ poste, ouvrir l'app, saisir une vente, restaurer une sauvegarde.
- **Dépendances :** autorisation, matériel. **Responsable :** PROPRIÉTAIRE / test humain.
- **Critère d'acceptation :** parcours complet fonctionnel sur 2ᵉ poste + PV signé.
- **Tests requis :** scénario GUIDE_TESTEUR_INSTALLATION.txt sur machine vierge.
- **Statut :** BLOQUE_TEST_HUMAIN.

### C0-04 — Journal d'avancement : trou des cycles 61–64
- **Exigence source :** convention du dépôt (un cycle = une section de `loop-state.md`) ; divergence D5 (cycle 65).
- **État :** *corrigé (cycle 70)* — les sections 61, 62 et 63 existaient mot pour mot dans les commits de documentation de leurs branches (`dbf3e64`, `1cbcdea`, `aed8931`, jamais fusionnées) ; la section 64 a été rédigée depuis les preuves réelles de la PR #81 (simulation d'installation, parité `migrer.ps1`/`migrer.sh`, 306/306). Toutes quatre insérées dans `loop-state.md` entre les cycles 60 et 65.
- **Preuve (exécutée ce cycle) :** `grep -n "^### Cycle 6[0-9]" loop-state.md` → sections 60 à 69 présentes et dans l'ordre, aucun trou depuis la baseline du cycle 56 ; lignes de scores C0 (78→**86**), C12 (92→**95**), C13 (71→**76**) resynchronisées sur la référence post-cycle-64 (leurs en-têtes n'avaient jamais été bougés dans les branches d'origine) ; moyennes indicatives 61-64 rétablies.
- **Gravité / risque métier :** P3 — l'auditabilité des preuves s'érode (un score qui monte sans journal est une promesse, pas une preuve).
- **Correction (exécutée cycle 70) :** sections rétrospectives insérées + tableau des scores synchronisé (ci-dessus).
- **Dépendances :** aucune. **Responsable :** développement (lot D).
- **Critère d'acceptation :** `loop-state.md` sans trou de cycle depuis la baseline du cycle 56.
- **Tests requis :** relecture — une section datée par cycle, un tableau de scores synchronisé.
- **Preuves (cycle 70) :** relecture structurelle (grep sections + scores) ; PR #87.
- **Statut :** CLOS (cycle 70).

---

## C1 — Base de données et intégrité (96 %)

### C1-01 — Paiements mixtes (addendum point a)
- **Exigence source :** addendum point a ; décision D2 (`DECISIONS_PROPRIETAIRE.md`, validée le 2026-10-23).
- **État (avant cycle 75) :** non construit — `ventes.mode_paiement` est une valeur unique (espèces/Mobile Money/chèque/virement), une vente ne peut pas combiner deux modes.
- **Preuve :** `db/migrations` (aucune table de répartition de paiement) ; `POST /ventes` accepte un mode unique.
- **Gravité / risque métier :** P1 — une vente réelle « 30 000 espèces + 20 000 Mobile Money » ne peut pas être enregistrée fidèlement.
- **Correction (exécutée cycle 75-C) :** migration **052** (`052_paiements_mixtes.sql` + inverse) : table `ventes_paiements` (une composante par mode, `UNIQUE(vente_id, mode_paiement)`, `montant > 0`), backfill des ventes existantes, **invariant somme = encaissé porté par la base** (constraint trigger DIFFÉRÉ vérifié au COMMIT, valable même en SQL direct), `ventes.mode_paiement` = mode unique ou `'mixte'`, `calculer_attendu_caisse` recalculée sur les composantes (le repartage espèces / Mobile Money de la clôture suit), grants + RLS par site ; API `paiements[]` (somme inexacte refusée 422, jamais avec `mode_paiement`), **toute vente encaissée écrit ses composantes** (chemin historique = 1 composante du total), recette de journal toujours **UNE du TOTAL** (aucun double comptage), crédit sans composante, annulation 017 inchangée, reçu PDF décomposé ; écran `vente.html` (case paiement mixte, décomposition affichée avant validation, jamais avec le crédit).
- **Dépendances :** D2 (validée). **Responsable :** développement.
- **Critère d'acceptation :** une vente à deux modes enregistrée, tracée, exportée ; total vérifié par la base.
- **Tests requis :** protections SQL + pytest + Playwright parcours vente.
- **Preuves (cycle 75-C) :** pytest `test_paiements_mixtes_d2.py` **10/10** (dont invariant SQL direct → `CheckViolation` au COMMIT) ; suite vente Playwright **63/63** dont 12 nouveaux contrôles écran (mode `'mixte'` et composantes `especes=3000.00 + orange_money=3500.00` en base, **une seule recette journal de 6 500**) ; régression pytest complète **354/354** ; migration appliquée sur base reconstruite (52 migrations). **PR #95** (empilée sur #94).
- **Statut :** CLOS (cycle 75).

### C1-02 — Ventilation HT/TTC sur les documents (addendum point d, question 5)
- **Exigence source :** addendum point d ; décision D5.
- **État :** prix saisis TTC (décidé cycle 6, `prix_saisis_ttc=oui`), TVA extraite sur le total de la vente (taux lu en base : défaut migrations 0 = aucune TVA appliquée, base de test 19,25 % décidé cycle 6 — la valeur exacte reste la question comptable Q2, migration 006) — mais la ventilation HT ligne à ligne n'est pas affichée sur le reçu/les rapports (seuls sous-total HT, montant TVA, total TTC de la vente le sont).
- **Partiellement soldé (cycle 75-G)** : décision D5 validée (2026-10-23, TTC conservé) et audit du traitement fiscal livré — `RAPPORT AVANCEMENT/D5_AUDIT_TTC.md` (constats de code pointés et prouvés ; 6 questions comptables listées, dont la ventilation ligne à ligne). Reste ouvert : réponses du comptable (Q1-Q6), puis colonne HT par ligne si requis.
- **Preuve :** `server/app/routes/rapports.py` (colonnes de l'export) ; reçu PDF cycle 19 ; audit cycle 75-G (`ventes.py:335-337, 378-384, 432-440, 543-552`, migration 006).
- **Gravité / risque métier :** P2 — conformité de présentation fiscale des factures.
- **Correction :** décision D5 puis ajout de la colonne HT par ligne si requis.
- **Dépendances :** D5 (validée) + réponses comptable (Q1-Q6). **Responsable :** PROPRIÉTAIRE (comptable), puis développement.
- **Critère d'acceptation :** facture présentant HT/TVA/TTC conformément à la décision.
- **Tests requis :** pytest reçu + comparaison montants.
- **Statut :** BLOQUE_PROPRIETAIRE (réponses comptable attendues avant import réel).

### C1-03 — Reprise sur une base contenant de vraies données
- **Exigence source :** chantier C1 « reprise » ; ordre permanent « aucun import de données réelles sans autorisation ».
- **État :** la reprise est prouvée sur volume réaliste synthétique (cycle 40) ; jamais sur les données réelles de la quincaillerie.
- **Preuve :** `loop-state.md` C1 (cycles 40, 55).
- **Gravité / risque métier :** P1 — le jour J, l'import du stock réel est l'opération la plus risquée du projet.
- **Correction :** protocole d'import (outil existant `importer_stock_initial.py`, prévu par `prevol.sql`) exécuté sur données réelles en présence du propriétaire, avec reprise d'essai sur copie.
- **Dépendances :** autorisation + fichier réel. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** base de production chargée, comptages réconciliés avec l'inventaire papier, PV signé.
- **Tests requis :** import à blanc sur copie, puis import réel, contrôles de comptage.
- **Statut :** BLOQUE_PROPRIETAIRE.

### C1-04 — Paramètre `seuil_remise_validation_pct` absent du jeu d'essai
- **Exigence source :** migration 037 (remises) ; convention « le jeu d'essai réamorce `parametres` ».
- **État :** `00_jeu_essai.sql` TRUNCATE `parametres` et réinsère une liste figée — la ligne `seuil_remise_validation_pct` (introduite par 037) n'y figure jamais. En environnement de test/CI, le paramètre n'existe tout simplement pas.
- **Preuve (exécutée ce cycle) :** `SELECT count(*) FROM parametres WHERE cle='seuil_remise_validation_pct'` sur `quincaillerie_c66` → **0** ; `00_jeu_essai.sql:36` (truncate) vs `db/migrations/037_remises.sql:94` (INSERT). Le code gère l'absence (`server/app/routes/ventes.py:263-267` → seuil inactif), donc **aucun impact fonctionnel** ; c'est une dérive de fidélité test/production (une installation réelle via migrations seule aurait la ligne).
- **Gravité / risque métier :** P3 — un test futur sur le seuil de remise ne pourrait pas échouer proprement en environnement de test ; l'écart s'aggravera à chaque nouveau paramètre oublié.
- **Correction (exécutée cycle 68) :** audit complet du seed vs les 50 migrations → **deux** clés manquantes corrigées (`seuil_remise_validation_pct` de 037 et `contact_support_technique`, détectée en cours d'audit), plus une absence justifiée (`logo_boutique_extension`, état runtime non seedable) désormais documentée dans le commentaire du seed ; verrou `server/tests/test_jeu_essai.py` (19 clés attendues, `logo_boutique_extension` interdite).
- **Dépendances :** aucune. **Responsable :** développement (lot B).
- **Critère d'acceptation :** rejeu du seed sur base neuve → ligne présente ; note d'audit des paramètres du seed vs migrations.
- **Tests requis :** rejeu `00_jeu_essai.sql` + contrôle présence ; suite SQL complète verte.
- **Preuves (cycle 68) :** pytest `test_jeu_essai.py` **1/1** ; régression complète sur base isolée verte ; PR #85.
- **Statut :** CLOS (cycle 68).

---

## C2 — Authentification et comptes (90 %)

### C2-01 — Confirmations : tentatives_max_connexion (5) — duree_session (480) appliquée
- **Exigence source :** cycle 38 ; `parametres.a_decider`.
- **État :** *moitié « session » résorbée au cycle 75* — D6 validée le
  2026-10-23 (session ≤ 480 minutes) : plafond, expiration et révocation
  prouvés par `test_session_d6.py` (migration 033, PR #97). La ligne
  `tentatives_max_connexion=5` porte encore `a_decider=TRUE` (à confirmer).
- **Preuve (exécutée cycle 75) :** `test_session_d6.py` vert (régression
  complète) ; `SELECT cle, valeur, a_decider FROM parametres` sur base de test.
- **Gravité / risque métier :** P2 — verrouillage trop laxé ou trop strict selon la confirmation.
- **Correction :** confirmation orale/écrite → basculer `a_decider` à FALSE avec référence.
- **Dépendances :** propriétaire. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** la ligne `tentatives_max_connexion` tranchée (voir C6-01, C7-01, C1-02).
- **Tests requis :** mise à jour du seed + contrôles `a_decider`.
- **Statut :** BLOQUE_PROPRIETAIRE (restreint à tentatives_max_connexion).

### C2-02 — Deuxième facteur (2FA)
- **Exigence source :** décision D10.
- **État :** *clos par décision (cycle 75)* — D10 validée le 2026-10-23 :
  2FA reportée après V1 (TOTP si retenu alors). Sept mesures compensatoires
  consignées et prouvées une par une (bcrypt coût 12, mot de passe provisoire
  forcé 403, limiteur de débit + verrouillage, sessions bornées 480 min
  révocables, coupure par désactivation/réinitialisation, cloisonnement
  PostgreSQL + RLS, journal d'audit non destructible) — liste et tests dans
  `DECISIONS_PROPRIETAIRE.md` D10, cycle 75-E (PR #97).
- **Preuve :** cycle 75-E, tous verts (régression complète) :
  `test_hachage_genere_par_le_serveur_est_verifiable_par_pgcrypto`,
  `test_changement_mdp_force.py`, `test_limitation_de_debit_sur_la_connexion`,
  `test_verrouillage_apres_echecs_repetes`, `test_deverrouillage_refuse_a_un_agent`,
  `test_session_d6.py`, `test_reinitialisation_responsable_coupe_jeton_encore_valide`,
  `test_privileges_sql_roles.py`.
- **Gravité / risque métier :** P2 — levé pour la V1 par décision ; le TOTP éventuel est un chantier post-V1.
- **Correction :** aucune en V1 (décision) ; TOTP après V1 si retenu.
- **Dépendances :** D10 (tranchée). **Responsable :** développement post-V1.
- **Critère d'acceptation :** décision écrite obtenue (2026-10-23).
- **Tests requis :** mesures compensatoires testées (voir preuve).
- **Statut :** CLOS (cycle 75, décision D10).

---

## C3 — Habilitations et cloisonnement (88 %)

### C3-01 — Visibilité des prix du caissier (addendum point h, question 3)
- **Exigence source :** addendum h q3 ; décision D1.
- **État :** vérifié par inspection + matrice (cycle 65) — aucun `prix_achat` n'atteint les écrans ni les réponses réseau de l'agent comptabilité (`vente.html:344-349` ne mappe que `prix_vente` ; vue 048 sans `prix_achat`, `security_invoker`) ; la **confirmation formelle** du propriétaire reste requise (option 1 = statu quo).
- **Preuve :** `MATRICE_ROLES_AKUMA.md` ; `DECISIONS_PROPRIETAIRE.md` D1 ; `db/migrations/048_ecarts_prix_vendeurs.sql`.
- **Gravité / risque métier :** P1 — tant que la question n'est pas tranchée, l'écran caisse reste en attente d'une éventuelle variante « total seul ».
- **Correction :** trancher D1 ; si « total seul », créer la variante d'écran caissier + tests.
- **Dépendances :** D1. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** décision écrite ; si variante, écran livré et testé.
- **Tests requis :** Playwright par rôle + contrôle réseau (aucun prix si « total seul »).
- **Statut :** BLOQUE_PROPRIETAIRE.

### C3-02 — Inventaire : le responsable ne compte pas (D8)
- **Exigence source :** décision D8 (`comptage à l'aveugle`, inventaire réservé `agent_stock`).
- **État :** *clos par décision (cycle 75)* — D8 validée le 2026-10-23 :
  l'agent stock effectue le comptage, le responsable supervise et valide.
  Le comportement livré est exactement celui-là : `inventaire.html` réservé
  à l'agent stock (gate), le responsable consulte les écarts et valide les
  déclarations (casse/retour client/article offert) sur `declarations.html`
  avec effet stock réel — répartition prouvée au cycle 75-D (PR #96).
- **Preuve :** Playwright inventaire 17/17 + stock 49/49 (régression
  complète cycle 75 : validation responsable décrémente/réintègre
  réellement) ; `MATRICE_ROLES_AKUMA.md` (table UI).
- **Gravité / risque métier :** P3 — levé.
- **Correction :** aucune (confirmation obtenue).
- **Dépendances :** D8 (tranchée). **Responsable :** —.
- **Critère d'acceptation :** décision écrite obtenue (2026-10-23).
- **Tests requis :** rejoués (voir preuve).
- **Statut :** CLOS (cycle 75, décision D8).

### C3-03 — Cumul de rôles : affichage à l'écran (D7)
- **Exigence source :** décision D7 ; cycle 43 (livré).
- **État :** *clos par décision et livraison (cycle 75)* — D7 validée le
  2026-10-23 : un compte cumulant plusieurs rôles voit TOUTES ses fonctions
  (union). Implémenté au cycle 75-D (PR #96) : carte `ROLES_PAR_PAGE`
  centralisée dans `api.js`, `ajusterNavigation()` retire du bandeau tout
  lien vers un écran interdit ET ajoute les liens manquants — chaque page
  liste l'union des écrans autorisés du compte. Les régressions découvertes
  par la régression complète (crash `stock.html` sur un lien retiré,
  débordements du bandeau à 768/1366 px) corrigées au cycle 75-H (PR #100).
- **Preuve :** Playwright roles (union des écrans par profil) + stock 49/49
  + comptes/rapports/caisse/rh verts (régression complète cycle 75) ;
  captures régénérées (bandeau à deux lignes = comportement voulu).
- **Gravité / risque métier :** P3 — levé.
- **Correction :** livrée (cycles 75-D et 75-H).
- **Dépendances :** D7 (tranchée). **Responsable :** —.
- **Critère d'acceptation :** décision écrite obtenue + implémentation testée.
- **Tests requis :** rejoués (voir preuve).
- **Statut :** CLOS (cycle 75, décision D7, PR #96 + #100).

---

## C4 — Articles et stock (78 %)

### C4-01 — Modèle point a vérifié (articles sans site, stock par site)
- **Exigence source :** addendum point a ; cycle 35.
- **État :** **vérifié ce cycle** — `articles` ne porte aucune colonne `site_id` (12 colonnes, catalogue commun) ; `stocks_sites` a pour clé primaire `(article_id, site_id)`.
- **Preuve (exécutée ce cycle) :** `information_schema.columns` sur `articles` ; `pg_index` sur `stocks_sites` (base `quincaillerie_c66`).
- **Gravité / risque métier :** — (contrôle de conformité, aucun écart).
- **Correction :** aucune ; écart clôturé par vérification.
- **Dépendances :** — **Responsable :** —.
- **Critère d'acceptation :** — **Tests requis :** —.
- **Statut :** CLOS.

### C4-02 — Export dédié au chantier stock
- **Exigence source :** `loop-state.md` C4 « reste : export dédié à C4 ».
- **État :** **LIVRÉ au cycle 67** — route `GET /rapports/stock` (responsable
  seulement) : lignes (article, site) avec quantités, seuil, prix d'achat,
  prix de vente, valorisations calculées EN SQL et alerte RUPTURE/SOUS_SEUIL/OK ;
  le xlsx ajoute une feuille « totaux par site » ; carte dédiée dans
  `rapports.html` (responsable uniquement). `prix_achat` reste un privilège
  du seul rôle responsable (migration 008) — aucun prix retiré après coup.
- **Preuve :** pytest `test_rapports.py` 24/24 (5 tests nouveaux : valorisations
  exactes du jeu d'essai — Ciment 150 000/195 000, « Article rare » SOUS_SEUIL,
  totaux par site 263 000/337 000 et 60 000/80 000 —, 403 agent stock et
  agent comptabilité, 422 format invalide, PDF avec valorisation) ;
  Playwright `verifier-rapports-reel.mjs` **45/45** (carte visible pour le
  responsable, absente pour les deux rôles agents, téléchargements xlsx+pdf
  réels — fichier de 5 826 octets). Fichiers : `server/app/routes/rapports.py`,
  `maquette/rapports.html`, `server/tests/test_rapports.py`,
  `maquette/verification/verifier-rapports-reel.mjs` (PR #84).
- **Gravité / risque métier :** P2 — levé.
- **Correction :** livrée (ci-dessus).
- **Dépendances :** — **Responsable :** développement (cycle 67).
- **Critère d'acceptation :** fichier xlsx téléchargé, contrôles croisés avec
  les soldes affichés — atteint (totaux relus depuis le fichier réel).
- **Tests requis :** pytest + Playwright téléchargement — exécutés, verts.
- **Statut :** CLOS (cycle 67, preuves d'exécution réelle).

### C4-03 — Campagne UX du parcours stock
- **Exigence source :** cycle 60 « campagne UX humaine (BLOCKED_HUMAN_TEST) ».
- **État :** aucune campagne humaine dédiée au parcours stock (réception, transfert, casse, comptage) sur la version actuelle.
- **Preuve :** `loop-state.md` C4.
- **Gravité / risque métier :** P1 — les écrans stock sont les plus denses de l'application.
- **Correction :** campagne guidée (guide testeur existant) + fiche de retour.
- **Dépendances :** temps du propriétaire/premier employé. **Responsable :** TEST HUMAIN.
- **Critère d'acceptation :** PV de campagne sans anomalie bloquante.
- **Tests requis :** scénario GUIDE_TESTEUR + captures.
- **Statut :** BLOQUE_TEST_HUMAIN.

---

## C5 — Ventes et facturation (88 %)

### C5-01 — `utilisateur_caisse_id` toujours attribué au responsable
- **Exigence source :** addendum h (caissier fusionné) + décision D9.
- **État :** corrigé au cycle 75 (décision D9 validée par le propriétaire le
  2026-10-23) — `POST /ventes` attribue désormais l'encaissement au compte
  **authentifié** (identifiant porté par le jeton signé) ; l'ancienne
  requête « premier responsable trouvé » est supprimée. Résistance à
  l'usurpation prouvée : `DemandeVente` n'expose aucun champ d'encaisseur et
  un test injecte le champ dans le JSON pour prouver qu'il est ignoré.
- **Preuve (exécutée cycle 75) :** `server/tests/test_encaissement_d9.py`
  **3/3** (agent saisit → encaisseur = agent ; responsable → encaisseur =
  responsable ; injection du champ ignorée) ; non-régression ventes
  **45/45**, caisse + crédit **35/35**.
- **Gravité / risque métier :** P2 — le journal d'audit prête l'encaissement au mauvais utilisateur ; en cas de litige caisse, la traçabilité « qui a encaissé » est faussée ; contradiction visible avec la décision de fusion du rôle caissier (2026-09-13).
- **Correction :** `ventes.py` : `utilisateur_caisse_id = session.utilisateur_id` (décision D9 du 2026-10-23) — aucune migration (colonne inchangée).
- **Dépendances :** D9 (validée). **Responsable :** développement.
- **Critère d'acceptation :** une vente saisie par `agent_comptabilite` porte son identifiant dans `utilisateur_caisse_id` ; tests qui l'affirment — **atteint**.
- **Tests requis :** pytest (vente par agent compta → colonne = son id) + protections SQL — 3 tests dédiés verts.
- **Statut :** CLOS (cycle 75).

### C5-02 — Seuil de validation des remises non décidé
- **Exigence source :** addendum f ; décision D4.
- **État (avant correction) :** mécanisme livré au cycle 42, **inactif** par défaut (`a_definir`) ; en environnement de test le paramètre était même absent du seed (voir C1-04).
- **Correction (cycle 75, décision D4 du propriétaire 2026-10-23) :** migration `051_seuil_remise_valide.sql` — paramètre `seuil_remise_validation_pct` fixé à **10**, `a_decider = FALSE` ; le blocage serveur 403 existant (ventes.py, par ligne et remise globale, condition strictement `> seuil`) devient actif sur toute la base ; seed `00_jeu_essai.sql` aligné sur l'état décidé.
- **Preuve :** `server/tests/test_seuil_remise_d4.py` 7/7 verts (0 % agent OK ; 10 % exact agent OK, remise 650 ; 10,01 % agent **403** ; 10,01 % responsable OK, remise 650.65 ; remise globale 15 % agent 403 ; remise négative 422 ; prix > catalogue → remise 0, jamais négative) + `test_jeu_essai.py` verts + non-régression `test_ventes.py` **42/42** + Playwright `verifier-vente-reelle.mjs` **51/51** (nouveau contrôle écran : remise globale 16,1 % par un agent → **403 serveur**, motif affiché dans la zone de confirmation, **aucune vente en base**) ; migration 051 appliquée (valeur `10|f`), inverse fournie.
- **Gravité / risque métier :** P1 — résorbée : au-delà de 10 %, seul un compte responsable peut enregistrer la vente, vérifié côté serveur (jamais un simple avertissement visuel).
- **Dépendances :** D4 (validée 2026-10-23). **Responsable :** développement.
- **Critère d'acceptation :** seuil en configuration, comportement conforme à la décision, tests — **atteint**.
- **Tests requis :** pytest dédiés + Playwright remise > seuil — **livrés et verts**.
- **Statut :** CLOS (cycle 75).

### C5-03 — Impression physique du ticket
- **Exigence source :** parcours vente — impression à l'encaissement.
- **État :** le reçu PDF est généré (`GET /ventes/{id}/recu`) ; l'impression sur imprimante thermique/standard n'a jamais été testée sur matériel réel.
- **Preuve :** cycle 19 (PDF) ; aucun test imprimante.
- **Gravité / risque métier :** P1 — au quotidien, le client repart avec un ticket ; un défaut d'impression se paie cash.
- **Correction :** test d'impression réel (bouton d'impression navigateur suffit pour v1), validation papier.
- **Dépendances :** imprimante disponible. **Responsable :** TEST HUMAIN.
- **Critère d'acceptation :** ticket imprimé lisible (mentions légales incluses), PV.
- **Tests requis :** impression réelle + contrôle visuel.
- **Statut :** BLOQUE_TEST_HUMAIN.

---

## C6 — Clôture de caisse et paiements (85 %)

### C6-01 — Fond de caisse + seuil d'écart toléré
- **Exigence source :** addendum point g (q5) ; décision D3.
- **État :** `seuil_ecart_caisse_tolere = a_definir` (`a_decider=TRUE`); le fond de caisse de départ n'est pas modélisé (aucune table/paramètre).
- **Preuve (exécutée ce cycle) :** `parametres` sur base d'audit ; `DECISIONS_PROPRIETAIRE.md` D3.
- **Gravité / risque métier :** P1 — sans seuil, chaque clôture avec écart exige une investigation manuelle ; sans fond modélisé, l'écart de caisse ne peut pas être calculé fidèlement.
- **Correction :** décision D3 (montant du fond, seuil toléré, qui régularise) → modèle + écran.
- **Dépendances :** D3. **Responsable :** PROPRIÉTAIRE puis développement.
- **Critère d'acceptation :** clôture calculant écart vs fond+ventes, seuil appliqué, régularisation tracée.
- **Tests requis :** protections SQL + pytest + Playwright clôture.
- **Statut :** BLOQUE_PROPRIETAIRE.

### C6-02 — Vente tardive, Mobile Money déconnecté, blocage post-clôture
- **Exigence source :** addendum point g (questions annexes).
- **État :** questions documentées, non tranchées : vente saisie après minuit comptée au jour précédent ? Mobile Money confirmé hors-ligne ? blocage des ventes après clôture ?
- **Preuve :** `DECISIONS_PROPRIETAIRE.md` ; `loop-state.md` C6.
- **Gravité / risque métier :** P2 — cas marginaux mais quotidiens en pratique commerciale.
- **Correction :** décisions écrites puis ajustements ciblés.
- **Dépendances :** propriétaire. **Responsable :** PROPRIÉTAIRE puis développement.
- **Critère d'acceptation :** règles posées + tests qui les vérifient.
- **Tests requis :** pytest (vente 23 h 59 / 00 h 01) selon décision.
- **Statut :** BLOQUE_PROPRIETAIRE.

---

## C7 — Inventaire et comptage (67 %)

### C7-01 — Plafond de vraisemblance à confirmer
- **Exigence source :** cycle 57 ; `plafond_vraisemblance_comptage`.
- **État :** 10 000 en configuration, mais la référence de décision dit « Défaut équipe de développement (2026-09-25), à confirmer par le propriétaire ».
- **Preuve (exécutée ce cycle) :** `parametres.reference_decision`.
- **Gravité / risque métier :** P2 — un plafond mal calibré laisse passer des comptages aberrants (ou bloque des comptages sains).
- **Correction :** confirmation → basculer `a_decider` (la ligne est déjà `a_decider=FALSE`, seule la référence demande confirmation écrite).
- **Dépendances :** propriétaire. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** confirmation datée dans le registre des décisions.
- **Tests requis :** aucun (déjà testé cycle 57).
- **Statut :** BLOQUE_PROPRIETAIRE.

### C7-02 — Historique/consultation des comptages
- **Exigence source :** `loop-state.md` C7 (reste : historique).
- **État :** *corrigé (constat d'audit erroné à l'origine)* — la route `/inventaire/historique-comptages` et l'écran « historique des comptages » existaient déjà ; le vrai écart portait sur l'exposition des **régularisations** exigée par le critère d'acceptation « écarts ET régularisations » (la requête ne joignait pas `regularisations_ecarts_comptage`).
- **Preuve :** `inventaire.py:historique_comptages` (route présente avant le cycle) ; registre initial sur-estimé l'écart (« aucune route d'historique » était périmé).
- **Gravité / risque métier :** P2 — le responsable ne peut pas revisiter une campagne passée sans SQL.
- **Correction (exécutée cycle 68) :** `LEFT JOIN regularisations_ecarts_comptage` dans `historique_comptages` → champs `regularisation_type/motif/date` exposés ; l'écran `maquette/inventaire.html` affiche « — régularisé : <type> (« <motif> ») » ; pytest `test_tableau_bord.py::test_historique_comptages_expose_la_regularisation` **1/1**.
- **Dépendances :** aucune. **Responsable :** développement (lot C).
- **Critère d'acceptation :** liste chronologique des campagnes avec écarts et régularisations.
- **Tests requis :** pytest + Playwright.
- **Preuves (cycle 68) :** pytest 44/44 sur les 4 fichiers touchés ; Playwright `verifier-rapports-reel.mjs` **52/52** (régularisation affichée à l'écran) ; PR #85.
- **Statut :** CLOS (cycle 68).

### C7-03 — Export dédié au chantier inventaire
- **Exigence source :** `loop-state.md` C7.
- **État :** pas d'export (xlsx/PDF) des écarts de comptage.
- **Preuve :** `rapports.py` ; matrice (exports existants recensés).
- **Gravité / risque métier :** P2 — l'inventaire papier/Excel est souvent exigé pour la déclaration fiscale.
- **Correction (exécutée cycle 68) :** route `/rapports/ecarts-comptage` (responsable seul — jointure régularisations + valorisation à prix d'achat, xlsx 2 feuilles + pdf, totaux cumulés) ; carte d'export ajoutée dans `maquette/rapports.html` ; matrice des rôles complétée (`/rapports/stock` omis au cycle 67 + nouvelle route).
- **Dépendances :** C7-02 (même source de données). **Responsable :** développement (lot C).
- **Critère d'acceptation :** fichier téléchargé, totaux cohérents avec l'écran.
- **Tests requis :** pytest + Playwright.
- **Preuves (cycle 68) :** pytest `test_rapports.py` **7/7** (valorisation −25 000/+5 600, totaux, 403 agents, 422 formats/dates) ; Playwright **52/52** (téléchargement réel xlsx 5 680 o, pdf `%PDF`, carte absente pour les deux agents) ; PR #85.
- **Statut :** CLOS (cycle 68).

### C7-04 — Deuxième campagne de comptage physique réel
- **Exigence source :** chantier C9/C10 (tests humains) ; `loop-state.md`.
- **État :** une campagne a été menée ; la seconde campagne (recette croisée) reste à faire.
- **Preuve :** `loop-state.md` C9/C10.
- **Gravité / risque métier :** P1 — la recette inventaire exige deux campagnes indépendantes concordantes.
- **Correction :** organiser la campagne avec le guide testeur.
- **Dépendances :** temps humain, stock physique. **Responsable :** TEST HUMAIN.
- **Critère d'acceptation :** deux campagnes concordantes + PV.
- **Tests requis :** scénario complet + captures.
- **Statut :** BLOQUE_TEST_HUMAIN.

---

## C8 — Interfaces et parcours (86 %)

### C8-01 — Divergences d'affichage recensées (D1–D4 de la matrice)
- **Exigence source :** cycle 65 — divergences entre maquette et comportement réel.
- **État :** recensement soldé au cycle 69 — chaque divergence est soit acceptée volontairement en l'état, soit tracée vers l'écart ou la décision qui la porte. Aucune correction de code nécessaire (aucun libellé ne ment sur le comportement réel : vérifié sur `comptes.html` et `inventaire.html`).
- **Preuve :** `MATRICE_ROLES_AKUMA.md` §9 ; `RAPPORT_TESTS_ROLES.md` §5.
- **Gravité / risque métier :** P3.
- **Correction (exécutée cycle 69) :** statuer sur chaque divergence — D1 (inventaire refuse le responsable) et D2 (UI cumul = rôle principal) **acceptées en l'état** (gates volontaires, recommandations D8/D7 option 1, confirmation propriétaire) ; D3 (`utilisateur_caisse_id`) tracée → C5-01/D9 ; D4 (prix caissier) tracée → C3-01/D1 ; D5 (journal 61-64) tracée → C0-04.
- **Dépendances :** D7, D8, D9, D1 (confirmations propriétaire) + C0-04. **Responsable :** développement (lot B) pour le recensement.
- **Critère d'acceptation :** registre des divergences soldé.
- **Tests requis :** rejeu des suites concernées.
- **Preuves (cycle 69) :** pytest `test_cumul_roles.py` + `test_matrice_roles.py` **6/6** (API : responsable autorisé à compter, cumul honoré) ; Playwright `verifier-cablage.mjs` **94/94** (UI : gate inventaire, redirections, aucun prix pour l'agent) ; inspection `ventes.py:220-227` (D3 toujours exacte) ; PR #86.
- **Statut :** CLOS (cycle 69).

### C8-02 — Captures d'écran de référence
- **Exigence source :** `loop-state.md` cycle 60 — « captures obsolètes à refaire ».
- **État :** **vérifié ce cycle** — les captures `tableau-bord-*` / `inventaire-*` ont été régénérées le 2026-10-20 (18:47) ; `git status` propre prouve que le contenu du disque est **identique** à ce qui est versionné (dernier commit touchant ces fichiers : `e1e1dcd`, 2026-09-24) ; l'UI n'ayant pas changé depuis, les captures restent fidèles.
- **Preuve (exécutée ce cycle) :** `git log` + `git status` sur `maquette/captures/` ; horodatage disque.
- **Gravité / risque métier :** P3 — le TODO du cycle 60 est soldé par la vérification (plus de « refaire à faire », seulement « refaire si l'UI change »).
- **Correction :** retirer la mention obsolète du tableau des TODO ; ajouter une ligne au cycle 60–64 dans le journal (voir C0-04).
- **Dépendances :** C0-04. **Responsable :** développement.
- **Critère d'acceptation :** TODO fermé au tableau.
- **Tests requis :** aucun.
- **Statut :** CLOS.

---

## C9 — Tests et recette (60 %)

### C9-01 — Campagne UX complète n°2 (tous parcours)
- **Exigence source :** chantier C9 — recette humaine.
- **État :** première campagne réalisée ; la seconde campagne de bout en bout (vente, stock, inventaire, caisse, comptes, rapports) sur la version courante reste ouverte. Fait écho à C4-03 et C7-04.
- **Preuve :** `loop-state.md` C9/C10 (BLOCKED_HUMAN_TEST).
- **Gravité / risque métier :** P1 — aucune montée à 99–100 % sur C9/C10 sans campagne complète documentée.
- **Correction :** exécuter le guide testeur poste par poste, fiche de retour par écran.
- **Dépendances :** fusions PR (pour tester la version fusionnée). **Responsable :** TEST HUMAIN.
- **Critère d'acceptation :** fiches de retour sans anomalie bloquante ; correctifs issus de la campagne traités (cycles dédiés).
- **Tests requis :** scénarios du GUIDE_TESTEUR + captures.
- **Statut :** BLOQUE_TEST_HUMAIN.

---

## C10 — Qualité et non-régression (58 %)

### C10-01 — Rapport de tests manuels consolidé et signé
- **Exigence source :** chantier C10 — « reste : cahier de recette + PV ».
- **État :** les tests automatisés couvrent largement le code, mais le rapport de campagne humaine consolidé (avec PV signé) n'existe pas encore.
- **Preuve :** `loop-state.md` C10.
- **Gravité / risque métier :** P1 — pièce attendue du dossier GO/NO-GO.
- **Correction :** consolider les fiches de la campagne C9-01 en PV.
- **Dépendances :** C9-01. **Responsable :** PROPRIÉTAIRE (signature) + développement (consolidation).
- **Critère d'acceptation :** PV de recette signé au dossier C14.
- **Tests requis :** — (document).
- **Statut :** BLOQUE_PROPRIETAIRE.

### C10-02 — Test multi-postes / simultané
- **Exigence source :** C10 (deux caisses en parallèle sur le même site).
- **État :** les tests de concurrence SQL existent (03_concurrence.sh) ; le test réseau à deux postes n'a pas été mené.
- **Preuve :** `db/tests/03_concurrence.sh` (SQL uniquement).
- **Gravité / risque métier :** P2 — le magasin physique prévoit deux postes.
- **Correction :** deux postes réels ou deux navigateurs distincts saisissant simultanément.
- **Dépendances :** 2ᵉ poste (C0-03). **Responsable :** TEST HUMAIN.
- **Critère d'acceptation :** ventes simultanées sans conflit, journaux corrects.
- **Tests requis :** scénario parallèle + vérification base.
- **Statut :** BLOQUE_TEST_HUMAIN.

---

## C11 — Sécurité (85 %)

### C11-01 — Faux positif Kaspersky sur `sauvegarder.ps1`
- **Exigence source :** incident récurrent — `PDM:Trojan.Win32.Generic` en quarantaine à chaque exécution du script de sauvegarde.
- **État :** script livré et fonctionnel (cycle 40) mais neutralisé par l'antivirus du poste de développement ; exclusion ou restauration = action sur la machine du propriétaire.
- **Preuve :** mémoire projet (fichier dédié) ; incident reproduit à chaque cycle de sauvegarde.
- **Gravité / risque métier :** P1 — tant que l'antivirus bloque, la sauvegarde chiffrée n'existe pas sur ce poste ; sur le poste de production, le même faux positif pourrait surgir au pire moment.
- **Correction :** exclusion ciblée du dossier/outil ou restauration + signalement du faux positif à l'éditeur AV.
- **Dépendances :** droits administrateur poste. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** sauvegarde exécutée sans quarantaine, copie chiffrée présente.
- **Tests requis :** exécution réelle + restauration.
- **Statut :** BLOQUE_PROPRIETAIRE.

### C11-02 — Vérifier le poste cible : lockfile figé, venv, empreinte de l'exécutable
- **Exigence source :** C0/C11 — environnement de production maîtrisé.
- **État :** livré dans PR #80 (exécutable reconstruit sur lockfile) et PR #81 (dossier) ; à revérifier sur le poste cible à l'installation.
- **Preuve :** PR #80/#81 ouvertes.
- **Gravité / risque métier :** P2.
- **Correction :** checklist d'installation (déjà dans le dossier) exécutée sur place.
- **Dépendances :** C0-01 (soldée). **Responsable :** développement lors de l'installation accompagnée.
- **Critère d'acceptation :** empreinte SHA de l'exe conforme, venv issu du lockfile.
- **Tests requis :** `pip-compile --check` équivalent + hash.
- **Statut :** EN_COURS (le contenu à vérifier est sur `main` depuis le cycle 73 ; exécution de la checklist au jour J, sur le poste cible).

---

## C12 — Sauvegarde et reprise (97 %)

### C12-01 — Restauration complète vérifiée sur un second poste
- **Exigence source :** C12 — RTO 2 h prouvé.
- **État :** sauvegarde chiffrée + restauration prouvées sur le poste de développement (cycle 40) ; non rejouées sur un second poste indépendant.
- **Preuve :** `loop-state.md` C12 ; C0-03.
- **Gravité / risque métier :** P1 — la reprise réelle est le cœur du RTO.
- **Correction :** opération restore sur 2ᵉ poste, connexion, contrôle de comptages.
- **Dépendances :** C0-03, C0-02. **Responsable :** TEST HUMAIN.
- **Critère d'acceptation :** base restaurée fonctionnelle sur 2ᵉ poste, PV signé.
- **Tests requis :** `restaurer.ps1` + scénario de reprise.
- **Statut :** BLOQUE_TEST_HUMAIN.

### C12-02 — Alerte en cas d'échec de sauvegarde
- **Exigence source :** C12 — notification d'échec ; décision validée le
  2026-10-23 (alerte visible ET testée).
- **État :** *livré et testé (cycle 75-F, PR #98)* — endpoint interprété
  `GET /exploitation/etat-sauvegarde` (quatre états fermés : succès daté /
  échec motivé / absent / inconnu — jamais de succès sans preuve), bandeau
  persistant `role=alert` en haut du tableau de bord nommant le motif
  consigné par le script, état absent = attention explicite, illisible =
  « protection non confirmée » ; pastille d'alerte sur la carte.
- **Preuve :** pytest `test_exploitation_etat.py` (8 tests via faux fichiers
  `QF_FICHIER_ETAT_SAUVEGARDE` — `sauvegarder.ps1` jamais exécuté, limite §7)
  + exploitation 14/14 + routes 65/65 + câblage 101/101 (bandeau : 4 états) ;
  route déclarée dans la matrice des rôles (403 agents).
- **Gravité / risque métier :** P2 — levé.
- **Correction :** livrée (cycle 75-F).
- **Dépendances :** décision obtenue (2026-10-23). **Responsable :** —.
- **Critère d'acceptation :** alerte testée en échec simulé — fait.
- **Tests requis :** rejoués (voir preuve).
- **Statut :** CLOS (cycle 75, PR #98).

### C12-03 — Cause racine : résilience du service PostgreSQL
- **Exigence source :** C12 — comportement au redémarrage / coupure de courant.
- **État :** service local non enregistré (voir C0-02) ; la cause racine de l'arrêt inopiné observé lors des cycles reste à investiguer sur le poste cible.
- **Preuve :** `loop-state.md` C12.
- **Gravité / risque métier :** P2 — un arrêt silencieux du moteur bloque toute la caisse.
- **Correction :** investigation sur poste cible (journal Windows + PostgreSQL) ; service enregistré + surveillance de présence.
- **Dépendances :** C0-02. **Responsable :** développement lors de l'installation.
- **Critère d'acceptation :** service démarré, test de coupure simulé documenté.
- **Tests requis :** arrêt/redémarrage contrôlé.
- **Statut :** OUVERT.

---

## C13 — Intégration continue (100 %)

### C13-01 — Job Playwright dans GitHub Actions
- **Exigence source :** cycle 62 — CI Playwright.
- **État :** *acquitté (cycle 73)* — la PR #79 est fusionnée dans `main`
  (commit 13c1338) ; le workflow `main` porte désormais les deux jobs
  `pytest` **et** `playwright` (postgres:17 isolé sur 5433, **13 suites
  depuis le cycle 73**, délai 600 s par suite, artefacts d'échec conservés
  7 jours).
- **Preuve (exécutée cycle 73) :** `.github/workflows/ci.yml` sur `main`
  (jobs pytest ligne 26, playwright ligne 105) ; le job playwright a tourné
  vert sur chacune des 13 fusions du cycle 73 (ex. run 39894259707 :
  playwright 8 min 39 s, 12 suites / 431 contrôles) **et sur la PR du
  cycle 73 avec la 13ᵉ suite (run 39900668426 : « 13/13 suites réussies »,
  roles compris — première exécution de `roles` en CI)**.
- **Gravité / risque métier :** P2 — levé.
- **Correction :** fusion de PR #79 — exécutée.
- **Dépendances :** — **Responsable :** développement (autorisé mission 1 du cycle 73).
- **Critère d'acceptation :** workflow « CI — pytest et Playwright » vert sur `main` — **atteint**.
- **Tests requis :** le job lui-même (chaque push) — vert sur les 13 fusions + PR cycle 73.
- **Statut :** CLOS (cycle 73).

### C13-02 — Régression complète automatisée en CI
- **Exigence source :** C13 — « régression complète Playwright ».
- **État :** correction livrée en deux parties au cycle 71 : (1) orchestrateur
  local — `db/outils/verifier_tout.sh` enchaîne désormais les **13 suites**
  (il en oubliait 5 : routes, comptes, caisse, ux, roles) avec un délai
  maximal par suite (600 s, code 124 explicite) et un `--basetemp` pytest
  (contournement documenté du symlink résiduel du cycle 56) ; (2) tableau de
  correspondance `maquette/verification/SUITES_CHANTIERS.md` (15 suites :
  mode, chantier(s), preuve, orchestration). La partie CI (12 suites) a été
  portée par la PR #79 ; **complétée au cycle 73 : `roles` ajoutée au
  tableau `SUITES` de `executer_suites_reelles.sh` (recommandation du
  cycle 71, exécutée) + repli PATH psql dans `verifier-roles.mjs` —
  prouvé par le run CI 39900668426 de la PR du cycle 73
  (« 13/13 suites réussies », roles compris)**.
- **Preuve (exécutée au cycle 71) :** 3 exécutions réelles de
  `verifier_tout.sh` — (1) blocage réel de la suite comptes (navigateur
  jamais fermé, défaut du cycle 61 corrigé dans PR #78 non fusionnée :
  correctif identique reporté) ; (2) 3 échecs honnêtes — nettoyage pytest
  (symlink cycle 56, `--basetemp` ajouté), course d'inventaire (correctif
  cycle 62 de PR #79 reporté), script npm `ux` **jamais commité** (ajouté) ;
  (3) **exécution complète verte : SQL (protections + habilitations +
  concurrence + aller/retour des migrations) OK, pytest 334/334, 13/13
  suites / 477 contrôles / 0 échec, EXIT=0**. Les 5 suites « oubliées » sont
  toutes passées (routes 65, ux 27, comptes 26, caisse 24, roles matrice OK).
- **Gravité / risque métier :** P2 — le risque de « suite oubliée » croît avec le nombre de suites.
- **Correction :** script orchestrateur « toutes les suites » rejoué en CI (ou matrice) ; tableau de correspondance suites↔chantiers.
- **Dépendances :** C13-01 (PR #79, fusion propriétaire). **Responsable :** développement (lot B).
- **Critère d'acceptation :** une commande unique rejoue l'ensemble, résultat consolidé — **satisfait localement** (`bash db/outils/verifier_tout.sh`, bilan + code de sortie) et **en CI** (job playwright du workflow, vert sur `main` depuis la fusion de #79 au cycle 73).
- **Tests requis :** le script orchestrateur — preuve cycle 71 (3 exécutions, la 3ᵉ entièrement verte) + **preuve fraîche cycle 73** sur le nouveau `main` (journal du cycle 73).
- **Statut :** CLOS (cycle 73 — fusion des PR #79 et #88, condition de clôture énoncée au cycle 71).

---

## C14 — Dossier de recette et mise en production (76 %)

### C14-01 — Versions candidates non fusionnées
- **Exigence source :** cycle 63/64 — exécutable + dossier d'installation.
- **État :** *acquitté (cycle 73)* — les PR #80 (Akuma.exe reconstruit,
  28,8 Mo) et #81 (dossier `INSTALLATION/` + guide testeur, schéma, outil
  premier responsable) sont fusionnées ; `main` = `d0fa264` porte la version
  candidate de référence de la recette finale.
- **Preuve (exécutée cycle 73) :** `server/fabrication/dist/` versionné +
  `INSTALLATION/` (README, CHECKLIST_INSTALLATION, PREUVE_SIMULATION) présents
  sur `main` ; CI verte sur les fusions #80/#81 ; exe reconstruit et exécuté
  sur le nouveau `main` au cycle 73 (journal).
- **Gravité / risque métier :** P1 — levé.
- **Correction :** fusion dans l'ordre — exécutée.
- **Dépendances :** — **Responsable :** développement (autorisé mission 1 du cycle 73).
- **Critère d'acceptation :** `main` contient exe + dossier ; CI verte — **atteint**.
- **Tests requis :** CI — verte.
- **Statut :** CLOS (cycle 73).

### C14-02 — PV de recette + dossier GO/NO-GO complet
- **Exigence source :** objectif final LOOP — « dossier de recette complet ».
- **État :** pièces disponibles ou planifiées (rapports, matrices, campagnes) ; la consolidation en dossier de recette avec **PV signé** et **rapport de risques résiduels** reste à produire (lot E).
- **Preuve :** `loop-state.md` C14 (65 %) ; plan des lots 67+.
- **Gravité / risque métier :** P1 — la décision GO/NO-GO se prend sur ce dossier.
- **Correction :** lot E : version candidate figée, guides, protocoles d'import, PV, plan de retour arrière, checklists J-1/Jour J, rapport de risques résiduels.
- **Dépendances :** C0-01, C9-01, C10-01, C12-01, décisions D1–D13. **Responsable :** développement (consolidation) + PROPRIÉTAIRE (signature).
- **Critère d'acceptation :** dossier complet, PV signé, GO/NO-GO consigné.
- **Tests requis :** — (document + reprises d'essais cités).
- **Statut :** BLOQUE_PROPRIETAIRE (ultime signature).

### C14-03 — Procédure de transfert (escrow)
- **Exigence source :** lot E — « transfert si dépendance à un tiers ».
- **État :** `NOTE_DE_TRANSFERT.md` rédigée à la racine (8 sections : contenu
  du dépôt, architecture, modèle de comptes, reconstruction from scratch,
  sauvegarde/restauration, état des décisions et risques, contacts/secrets à
  compléter par le propriétaire, ordre de lecture). Aucune donnée nominative
  inventée : la section contacts est volontairement en attente de saisie
  propriétaire.
- **Preuve :** relecture vérifiée au cycle 72 — 22/22 chemins cités existent
  (contrôle automatisé), remote git conforme, faits spot-checkés (migration
  023 : SECURITY DEFINER + garde-fou second compte ; 3 rôles métier dans
  `db/tests/02_habilitations.sql` ; AES-256 dans `sauvegarder.ps1` ; 102
  fichiers de migrations 000→050 ; « 334 tests pytest » = exécution réelle
  du cycle 71). **Cycle 73 :** le contenu est désormais réellement sur
  `main` via la PR #90 (`NOTE_DE_TRANSFERT.md`, 8 674 octets, vérifié sur
  `main` = `d0fa264`) — la PR #89 ayant été fusionnée par erreur dans sa
  base empilée, corrigée sans réécriture d'historique.
- **Gravité / risque métier :** P3 — dépendance à la connaissance du projet.
- **Correction :** note de transfert (architecture, comptes, procédures de restauration, contacts).
- **Dépendances :** lot E. **Responsable :** développement.
- **Critère d'acceptation :** note présente et relue.
- **Tests requis :** relecture.
- **Statut :** CLOS (livré au cycle 72, PR #89).

---

## Tableau de bord des décisions associées

| Décision | Écart(s) lié(s) | Statut |
|----------|-----------------|--------|
| D1 prix caissier | C3-01, C8-01 | BLOQUE_PROPRIETAIRE |
| D2 paiements mixtes | C1-01 | **VALIDÉE (2026-10-23) — implémentée, C1-01 CLOS (cycle 75)** |
| D3 fond caisse / seuil écart | C6-01, C5-01 (afférent) | BLOQUE_PROPRIETAIRE |
| D4 seuil remises | C5-02 (+ C1-04 drift seed) | **VALIDÉE (2026-10-23) — implémentée, C5-02 CLOS (cycle 75)** |
| D5 ventilation HT/TTC | C1-02 | **VALIDÉE (2026-10-23)** — audit TTC cycle 75-G |
| D6 durée session | — (décidée 480, confirmation rétrospective) | **VALIDÉE (2026-10-23) — tests cycle 75-E** |
| D7 cumul rôles UI | C3-03 (livré cycle 43) | **VALIDÉE (2026-10-23) — implémentation cycle 75-D** |
| D8 inventaire responsable | C3-02 | **VALIDÉE (2026-10-23) — comportement conforme, preuve par tests cycle 75-D** |
| D9 utilisateur_caisse_id | C5-01 | **VALIDÉE (2026-10-23) — implémentée, C5-01 CLOS (cycle 75)** |
| D10 2FA | C2-02 | **VALIDÉE (2026-10-23 — reportée après V1, mesures compensatoires) — cycle 75-E** |
| D11 Kaspersky | C11-01 | BLOQUE_PROPRIETAIRE |
| D12 tests physiques / GO | C9-01, C10-01, C12-01, C14-02 | BLOQUE_PROPRIETAIRE / TEST HUMAIN |
| D13 fusions PR | C0-01, C13-01, C14-01 | **SOLDEE (cycle 73** — 12 fusions + #90 exécutées ; restent le sort de la PR #60, la PR #92 et la pile cycle 75 #93→#100, décisions propriétaire**)** |
| C12-02 alerte sauvegarde | C12-02 | **VALIDÉE (2026-10-23) — implémentée et testée en échec simulé, C12-02 CLOS (cycle 75-F, PR #98)** |

**Confirmations de paramètres restantes (6 lignes `a_decider=TRUE`, base du
2026-10-23 après migration 051)** : `boutique_numero_contribuable`,
`boutique_telephone`, `contact_support_technique`, `seuil_alerte_plancher`,
`seuil_ecart_caisse_tolere` (C6-01), `tentatives_max_connexion` (C2-01) —
plus la confirmation écrite du `plafond_vraisemblance_comptage` (C7-01).
*Le seuil de remises (`seuil_remise_validation_pct`) est sorti de cette liste
au cycle 75 : décidé à 10 % (migration 051, décision D4).*

---

*Règle de tenue : ce registre se met à jour à chaque cycle correctif (statuts,
preuves). Un écart ne passe à CLOS que sur preuve d'exécution réelle — jamais
par estimation.*

## Décisions propriétaire du 24/10/2026 — exécution Codex

Référence : instruction explicite du propriétaire du 24/10/2026. Portée et contrat : CONTRAT_DECISIONS_20261024.md. Responsable métier : propriétaire ; responsable technique : Codex, coordination Qoder pour ventes/interface/supervision.

- D-N1 : plafond 10 % effectifs sur toute la vente, toutes remises confondues ; au-delà, approbation serveur du responsable et trace. VALIDÉE ; correction/tests EN_COURS.
- D-N5 : alerte à 60 minutes depuis la dernière sauvegarde complète et vérifiée ; un essai échoué/incomplet/non vérifié ne remet pas le délai à zéro. VALIDÉE ; correction/tests EN_COURS.
- D1 : caissier autorisé aux prix de vente TTC et montants ; achats, coûts et marges interdits, y compris indirect/API/export. Droits comptable non tranchés. VALIDÉE ; audit/tests EN_COURS.
- C2-01 : cinq échecs consécutifs, verrouillage temporaire 15 minutes ; concurrence/comptage/contournement/DoS à vérifier. VALIDÉE ; correction/tests EN_COURS. Remplace l'ancien déverrouillage exclusivement manuel.
- Les scores restent inchangés ; décision ≠ preuve de correction. Q1–Q6 restent au comptable.

## Livraison Codex des décisions du 24/10/2026 — PR #110

- Socle d'intégration : origin/main 546fa957571b7d1c105440889376efacd442752b (#104/#105/#106 inclus). Le brouillon #107 est remplacé par #110, branches conservées ; aucune fusion GitHub.
- D-N1, D-N5, D1 et C2-01 : VALIDÉES métier le 24/10 ; corrections techniques en revue dans #110, preuves détaillées dans RAPPORT_DECISIONS_20261024_CODEX.md et les commentaires de la PR. Aucune clôture globale ni score relevé par la décision seule.
- Contrôles locaux : 41 pytest ciblés ; SQL protections 202/202, habilitations 55/55, concurrence 6/6 et 055 ; migration 054→055/inverse/réapplication, inverse refusée avec audit intact ; charge 20 refus concurrents et un compte distinct accepté ; responsable secondaire HTTP 201, auteur correctement tracé.
- Dernière CI complète avant les ultimes contrôles réseau/cache : 6d0ebe4, pytest/13 suites verts. La CI du commit complet est à vérifier sur #110 ; aucun succès de ce nouveau commit n'est anticipé dans ce journal.
- 055 demeure réservée à cette livraison, utilisée une seule fois ; aucun fichier 000–054 réécrit. Pas de nouvelle réservation ni migration concurrente.
- D-N5 : producteur en quarantaine non exécuté et non qualifié ; alerte prudente sur son ancien format non vérifié. Droits comptable et Q1–Q6 toujours réservés. Scores de référence inchangés : C1 96 %, C2 90 %, C3 88 %.
- Fiches historiques publiées dans #109 (CI verte), D1/C2-01 actualisées. Rejeu des trois défauts post-#103 AVANT effectué sur 546fa95 ; APRÈS et verdict en attente de la PR qoder/correctifs-post-103. Aucune branche tierce modifiée. verif-integration conservé.
