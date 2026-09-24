# Vérification de la maquette (cycle 1, chantier C9)

Deux scripts qui **exécutent réellement** la maquette dans un navigateur et
vérifient les critères de sortie du cycle 1. Ils servent de preuve : une maquette
non affichée est réputée non faite.

## Prérequis

- Node.js (testé avec la v24).
- Google Chrome installé (les scripts utilisent `channel: "chrome"` de Playwright,
  pour éviter de télécharger un navigateur supplémentaire).
- La maquette servie en local. Depuis le dossier `../` :

  ```
  py -m http.server 8080
  ```

## Lancer

Depuis ce dossier :

```
npm install
npm run affichage   # 4 écrans x 5 largeurs : débordement, erreurs console, cibles tactiles + captures
npm run flux        # parcours clés : connexion, ajout au panier en 2 actions, F4/F9, inventaire à l'aveugle
```

`MAQUETTE_URL` permet de pointer une autre adresse (par défaut `http://127.0.0.1:8080/`).

## Ce qui est vérifié

### `verifier-affichage.mjs`
- Les 4 écrans se chargent aux largeurs **360, 390, 768, 1366 et 1920 px**.
- `document.documentElement.scrollWidth <= clientWidth` → **aucun débordement horizontal**.
- **Aucune erreur** dans la console ni d'exception JavaScript.
- Sur mobile (≤ 768 px), la plus petite cible interactive fait **≥ 44 px** de haut.
- Une capture par cas est écrite dans `../captures/` (20 fichiers).

### `verifier-flux.mjs`
- **Connexion** : message d'erreur affiché près du champ si la saisie est vide ;
  message clair « identifiant ou mot de passe incorrect » avec mention du blocage ;
  le couple valide mène à l'écran de vente.
- **Vente** : « taper la recherche » + `Entrée` ajoute une ligne au panier
  (**2 actions**) ; un article déjà présent voit sa quantité augmenter sans
  doublon ; le focus revient sur la recherche pour enchaîner ; `F4` change le mode
  de paiement ; `F9` demande **une seule** confirmation puis valide ; **aucune
  fenêtre superposée** (0 `dialog` / `modal`).
- **Inventaire à l'aveugle** : le tableau de données ne porte que `id` / `nom` /
  `unité` (aucune quantité attendue ne descend jusqu'à la page) ; le champ de
  saisie est vide au départ ; `Entrée` passe à l'article suivant et la progression
  s'incrémente.

Sortie attendue au dernier lancement du cycle 1 : **affichage 20/20**, **flux 14/14**.

## Scripts ajoutés depuis (cycles 5 et 6)

Ces deux scripts ciblent le **noyau serveur réel** (`SERVEUR_URL`, par défaut
`http://127.0.0.1:8010`), pas le serveur statique du cycle 1 — ils
réinitialisent eux-mêmes la base de test (jeu d'essai + comptes réels).

- **`verifier-cablage.mjs`** (cycle 5, C9/C10 ; complété au cycle 10, C8) :
  les 4 écrans câblés sur le noyau serveur — connexion réelle, séparation
  des rôles prouvée sur le CONTENU des réponses, quantité attendue absente
  du comptage à l'aveugle (page/réseau/code source), erreurs toujours en
  français près du champ, alertes de stock réelles (cycle 10), captures
  aux 5 largeurs. Dernier résultat : **76/76**.
- **`verifier-vente-reelle.mjs`** (cycle 6, C5) : l'écran de vente enregistre
  une VRAIE vente (`POST /ventes`) — crédit client absent des choix, vente à
  découvert de stock acceptée avec écart affiché (jamais un refus), le
  responsable doit choisir un site avant de valider, et l'aperçu affiché
  AVANT validation correspond exactement à ce que le serveur confirme.
  Dernier résultat : **10/10**.
- **`verifier-inventaire-reel.mjs`** (cycle 7, C7 ; complété au cycle de
  correction après le cycle 7) : le comptage à l'aveugle est réel
  (`GET/POST /inventaire/...`) — liste sans aucune quantité, un comptage
  produisant un écart réel ne le laisse fuir nulle part (page, réseau, code
  source), un article déjà compté disparaît de la liste, le tableau de bord
  du responsable affiche l'écart de comptage ET l'écart de vente à
  découvert (valeurs exactes), et une double soumission (panne réseau
  simulée à deux onglets) laisse l'agent avancer normalement au lieu de le
  bloquer sur un 409. Dernier résultat : **17/17**.
- **`verifier-echappement-html.mjs`** (cycle de correction après le
  cycle 7) : un nom d'article contenant une charge HTML/JS ne s'exécute
  JAMAIS — vérifié sur les suggestions et le panier de `vente.html`, et sur
  les deux listes d'écarts de `tableau-bord.html` — et s'affiche partout
  comme texte brut. Dernier résultat : **11/11**.
- **`verifier-stock-reel.mjs`** (cycle 11, C4) : `stock.html` — les 6
  opérations d'articles et de stock exécutées réellement (création,
  modification, réception, transfert inter-sites, casse, retours),
  **aucune occurrence de « FCFA » ni de champ de prix dans la page ou les
  réponses réseau vues par l'agent stock**, aucun bouton « Casse » pour
  lui, layout aux 5 largeurs. Dernier résultat : **26/26**.
- **`verifier-rapports-reel.mjs`** (cycle 12, C8) : `rapports.html` —
  historique des comptages filtré par période avec un vrai écart affiché ;
  sections gatées par rôle (l'agent stock ne voit que l'export du
  catalogue, jamais l'historique ni l'export des ventes, ni aucune
  occurrence de « FCFA ») ; un clic sur un bouton d'export déclenche un
  **vrai téléchargement de navigateur** intercepté et dont les premiers
  octets sont relus (`PK` pour un `.xlsx`, `%PDF` pour un `.pdf`) — pas
  seulement un code HTTP 200. Dernier résultat : **29/29**.

```
node verifier-cablage.mjs
node verifier-vente-reelle.mjs
node verifier-inventaire-reel.mjs
node verifier-echappement-html.mjs
node verifier-stock-reel.mjs
node verifier-rapports-reel.mjs
```

Détail complet des deux dans `DERNIER_RESULTAT.md`.

## `verifier-routes-appelees.mjs` (chantier A, point f)

Contrôle **statique** (aucun serveur, aucune base, aucun navigateur — juste
de la lecture de fichiers) : ajouté après avoir constaté que les boutons
« Casse » et « Retour client » de `stock.html` pointaient vers des routes
supprimées depuis le sous-chantier 2 (404 en production), sans qu'aucune
des 94 suites `verifier-cablage.mjs` ne le voie — aucune d'elles ne
cliquait sur ces deux boutons précis.

Construit deux listes puis les compare :
1. les routes RÉELLES, lues dans `server/app/routes/*.py` (préfixe du
   routeur déduit dynamiquement, jamais codé en dur) ;
2. les routes APPELÉES, lues dans `maquette/*.html` et `maquette/api.js`
   (`appelApi`, `telechargerFichier`, `fetch`, `.src = "/..."`) — en
   suivant les enveloppes locales (ex. `appeler(chemin, methode, ...)`
   dans `stock.html`/`rh.html`), sans quoi les appels qui PASSENT PAR
   elles seraient invisibles.

Échoue dès qu'un écran appelle une route qui n'existe pas ; affiche aussi,
en simple constat (jamais un échec), les routes réelles qu'aucun écran
n'appelle — une route sans écran n'est pas forcément un bug.

```
node verifier-routes-appelees.mjs
```

**Limite assumée** : preuve que rien n'appelle un 404 garanti, pas une
navigation réelle (ça reste le rôle des scripts Playwright ci-dessus). Un
appel construit de façon trop dynamique pour être reconnu par les motifs
du script (aucun cas de ce genre dans la maquette au moment où il a été
écrit) resterait invisible — à surveiller si un écran futur change de
style d'appel.
