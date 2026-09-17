# Piste UX — corrections UX_BASELINE.md §4 bis

Worktree : `_worktrees/piste-ux` — branche `piste-ux-corrections` — base
`quincaillerie_ux` (127.0.0.1:5433) — port serveur 8011.

## Cycle unique — Correction des 8 constats UX confiés à la piste

- Date : 2026-09-14 → 2026-09-17

### Étape 1 — Diagnostic (par exécution réelle, sur quincaillerie_ux)

Avant toute modification, rejeu de toutes les suites existantes dans ce
worktree, sur cette base, serveur sur le port 8011 :

- **pytest** (`server/tests/`) : **144/144**, identique au dernier résultat
  connu du dépôt principal. Nécessite une adaptation minimale de
  `server/tests/conftest.py` (voir « Adaptations d'infrastructure »
  ci-dessous) pour ne jamais toucher `quincaillerie_test`.
- **verifier-cablage.mjs** : 87/87.
- **verifier-vente-reelle.mjs** : 12/12.
- **verifier-inventaire-reel.mjs** : 14/17 au premier essai, avec un écart
  trouvé et diagnostiqué (voir encart dédié ci-dessous) — **sans rapport
  avec les 8 constats UX**, confirmé pré-existant.
- **verifier-rh-reel.mjs** : 21/21.
- **verifier-stock-reel.mjs** : 26/26.
- **verifier-rapports-reel.mjs** : 29/29.
- **verifier-echappement-html.mjs** : 11/11 (après correction d'un import
  cassé par ma propre adaptation, voir plus bas).

Aucun écart avec les chiffres déjà documentés dans `server/README.md` /
`maquette/verification/DERNIER_RESULTAT.md`, hormis l'inventaire (détail
ci-dessous). La PR du cycle précédent (câblage complet des 4 écrans) est
donc confirmée fusionnable en l'état sur ce périmètre.

#### Écart trouvé et diagnostiqué : `verifier-inventaire-reel.mjs`, 3/17 intermittents

**Sans rapport avec les 8 constats UX visés par ce chantier.** Root-cause
identifiée par exécution, pas supposée :

1. Le script clique toujours `#btn-matin` en section 1, même quand
   « matin » est déjà le mode par défaut (avant 13h).
2. Ce clic redéclenche `chargerListe()` (un appel réseau asynchrone),
   mais le script attend seulement `!bloc-comptage.hidden` — qui est
   **déjà vrai** puisque le bloc était visible avant le clic. L'attente
   se résout donc immédiatement, sans attendre la fin du rechargement.
3. La boucle qui cherche « Ciment CIM II 50 kg » (délai fixe de 50 ms par
   passage) peut alors s'exécuter pendant que la liste est en cours de
   remplacement, et le comptage réellement soumis peut ne pas être celui
   attendu par les assertions suivantes.

Reproduit et confirmé par un script de diagnostic isolé
(`debug-inventaire.mjs`, non committé, scratchpad) : avec des délais plus
généreux après le clic « matin », la même séquence réussit **à chaque
essai** (POST `/inventaire/comptages` → 201). Rejoué plusieurs fois dans ce
travail : tantôt 17/17, tantôt 14/17 — confirmé **intermittent**,
dépendant de la charge du moment (probablement aggravé par les trois
sessions de piste qui partagent la même instance PostgreSQL). C'est donc
une fragilité **pré-existante du script de test lui-même**, présente avec
ou sans mes changements (reproduite sur une base fraîchement réinitialisée,
sans qu'aucun de mes correctifs applicatifs ne soit en cause). Conforme à
la règle « ajout seulement en fin de fichier » sur les suites communes, je
n'ai **pas** corrigé cette course dans le fichier partagé — je le signale
ici pour que la piste qui possède ce fichier (ou le propriétaire) décide.

### Étape 2/3 — Objectif et plan (déjà validés par le propriétaire, transmis avec la mission)

Voir la mission initiale : corriger, par ordre de gêne réelle, UX-7, UX-1,
UX-2, UX-3, UX-4, UX-6, UX-9, UX-10. Aucune déviation par rapport au plan
transmis.

### Étape 4 — Mise en œuvre, preuves, résultats

Branche : `piste-ux-corrections` (déjà existante, travaillée directement
dessus comme prévu par la coordination du travail en parallèle).

#### UX-7 (le plus sérieux) — coupure réseau en pleine requête

**Cause** : `fetch()` sans délai maximal ne rejette jamais si la connexion
est coupée EN COURS de requête (contrairement à un refus de connexion
immédiat, déjà géré par `RESEAU_INACCESSIBLE`).

**Correctif** : `maquette/api.js`, `appelApiBrut()` — un `AbortController`
avec un délai de 20 s entoure désormais `fetch()`. Un abandon par délai
aboutit au même message déjà existant (« Impossible de contacter le
serveur. Vérifiez qu'il est démarré, puis réessayez. »).

**Preuve par exécution** (`verifier-ux-corrections.mjs`) : la requête
`POST /ventes` est interceptée par Playwright et **jamais honorée** (ni
`route.fulfill()` ni `route.abort()` — exactement une coupure en cours de
requête, pas un refus immédiat). Le message apparaît en 20 009 ms, en
français, dans la zone de confirmation ; le bouton « Valider la vente »
redevient utilisable sans recharger la page ; une fois le réseau
« rétabli » (route libérée), une nouvelle tentative aboutit à une vraie
vente sans recharger la page.

#### UX-1 — ajouter un article en ≤ 2 actions

**Diagnostic** (avant tout code) : le parcours « taper + Entrée » était
déjà à 2 actions pour une quantité de 1 — mais la mesure réelle (A3, 3-4
actions) correspond au cas courant en quincaillerie où la quantité n'est
presque jamais 1, ce qui obligeait à rouvrir la ligne du panier après coup
(3e, voire 4e action pour sélectionner puis remplacer le contenu du champ
quantité).

**Correctif** : `maquette/vente.html` — un nombre en tête de la recherche
(ex. « 5 ciment ») fixe la quantité dès l'ajout. Toujours 2 actions (taper
+ Entrée), quelle que soit la quantité.

**Preuve par exécution** : `verifier-ux-corrections.mjs`, article ajouté
avec quantité 5 en exactement 2 actions (remplir le champ + Entrée),
quantité affichée dans le panier vérifiée à "5" sans action
supplémentaire.

#### UX-2 — vente entière au clavier seul

**Diagnostic** (par exécution, pas par lecture du code — l'écart entre
l'automatisé et le réel demandé par le plan) : `verifier-cablage.mjs`
et `verifier-vente-reelle.mjs` utilisent déjà le clavier pour valider une
vente, mais **jamais avec un prix négocié** — leur scénario ajoute un
article et valide directement au prix catalogue. Or une vraie vente
négocie presque toujours le prix (addendum, point d), et c'est
précisément ce prix qu'aucun raccourci n'atteignait : seule la souris ou
une chaîne de <kbd>Tab</kbd> incertaine (à travers tout le panier, les
sélecteurs de site/paiement...) pouvait l'atteindre. Les suites existantes
ne pouvaient donc pas montrer ce que le testeur humain a rencontré,
puisqu'elles ne testaient jamais ce chemin.

**Correctif** : `maquette/vente.html` — nouveau raccourci `F3` : amène le
focus directement sur le champ de prix de la DERNIÈRE ligne ajoutée
(contenu présélectionné pour un remplacement immédiat) ; <kbd>Entrée</kbd>
dans ce champ ramène le focus à la recherche. Documenté dans l'aide
clavier de bas d'écran.

**Preuve par exécution** : `verifier-ux-corrections.mjs` — scénario
n'utilisant **aucune souris**, de la recherche à la validation d'une vente
avec un prix négocié (recherche → Entrée → F3 → taper le nouveau prix →
Entrée → F4 → F9 → F9), réussit de bout en bout (vente réellement
enregistrée, réponse serveur avec numéro de vente et TVA).

#### UX-3 / UX-4 — débordement mobile et chiffres illisibles

**Diagnostic** (le facteur non couvert par les 5 largeurs standard) : les
suites automatisées utilisent TOUJOURS les libellés courts et fixes du
jeu d'essai (« Ciment CIM II 50 kg », « Article rare »...). Un contenu
réel plus long (nom d'article, motif de mouvement) ne peut donc jamais
provoquer de débordement dans ces suites, **quelle que soit la largeur
testée** — ce n'est pas un problème de largeur de viewport, c'est un
problème de longueur de contenu non couvert par le jeu d'essai. Cause CSS
précise trouvée : `grid-template-columns: 1fr` (sans `minmax(0, ...)`)
laisse un minimum implicite « auto » = la taille du contenu le plus
large ; combiné à l'absence de `min-width: 0`/`overflow-wrap` sur les
cartes et les listes, un mot non sécable (nom d'article composé de tirets,
motif long, etc.) peut pousser toute la grille plus large que l'écran —
un piège CSS bien identifié, invisible tant que le contenu de test reste
court.

**Correctif** :
- `maquette/styles.css` : `.tb-grille` et `.kv` passent de `1fr`/`1fr auto`
  à `minmax(0, 1fr)`/`minmax(0, 1fr) auto` à tous les points de rupture ;
  `.carte` gagne `min-width: 0` ; `.kv dt` gagne `overflow-wrap: anywhere`.
- `maquette/api.js` : `creerLigneListe()` (utilisée par les 3 listes du
  tableau de bord) pose `min-width: 0` et `overflow-wrap: anywhere` sur le
  libellé principal.
- `maquette/tableau-bord.html` (style scopé à cet écran, comme l'ont fait
  les cycles précédents pour ses propres débordements) : taille de police
  minimale garantie sur les chiffres des cartes — montants par site à
  `--t-md` (20px, contre 17px non garanti), pastilles d'écart à `--t-base`
  (17px, contre 15px).

**Preuve par exécution** : `verifier-ux-corrections.mjs` — un nom
d'article RÉELLEMENT long et non sécable (« Vis-autoperceuse-inoxydable-
tete-fraisee-torx-6x80-boite-de-200-unites ») posé en base, tableau de
bord chargé aux 5 largeurs standard (360/390/768/1366/1920) : **0 px de
débordement à chacune**, captures dans
`maquette/captures/ux-corrections-tableau-bord-*.png`. Taille de police
des pastilles mesurée réellement (`getComputedStyle`) ≥ 16px à 360 et
390px.

**Honnêteté (comme prévu par le plan si la cause s'avérait non
diagnosticable à 100 %)** : l'identité exacte du téléphone et du
navigateur du testeur n'a jamais été renseignée (voir l'en-tête de §4 bis
de `UX_BASELINE.md`), donc un facteur non reproductible ici (zoom système
du téléphone, comportement propre à un navigateur mobile précis) n'est
**pas formellement exclu** comme cause additionnelle. Seule la cause
CSS/longueur de contenu ci-dessus a pu être diagnostiquée et corrigée par
exécution réelle — c'est la cause la plus plausible au vu de l'indice
donné par le plan (« jamais détecté par les 5 largeurs standard »),
puisqu'elle est indépendante de la largeur par construction.

#### UX-6 — clavier numérique pour le comptage

**Constat à l'inspection** : déjà correct, aucun changement de code
nécessaire. `maquette/inventaire.html#saisie` porte déjà `type="number"`
ET `inputmode="numeric"`.

**Preuve par exécution** : `verifier-ux-corrections.mjs` lit l'attribut
RÉELLEMENT rendu dans le DOM (`page.getAttribute`, pas la lecture du
fichier source) : `type="number"` et `inputmode="numeric"` confirmés.

#### UX-9 — prix indicatif en gris pris pour le prix facturé

**Correctif** : `maquette/vente.html` — le message affiché après l'ajout
d'un article précise désormais explicitement : « Prix indicatif du
catalogue : ... — PAS le prix qui sera facturé : ajustez-le dans le
panier (ou F3) si le prix négocié est différent. » (auparavant : « ajouté
[...], prix X — modifiable dans le panier », sans indication que ce prix
n'est qu'indicatif).

**Preuve par exécution** : `verifier-ux-corrections.mjs` vérifie la
présence du mot « indicatif » et de la précision explicite « PAS le prix
facturé » dans le texte réellement affiché.

#### UX-10 — caractère définitif d'un comptage non signalé

**Contrainte respectée** : pas de dialogue bloquant (le comptage est déjà
mesuré trop lent, A7 : 3 min 05 au pire essai contre un objectif de
2 min — ajouter un clic l'aurait aggravé).

**Correctif** : `maquette/inventaire.html` — un avertissement TOUJOURS
visible sous le champ de saisie (« Une fois enregistré ci-dessous, ce
comptage est **définitif** : il ne pourra plus être modifié. »), style
scopé à cet écran (`--c-attention`, « avertissements non bloquants »).

**Preuve par exécution** : `verifier-ux-corrections.mjs` vérifie que
l'avertissement est visible sans action supplémentaire, que son texte
n'est pas ambigu, et — pour prouver l'absence de friction ajoutée —
qu'aucun `dialog` navigateur (`confirm()`) n'est déclenché lors de la
soumission d'un comptage.

### Adaptations d'infrastructure (nécessaires, hors périmètre strict — signalées immédiatement au propriétaire pendant le travail)

- **`server/tests/conftest.py`** : ajout d'une variable d'environnement
  `QF_TEST_DBNAME` (défaut inchangé : `quincaillerie_test`) et d'un repli
  sur `_pgdev/` du dépôt principal quand le worktree n'en a pas de copie
  — strictement nécessaire pour rejouer pytest sans jamais toucher
  `quincaillerie_test`, conformément à la règle absolue de cette piste.
  Changement rétrocompatible (défaut identique pour toute autre
  invocation). Signalé au propriétaire pendant le travail, qui a confirmé
  vouloir la même approche (variable d'environnement, valeur par défaut
  inchangée) pour les suites Playwright — voir point suivant.
- **7 suites Playwright existantes** (`verifier-cablage.mjs`,
  `verifier-vente-reelle.mjs`, `verifier-inventaire-reel.mjs`,
  `verifier-rh-reel.mjs`, `verifier-stock-reel.mjs`,
  `verifier-rapports-reel.mjs`, `verifier-echappement-html.mjs`) :
  remplacement du nom de base codé en dur par
  `process.env.PGDATABASE_PISTE || "quincaillerie_test"` (défaut
  inchangé), plus un repli sur le `_pgdev/` du dépôt principal si absent
  du worktree — demandé explicitement par le propriétaire en cours de
  travail pour que les trois pistes convergent vers le **même** motif
  (`PGDATABASE_PISTE`), évitant tout conflit de fusion même si une autre
  piste fait la même adaptation sur les mêmes lignes.
- Un import cassé introduit par ma propre adaptation dans
  `verifier-echappement-html.mjs` (`existsSync` non importé, ce fichier
  ayant un import `node:fs` différent des autres) a été corrigé dans la
  foulée.
- **Nouveau fichier** `maquette/verification/verifier-ux-corrections.mjs`
  (27 contrôles, 0 échec) : dédié aux 8 constats de ce chantier, plutôt
  qu'un ajout réparti dans plusieurs suites existantes (ce chantier touche
  3 écrans à la fois).
- **`db/outils`, `server/README.md`, `db/README.md`** : non touchés
  (gelés).

### Résultat final des vérifications (état final commité)

| Suite | Résultat |
|---|---|
| `pytest server/tests/` | 144/144 |
| `verifier-cablage.mjs` | 87/87 |
| `verifier-vente-reelle.mjs` | 12/12 |
| `verifier-inventaire-reel.mjs` | 17/17 (intermittent, voir écart ci-dessus — sans rapport avec ce chantier) |
| `verifier-rh-reel.mjs` | 21/21 |
| `verifier-stock-reel.mjs` | 26/26 |
| `verifier-rapports-reel.mjs` | 29/29 |
| `verifier-echappement-html.mjs` | 11/11 |
| `verifier-ux-corrections.mjs` (nouveau) | 27/27 |

Aucune régression détectée sur aucune suite existante.

### Incidents pendant le travail, signalés en temps réel

- **PostgreSQL (127.0.0.1:5433) injoignable pendant une partie du
  travail** (connexion refusée sur plusieurs essais consécutifs) :
  signalé immédiatement, **aucune action engagée sur PostgreSQL lui-même**
  (ni arrêt, ni redémarrage, ni reconfiguration) — attente passive, reprise
  du diagnostic dès que la base a répondu de nouveau. Le serveur applicatif
  (uvicorn, port 8011) a été relancé plusieurs fois, lui, à chaque
  interruption de session — jamais PostgreSQL.
- **`server/tests/conftest.py`** touché alors qu'il n'est pas listé dans
  les fichiers exclusifs à la piste UX : signalé immédiatement au
  propriétaire avant de poursuivre (voir échange en cours de travail),
  confirmé nécessaire et sans risque de collision (fichier non revendiqué
  par une autre piste, changement rétrocompatible).

### Reste à faire / hors périmètre de ce chantier

- **UX-0** (méthodologie : pire des 3 essais vs. 3e essai) — décision à
  prendre par le propriétaire, aucun code n'y répond.
- **UX-5** (recette depuis le téléphone, 1 min 02 vs. < 45 s) — hors du
  plan validé pour cette piste.
- **UX-8** (annuler une ligne du panier non trouvé seul) — hors du plan
  validé pour cette piste.
- **Fragilité intermittente de `verifier-inventaire-reel.mjs`** (voir
  encart dédié) — appartient au fichier commun, pas corrigée ici
  conformément à la règle « ajout seulement en fin de fichier », signalée
  pour arbitrage.
- Captures des 5 largeurs pour les AUTRES écrans (`vente.html`,
  `inventaire.html`) déjà couvertes par `verifier-cablage.mjs` (rejouées
  sans régression) — non reprises spécifiquement pour UX-3/4, qui ne
  concernait que le tableau de bord (seul écran visé par la campagne
  réelle B2/B3).

## Pull request

Branche `piste-ux-corrections` poussée vers `origin`, pull request ouverte
vers `main` (première à fusionner dans l'ordre décidé par
`RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`). Non fusionnée par cette
session — le propriétaire décide.
