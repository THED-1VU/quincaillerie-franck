# Coordination opération 100 % — Lot B (Qoder) / Lot A (Codex)

Note de coordination technique, 2026-10-23. Opération 100 % :
- **Codex** : C1 (base de données et intégrité), C2 (authentification et
  comptes), C3 (habilitations et cloisonnement).
- **Lot B / Qoder** : C5 (ventes et facturation), C8 (interfaces et
  parcours), C12 (sauvegarde et reprise).

## SHA de référence

- `main` = `f255dc6` (fusion #93, D9) au moment de cette note.
- **La PR #100 (sommet `2dae406`, branche `cycle-75-h-corrections-regression-d7`)
  est CLEAN avec CI verte (pytest + 13/13 suites) et attend sa fusion par le
  propriétaire.** Elle contient l'intégralité du cycle 75.
- **Base de travail commune à tous les agents : le sommet testé `2dae406`.**
  Baséz vos branches dessus (ou sur `main` dès que #100 est fusionnée —
  contenu identique à `2dae406` près des commits de fusion).
- Après fusion de #100 par le propriétaire : **SHA de référence = HEAD de
  `main`** (à relever ici par chacun, la présente note ne préjuge pas du SHA
  de fusion).

## Où travaille chaque agent

| Agent | Checkout | Branche | Base de test | Port serveur |
|---|---|---|---|---|
| Codex (C1/C2/C3) | checkout principal `QuincaillerieFranck_Test` | la sienne | `quincaillerie_test` (défaut) | 8010 (défaut) |
| Lot B (C5/C8/C12) | worktree `QuincaillerieFranck_Test_LotB` | `operation-100-lot-b` (base `2dae406`) | `quincaillerie_lotb` | 8020 |

Le Lot B lance toute régression avec :
`PORT_SERVEUR=8020 BASE_TEST=quincaillerie_lotb bash db/outils/verifier_tout.sh`
(paramètres prévus par le script — `SERVEUR_URL` et `PGDATABASE_PISTE`
suivent automatiquement). **Précision vérifiée : la suite SQL de l'étape 1
(`db/tests/executer_tests.sh`) suit AUSSI `BASE_TEST`** — l'isolement est
effectif pour SQL et les 13 suites Playwright. **Aucun des deux agents ne
doit modifier `verifier_tout.sh` ni `executer_tests.sh` sans coordination
préalable.** Piège partagé connu : l'étape 7 de la suite SQL recrée les
rôles applicatifs GLOBAUX du serveur (fenêtre où `qf_app` a un mot de
passe vide) — si l'un de nous voit des échecs d'authentification en
cascade, c'est l'autre qui joue la suite SQL à ce moment.

**DÉFAUT D'ISOLEMENT DÉCOUVERT PAR L'EXÉCUTION (2026-10-23, corrigé dans
la branche Lot B)** : dans `verifier_tout.sh` d'origine, deux étapes
IGNORAIENT `BASE_TEST` et visaient `quincaillerie_test` quoi qu'il
arrive — (1) l'étape pytest : `server/tests/conftest.py` lit
`QF_TEST_DBNAME` (défaut `quincaillerie_test`), jamais exporté par le
script ; (2) le serveur des suites Playwright : `uvicorn` lit
`server/config.ini` (`dbname = quincaillerie_test`). Le Lot B a donc
corrigé son orchestrateur (branche `operation-100-lot-b`) : export de
`QF_TEST_DBNAME="$BASE_TEST"` avant pytest et génération d'un
`config.ini` temporaire (base + `tentatives_max_par_minute = 1000`) passé
par `QF_CONFIG` au serveur — plus de config.ini copié à la main, plus de
collision possible avec l'autre agent. **Toute exécution en parallèle
d'un autre agent exige cette version corrigée.**

Avec bases et ports distincts + worktrees distincts (captures séparées),
les campagnes Playwright des deux agents peuvent tourner en parallèle.
Règle conservée : jamais deux campagnes sur la MÊME base.

## Périmètres et fichiers

| Domaine | Responsable | Fichiers typiques |
|---|---|---|
| Migrations SQL (dès 053), invariants, protections | **Codex** | `db/migrations/`, `db/tests/` |
| Auth, jetons, sessions, verrouillage | **Codex** | `server/app/securite.py`, `auth.py` |
| Habilitations, dépendances, matrice rôles | **Codex** | `server/app/dependances.py`, matrice SQL |
| Ventes, caisse, reçus, remises, paiements mixtes | **Lot B** | `server/app/routes/ventes.py`, `caisse.py`, `rapports.py` |
| Écrans, parcours, suites Playwright | **Lot B** | `maquette/*.html`, `maquette/verification/*.mjs` |
| Sauvegarde/restauration, exploitation | **Lot B** | `db/outils/restaurer.ps1`, exploitation, docs C12 |

- **Migrations : le prochain numéro libre est 053, réservé à Codex.**
  Le Lot B n'en prévoit aucune ; s'il en fallait une, coordination préalable
  obligatoire (aucune modification des invariants de base par le Lot B
  sans accord Codex).
- Fichiers à risque de conflit de documentation : `REGISTRE_ECARTS_100.md`,
  `RAPPORT AVANCEMENT/loop-state.md` — les deux agents les mettent à jour ;
  conflits textuels attendus, à résoudre au merge sans perdre les lignes de
  l'autre.

## Règles impératives communes

1. `db/outils/sauvegarder.ps1` est en quarantaine Kaspersky : **jamais
   restauré, jamais exécuté, aucune exclusion AV** sans autorisation
   explicite du propriétaire. Son état `D` au `git status` n'est **jamais
   commité**. Audit par `git show HEAD:db/outils/sauvegarder.ps1` uniquement.
2. Aucune fusion de PR par un agent (couche de sécurité + règle
   propriétaire), sauf autorisation explicite en session.
3. Aucun score sans preuve d'exécution réelle ; tests automatisés ≠
   validation humaine.
4. Aucune production, aucun import réel, aucune installation réelle sans
   autorisation explicite du propriétaire.
5. Messages de commit SANS accents (heredoc bash sur ce poste).
