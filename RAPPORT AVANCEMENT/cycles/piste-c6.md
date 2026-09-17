# Piste C6 — Comptabilité et RH (clôture de caisse)

Worktree `_worktrees/piste-c6`, branche `piste-c6-comptabilite-rh`, base
`quincaillerie_c6` (127.0.0.1:5433, port serveur de convention 8012).
Travail mené en parallèle des pistes UX et C12 — voir
`RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`.

## Cycle piste C6 — C6 Comptabilité et RH : clôture de caisse — 2026-09-14/17

### Étape 1 — Diagnostic

Rejoué **par exécution réelle**, dans ce worktree, sur `quincaillerie_c6`
(jamais `quincaillerie_test`) :

- **pytest complet** (avant tout code de ce cycle) : `144 passed, 0 failed`
  — exactement le chiffre annoncé par `loop-state.md` pour C6 (cycle 18),
  aucun écart.
- **`verifier-rh-reel.mjs`** : `21/21` — écran RH (employés, absences/congés,
  avances + remboursement) intégralement réel.
- **`verifier-cablage.mjs`** : `87/87` — aucune régression sur les écrans
  déjà câblés (connexion, vente, inventaire, tableau de bord).
- Relecture de `server/app/routes/transactions.py` et `routes/rh.py` : les
  deux disent déjà explicitement, depuis le cycle 16, que la clôture de
  caisse est **hors périmètre, volontairement**. Confirmé par grep : aucune
  table, route ni écran de clôture n'existe nulle part dans le dépôt avant
  ce cycle.

**Verdict** : le score de 55 % annoncé pour C6 est honnête et vérifié. Rien
n'a été refait. Le seul manque réel est la clôture de caisse (point g de
l'addendum), conformément au plan reçu.

**Obstacle rencontré et documenté** : la suite pytest (`server/tests/
conftest.py`) et les suites Playwright partagées (`verifier-cablage.mjs`,
`verifier-rh-reel.mjs`) pointaient en dur vers `quincaillerie_test`, une
base interdite à cette piste. Correctif partagé, convergé avec la piste UX
à la demande du coordinateur pour un texte identique sur ces fichiers
communs (évite tout conflit de fusion) :
- `server/tests/conftest.py` : nouvelle variable d'environnement
  `QF_TEST_DBNAME` (défaut inchangé `quincaillerie_test`).
- `maquette/verification/verifier-cablage.mjs` et `verifier-rh-reel.mjs` :
  nouvelle variable `PGDATABASE_PISTE` (même défaut) + `PGDEV_RACINE` pour
  le chemin de `psql.exe` (absent du worktree, symlink local `_pgdev` créé,
  gitignoré, non commité).
- Rejoué après correctif : pytest `144 passed` et les deux suites Playwright
  toujours au même score, cette fois réellement sur `quincaillerie_c6` via
  `QF_TEST_DBNAME=quincaillerie_c6` / `PGDATABASE_PISTE=quincaillerie_c6`.

**Incident hors piste** (signalé et attendu avant de reprendre, comme
demandé) : PostgreSQL a réellement crashé pendant ce cycle (« could not
reserve shared memory region », bug connu sous Windows, sans rapport avec
ce travail). Aucune action prise sur le serveur PostgreSQL lui-même par
cette piste ; redémarré par le coordinateur (rejeu WAL, aucune perte de
données constatée : 24 tables dont `clotures_caisse`, 5 utilisateurs,
migration 019 toujours à son état).

### Étape 2 — Propositions

Un seul chantier candidat pour cette piste, déjà fixé par le plan reçu :
la clôture de caisse (point g). Pas d'alternative proposée ici — la piste
C6 a un périmètre dédié dans le travail en parallèle, hors du choix libre
habituel de l'étape 2 du cycle de finalisation.

### Étape 3 — Objectif retenu et plan

Objectif : rendre la clôture de caisse par site **100 % opérationnelle**,
avec écran dédié, calcul serveur de l'attendu et de l'écart, immutabilité
et cloisonnement par rôle prouvés par exécution.

**VALIDÉ PAR LE PROPRIÉTAIRE** au moment de la commande initiale de cette
piste (plan détaillé donné en tâche, 2026-09-14).

### Étape 4 — Mise en œuvre, vérification

**Branche** : `piste-c6-comptabilite-rh` (imposée par la coordination du
travail en parallèle, pas de sous-branche par cycle pour cette piste).

**Migration `db/migrations/019_cloture_caisse.sql`** (+ inverse) :
- Table `clotures_caisse` : `site_id`, `date_cloture`, quatre montants
  **attendus** par mode de paiement (espèces, Orange Money, MTN MoMo,
  autre), quatre montants **comptés** (espèces obligatoire, le reste
  optionnel), quatre **écarts**, `commentaire`, `utilisateur_id`,
  `cloture_rectificative_de` (auto-référence, NULL pour une clôture
  originale), horodatage.
- Contrainte d'unicité **partielle** : un seul enregistrement avec
  `cloture_rectificative_de IS NULL` par `(site_id, date_cloture)` — les
  rectificatives peuvent s'accumuler sans limite imposée (question non
  tranchée, sans effet bloquant).
- **Immutabilité totale** : trigger `BEFORE UPDATE` qui refuse absolument
  toute modification (pas seulement une transition de statut comme pour
  les ventes), et le trigger de journal existant (`interdire_suppression_
  journal`, migration 004) en `BEFORE DELETE`. Aucun rôle, pas même
  `postgres` en direct, ne peut modifier ou supprimer une ligne créée.
- **Seul point d'écriture** : fonction `cloturer_caisse(...)` (`SECURITY
  DEFINER`). Aucun `GRANT INSERT`/`UPDATE` n'est donné à qui que ce soit,
  pas même au responsable — prouvé par un test dédié (insertion directe
  refusée même sous `qf_responsable`).
- Fonction `calculer_attendu_caisse(site_id, date)` : **source unique** du
  calcul de l'attendu (ventes `payee` du site et du jour, `credit_client`
  exclu), utilisée à la fois par `cloturer_caisse()` et par la route de
  **prévisualisation** `GET /caisse/attendu` (nécessaire car l'addendum
  décrit deux étapes distinctes : afficher l'attendu, PUIS saisir le
  comptage).
- Paramètre `seuil_ecart_caisse_tolere` ajouté à `parametres`, amorcé à la
  sentinelle `a_definir` (addendum, question 5 non tranchée) — voir
  « Décisions et points ouverts » ci-dessous pour le comportement appliqué
  tant qu'il n'est pas fixé.
- Cloisonnement : `REVOKE ALL` pour `qf_agent_stock` et
  `qf_agent_comptabilite` sur `clotures_caisse` et sur les deux fonctions ;
  `GRANT SELECT` seul pour `qf_responsable` sur la table ; RLS par site en
  défense en profondeur (le responsable voit les deux sites).

**Routes `server/app/routes/caisse.py`** (nouveau fichier, enregistré dans
`server/app/main.py`) :
- `GET /caisse/attendu?site_id=&date_cloture=` — prévisualisation, lecture
  seule, réservée au responsable.
- `POST /caisse` — crée une clôture (ou une rectificative si
  `cloture_rectificative_de` est fourni), réservée au responsable, aucun
  champ d'attendu ni d'écart accepté en entrée.
- `GET /caisse` — historique, filtré par site via la RLS, jamais par un
  paramètre client.

**Schémas** (`server/app/schemas.py`) : `DemandeClotureCaisse` /
`ReponseClotureCaisse` — reflètent exactement les colonnes de la fonction,
aucun champ calculé côté application.

**Écran `maquette/cloture-caisse.html`** (nouveau, URL propre
`/app/cloture-caisse.html`, **aucun lien ajouté depuis
`tableau-bord.html`** — voir « Point signalé, non traité » ci-dessous) :
- sélection du site et de la date, aperçu de l'attendu par mode de
  paiement (GET, avant toute saisie) ;
- saisie du comptage (espèces obligatoires, Mobile Money optionnel,
  commentaire) ;
- détection côté écran d'une clôture déjà existante pour le couple
  (site, date) choisi, propose alors explicitement une clôture
  **rectificative** plutôt que de laisser l'utilisateur découvrir le refus
  serveur sans contexte ;
- historique des clôtures passées, mis à jour après chaque création.

**Preuves d'exécution** :
- **SQL direct** (contournant complètement l'API, sous les rôles
  PostgreSQL réels) : calcul de l'attendu correct, écart calculé par la
  fonction, refus d'un écart non commenté, acceptation avec commentaire,
  refus d'une deuxième clôture originale sur le même (site, jour), clôture
  rectificative acceptée et tracée, `UPDATE` direct refusé (« figée »),
  `DELETE` direct refusé (« journal »), lecture et exécution de la fonction
  **totalement refusées** (`permission denied`) pour `qf_agent_stock` et
  `qf_agent_comptabilite`, responsable voyant les deux sites.
- **API réelle** (requêtes HTTP, serveur démarré sur le port 8012) : même
  scénario complet rejoué via `curl` — prévisualisation, clôture exacte,
  refus sans commentaire (422), acceptation avec commentaire (201),
  clôture rectificative (201), historique (200) ; `agent_comptabilite` et
  `agent_stock` reçoivent `403` sur les trois routes (`GET /caisse`,
  `POST /caisse`, `GET /caisse/attendu`).
- **`server/tests/test_caisse.py`** (nouveau, 19 tests) : `19 passed`.
  Couvre le calcul serveur de l'attendu et de l'écart, le seuil
  `a_definir` (tolérance nulle documentée, pas inventée) **et** le cas où
  le propriétaire fixerait un jour une vraie valeur (appliquée sans
  changement de code), l'immutabilité (`UPDATE`/`DELETE`/`INSERT` direct
  refusés, y compris pour `qf_responsable`), l'unicité et la clôture
  rectificative, et le cloisonnement par rôle aux deux niveaux (API 403,
  SQL direct `InsufficientPrivilege`).
- **`maquette/verification/verifier-caisse-reel.mjs`** (nouveau) :
  `24/24`. Accès réservé au responsable, mise en page aux 5 largeurs
  (360/390/768/1366/1920, aucun débordement, cibles tactiles ≥ 44 px),
  attendu réel affiché avant saisie, clôture exacte, clôture en écart
  refusée puis acceptée avec commentaire, historique mis à jour — le tout
  avec de vraies ventes créées pour l'occasion et une vraie session
  responsable.
- **Suite pytest complète, rejouée après ajout** : `163 passed, 0 failed`
  (144 existants + 19 nouveaux) — aucune régression.
- **`verifier-cablage.mjs` et `verifier-rh-reel.mjs`**, rejouées après le
  correctif partagé de l'étape 1 : toujours `87/87` et `21/21`.

### Décisions prises et points ouverts (addendum, point g)

- **Décidé et appliqué** : une clôture par site, attendu calculé
  serveur, comptage saisi par le responsable, écart calculé serveur,
  clôture figée, correction uniquement par rectificative tracée.
- **Question 2 (fond de caisse initial)** : **non traitée, absente du
  modèle**. L'attendu en espèces ne compte que les ventes du jour — aucun
  fond de caisse de départ n'existe dans le schéma. Si un fond de caisse
  existe réellement dans la boutique, le compte rendu ci-dessus **sous-
  estime** d'autant l'attendu réel. Signalé ici, pas deviné.
- **Question 3 (qui clôture, ventes saisies en retard)** : réservé au
  responsable (périmètre RH/rémunération). Aucune règle de rattachement ou
  de blocage n'est appliquée à une vente saisie après la clôture d'une
  journée — elle n'apparaît simplement pas dans l'attendu déjà figé,
  visible seulement par une éventuelle rectificative.
- **Question 4 (rapprochement Mobile Money)** : champs de comptage
  optionnels seulement, aucun relevé d'opérateur importé ni comparé.
- **Question 5 (seuil d'écart toléré)** : paramètre `seuil_ecart_caisse_
  tolere` amorcé à `a_definir`. **Aucun chiffre inventé** : tant que le
  propriétaire ne tranche pas, `cloturer_caisse()` applique une tolérance
  **nulle** (tout écart non nul exige un commentaire) — traitement neutre
  et sûr, du même principe que `taux_tva = 0` avant la décision du point
  d. Testé et documenté (`test_seuil_a_definir_impose_un_commentaire_
  pour_tout_ecart_non_nul`) ; un second test prouve que la mécanique
  fonctionne déjà correctement pour une vraie valeur, dès que le
  propriétaire la fixera.
- **Question 6 (blocage après clôture)** : aucune route de ce cycle ne
  bloque une saisie sur une journée déjà clôturée — seule l'immutabilité
  de la clôture elle-même est garantie.

Aucune de ces sous-questions ne s'est révélée bloquante pour livrer la
structure — conformément au plan reçu.

### Point signalé, non traité (règle de non-collision)

Le tableau de bord du responsable (`maquette/tableau-bord.html`) serait
l'endroit naturel pour signaler une journée non clôturée ou lier vers
l'écran de clôture. **Ce fichier est réservé à la piste UX pour ce
tour** (`RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`) : aucune modification
n'y a été faite. Le lien devra être ajouté **après la fusion de la piste
UX et un rebase de C6 sur `main`**, comme prévu par la règle n°2.

### Score

C6 : 55 % → estimation **~85 %** (clôture de caisse livrée avec écran,
tests et cloisonnement complets ; restent le lien tableau de bord après
rebase UX, et les sous-questions non bloquantes du point g listées
ci-dessus). **Le score officiel de `loop-state.md` sera mis à jour par la
session qui fusionne**, jamais par cette piste (règle n°1 du travail en
parallèle).

### Fichiers de cette piste

- `db/migrations/019_cloture_caisse.sql` (+ `_inverse.sql`) — nouveau,
  migration réservée à C6.
- `server/app/routes/caisse.py` — nouveau.
- `server/app/schemas.py` — ajout de `DemandeClotureCaisse` /
  `ReponseClotureCaisse`.
- `server/app/main.py` — enregistrement du nouveau routeur (une ligne
  d'import, une ligne `include_router`).
- `maquette/cloture-caisse.html` — nouveau.
- `server/tests/test_caisse.py` — nouveau, 19 tests.
- `maquette/verification/verifier-caisse-reel.mjs` — nouveau, 24 contrôles.
- `maquette/verification/package.json` — ajout du script `npm run caisse`
  (ajout en fin de liste, aucune ligne existante modifiée).
- `db/tests/00_jeu_essai.sql` — ajout du paramètre
  `seuil_ecart_caisse_tolere` au jeu d'essai (même valeur que la migration
  019), pour que la base de test reflète une base migrée jusqu'au bout.
- `server/tests/conftest.py`, `maquette/verification/verifier-cablage.mjs`,
  `maquette/verification/verifier-rh-reel.mjs` — correctif partagé
  (variables d'environnement `QF_TEST_DBNAME` / `PGDATABASE_PISTE` /
  `PGDEV_RACINE`), convergé avec la piste UX à la demande du coordinateur.
- `maquette/captures/cloture-caisse-*.png` — captures des 5 largeurs de
  vérification.

### Reste à faire

- Lien vers `cloture-caisse.html` depuis `tableau-bord.html`, après fusion
  UX et rebase.
- Sous-questions 2, 3, 4, 6 du point g (fond de caisse initial, horaire et
  ventes tardives, rapprochement Mobile Money exact, blocage après
  clôture) — non bloquantes, à trancher par le propriétaire quand il le
  souhaite.
- Seuil `seuil_ecart_caisse_tolere` à fixer par le propriétaire
  (actuellement tolérance nulle appliquée par défaut).
- Rôle `caissier` (point h de l'addendum) : hors périmètre de cette piste
  (chantier C3), non traité ici.
