# UX_BASELINE — protocole de mesure d'ergonomie (chantier C9)

Ce document définit **comment mesurer** l'ergonomie de l'application, avec un
humain, chronomètre en main. Il est produit au cycle 1 à partir de la maquette
non câblée (`maquette/`).

> **Règle de progression du chantier C9 :**
> tant que le tableau de mesures ci-dessous (§4) n'est **pas rempli par un
> testeur humain** sur la vraie application, **C9 ne peut pas dépasser 60 %**.
> Les vérifications automatiques (`maquette/verification/`) prouvent l'absence de
> débordement et le nombre d'actions, mais **pas** la vitesse ni la
> compréhension : seul un test humain le fait.

---

## 1. Conditions de test (à respecter à chaque campagne)

| Paramètre | Valeur imposée |
|---|---|
| Poste PC de caisse | Windows d'entrée de gamme, écran **1366 × 768**, navigateur en plein écran |
| Téléphones | trois largeurs : **360**, **390** et **≈ 430 px** (un appareil réel par largeur si possible) |
| Réseau | réseau local de la boutique (pas une machine de développement) |
| Testeur | une personne **sans formation informatique préalable**, découvrant l'écran |
| Langue | interface **intégralement en français**, y compris messages d'erreur |
| Données | catalogue à **volumétrie réelle** (voir addendum, point j) une fois connue ; à défaut, au moins 40 articles |
| Chronométrage | chronomètre séparé ; on garde **le pire des 3 essais** par mesure |
| Preuve | capture d'écran à chaque anomalie ; heure et poste notés |

Un test est **accepté** seulement si l'objectif est atteint **sans contournement**
et **sans erreur non expliquée**.

---

## 2. Scénario chronométré (parcours de référence)

À exécuter dans l'ordre, sur la vraie application (pas la maquette), une fois
celle-ci câblée.

### Étape A — Connexion
1. Partir de l'écran de connexion, champs vides.
2. Saisir identifiant + mot de passe.
3. **Arrêt du chrono** quand le tableau de bord (ou l'écran de vente) est affiché
   et utilisable.
   → **Objectif : moins de 30 secondes.**

### Étape B — Vente de trois articles
1. Partir de l'écran de vente, panier vide. **Départ du chrono.**
2. Ajouter **article 1** : chercher par son nom, l'ajouter, régler la quantité.
3. Ajouter **article 2** de la même façon.
4. Ajouter **article 3** de la même façon.
5. Choisir un **mode de paiement**.
6. **Valider** la vente (une seule confirmation).
7. **Arrêt du chrono** quand la vente est enregistrée (message de succès).
   → **Objectif : moins de 60 secondes**, à partir de l'écran de vente prêt.

### Étape C — Correction d'une quantité
1. Sur une vente en préparation (2–3 lignes), **modifier la quantité** d'une ligne
   déjà saisie.
   → **Objectif : sans changer d'écran, sans rouvrir l'article.**

### Étape D — Annulation d'une ligne
1. Sur la même vente, **retirer une ligne** du panier.
   → **Objectif : une action identifiable, résultat visible immédiatement, le
   reste du panier conservé.**

### Étape E — Compréhension d'un message d'erreur
1. Provoquer 5 erreurs types (champ vide, quantité 0, mauvais mot de passe,
   recherche sans résultat, validation d'un panier vide).
2. Pour chacune : le testeur dit **à voix haute** ce qu'il doit faire pour
   corriger, **sans aide**.
   → **Objectif : message en français, placé près du champ concerné, action
   corrective comprise du premier coup.**

### Étape F — Lisibilité mobile
1. Ouvrir le tableau de bord responsable et l'écran de comptage sur les trois
   largeurs mobiles.
   → **Objectif : lisible sans zoom, sans défilement horizontal, boutons
   cliquables au pouce (≥ 44 px).**

---

## 3. Ce qui est déjà acquis au cycle 1 (maquette, vérifié par exécution)

Preuves : `maquette/verification/` (scripts `verifier-affichage.mjs` et
`verifier-flux.mjs`) et `maquette/captures/` (20 captures).

| Critère de sortie du cycle 1 | Résultat |
|---|---|
| Le serveur de maquette démarre, les 4 écrans s'affichent | **OK** (`py -m http.server 8080`) |
| Captures à 360, 390, 768, 1366 et 1920 px, sans débordement horizontal ni texte tronqué | **OK** — 20/20, `débordement=false` partout |
| Aucune erreur console sur les 4 écrans | **OK** — 0 erreur |
| Écran de vente : ajouter un article au panier ≤ 2 actions | **OK** — « taper la recherche » + `Entrée` (2 actions) ; 1 action si le texte est déjà saisi ou au clic |
| Cibles tactiles ≥ 44 px sur mobile | **OK** — minimum mesuré 44 px |
| Écran de vente entièrement utilisable au clavier | **OK partiel** — `F2` recherche, `Entrée` ajout, `↑`/`↓` sélection, `F4` paiement, `Échap` efface, `F9` valide (une confirmation) ; à confirmer en test humain sur clavier réel |
| Comptage d'inventaire à l'aveugle : quantité attendue absente de l'écran **et** du code de la page | **OK** — `donnees-simulees.js` ne porte que `id`/`nom`/`unité` pour l'inventaire ; champ de saisie vide au départ |
| Un seul fichier de thème, aucune couleur en dur dans un écran | **OK** — `maquette/theme.css` ; les écrans n'utilisent que `var(--…)` |
| Aucune largeur fixe > 1300 px | **OK** — conteneur `--largeur-max: 1280px` |
| Données simulées isolées | **OK** — `maquette/donnees-simulees.js`, remplaçable par des appels serveur |

**Ce que le cycle 1 NE prouve pas** (et qui fixe le plafond à 60 %) :
la vitesse réelle (étapes A et B chronométrées), la compréhension des messages
d'erreur par un utilisateur non formé (étape E), le confort sur appareils
mobiles réels, et le parcours clavier complet sur un vrai clavier de caisse.

---

## 4. Tableau de mesures — À REMPLIR PAR UN TESTEUR HUMAIN

Reproduire ce tableau à chaque campagne. Tant qu'il est vide, **C9 ≤ 60 %**.

| # | Mesure | Objectif | Essai 1 | Essai 2 | Essai 3 | Retenu (pire) | Conforme ? | Observation / capture |
|---|--------|----------|---------|---------|---------|---------------|-----------|-----------------------|
| A | Connexion (chrono) | < 30 s | | | | | ☐ oui ☐ non | |
| B | Vente de 3 articles (chrono) | < 60 s | | | | | ☐ oui ☐ non | |
| C | Correction d'une quantité | sans changer d'écran | | | | | ☐ oui ☐ non | |
| D | Annulation d'une ligne | 1 action, panier conservé | | | | | ☐ oui ☐ non | |
| E1 | Erreur « champ vide » comprise seul | oui | | | | | ☐ oui ☐ non | |
| E2 | Erreur « quantité 0 » comprise seul | oui | | | | | ☐ oui ☐ non | |
| E3 | Erreur « mot de passe » comprise seul | oui | | | | | ☐ oui ☐ non | |
| E4 | Erreur « recherche sans résultat » comprise seul | oui | | | | | ☐ oui ☐ non | |
| E5 | Erreur « panier vide » comprise seul | oui | | | | | ☐ oui ☐ non | |
| F1 | Tableau de bord lisible à 360 px sans zoom | oui | | | | | ☐ oui ☐ non | |
| F2 | Tableau de bord lisible à 390 px sans zoom | oui | | | | | ☐ oui ☐ non | |
| F3 | Comptage utilisable à une main à ≈ 430 px | oui | | | | | ☐ oui ☐ non | |
| G | Écran de vente : parcours complet **au clavier seul** | possible de bout en bout | | | | | ☐ oui ☐ non | |
| H | Aucun débordement à 1366 × 768 sur la vraie appli | oui | | | | | ☐ oui ☐ non | |

**Identité de la campagne**

- Date / heure : ______________________
- Testeur (nom, poste occupé) : ______________________
- Version de l'application : ______________________
- Poste Windows / résolution : ______________________
- Téléphones utilisés : ______________________

**Décision C9**

- ☐ Toutes les lignes conformes → C9 peut viser 100 % (sous réserve des autres critères du cycle en cours).
- ☐ Lignes non conformes : ______________________ → C9 plafonné, corrections à planifier.
