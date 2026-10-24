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

Le harnais est **gardé** par `QF_AUDIT_C78=1` : sans la variable, les 37 tests
sont ignorés (vérifié : `37 skipped`), donc la suite ordinaire et la CI ne
sont pas modifiées.

**Résultat sur `7bebded` : 10 réussis, 27 échoués en 86,90 s.**
Journal brut conservé hors dépôt :
`C:/Users/USER/AppData/Local/Temp/qf_c78_preuves/audit_7bebded.txt`.

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
| D-N1 | `server/app/routes/ventes.py` (contrôles 313-373) ; à venir : `approbations_remises` + trace (migration 055, Codex) | 7 tests D-N1 (cumul, bornes 10 %/10,01 %, pondération, fausse approbation, trace, immuabilité) | 6 rouges / 1 vert sur `7bebded` ; 201 à 17,19 % et 19 % ; `UndefinedTable` sur la trace | PR #107 (Codex, DRAFT) pour la correction ; PR d'audit Qoder à ouvrir | OUVERT — correction portée par #107, vérification indépendante à refaire sur son commit |
| D-N5 | `server/app/routes/exploitation.py` ; `maquette/tableau-bord.html` ; producteur `db/outils/sauvegarder.ps1` (exclu/quarantaine) | 17 tests D-N5 (fraîcheur, bornes 3599/3600/3601 s, complétude/vérification, preuve antérieure, absence/corruption, dates invalides, accès) | 16 rouges / 1 vert ; aucune alerte ni âge sur la route actuelle | PR #107 (Codex) ; producteur hors périmètre contractuel | OUVERT — consommateur en cours ; producteur non vérifiable sans exécution (interdite) |
| D1 | `demonstration.py`, `rapports.py`, `tableau_bord.py`, `inventaire.py`, GRANT 008/029/034 | 5 tests D1 (API, xlsx, PDF, JSON, 403, SQL direct, cumul) | 5/5 verts sur `7bebded` | Aucune correction nécessaire sur le périmètre audité ; PR d'audit Qoder | OUVERT — UI non rejouée, droits comptable non arbitrés, preuve humaine requise |
| C2-01 | `db/migrations/053_sessions_serveur.sql` (`verifier_connexion`), `server/app/routes/auth.py` ; 055 (Codex) | 8 tests C2-01 (5 échecs, non-prolongation, expiration, série, seuil, identifiant inconnu, concurrence ×2) | 5 rouges / 3 verts ; colonne `verrouille_jusqua` absente ; `(5, True)` au lieu de `(5, False)` | PR #107 (Codex) ; PR d'audit Qoder | OUVERT — correction portée par #107, vérification indépendante à refaire |

## 5. Coordination et précautions respectées

- **Migration 055 réservée à Codex** (PR #107) : Qoder n'a créé ni 055 ni 056,
  n'a modifié aucun fichier du worktree Codex et n'a pas fusionné/poussé sur
  `main`.
- **Aucune exécution de `sauvegarder.ps1`** (quarantaine Kaspersky) ; aucune
  restauration. Le producteur est analysé par lecture seule.
- **PR #107** : DRAFT au moment de l'audit, tip publié `46616ae` (docs de
  réservation seulement) ; les changements de code (`auth.py`, `ventes.py`,
  `exploitation.py`, `tableau-bord.html`, migration 055) étaient encore non
  commités dans son worktree. La vérification indépendante du code corrigé
  sera faite dans un worktree séparé dès qu'un commit sera poussé, jamais dans
  son worktree actif.
- **PR #105** (ventes simultanées) : non fusionnée, non remplacée ; sa
  compatibilité avec D-N1/C2-01 reste à revalider avant toute fusion.

## 6. Points à vérifier sur la branche de correction (constats d'audit)

1. **Immuabilité de l'approbation** : le déclencheur
   `interdire_suppression_journal()` lève `restrict_violation` (classe psycopg
   `RestrictViolation`), pas `RaiseException`. Le test de la branche #107 qui
   attend `RaiseException` échouera ; le test d'audit Qoder attend la bonne
   classe.
2. **Rôles cumulés et approbation** : `tracer_approbation_remise` contrôle
   `utilisateurs.role = 'responsable'` (rôle principal), alors que
   `exiger_role` retient l'union des rôles. Un compte dont le rôle principal
   est `agent_comptabilite` mais qui détient `responsable` en cumul peut être
   reconnu responsable par la route puis refusé par la fonction de trace
   (500). À arbitrer et couvrir.
3. **Seuil codé en dur** : la fonction 055 fixe `seuil := 5` au lieu de lire
   `parametres.tentatives_max_connexion`, pourtant mis à jour. Cohérent
   aujourd'hui, mais deux sources de vérité à surveiller.
4. **Producteur D-N5** : sans `complete`/`verifiee` et avec un horodatage
   sans fuseau, l'état réel restera `inconnu`/alerte. C'est conforme au
   contrat (fail-safe), mais l'exploitation verra une alerte permanente tant
   que le producteur n'est pas enrichi — décision/chantier séparé.
5. **Interface D-N5** : l'actualisation du bandeau sans rechargement et le
   passage à l'alerte à 60 min restent à prouver par Playwright sur la branche
   #107.

## 7. Conclusion du cycle

- Les décisions sont **inscrites** et leur contrat est publié (PR #107).
- Trois décisions (D-N1, D-N5, C2-01) présentent des **écarts reproduits par
  exécution réelle** sur `main` ; leurs corrections sont portées par Codex
  (migration 055), pas dupliquées par Qoder.
- D1 est **conforme sur le périmètre API/export/SQL testé** ; sa clôture exige
  encore la preuve UI et l'arbitrage des droits du comptable par le
  propriétaire.
- Les scores C0–C14 restent **inchangés** : aucune correction n'est prouvée
  verte sur la branche #107 à ce stade.
- Prochaine étape : commit poussé par Codex → worktree de vérification séparé
  → rejeu des 37 tests d'audit + suite complète + 13 suites Playwright → mise
  à jour de ce rapport et de la PR d'audit.
