# Travail en parallèle — trois pistes simultanées (2026-09-14)

Trois sessions Claude Code travaillent en même temps sur ce dépôt, chacune
dans son propre worktree Git, sur sa propre base PostgreSQL. Ce document
fixe les règles qui empêchent qu'elles se marchent dessus. **Toute piste
qui doit s'écarter de ces règles s'arrête et le signale — elle ne
tranche pas seule.**

Isolation technique (worktrees, bases, ports) : voir `db/README.md`,
section « Bases dédiées au travail en parallèle », vérifiée par exécution
le 2026-09-14.

| Piste | Worktree | Branche | Base | Port | Rapport |
|---|---|---|---|---|---|
| UX | `_worktrees/piste-ux` | `piste-ux-corrections` | `quincaillerie_ux` | 8011 | `RAPPORT AVANCEMENT/cycles/piste-ux.md` |
| C6 | `_worktrees/piste-c6` | `piste-c6-comptabilite-rh` | `quincaillerie_c6` | 8012 | `RAPPORT AVANCEMENT/cycles/piste-c6.md` |
| C12 | `_worktrees/piste-c12` | `piste-c12-sauvegarde` | `quincaillerie_c12` | 8013 | `RAPPORT AVANCEMENT/cycles/piste-c12.md` |

---

## Règle n°1 — Fichiers transversaux : jamais modifiés pendant le travail en parallèle

Aucune piste ne touche, pendant toute la durée du travail en parallèle
(entre le début des trois sessions et la fusion de la dernière) :

- `RAPPORT AVANCEMENT/loop-state.md`
- `.agents/skills/finalisation-loop/SKILL.md`
- `server/README.md`
- `db/README.md`
- `PERIMETRE_LIVRE.md`
- `ADDENDUM_CAHIER_DES_CHARGES.md`
- `MODELE_DONNEES.md`

Ce sont des fichiers **partagés en prose continue** : trois sessions qui y
ajoutent chacune leur propre section produiraient un conflit de fusion
réel (pas juste un ajout trivial en fin de fichier). Chaque piste
consigne à la place **tout** ce qu'elle ferait normalement écrire
ailleurs — diagnostic, décisions, résultats de test, captures, pièges
rencontrés — dans son propre rapport, `RAPPORT AVANCEMENT/cycles/<nom-de-piste>.md`,
au format du cycle habituel (voir `SKILL.md`, section « Format d'un cycle »).

**`UX_BASELINE.md` fait exception** : la piste UX peut y marquer ses
propres constats (UX-1 à UX-10) comme corrigés et vérifiés, avec la
preuve — c'est le seul document dont elle est la source de vérité pour ce
travail, et aucune autre piste n'y touche.

La mise à jour de `loop-state.md` (nouveau score, section « Cycle N »
en bonne et due forme) se fait **une seule fois par piste, à la fusion**,
par la session qui fusionne — jamais par la piste elle-même, jamais
avant que son code ne soit sur `main`.

---

## Règle n°2 — Périmètre de fichiers de code exclusif à chaque piste

### Piste UX

Constats visés (voir `UX_BASELINE.md` §4 bis), par ordre de gêne réelle :
UX-7, UX-1, UX-2, UX-3, UX-4, UX-6, UX-9, UX-10.

**Fichiers dont la piste UX a l'exclusivité :**
- `maquette/vente.html`
- `maquette/tableau-bord.html`
- `maquette/inventaire.html`
- `maquette/api.js`
- `maquette/styles.css`, `maquette/theme.css` (uniquement si un correctif
  visuel l'exige — préférer un style scopé à l'écran concerné, comme
  l'ont fait les cycles précédents)
- `UX_BASELINE.md` (exception à la règle n°1, voir ci-dessus)

**Interdit à la piste UX** : `maquette/stock.html`, `maquette/rapports.html`,
`maquette/rh.html` (appartiennent implicitement aux pistes qui les
utilisent ou n'en ont pas besoin cette fois) — si un constat UX s'avère
concerner un de ces écrans, la piste s'arrête et le signale plutôt que
de le corriger.

### Piste C6

**Fichiers dont la piste C6 a l'exclusivité :**
- `db/migrations/019_*.sql` (+ inverse) — **la piste C6 réserve le numéro
  019** ; elle fusionne avant C12, aucun conflit de numérotation attendu.
- `server/app/routes/transactions.py`, `server/app/routes/rh.py`
- Toute nouvelle route de clôture de caisse (fichier nouveau, ex.
  `server/app/routes/caisse.py` — au choix du diagnostic de la piste)
- `server/app/schemas.py` (seule piste des trois à toucher des modèles
  Pydantic ce tour-ci)
- `maquette/rh.html`
- Tout nouvel écran de clôture de caisse (fichier nouveau, ex.
  `maquette/cloture-caisse.html`)
- `server/tests/test_transactions.py`, `server/tests/test_rh.py`, et tout
  nouveau fichier de test pour la clôture de caisse
- `server/tests/DERNIER_RESULTAT.md` (propre à la piste ; fusionné dans le
  fichier principal seulement au moment de la fusion réelle sur `main`,
  comme les autres docs transversales — écrire les résultats dans
  `RAPPORT AVANCEMENT/cycles/piste-c6.md` en attendant)

**Interdit à la piste C6** : `maquette/tableau-bord.html` (réservé à UX
pour ce tour, même si la clôture de caisse semblerait naturellement y
avoir sa carte). Si le plan validé de C6 a besoin d'un lien vers son
écran de clôture depuis le tableau de bord, **ce lien est ajouté après
la fusion de la piste UX et un rebase de C6 sur `main`**, jamais avant.

### Piste C12

**Fichiers dont la piste C12 a l'exclusivité :**
- `db/outils/sauvegarder.ps1`, `db/outils/restaurer.ps1`
- Tout nouveau script d'automatisation (planification, copie hors
  serveur, journal, alerte — noms au choix du diagnostic de la piste)
- `server/fabrication/` (spec PyInstaller, `construire.ps1`) et
  `server/requirements.txt` si une version doit être ajustée
- `server/README.md` → non, voir règle n°1 : consigner dans
  `RAPPORT AVANCEMENT/cycles/piste-c12.md`

**Si la piste C12 a besoin d'une migration** (ex. une table de journal des
sauvegardes) : elle ne choisit son numéro **qu'après avoir rebasé sur
`main`** une fois la piste C6 fusionnée (voir règle n°3) — jamais 019 par
anticipation, jamais un numéro choisi avant d'avoir vu ce que C6 a
réellement fusionné.

**Interdit à la piste C12** : tout fichier sous `maquette/` (aucun écran
prévu pour ce chantier ce tour-ci).

### Fichiers communs aux trois — règle d'ajout, jamais de modification

- `maquette/verification/*.mjs` (suites Playwright existantes) : une
  piste peut **ajouter** de nouveaux contrôles à une suite existante dont
  elle corrige l'écran, mais **uniquement en ajoutant un bloc à la fin du
  fichier**, jamais en modifiant une section déjà écrite par une autre
  piste. Un conflit de fusion sur un simple ajout en fin de fichier est
  trivial à résoudre (garder les deux blocs) ; préférer néanmoins un
  **nouveau fichier dédié** (`verifier-ux-corrections.mjs`,
  `verifier-caisse-reel.mjs`...) quand c'est raisonnable, pour l'éviter
  complètement.
- `maquette/verification/package.json` : ajout d'un script `npm run
  <nom>` par la piste qui crée le fichier correspondant — même principe
  d'ajout, jamais de modification d'une ligne existante.
- `.gitignore` : déjà mis à jour pour `_worktrees/` avant le démarrage des
  trois pistes ; aucune piste n'a de raison d'y toucher.
- `db/outils/verifier_tout.sh` : **gelé pour les trois pistes** — aucune
  n'y touche pendant le travail en parallèle, même pour y intégrer une
  nouvelle suite. Si une piste juge que c'est nécessaire, elle s'arrête et
  le signale au lieu de le modifier.

---

## Règle n°3 — Ordre de fusion et rebase

Ordre décidé à l'avance, **non négociable en cours de route** sans
repasser par le propriétaire :

1. **UX en premier** — elle touche des écrans partagés
   (`tableau-bord.html`, `vente.html`) que les deux autres pistes
   n'osent pas toucher précisément pour cette raison ; les fusionner
   après elles forcerait C6/C12 à rebaser deux fois sur des écrans
   déplacés sous leurs pieds.
2. **C6 ensuite** — réserve la migration 019, seule piste à toucher
   `schemas.py`.
3. **C12 en dernier** — si elle a besoin d'une migration, choisit son
   numéro après avoir vu ce que C6 a réellement fusionné.

**Après chaque fusion**, les pistes encore actives rebasent leur branche
sur `main` avant de continuer (`git fetch origin && git rebase
origin/main`, résolu depuis leur propre worktree). Une piste qui
découvre, en rebasant, que son périmètre de fichiers a changé sous elle
(par exemple `tableau-bord.html` a bougé de façon incompatible avec ce
qu'elle prévoyait) s'arrête et le signale plutôt que de forcer la fusion.

La fusion elle-même (revue, `git merge`/`gh pr merge`, mise à jour de
`loop-state.md`) est faite par **une seule session à la fois** — jamais
deux pistes qui fusionnent en même temps l'une sur l'autre.

---

## Règle n°4 — Le cycle en 4 étapes s'applique à chaque piste

Chaque piste suit `SKILL.md` intégralement, y compris l'arrêt obligatoire
de l'étape 3 : diagnostic (rejouer les suites existantes **dans son
propre worktree, sur sa propre base**), propositions, objectif et plan
pour son propre chantier, **arrêt et attente de validation explicite**
avant tout code — même si le plan d'ensemble a déjà été validé en bloc
par le propriétaire au niveau de la coordination, chaque piste reste
responsable de ne pas dévier de CE plan précis sans le signaler.

Aucune piste ne fusionne sa propre PR. Chaque piste s'arrête après avoir
ouvert sa pull request.
