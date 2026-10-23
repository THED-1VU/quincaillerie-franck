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

40 écarts recensés, dont **8 clôturés par vérification ou livraison** (C4-01 et
C8-02 vérifiés au cycle 66 ; C4-02 livré au cycle 67 ; C1-04, C7-02 et C7-03
livrés au cycle 68 ; C8-01 soldé au cycle 69 ; C0-04 reconstruit au cycle 70).
32 écarts ouverts :

| Gravité | Total | Détail | Actionnable par le développement |
|---------|:-----:|--------|:--------------------------------:|
| P0 | **0** | aucun écart d'intégrité, de comptabilité ou de sécurité | — |
| P1 | **17** | 11 BLOQUE_PROPRIETAIRE + 6 BLOQUE_TEST_HUMAIN | 0 |
| P2 | **11** | 8 BLOQUE_PROPRIETAIRE / TEST HUMAIN / fusion PR | 2 |
| P3 | **4** | 3 BLOQUE_PROPRIETAIRE (confirmations) | 1 |
| **Total ouverts** | **32** | 19 BLOQUE_PROPRIETAIRE · 7 BLOQUE_TEST_HUMAIN · 6 EN_COURS/OUVERT | **3** |

Lecture : **aucun écart d'intégrité**. Le chemin vers 99–100 % se joue sur
trois catégories : (1) décisions du propriétaire déjà répertoriées dans
`DECISIONS_PROPRIETAIRE.md` (D1–D13) ; (2) validations humaines (campagnes,
impression, 2ᵉ poste) ; (3) **onze fusions Git** réservées au propriétaire
(#78 → #88 dans l'ordre ; hors #60, doc ancienne — « fusionner ou fermer »
comme décidé au cycle 56). Le développement garde **3 écarts actionnables**
(C12-03, C14-03, C11-02) traités cycle par cycle ;
les correctifs codables mais suspendus à une décision
(C1-01, C1-02, C2-02, C5-01, C5-02, C6-01, C6-02) démarreront dès que les
décisions D2–D5, D9, D10 tombent.

**Rattrapage d'en-têtes de score (cycle 71)** — les en-têtes de sections
suivent désormais les scores prouvés par cycle : C4 77→**78** (cycle 67),
C7 65→**67** (cycle 68), C8 85→**86** (cycle 69), C13 76→**77** (cycle 71,
C13-02). Aucune de ces corrections n'est un score nouveau : ce sont des
reportages de preuves déjà établies.

---

## C0 — Infrastructure et dépôt (86 %)

### C0-01 — Fusions des PR #78 → #82 en attente
- **Exigence source :** PROMPT MAÎTRE (« fusion des PR = propriétaire uniquement ») + D13.
- **État :** 5 PR ouvertes empilées : #78 (cycle 61 régression), #79 (CI Playwright), #80 (exe cycle 63), #81 (dossier installation cycle 64), #82 (matrice rôles cycle 65).
- **Preuve :** `gh pr list` — les 5 au statut OPEN ; `main` à `c1784c6`.
- **Gravité / risque métier :** P1 — chaque chantier livré mais non sur `main` ; la base commune dérive des branches, la recette finale ne peut pas se figer.
- **Correction :** fusion dans l'ordre #78 → #79 → #80 → #81 → #82 (+ #83 ce registre), rebase au besoin, CI verte à chaque étape.
- **Dépendances :** approbation propriétaire. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** `main` contient tous les cycles 61–66, CI verte, aucun conflit masqué, historique linéaire sans force-push.
- **Tests requis :** CI GitHub complète (pytest) sur chaque PR ; régression complète une fois la dernière fusion faite.
- **Statut :** BLOQUE_PROPRIETAIRE.

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

## C1 — Base de données et intégrité (92 %)

### C1-01 — Paiements mixtes (addendum point a)
- **Exigence source :** addendum point a ; décision D2 (`DECISIONS_PROPRIETAIRE.md`).
- **État :** non construit — `ventes.mode_paiement` est une valeur unique (espèces/Mobile Money/chèque/virement), une vente ne peut pas combiner deux modes.
- **Preuve :** `db/migrations` (aucune table de répartition de paiement) ; `POST /ventes` accepte un mode unique.
- **Gravité / risque métier :** P1 — une vente réelle « 30 000 espèces + 20 000 Mobile Money » ne peut pas être enregistrée fidèlement.
- **Correction :** après décision D2 : table `ventes_paiements` (vente_id, mode, montant) avec contrôle du total — migration 051+.
- **Dépendances :** D2 (propriétaire). **Responsable :** développement après décision.
- **Critère d'acceptation :** une vente à deux modes enregistrée, tracée, exportée ; total vérifié par la base.
- **Tests requis :** protections SQL + pytest + Playwright parcours vente.
- **Statut :** BLOQUE_PROPRIETAIRE.

### C1-02 — Ventilation HT/TTC sur les documents (addendum point d, question 5)
- **Exigence source :** addendum point d ; décision D5.
- **État :** prix saisis TTC (décidé cycle 6, `prix_saisis_ttc=oui`), TVA 19,25 % calculée — mais la ventilation HT ligne à ligne n'est pas affichée sur le reçu/les rapports (seuls sous-total HT, montant TVA, total TTC de la vente le sont).
- **Preuve :** `server/app/routes/rapports.py` (colonnes de l'export) ; reçu PDF cycle 19.
- **Gravité / risque métier :** P2 — conformité de présentation fiscale des factures.
- **Correction :** décision D5 puis ajout de la colonne HT par ligne si requis.
- **Dépendances :** D5. **Responsable :** développement après décision.
- **Critère d'acceptation :** facture présentant HT/TVA/TTC conformément à la décision.
- **Tests requis :** pytest reçu + comparaison montants.
- **Statut :** BLOQUE_PROPRIETAIRE.

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

## C2 — Authentification et comptes (82 %)

### C2-01 — Confirmations : tentatives_max_connexion (5) — duree_session (480) appliquée
- **Exigence source :** cycle 38 ; `parametres.a_decider`.
- **État :** `tentatives_max_connexion=5` porte encore `a_decider=TRUE` (à confirmer) ; `duree_session_minutes=480` est décidé (2026-09-22) mais sa confirmation formelle reste à glaner.
- **Preuve (exécutée ce cycle) :** `SELECT cle, valeur, a_decider FROM parametres` sur base d'audit.
- **Gravité / risque métier :** P2 — verrouillage trop laxé ou trop strict selon la confirmation.
- **Correction :** confirmation orale/écrite → basculer `a_decider` à FALSE avec référence.
- **Dépendances :** propriétaire. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** les 5 lignes `a_decider=TRUE` restantes tranchées (voir C6-01, C7-01, C1-02).
- **Tests requis :** mise à jour du seed + contrôles `a_decider`.
- **Statut :** BLOQUE_PROPRIETAIRE.

### C2-02 — Deuxième facteur (2FA)
- **Exigence source :** décision D10.
- **État :** non construit (jeton signé + bcrypt + verrouillage seulement).
- **Preuve :** `DECISIONS_PROPRIETAIRE.md` D10.
- **Gravité / risque métier :** P2 — mitigation si un mot de passe fuite.
- **Correction :** après décision : TOTP ou équivalent hors-ligne.
- **Dépendances :** D10. **Responsable :** développement après décision.
- **Critère d'acceptation :** connexion avec 2ᵉ facteur, procédure de récupération documentée.
- **Tests requis :** pytest + parcours Playwright.
- **Statut :** BLOQUE_PROPRIETAIRE.

---

## C3 — Habilitations et cloisonnement (77 %)

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
- **État :** l'écran inventaire est réservé à l'agent stock ; le responsable ne peut ni saisir ni valider un comptage, seulement consulter les écarts. D8 demandait confirmation de cette répartition.
- **Preuve :** `MATRICE_ROLES_AKUMA.md` (table UI).
- **Gravité / risque métier :** P3 — praticité du jour J si l'agent stock est absent.
- **Correction :** confirmation D8 ou déléguer la saisie.
- **Dépendances :** D8. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** décision écrite.
- **Tests requis :** adaptateur Playwright si délégation.
- **Statut :** BLOQUE_PROPRIETAIRE.

### C3-03 — Cumul de rôles : affichage à l'écran (D7)
- **Exigence source :** décision D7 ; cycle 43 (livré).
- **État :** livré et testé (case « cumuler » + affichage des rôles dans `comptes.html`) ; D7 listée au registre des décisions pour confirmation formelle.
- **Preuve :** cycle 43 — pytest 229/229, `comptes.html`, PR associée.
- **Gravité / risque métier :** P3.
- **Correction :** confirmation écrite → fermer D7.
- **Dépendances :** propriétaire. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** D7 marquée décidée.
- **Tests requis :** aucun (déjà livré).
- **Statut :** BLOQUE_PROPRIETAIRE.

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

## C5 — Ventes et facturation (81 %)

### C5-01 — `utilisateur_caisse_id` toujours attribué au responsable
- **Exigence source :** addendum h (caissier fusionné) + décision D9.
- **État :** confirmé ce cycle — `POST /ventes` attribue **systématiquement** l'encaissement au compte responsable (`SELECT id FROM utilisateurs WHERE role='responsable' LIMIT 1`), même quand un agent comptabilité saisit réellement ; le commentaire du code (`server/app/routes/ventes.py:210-227`) documente ce désaccord comme volontairement non corrigé.
- **Preuve :** `server/app/routes/ventes.py:210-227` (lu ce cycle).
- **Gravité / risque métier :** P2 — le journal d'audit prête l'encaissement au mauvais utilisateur ; en cas de litige caisse, la traçabilité « qui a encaissé » est faussée ; contradiction visible avec la décision de fusion du rôle caissier (2026-09-13).
- **Correction :** attribuer `utilisateur_caisse_id` au compte authentifié ayant créé la vente (le jeton le porte déjà), en gardant une contrainte de rôle ; trancher D9 (journal actuel conservé ou corrigé rétroactivement — les environnements de test sont réinitialisés, aucune donnée réelle touchée).
- **Dépendances :** D9. **Responsable :** développement après décision.
- **Critère d'acceptation :** une vente saisie par `agent_comptabilite` porte son identifiant dans `utilisateur_caisse_id` ; tests qui l'affirment.
- **Tests requis :** pytest (vente par agent compta → colonne = son id) + protections SQL.
- **Statut :** BLOQUE_PROPRIETAIRE (point de décision) — correctif prêt à être codé.

### C5-02 — Seuil de validation des remises non décidé
- **Exigence source :** addendum f ; décision D4.
- **État :** mécanisme livré au cycle 42, **inactif** par défaut (`a_definir`) ; en environnement de test le paramètre est même absent du seed (voir C1-04). Aucun blocage par design tant que non décidé.
- **Preuve :** `server/app/routes/ventes.py:258-267` ; `DECISIONS_PROPRIETAIRE.md` D4 ; C1-04.
- **Gravité / risque métier :** P1 — tant qu'il n'y a pas de seuil, une remise de 99 % reste possible sans alerte (toléré par décision, à confirmer avant GO).
- **Correction :** décision D4 (pourcentage) → basculer le paramètre + activer le blocage/alerte décidé.
- **Dépendances :** D4. **Responsable :** PROPRIÉTAIRE puis développement.
- **Critère d'acceptation :** seuil en configuration, comportement (blocage ou alerte) conforme à la décision, tests.
- **Tests requis :** pytest dédiés + Playwright remise > seuil.
- **Statut :** BLOQUE_PROPRIETAIRE.

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
- **Dépendances :** C0-01, C0-02. **Responsable :** développement lors de l'installation accompagnée.
- **Critère d'acceptation :** empreinte SHA de l'exe conforme, venv issu du lockfile.
- **Tests requis :** `pip-compile --check` équivalent + hash.
- **Statut :** EN_COURS (PR ouvertes).

---

## C12 — Sauvegarde et reprise (95 %)

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
- **Exigence source :** C12 — notification d'échec.
- **État :** documentée comme **limite acceptée** (cycle 40, décision du propriétaire) : l'échec n'est notifié que dans le journal local.
- **Preuve :** `loop-state.md` C1 (cycle 40) — « notification d'échec documentée comme limite ».
- **Gravité / risque métier :** P2 — une sauvegarde silencieusement en échec pendant des semaines reste invisible.
- **Correction :** décision : mécanisme minimal (fichier d'alerte visible au démarrage de l'app + carte tableau de bord) ou acceptation écrite renouvelée.
- **Dépendances :** décision propriétaire (peut être glanée avec C12-03). **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** décision écrite ; si mécanisme : alerte testée en échec simulé.
- **Tests requis :** pytest (alerte) si mécanisme retenu.
- **Statut :** BLOQUE_PROPRIETAIRE.

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

## C13 — Intégration continue (77 %)

### C13-01 — Job Playwright dans GitHub Actions
- **Exigence source :** cycle 62 — CI Playwright.
- **État :** livré dans PR #79 ; `main` ne contient que le job pytest (« CI — tests pytest »). Tant que la PR n'est pas fusionnée, la CI ne joue pas les parcours navigateur.
- **Preuve :** `.github/workflows/ci.yml` sur `main` (un seul job) ; PR #79 ouverte.
- **Gravité / risque métier :** P2 — une régression UI peut atteindre `main` sans être vue (les suites restent jouées localement à chaque cycle).
- **Correction :** fusion de PR #79 (propriétaire) ; ajustement si la CI distante révèle des écarts d'environnement.
- **Dépendances :** C0-01 (ordre des fusions). **Responsable :** PROPRIÉTAIRE (fusion).
- **Critère d'acceptation :** workflow « CI — pytest + Playwright » vert sur `main`.
- **Tests requis :** le job lui-même (chaque push).
- **Statut :** EN_COURS (PR #79).

### C13-02 — Régression complète automatisée en CI
- **Exigence source :** C13 — « régression complète Playwright ».
- **État :** correction livrée en deux parties au cycle 71 : (1) orchestrateur
  local — `db/outils/verifier_tout.sh` enchaîne désormais les **13 suites**
  (il en oubliait 5 : routes, comptes, caisse, ux, roles) avec un délai
  maximal par suite (600 s, code 124 explicite) et un `--basetemp` pytest
  (contournement documenté du symlink résiduel du cycle 56) ; (2) tableau de
  correspondance `maquette/verification/SUITES_CHANTIERS.md` (15 suites :
  mode, chantier(s), preuve, orchestration). La partie CI reste portée par la
  PR #79 (12 suites) — ajout de `roles` recommandé après sa fusion (une
  entrée dans le tableau `SUITES` du script ; le job exporte déjà
  `PGDATABASE_PISTE`).
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
- **Critère d'acceptation :** une commande unique rejoue l'ensemble, résultat consolidé — **satisfait localement** (`bash db/outils/verifier_tout.sh`, bilan + code de sortie) ; satisfait en CI après fusion de la PR #79.
- **Tests requis :** le script orchestrateur — **rejoué 3 fois, preuves ci-dessus**.
- **Statut :** EN_COURS (PR #79 pour la partie CI, PR #88 pour l'outillage local et la correspondance ; clôture à la fusion des deux).

---

## C14 — Dossier de recette et mise en production (65 %)

### C14-01 — Versions candidates non fusionnées
- **Exigence source :** cycle 63/64 — exécutable + dossier d'installation.
- **État :** PR #80 (Akuma.exe reconstruit, 28,8 Mo) et PR #81 (dossier `QuincaillerieFranck_Test/` : guide testeur, schéma, outil premier responsable) ouvertes.
- **Preuve :** `gh pr list`.
- **Gravité / risque métier :** P1 — la version candidate de référence doit être sur `main` pour la recette finale.
- **Correction :** fusion dans l'ordre (après #78/#79).
- **Dépendances :** C0-01. **Responsable :** PROPRIÉTAIRE.
- **Critère d'acceptation :** `main` contient exe + dossier ; CI verte.
- **Tests requis :** CI.
- **Statut :** EN_COURS (PR ouvertes).

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
- **État :** non rédigé — le dépôt est autonome mais la procédure de reprise par un tiers n'est pas documentée.
- **Preuve :** absence de document de transfert à la racine.
- **Gravité / risque métier :** P3 — dépendance à la connaissance du projet.
- **Correction :** note de transfert (architecture, comptes, procédures de restauration, contacts).
- **Dépendances :** lot E. **Responsable :** développement.
- **Critère d'acceptation :** note présente et relue.
- **Tests requis :** relecture.
- **Statut :** OUVERT.

---

## Tableau de bord des décisions associées

| Décision | Écart(s) lié(s) | Statut |
|----------|-----------------|--------|
| D1 prix caissier | C3-01, C8-01 | BLOQUE_PROPRIETAIRE |
| D2 paiements mixtes | C1-01 | BLOQUE_PROPRIETAIRE |
| D3 fond caisse / seuil écart | C6-01, C5-01 (afférent) | BLOQUE_PROPRIETAIRE |
| D4 seuil remises | C5-02 (+ C1-04 drift seed) | BLOQUE_PROPRIETAIRE |
| D5 ventilation HT/TTC | C1-02 | BLOQUE_PROPRIETAIRE |
| D6 durée session | — (décidée 480, confirmation rétrospective) | BLOQUE_PROPRIETAIRE |
| D7 cumul rôles UI | C3-03 (livré cycle 43) | BLOQUE_PROPRIETAIRE (confirmation) |
| D8 inventaire responsable | C3-02 | BLOQUE_PROPRIETAIRE |
| D9 utilisateur_caisse_id | C5-01 | BLOQUE_PROPRIETAIRE |
| D10 2FA | C2-02 | BLOQUE_PROPRIETAIRE |
| D11 Kaspersky | C11-01 | BLOQUE_PROPRIETAIRE |
| D12 tests physiques / GO | C9-01, C10-01, C12-01, C14-02 | BLOQUE_PROPRIETAIRE / TEST HUMAIN |
| D13 fusions PR | C0-01, C13-01, C14-01 | BLOQUE_PROPRIETAIRE |

**Confirmations de paramètres restantes (5 lignes `a_decider=TRUE`, base d'audit du
2026-10-21) :** `boutique_numero_contribuable`, `boutique_telephone`,
`seuil_alerte_plancher`, `seuil_ecart_caisse_tolere` (C6-01),
`tentatives_max_connexion` (C2-01) — plus la confirmation écrite du
`plafond_vraisemblance_comptage` (C7-01).

---

*Règle de tenue : ce registre se met à jour à chaque cycle correctif (statuts,
preuves). Un écart ne passe à CLOS que sur preuve d'exécution réelle — jamais
par estimation.*
