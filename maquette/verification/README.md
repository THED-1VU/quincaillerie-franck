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
