# Cycle 78 — audit indépendant des décisions propriétaire du 24/10/2026

**Date** : 2026-10-24
**Socle audité** : `origin/main` = `7bebdeddc67d00d11b750238cca42b6d7154a21d` (#103 fusionnée)
**Worktree isolé** : `QuincaillerieFranck_Test_Cycle78`, branche `cycle-78-decisions-proprietaire`
**Base isolée** : `quincaillerie_c78` (migrations 000–054 + jeu d'essai), jamais la base partagée
**Harnais** : `server/tests/test_c78_audit_independant.py`
SHA-256 du harnais : `1a39410165b8237b67fcec63320350445719f80418a1c8ade71d8513dd20be97`
**Aucun score n'est modifié par ce cycle** : une décision validée n'est pas une correction testée.

## 1. Décisions inscrites (date, portée, responsable, statut)

Le contrat partagé et les entrées canoniques ont été publiés par Codex dans
`CONTRAT_DECISIONS_20261024.md`, `DECISIONS_PROPRIETAIRE.md`,
`REGISTRE_ECARTS_100.md` et `RAPPORT AVANCEMENT/loop-state.md`
(commit `46616aebf28aa53579631bcdf6cf26314abce492`, PR **#107**, DRAFT).
Qoder ne duplique pas ce texte : ce rapport en est l'audit indépendant.

| Décision | Date | Portée | Responsable | Statut au 24/10 |
|---|---|---|---|---|
| D-N1 | 2026-10-24 | Remise effective totale ≤ 10 % du catalogue pondéré par quantités, toutes remises confondues ; au-delà, approbation du responsable authentifié, contrôlée serveur et tracée | Propriétaire (métier) ; Codex (code) ; Qoder (audit) | VALIDÉE ; conformité **reproduite non conforme** sur `7bebded` |
| D-N5 | 2026-10-24 | Alerte visible dès 60 min d'ancienneté de la dernière sauvegarde complète ET vérifiée ; échec/incomplet/non vérifié ne réinitialise pas le délai | Propriétaire ; Codex (code) ; Qoder (audit) | VALIDÉE ; conformité **reproduite non conforme** sur `7bebded` |
| D1 | 2026-10-24 | Caissier = `agent_comptabilite` : prix de vente TTC et montants autorisés ; prix d'achat, coûts, marges interdits (API, export, SQL, indirect). Droits du comptable réservés au propriétaire | Propriétaire ; Qoder (audit) | VALIDÉE ; **aucun écart reproduit** sur le périmètre API/export/SQL |
| C2-01 | 2026-10-24 | 5 échecs consécutifs → verrou temporaire 15 min, atomique, non prolongeable, levé à l'expiration ; concurrence, contournement, comptage et déni de service vérifiés | Propriétaire ; Codex (schéma/auth) ; Qoder (audit) | VALIDÉE ; conformité **reproduite non conforme** sur `7bebded` |

## 2. Méthode et commande rejouable

```bash
export PATH=".../QuincaillerieFranck_Test/_pgdev/pgsql/bin:$PATH"
export QF_TEST_DBNAME=quincaillerie_c78
export QF_AUDIT_C78=1
python -m pytest -q -rA --tb=line \
  server/tests/test_c78_audit_independant.py \
  --basetemp=... -p no:cacheprovider
```

Le harnais est **gardé** par `QF_AUDIT_C78=1` : sans la variable, les 38 tests
sont ignorés (vérifié : `38 skipped`), donc la suite ordinaire et la CI ne
sont pas modifiées.

**Résultat sur `7bebded` : 10 réussis, 28 échoués en 81,44 s.**
Journal brut conservé hors dépôt :
`C:/Users/USER/AppData/Local/Temp/qf_c78_preuves/audit_7bebded_38.txt`.

Commits d'audit sur `cycle-78-decisions-proprietaire` (PR #108, DRAFT) :
`7d63ed5` (harnais + rapport), `2e1db30` (vérification du snapshot Codex +
test de cumul de rôles), `362d239` (constat Playwright).

## 3. Résultats par décision

### 3.1 D-N1 — remises cumulées : écart reproduit

| Cas | Attendu | Observé sur `7bebded` | Verdict |
|---|---|---|---|
| 9 % ligne + 9 % globale (article 1 × 1) | 403 | **201**, `remise_totale = 1117,35` FCFA sur 6500 (**17,19 %**) | NON CONFORME |
| 5 % ligne + 325 FCFA globale (= 10 % exact) | 201 | 201 | CONFORME (limite inclusive) |
| 5 % ligne + 325,01 FCFA globale (= 10,00015 %) | 403 | **201**, `remise_totale = 650,01` | NON CONFORME |
| 20 % sur 1 × 6500 + 0 % sur 10 × 3500 (= 3,13 % de la vente) | 201 | **403** (contrôle par ligne) | NON CONFORME (sur-blocage) |
| Agent + fausse approbation dans le corps JSON | 403 | **201**, `remise_totale = 1235` (**19 %**) | NON CONFORME |
| Responsable > 10 % : trace liée à la vente | 201 + ligne d'approbation | **`UndefinedTable: approbations_remises`** | MÉCANISME ABSENT |

Le contrôle actuel (`server/app/routes/ventes.py`, lignes ~313-373) vérifie
séparément la remise par ligne et la remise globale : chaque mécanisme reste
sous 10 %, leur **cumul** ne l'est pas. Il bloque aussi une remise de 20 % sur
une petite part d'une vente dont la remise effective totale est de 3,13 %.

Un huitième test couvre le **cumul de rôles** : un compte dont le rôle
principal est `agent_comptabilite` mais qui détient aussi `responsable`
(`utilisateurs_roles`, migration 035) doit pouvoir approuver. Il est rouge sur
`7bebded` (mécanisme absent) et reste rouge sur l'état de travail de Codex
pour une cause distincte, documentée en §6.2.

### 3.2 D-N5 — fraîcheur des sauvegardes : écart reproduit

La route `GET /exploitation/etat-sauvegarde` ne renvoie aujourd'hui que
`etat` (`succes`/`echec`/`absent`/`inconnu`) et `horodatage`. Constats :

- une preuve SUCCES de 60 s → `etat = succes`, **aucune** clé `alerte`,
  `age_secondes` ni `seuil_secondes` (`KeyError: 'alerte'`) ;
- à 3600 s et 3601 s → toujours `succes`, jamais `perime` ;
- SUCCES sans `complete`/`verifiee`, SUCCES non vérifié, état absent,
  horodatage invalide/futur/sans fuseau → toujours `succes` ou erreur de clé,
  jamais d'alerte ;
- aucune conservation d'une preuve vérifiée antérieure : un échec frais ne
  peut pas être comparé à la dernière preuve de 2 h.

**Constat de chaîne** : `db/outils/sauvegarder.ps1` écrit
`{horodatage, resultat, messages…}` **sans** `complete`/`verifiee` et avec un
horodatage **sans fuseau**. Le consommateur corrigé refusera donc cet état
comme preuve (comportement fail-safe correct), mais le producteur devra être
enrichi d'une vérification réelle du dump. Le contrat `CONTRAT_DECISIONS_20261024.md`
exclut explicitement le producteur en quarantaine de ce lot : c'est une
**limite déclarée**, pas une correction à revendiquer.

### 3.3 D1 — visibilité des prix : aucun écart reproduit

5 tests sur 5 réussis sur `7bebded`, y compris après ajout du contrôle PDF :

- `GET /articles` pour `agent_comptabilite` : `prix_vente` présent, aucune clé
  `prix_achat`, `cout_revient`, `marge`, `valorisation_achat`… même avec
  `?role=responsable&prix_achat=true` ;
- exports `/rapports/articles` **xlsx et PDF** : colonne `prix_vente`, aucune
  colonne interdite ; `/rapports/ventes` xlsx et
  `/rapports/ecarts-prix-vendeurs` JSON : aucune donnée d'achat/coût/marge ;
- `/rapports/stock`, `/rapports/ecarts-comptage`, `/tableau-bord/credit-client`,
  `/inventaire/ecarts`, `/exploitation/etat-sauvegarde` → **403** ;
- SQL direct : `qf_agent_comptabilite` lit `prix_vente` mais reçoit
  `InsufficientPrivilege` sur `prix_achat`, `SELECT * FROM articles` et
  `historique_prix_articles` ;
- cumul `agent_comptabilite` + `agent_stock` : aucun privilège de colonne
  supplémentaire.

**Limites** : la décision D1 réserve les droits du comptable au propriétaire
(non tranchés) ; l'écran navigateur `maquette/` n'a pas été rejoué dans ce
run, seuls l'API, les exports et SQL l'ont été. Aucun score n'est relevé.

### 3.4 C2-01 — verrouillage 5 échecs / 15 minutes : écart reproduit

| Cas | Attendu | Observé sur `7bebded` | Verdict |
|---|---|---|---|
| 5 échecs consécutifs → verrou 15 min | `verrouille_jusqua` posé, ~900 s | **colonne inexistante** ; verrou permanent par compteur | NON CONFORME |
| Bon/mauvais mot de passe pendant le verrou | 401, échéance inchangée | 401 (verrou permanent), aucune échéance | NON CONFORME |
| Expiration → bon mot de passe | 200, compteur à 0 | impossible sans colonne d'échéance | NON CONFORME |
| 4 échecs + succès + 4 échecs | pas de verrou (série rompue) | conforme | CONFORME |
| Identifiant inconnu × 6 | aucun compte verrouillé, 6 journaux | conforme | CONFORME |
| 10 échecs concurrents | compteur = 5, 10 journaux | conforme (`FOR UPDATE` déjà en place) | CONFORME (comptage) |
| Seuil décidé en base | `5`, `a_decider = false` | `5`, **`a_decider = true`** | NON CONFORME |

Le verrou actuel (migration 053) est **sérieux mais permanent** : il exige une
levée manuelle par le responsable et ne satisfait pas la décision « verrou
temporaire de 15 minutes ».

## 4. Tableau de livraison exigé

| Décision | Code concerné | Tests | Preuves | PR | Statut de clôture |
|---|---|---|---|---|---|
| D-N1 | `server/app/routes/ventes.py` (contrôles 313-373) ; à venir : `approbations_remises` + trace (migration 055, Codex) | 8 tests D-N1 (cumul, bornes 10 %/10,01 %, pondération, fausse approbation, trace, immuabilité, cumul de rôles) | `7bebded` : 7 rouges / 1 vert ; 201 à 17,19 % et 19 % ; `UndefinedTable` sur la trace. Snapshot WIP Codex : 7 verts / 1 rouge (cumul de rôles → 403, aucun contournement) | #107 (Codex, DRAFT) ; #108 (audit Qoder, DRAFT) | OUVERT — 3 corrections à porter dans #107 (§6) |
| D-N5 | `server/app/routes/exploitation.py` ; `maquette/tableau-bord.html` ; `maquette/verification/verifier-exploitation-reel.mjs` ; producteur `db/outils/sauvegarder.ps1` (exclu/quarantaine) | 17 tests D-N5 (fraîcheur, bornes 3599/3600/3601 s, complétude/vérification, preuve antérieure, absence/corruption, dates invalides, accès) | `7bebded` : 16 rouges / 1 vert, aucune alerte ni âge. Snapshot WIP Codex : 17/17 verts sur la route ; producteur réel non qualifié (fail-safe) ; fixture Playwright encore au format producteur actuel → 2 contrôles à adapter | #107 (Codex) ; #108 (audit Qoder) | OUVERT — consommateur vérifié sur snapshot ; suite Playwright et producteur à traiter |
| D1 | `demonstration.py`, `rapports.py`, `tableau_bord.py`, `inventaire.py`, GRANT 008/029/034 | 5 tests D1 (API, xlsx, PDF, JSON, 403, SQL direct, cumul) | `7bebded` : 5/5 verts. Snapshot WIP Codex : 5/5 verts ; le test d'export cumulé de Codex est rouge pour une attente contraire à la précédence C3 (§6.3), sans fuite constatée | Aucune correction nécessaire sur le périmètre audité | OUVERT — UI non rejouée, droits comptable non arbitrés, preuve humaine requise |
| C2-01 | `db/migrations/053_sessions_serveur.sql` (`verifier_connexion`), `server/app/routes/auth.py` ; 055 (Codex) | 8 tests C2-01 (5 échecs, non-prolongation, expiration, série, seuil, identifiant inconnu, concurrence ×2) | `7bebded` : 5 rouges / 3 verts ; colonne absente ; `(5, True)`. Snapshot WIP Codex : 7 verts / 1 rouge — dérive du seed `00_jeu_essai.sql` (§6.1), migration 055 vérifiée directement en psql (`5|f`) | #107 (Codex) ; #108 (audit Qoder) | OUVERT — corriger le seed puis rejouer |

## 5. Coordination et précautions respectées

- **Migration 055 réservée à Codex** (PR #107) : Qoder n'a créé ni 055 ni 056,
  n'a modifié aucun fichier du worktree Codex et n'a pas fusionné/poussé sur
  `main`.
- **Aucune exécution de `sauvegarder.ps1`** (quarantaine Kaspersky) ; aucune
  restauration. Le producteur est analysé par lecture seule.
- **PR #107** : DRAFT, tip publié `46616ae` (docs de réservation seulement) ;
  les changements de code (`auth.py`, `ventes.py`, `exploitation.py`,
  `tableau-bord.html`, migration 055) restent non commités dans son worktree.
  Qoder a vérifié une **copie en lecture seule** de ce diff dans un worktree
  séparé (§6), jamais dans son worktree actif ; la vérification finale sera
  refaite sur le SHA poussé.
- **PR #105** (ventes simultanées) : non fusionnée, non remplacée ; sa
  compatibilité avec D-N1/C2-01 reste à revalider avant toute fusion.

## 6. Vérification indépendante de l'état de travail de Codex (snapshot non commité)

Codex n'avait pas encore poussé son code au moment de l'audit (`#107` DRAFT,
tip `46616ae` = documentation de réservation seulement). Pour ne pas attendre,
Qoder a créé un worktree **séparé** (`_worktrees/qoder-verif-codex-20261024`,
détaché sur `46616ae`), y a appliqué une **copie en lecture seule** du diff non
commité de Codex (`auth.py`, `ventes.py`, `exploitation.py`,
`tableau-bord.html`) et de ses fichiers 055 / inverse / test, sans jamais
toucher à son worktree actif. Base dédiée `quincaillerie_c78_verif` clonée de
`quincaillerie_c78`, migration 055 appliquée directement — vérifié en psql :
`schema_migrations` max = `055`, colonne `verrouille_jusqua` présente,
paramètre `tentatives_max_connexion = 5`, `a_decider = false`.

Commandes (depuis `.../qoder-verif-codex-20261024/server`) :

```bash
QF_AUDIT_C78=1 QF_TEST_DBNAME=quincaillerie_c78_verif python -m pytest -q -rA \
  tests/test_c78_audit_independant.py      # harnais d'audit Qoder
python -m pytest -q tests/test_decisions_20261024.py   # suite de Codex
```

**Harnais Qoder : 36 réussis / 2 échoués en 89,32 s** ; journal
`qf_c78_preuves/audit_codex_wip_38.txt`. **Suite Codex : 23 réussis / 2
échoués en 40,73 s** ; journal `qf_c78_preuves/codex_tests_wip.txt`. Les
quatre échecs se répartissent en trois constats :

### 6.1 Dérive du seed — `tentatives_max_connexion` (échec Qoder)

`test_c201_seuil_decide_en_base` observe `(5, True)` alors que la migration 055
a bien écrit `(5, False)`. Cause : `db/tests/00_jeu_essai.sql` vide et
réamorce `parametres` **avant chaque test**, en réinscrivant
`tentatives_max_connexion` à `a_decider = TRUE` — la décision de 055 est donc
annulée dans la base de test à chaque rechargement. La migration elle-même est
correcte (vérifiée directement en psql). **Codex doit mettre le seed en
cohérence avec 055** (règle déjà inscrite en tête du seed : toute migration
ajoutant un paramètre doit s'y refléter).

### 6.2 Cumul de rôles et approbation D-N1 (échec Qoder)

Nouveau test `test_dn1_cumul_responsable_secondaire_peut_approuver` : compte
`magasin.compta` (rôle principal `agent_comptabilite`) auquel on ajoute
`responsable` dans `utilisateurs_roles` (migration 035), puis vente à
10 % + 10 %. La route l'accepte (`exiger_role` retient l'union et choisit
`responsable`), le contrôle Python passe, puis `tracer_approbation_remise`
refuse : `Approbation réservée au responsable authentifié` (contrôle
`utilisateurs.role = 'responsable'`, donc rôle **principal** seulement).
Réponse observée : **403 « Accès refusé »**, vente annulée par la transaction —
donc **aucun contournement**, mais un responsable pourtant habilité ne peut
pas approuver. Correctif attendu : tester l'appartenance à
`roles_utilisateur(auteur)` / `utilisateurs_roles` (qui contient déjà le rôle
principal depuis 035), pas la seule colonne `utilisateurs.role`.

### 6.3 Deux tests de la suite Codex échouent sur des attentes à corriger

1. `test_n1_approbation_authentifiee_atomique_et_immuable` attend
   `psycopg.errors.RaiseException` ; le déclencheur
   `interdire_suppression_journal()` lève `restrict_violation`
   (`RestrictViolation`). L'immuabilité est bien prouvée — c'est l'attente du
   test qui est fausse.
2. `test_d1_api_exports_et_acces_indirects_confidentiels[True]` attend
   `prix_vente` dans l'export `/rapports/articles?format=xlsx` d'un compte
   cumulant `agent_stock` + `agent_comptabilite`. Or `exiger_role` retient le
   **premier rôle déclaré par la route** (`agent_stock`, avant
   `agent_comptabilite`, `rapports.py:110-152`) : l'export servi est le
   catalogue stock, sans aucun prix. Comportement **préexistant** sur
   `7bebded` (C3 / ordre de déclaration), et **restrictif** — aucune fuite de
   prix d'achat. C'est l'attente du test qui doit être corrigée (ou la
   précédence des rôles à l'export arbitrée séparément, hors de cette
   mission).

### 6.4 Suite Playwright d'exploitation : fixture périmée (constat statique)

`maquette/verification/verifier-exploitation-reel.mjs` écrit un fichier d'état
au **format producteur actuel** — `{resultat: "SUCCES", horodatage:
"2026-09-25 12:34:56"}` (ni `complete`, ni `verifiee`, horodatage sans
fuseau) — puis attend `etat === "succes"` et le bandeau masqué
(lignes 80-86, 184-187). Avec le contrat D-N5, ce fichier est **non qualifié** :
la route répondra `inconnu` avec `alerte = true`, donc deux contrôles de la
suite échoueront. La suite n'a pas été modifiée par le diff de Codex : elle
doit être mise à jour dans #107 (fixture qualifiée + cas 60 min), sinon le job
Playwright de la CI échouera même si pytest est vert.

### 6.5 Ce que le snapshot prouve déjà

Sur le périmètre exécuté : cumul de remises bloqué, bornes 10 % / 10,01 %
exactes, pondération par quantités, fausses approbations ignorées, trace
d'approbation liée à la vente et immuable ; fraîcheur D-N5 (bornes
3599/3600/3601 s, complétude + vérification, preuve antérieure conservée,
absence/corruption/dates invalides) ; D1 API/export/PDF/JSON/SQL ; C2-01
verrou 15 min non prolongeable, expiration, série rompue, identifiant inconnu,
concurrence SQL ×2. Limites : snapshot **non commité** (diff copié), base
clonée, **aucune suite Playwright** rejouée sur ce snapshot, producteur D-N5
non exécuté (quarantaine), aucune validation humaine, **aucune fusion**.

## 7. Actions attendues dans #107 avant revue

1. Mettre `00_jeu_essai.sql` en cohérence avec 055 (§6.1).
2. Corriger les deux attentes de tests de la suite Codex (§6.3).
3. Arbitrer/corriger le contrôle de rôle de `tracer_approbation_remise` pour
   l'union des rôles (§6.2).
4. Lire `tentatives_max_connexion` depuis `parametres` au lieu du `seuil := 5`
   codé en dur — cohérent aujourd'hui, mais deux sources de vérité.
5. Mettre à jour la suite Playwright d'exploitation (fixture qualifiée
   `complete`/`verifiee` + fuseau, cas d'alerte à 60 min) — sinon deux
   contrôles échoueront (§6.4).
6. Prouver par Playwright l'alerte visible D-N5 et son passage à 60 min.
7. Producteur D-N5 : sans `complete`/`verifiee` et avec un horodatage sans
   fuseau, l'état réel restera `inconnu`/alerte — conforme au contrat
   (fail-safe), mais alerte permanente tant que le producteur n'est pas
   enrichi : décision/chantier séparé.

## 8. Conclusion du cycle

- Les décisions sont **inscrites** et leur contrat est publié (PR #107).
- Trois décisions (D-N1, D-N5, C2-01) présentent des **écarts reproduits par
  exécution réelle** sur `main` ; leurs corrections sont portées par Codex
  (migration 055), pas dupliquées par Qoder.
- La vérification indépendante du **snapshot de travail** de Codex montre que
  les corrections fonctionnent sur 36/38 tests d'audit et 23/25 tests Codex ;
  aucun contournement constaté. Les quatre échecs sont des **défauts de test
  ou de seed**, plus un cas de cumul de rôles à corriger (§6, §7).
- La suite Playwright d'exploitation encode encore l'ancien format de preuve
  (§6.4) : sans adaptation, le job Playwright de la CI échouera sur la branche
  corrigée même si pytest est vert.
- D1 est **conforme sur le périmètre API/export/SQL testé** ; sa clôture exige
  encore la preuve UI et l'arbitrage des droits du comptable par le
  propriétaire.
- Les scores C0–C14 restent **inchangés** : le snapshot n'est ni commité ni
  vert, aucune correction n'est prouvée sur un SHA poussé, et la CI n'a pas
  tourné dessus.
- Prochaine étape : commit poussé par Codex → rejeu des 38 tests d'audit,
  pytest complet, 13 suites Playwright et contrôles SQL sur le SHA poussé →
  mise à jour de ce rapport et de la PR #108.
