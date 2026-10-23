# OPÉRATION 100 % — LOT B : RAPPORT FINAL (Qoder, 2026-10-23)

Mission du propriétaire : C5 (Ventes et facturation 88 % → 100 %),
C8 (Interfaces et parcours 86 % → 100 %), C12 (Sauvegarde et reprise
97 % → 100 %), en parallèle de Codex (C1/C2/C3). Ce rapport consolide
les livrables exigés : tableau des écarts, correctifs, preuves
d'exécution, fiches humaines, dépendances Codex, scores justifiés,
décisions bloquantes.

**Livraison** : PR **#103** (branche `operation-100-lot-b`), validée sur la
base `2dae406` (CI verte run 39973236711), puis **alignée sur `main`
`d745ead` au cycle 77** (fusion `76f3d5e` ; #100/#101/#102 intégrés) et
revalidée sur l'état combiné (pytest 396/396, 13/13 suites ; CI verte run
40035602067 sur `835e0fb` ; le run de consignation 40037134895 a révélé une
course de la suite `caisse`, défaut du TEST corrigé et re-prouvé — voir
`CYCLE_77_REVALIDATION.md` §5) — fusion par le propriétaire.

**Contraintes respectées, traçables dans chaque document** : aucune
production, aucune importation réelle, aucune exclusion antivirus ;
`db/outils/sauvegarder.ps1` jamais exécuté ni restauré ni commité
(quarantaine Kaspersky, audit par `git show` uniquement) ; aucun test
concurrent sur une base partagée (base dédiée `quincaillerie_lotb`,
port 8020, worktree dédié) ; invariants de base de données confiés à
Codex jamais touchés (aucune migration du Lot B — le correctif
`restaurer.ps1` est un script d'exploitation, pas un invariant) ;
tests automatisés jamais confondus avec validation humaine.

---

## 1. Tableau des écarts C5 / C8 / C12

| Chantier | Écart | État initial (registre) | État après Lot B | Preuve |
|---|---|---|---|---|
| C5 | Paiements mixtes D2 | 86–88 % (écart ouvert) | CLOS (cycle 75, fusionné via #100 → 335eb91) | 8 tests `test_paiements_mixtes_d2.py` + campagne N3 |
| C5 | Seuil remise D4 | ouvert | CLOS (cycle 75) | `test_seuil_remise_d4.py` + campagne N4/L1/L2/L3 |
| C5 | Encaissement attribué D9 | ouvert | CLOS (cycle 75) | `test_encaissement_d9.py` + campagne L9 |
| C5 | Parcours complet FCFA | jamais rejoué en un seul tenant | **PROUVÉ** : journée N1–N11 + limites L1–L11 par exécution | `test_campagne_fcfa_c5.py` 2/2, LOTB_CAMPAGNE_C5_FCFA.md §5 |
| C5 | Factures TTC sans inventer les règles | 6 questions comptables D5 listées | DOCUMENTÉ (aucune règle inventée, taux réels audités) | D5_AUDIT_TTC.md ; **décision comptable = propriétaire** |
| C8 | Divergences affichage D1–D4 | clos au cycle 75 (D1 vendue, D2/D3 testées) | re-prouvé par la régression du Lot B | run 4, 13/13 suites |
| C8 | Cumul rôles D7 (menus) | clos au cycle 75 | re-prouvé (35 contrôles suite roles) | run 4 |
| C8 | Parcours tous rôles + responsive | partiellement couvert | **PROUVÉ** : 505 contrôles, 5 largeurs 360→1920 | LOTB_C8_INTERFACES.md §1 |
| C8 | Compatibilité exécutable Windows | prouvée au cycle 73 sur main d0fa264 | reconstruit sur le code Lot B + campagne contre l'exe | LOTB_C8_INTERFACES.md §3 |
| C12 | Chaîne mécanique (chiffrement, intégrité, restauration, reprise, journalisation, détection, alerte) | 97 % | **PROUVÉE PAR EXÉCUTION** via doubles de test sûrs + vrai `restaurer.ps1` | LOTB_C12_SAUVEGARDE.md §2 |
| C12 | Hygiène fichiers clairs de `restaurer.ps1` | défaut réel trouvé (refus sans -Forcer = clair résiduel) | **CORRIGÉ** et re-prouvé (2 chemins de refus sans résidu, succès non régressé) | LOTB_C12_SAUVEGARDE.md §2.3 |
| C12 | Kaspersky / sauvegarder.ps1 | BLOCAGE SÉCURITÉ (quarantaine) | procédure S1–S6 prête, empreintes consignées ; **décision = propriétaire** | LOTB_C12_SAUVEGARDE.md §3 |
| C12 | Second PC C12-01 | non éprouvé | fiche P1–P9 prête (RTO ≤ 2 h) ; **épreuve physique = à dater/signer** | LOTB_C12_SAUVEGARDE.md §4 |
| C12 | C12-03 résilience service | hors périmètre | inchangé (installation, C0) | registre |

---

## 2. Correctifs livrés par le Lot B (branche `operation-100-lot-b`)

| Fichier | Nature | Preuve |
|---|---|---|
| `db/outils/verifier_tout.sh` | **Correctif d'isolation** : export `QF_TEST_DBNAME`, configuration éphémère `QF_CONFIG` partagée pytest+uvicorn (jamais le vrai `config.ini`), nettoyage au trap — supprime les deux trous d'isolation avec Codex (pytest et serveur Playwright visaient `quincaillerie_test` quoi qu'il arrive) | run 4 : suite SQL OK, pytest 368/369 (1 flake réseau, passé ensuite), 13/13 suites ; puis 371/371 en passe finale |
| `db/outils/restaurer.ps1` | **Correctif d'hygiène** : `Nettoyer-FichiersClairs` appelé sur TOUS les chemins de sortie (refus base existante, fichier roles introuvable), défini avant tout déchiffrement — l'invariant « jamais de clair au-delà de cette restauration » tient désormais sur chaque chemin | 2 refus sans résidu + restauration complète 38 tables exit 0 |
| `db/tests/c12/double_chiffrement.ps1` | **Nouveau** : double sûr du contrat de chiffrement C12 (même format `[sel][IV][AES-CBC][HMAC]`, PBKDF2 100 000 itérations, HMAC avant déchiffrement, temps constant) + autotest 11 contrôles — permet de prouver la mécanique SANS exécuter le script en quarantaine | **11/11**, Kaspersky silencieux |
| `server/tests/test_campagne_fcfa_c5.py` | **Nouveau** : campagne métier FCFA exigée par la mission (journée complète N1–N11 + limites/erreurs L1–L11) | **2/2 passed** (2026-10-23) |
| `db/outils/campagne_exe_lotb.sh` | **Nouveau** : campagne 13 suites CONTRE `Akuma.exe` sur base jetable dédiée (procédure cycle 63/73 rejouée pour le code Lot B) | LOTB_C8_INTERFACES.md §3.2 |
| `server/fabrication/quincaillerie_franck.spec` | aucun changement nécessaire — complétude du paquet vérifiée par diff (aucun écran nouveau depuis le cycle 73) | build + SHA-256 |

Aucune migration SQL, aucun invariant, aucun fichier C1/C2/C3 modifié.

---

## 3. Preuves d'exécution (résumé)

| Preuve | Résultat | Journal / document |
|---|---|---|
| Baseline run 4 (`verifier_tout.sh` corrigé, base `quincaillerie_lotb`, port 8020) | suite SQL OK (10 verdicts), base reconstruite OK, pytest OK*, 13/13 suites Playwright = **505 contrôles, 0 échec** | `%TEMP%\lotb_regress4.log` |
| *flake run 4 | 1 échec pytest transitoire `psycopg.ConnectionTimeout` à 97 % du run (368/369), PostgreSQL sain avant/après — reconnu flake d'infrastructure | idem, analysé LOTB_C8_INTERFACES.md §1 |
| Suite pytest complète incluant campagne C5 | **371 passed, 0 failed** (2026-10-23, 13 min 56 s, base `quincaillerie_lotb`) | `%TEMP%\lotb_pytest_final.log` |
| Campagne C5 FCFA (2 tests) | **2/2 passed** : mixte recette unique 6 500 + reçu PDF, remise 10 % → 5 850 / 10,01 % → 403 agent + 5849,35 resp, crédit FIFO 3250+3250, refus 3251, annulations, survente à 0 + écart tracé, D9 encaisseur réel | `lotb_pytest_c5e.log`, LOTB_CAMPAGNE_C5_FCFA.md §5 |
| C12 — autotest du double | **11/11** | LOTB_C12_SAUVEGARDE.md §2.1 |
| C12 — restauration réelle par le VRAI `restaurer.ps1` (dump chiffré par le double) | 38 tables, privilèges 556, RLS 13, migrations 52 — comptages identiques source↔restaurée ; app démarre sur la base restaurée, cloisonnement prix intact | LOTB_C12_SAUVEGARDE.md §2.2 |
| C12 — correctif hygiène re-prouvé | 2 refus sans résidu + succès 38 tables | LOTB_C12_SAUVEGARDE.md §2.3 |
| Akuma.exe reconstruit sur le code Lot B | 30 224 147 octets, SHA-256 `df936f62a4aa18283f7c671688273c0fe68f736289226ae71dc9cb8499ed8597` | LOTB_C8_INTERFACES.md §3.1 |
| Campagne 13 suites contre l'exe | **13/13 suites, 505 contrôles, 0 échec** (2026-10-23, base jetable `quincaillerie_lotbexe` supprimée après, journal exe 2 248 lignes 0 erreur) | `%TEMP%\lotb_campagne_exe.log`, LOTB_C8_INTERFACES.md §3.2 |

---

## 4. Fiches de recette humaine (exigées par la mission)

- **C5** : H1–H4 (impression ticket, reçu mixte sur papier 58 mm, litige
  prix, négociation remise au comptoir) — LOTB_CAMPAGNE_C5_FCFA.md §4.
- **C8** : fiches R1 (campagne UX), R2 (recette 3 rôles), R5
  (GO/NO-GO final) — CYCLE_73_FICHES_RECETTE.md, reprises sans
  duplication ; poste réel/kiosque listé LOTB_C8_INTERFACES.md §4.
- **C12** : P1–P9 second PC (RTO ≤ 2 h, PV signé) —
  LOTB_C12_SAUVEGARDE.md §4.

## 5. Dépendances avec Codex

Document de coordination complet : `COORDINATION_LOT_B_CODEX.md`
(état au cycle 76 ; **actualisé au cycle 77** : `main` = `d745ead` après
fusion de #100 → 335eb91, #101 → 75aaae0, #102 → d745ead ; migrations
053 et 054 intégrées ; prochain numéro libre **055**, à réserver dans
`loop-state.md` avant usage ; règle d'isolement ; pièges partagés).
Points saillants :

1. le correctif d'isolation du `verifier_tout.sh` (branche Lot B) est
   **obligatoire pour toute exécution parallèle** — sans lui, pytest et
   le serveur Playwright écrasent `quincaillerie_test` ;
2. conflits de documentation attendus sur `loop-state.md` et le
   registre — fusion en union, jamais de lignes perdues ;
3. aucune action du Lot B n'a touché les migrations, invariants,
   schémas, auth ou habilitations.

## 6. Scores justifiés

| Chantier | Score technique (automatisable) | Score global | Justification |
|---|---|---|---|
| **C5** | **100 % des critères reproductibles** : parcours complet, paiements mixtes, unicité, reçu détaillé, remises 10 %, validation > 10 %, encaissement réel, annulations/crédit/FIFO, cohérence caisse, survente tracée — 371 tests pytest + campagne FCFA 2/2 + suites vente/caisse/rapports du run 4 | **≈ 97 % — pas 100 %** | restent HUMAINS : H1–H4 (papier, litige, négociation) + décision comptable D5 (6 questions TTC/TVA) — la mission interdit d'inventer les règles fiscales |
| **C8** | **100 % des critères reproductibles** : 505/505 contrôles, 5 rôles + cumul, 5 largeurs, alertes, échappement, ET campagne contre l'exécutable reconstruit (13/13 suites, 505 contrôles, journal exe 0 erreur) | **≈ 95 % — pas 100 %** | restent HUMAINS : R1/R2/R5 (confort réel, 3 rôles en parallèle, GO/NO-GO) + poste/kiosque réel du magasin |
| **C12** | **100 % de la chaîne mécanique** : chiffrement, intégrité (HMAC avant déchiffrement), restauration 38 tables, reprise applicative, journalisation, détection/état, alerte visible — prouvé par doubles sûrs + vrai restaurer.ps1 | **≈ 98 % — pas 100 %** | l'ordre est explicite : pas de 100 % tant que P1–P9 (second PC) et S1–S6 (résolution sécurisée Kaspersky) ne sont pas signés par le propriétaire ; C12-03 hors périmètre |

**Aucun 100 % global n'est déclaré** : chacun des trois chantiers
conserve des maillons dont la mission réserve la preuve à un humain ou
au propriétaire. C'est la conclusion exigée par l'ordre
(« Ne pas confondre tests automatisés et validation humaine »).

## 7. Décisions bloquantes pour le propriétaire

1. **Fusionner la PR #103** (Lot B) — #100, #101 et #102 sont déjà
   fusionnées (`main` = `d745ead`) ; #103 a été alignée sur `main` au
   cycle 77 et revalidée sur l'état combiné (voir
   `CYCLE_77_REVALIDATION.md`).
2. **Kaspersky** : exécuter la procédure S1–S6 (LOTB_C12_SAUVEGARDE.md
   §3) — restauration du script depuis le dépôt avec vérification
   d'empreinte, soumission à l'antivirus PUIS exclusion ciblée au seul
   fichier, décision signée. Aucune action de ce type n'a été faite par
   le Lot B (interdite sans autorisation).
3. **Planifier la recette second PC** (P1–P9, RTO ≤ 2 h) avec le
   dossier livré et la version corrigée de `restaurer.ps1`.
4. **Comptable** : trancher les 6 questions D5 (D5_AUDIT_TTC.md) —
   C5 ne peut pas dépasser ~97 % sans elles.
5. **Planifier les campagnes humaines** : C8 (R1/R2/R5), C5 (H1–H4) —
   calendrier du cycle 74 disponible.
6. **Installation réelle / C12-03 / mode kiosque sur poste** : hors
   Lot B, exigent l'autorisation d'installation du propriétaire.
