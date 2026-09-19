# Maquette d'ergonomie — Akuma (cycle 1, chantier C9)

Maquette **fonctionnelle mais non câblée** des quatre écrans clés. Sert à mesurer
l'ergonomie **avant** tout développement métier.

- **Aucune connexion à PostgreSQL.** Aucune règle métier réelle.
- Toutes les données affichées viennent de `donnees-simulees.js`, seul fichier de
  données, qui sera remplacé plus tard par des appels au serveur.
- HTML + CSS + JavaScript simples. **Aucune chaîne de compilation.**
- Tous les jetons de design (couleurs, tailles, espacements, rayons, ombres) sont
  définis **une seule fois** dans `theme.css`. Aucune couleur en dur ailleurs.

## Lancer la maquette

Depuis ce dossier `maquette/` :

```
py -m http.server 8080
```

Puis ouvrir <http://localhost:8080/> dans un navigateur.

> `python -m http.server` fonctionne aussi si `python` est dans le PATH.
> Ouvrir les fichiers en `file://` fonctionne également, sauf le petit chargement
> de `donnees-simulees.js` qui exige un serveur : utilisez la commande ci-dessus.

## Écrans

| Fichier | Écran | Cible d'affichage |
|---|---|---|
| `index.html` | Sommaire | toutes |
| `connexion.html` | Connexion | PC + téléphone |
| `vente.html` | Vente (PC de caisse), tout au clavier | 1366×768 |
| `tableau-bord.html` | Tableau de bord responsable | téléphone d'abord (390 px) |
| `inventaire.html` | Comptage d'inventaire à l'aveugle | téléphone, une main |

## Raccourcis clavier de l'écran de vente

| Touche | Action |
|---|---|
| `F2` | Aller au champ de recherche |
| `Entrée` | Ajouter au panier l'article sélectionné |
| `↑` `↓` | Choisir dans la liste de suggestions |
| `F4` | Changer de mode de paiement |
| `Échap` | Effacer la recherche |
| `F9` | Valider la vente (une confirmation) |

Ajouter un article au panier = **taper la recherche puis `Entrée`** (deux actions ;
une seule si le texte est déjà saisi, ou un clic sur une suggestion).

## Comptage à l'aveugle — note importante

`donnees-simulees.js` **ne contient pas** de champ « quantité attendue » pour
l'inventaire, et l'écran n'en charge aucune. C'est volontaire : le comptage doit
être un vrai contrôle. L'écart sera calculé côté serveur (voir `MODELE_DONNEES.md`
et le chantier C1).

## Captures

`captures/` contient une capture de chaque écran à 360, 390, 768, 1366 et 1920 px
de large, produites lors de la vérification du cycle 1 (voir `../maquette/captures/`
et `../UX_BASELINE.md`).
