---
name: finalisation-loop
description: >-
  Cycle de finalisation en 5 phases pour la reconstruction de l'application
  Quincaillerie Franck. À invoquer à chaque itération : on choisit UN seul
  chantier du référentiel fixe C0–C14, on mesure son état réel par exécution,
  on l'implémente sur une branche dédiée, on prouve le résultat par exécution
  réelle, puis on met à jour l'état, on committe et on fusionne.
---

# Cycle de finalisation — Quincaillerie Franck

## But

Amener chacun des 15 chantiers (`C0`–`C14`) à 100 % de façon **vérifiable**, un
chantier à la fois, sans jamais se fier à la lecture du code ou à une intention :
**seule une exécution réelle fait foi**.

## Règles permanentes

- **Un seul chantier par cycle.** Pas de « pendant que j'y suis ».
- **Mesure par exécution.** Lancer l'application / les tests / les requêtes.
  Une correction non exécutée est réputée **non faite**.
- **Ne jamais deviner une règle métier.** Si une décision manque, elle est posée
  dans `ADDENDUM_CAHIER_DES_CHARGES.md` et le cycle s'arrête sur ce point tant
  que la réponse n'est pas là.
- **Référentiel fixe, jamais renuméroté** (voir plus bas).
- **Français** pour tous les livrables, messages, commits.
- Ne pas committer : `config.ini` réel, mots de passe, clés, sauvegardes de
  données réelles, exécutables.

## Le référentiel fixe (NE JAMAIS RENUMÉROTER)

| Code | Chantier |
|------|----------|
| C0 | Infrastructure et dépôt |
| C1 | Base de données et intégrité |
| C2 | Authentification et comptes |
| C3 | Habilitations et cloisonnement des rôles |
| C4 | Articles et stock |
| C5 | Ventes et facturation |
| C6 | Comptabilité et RH |
| C7 | Inventaire et écarts |
| C8 | Tableaux de bord et rapports |
| C9 | Ergonomie et UI *(priorité 1)* |
| C10 | Mobile et API web *(priorité 1)* |
| C11 | Sécurité applicative |
| C12 | Sauvegarde et exploitation |
| C13 | Tests automatisés et qualité |
| C14 | Documentation et livrables |

Priorités du propriétaire, dans l'ordre : **1. rendu / ergonomie / responsivité —
2. usage téléphone (suivi ET saisie) — 3. fiabilité métier.** À score égal, on
traite d'abord le chantier qui sert la priorité la plus haute.

---

## Les 5 phases

### Phase 1 — Diagnostic / test

Mesurer l'**état réel** du candidat, par exécution, jamais par lecture seule.

- Lancer ce qui existe : application, API, migrations, suite de tests, requêtes
  SQL de contrôle.
- Rejouer les scénarios pertinents (`GUIDE_TESTEUR_POSTES_ET_SCENARIO`,
  checklists du dossier de recette, tests transversaux).
- Consigner : ce qui marche, ce qui casse, avec **la sortie réelle** (log,
  message d'erreur, capture, résultat de requête).
- En déduire le **score actuel** du chantier (0–100 %) et le justifier en une
  phrase adossée à une preuve.

Sortie de phase : une section « constat » horodatée dans `loop-state.md`.

### Phase 2 — Objectif

Choisir **UN seul chantier** et écrire un **critère de sortie vérifiable**.

- Le critère est une phrase testable : « quand j'exécute X, j'obtiens Y ».
  Exemples : « `pytest tests/test_stock.py` passe à 100 % », « deux ventes
  concurrentes sur stock=1 laissent le stock à 0, jamais négatif, avec un seul
  écart consigné », « la page de vente s'affiche sans débordement à 1366×768
  (capture jointe) ».
- Pas de critère vague (« améliorer », « nettoyer »).
- Si le chantier dépend d'une décision métier non tranchée → **stop**, on
  renvoie à l'addendum et on choisit un autre chantier.

Sortie de phase : l'objectif du cycle N écrit dans `loop-state.md`.

### Phase 3 — Action

Implémenter sur une **branche dédiée** : `cycle-N-<chantier>`
(ex. `cycle-3-C4-stock`, `cycle-7-C9-ecran-vente`).

- Portée limitée au chantier choisi et à son critère de sortie.
- Pas de code applicatif pendant un cycle de **cadrage** (comme celui-ci) ;
  à partir des cycles de reconstruction, le code est autorisé sur la branche.
- Migrations de schéma numérotées, jamais de modification manuelle de la base.

### Phase 4 — Vérification

**Prouver par exécution réelle** que le critère de sortie est atteint.

- Rejouer exactement la commande / le scénario du critère.
- Joindre la **preuve** : sortie de test, capture, journal, résultat de requête,
  avant / après.
- Rejouer aussi un **test de non-régression** minimal sur le chantier voisin le
  plus exposé.
- Si la preuve n'est pas concluante → retour en Phase 3. **Une correction non
  exécutée est réputée non faite.**

### Phase 5 — Mémoire

- Mettre à jour `RAPPORT AVANCEMENT/loop-state.md` : nouveau score du chantier,
  date, preuve, reste à faire.
- **Committer** sur la branche (`git commit`), message en français décrivant le
  chantier, le critère et la preuve.
- **Ouvrir la PR** vers `main`.
- **Fusionner après vérification** (la PR référence la preuve).
- Choisir le chantier du cycle suivant (retour Phase 1).

---

## Format d'un cycle dans `loop-state.md`

```
## Cycle N — <Code chantier> <titre>
- Date : AAAA-MM-JJ
- Phase 1 — Constat : <état réel mesuré, preuve>
- Phase 2 — Objectif : <critère de sortie vérifiable>
- Phase 3 — Branche : cycle-N-<chantier>
- Phase 4 — Vérification : <commande rejouée + résultat + preuve>
- Phase 5 — Score : <ancien> % -> <nouveau> % | PR #<n> fusionnée le AAAA-MM-JJ
- Reste à faire : <points ouverts, renvois addendum>
```

## Définition de « fini » pour un chantier

Un chantier est à **100 %** quand :

1. tous ses critères de sortie sont **prouvés par exécution** ;
2. il a une **couverture de test** rejouable (C13) ;
3. il est **documenté** (C14) ;
4. aucune décision métier le concernant n'est en attente dans l'addendum.
