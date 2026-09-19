---
name: finalisation-loop
description: >-
  Cycle de finalisation en 4 étapes pour la reconstruction d'Akuma, l'application
  de gestion de quincaillerie déployée aux Ets Quincaillerie Franck. À invoquer à
  chaque itération : on diagnostique par
  exécution réelle le cycle précédent, on propose des chantiers candidats du
  référentiel fixe C0–C14 sans en choisir aucun soi-même, on écrit l'objectif
  et le plan du chantier retenu puis on S'ARRÊTE pour attendre la validation
  explicite du propriétaire, et ce n'est qu'après cette validation qu'on
  implémente sur une branche dédiée, qu'on prouve le résultat par exécution
  réelle, puis qu'on met à jour l'état et qu'on committe.
---

# Cycle de finalisation — Akuma (Ets Quincaillerie Franck)

## But

Amener chacun des 15 chantiers (`C0`–`C14`) à 100 % de façon **vérifiable**, un
chantier à la fois, sans jamais se fier à la lecture du code ou à une intention :
**seule une exécution réelle fait foi**.

## Règles permanentes

- **Un seul chantier par cycle.** Pas de « pendant que j'y suis ».
- **Aucun chantier n'est choisi par l'agent seul.** L'agent diagnostique et
  propose ; c'est le propriétaire qui retient l'option. Cette règle n'a
  **pas** été respectée sur les cycles 4 à 7 (chantiers enchaînés sans
  validation intermédiaire) — elle est désormais obligatoire, voir l'Étape 3
  ci-dessous.
- **Mesure par exécution.** Lancer l'application / les tests / les requêtes.
  Une correction non exécutée est réputée **non faite**. Ceci s'applique
  aussi à la **vérification d'un cycle déjà livré** : ne jamais se fier au
  rapport produit à sa propre fin de cycle, le rejouer.
- **Ne jamais deviner une règle métier.** Si une décision manque, elle est posée
  dans `ADDENDUM_CAHIER_DES_CHARGES.md` et le cycle s'arrête sur ce point tant
  que la réponse n'est pas là. Un chantier qui obligerait à inventer une
  règle métier à la place du propriétaire n'est **pas proposable**.
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

## Les 4 étapes, avec un arrêt obligatoire à l'étape 3

Un cycle ne se déroule **jamais** en enchaînant directement diagnostic puis
implémentation. Les étapes 1 à 3 se font **avant tout code applicatif**, et
l'étape 3 se termine par un **arrêt obligatoire** : l'agent ne choisit pas
lui-même le chantier du cycle, il le propose et attend.

### Étape 1 — Test et diagnostic du cycle précédent

**Avant toute chose**, par exécution réelle — jamais en se fiant au rapport
produit à la fin du cycle précédent, jamais par lecture seule du code.

- Relancer **soi-même** la totalité des suites de tests annoncées par le
  cycle précédent (tests automatisés, suites SQL, vérifications Playwright
  ou autres) et comparer les résultats obtenus aux chiffres annoncés.
  Signaler tout écart, même minime.
- Relire le code de la pull request du cycle précédent comme le ferait un
  relecteur extérieur : chercher ce qui a été oublié, les cas limites non
  couverts, les protections qui ne tiennent que par une discipline de code
  plutôt que par la base (grants, contraintes, RLS).
- Vérifier **par exécution**, pas par lecture, les garanties critiques que
  le cycle précédent affirme avoir établies (ex. une donnée qui ne doit
  jamais fuiter, un rôle qui ne doit jamais accéder à une colonne) — y
  compris en contournant l'API pour aller directement en SQL sous le rôle
  concerné.
- Vérifier l'honnêteté de `loop-state.md` : chaque score est-il adossé à une
  preuve **vérifiable et rejouée** ? Corriger à la baisse tout score qui ne
  l'est pas, et le dire explicitement.
- Conclure clairement : la pull request du cycle précédent est-elle
  fusionnable en l'état, ou faut-il corriger quelque chose avant ?

Sortie de l'étape : une section « diagnostic » horodatée, avec les résultats
réels obtenus (pas recopiés du rapport précédent), consignée pour l'étape 2.

### Étape 2 — Propositions

Lister les options du prochain cycle : d'un côté d'éventuelles corrections
du cycle précédent (si l'étape 1 en a trouvé), de l'autre les chantiers
candidats du référentiel fixe. **Ne rien choisir** : proposer.

- Pour chaque option, en quelques lignes : ce qu'elle apporte au
  propriétaire, ce qu'elle exige comme décision métier non encore prise
  (le cas échéant), et ce qu'elle débloque pour la suite (ce qu'elle coûte
  en termes de portée/risque).
- Rappeler les blocages connus (décisions d'addendum non tranchées, mesures
  humaines de `UX_BASELINE.md` non faites, etc.) plutôt que de les redécouvrir
  à chaque fois.
- **Aucun chantier qui obligerait à inventer une règle métier** à la place
  du propriétaire ne doit être proposé.

### Étape 3 — Objectif retenu et plan d'action, PUIS ARRÊT

Pour **l'option recommandée, et pour elle seule** (l'agent peut recommander,
il ne décide pas) :

- l'objectif en une phrase ;
- des **critères de sortie mesurables et vérifiables par exécution** — une
  phrase testable : « quand j'exécute X, j'obtiens Y » (jamais « améliorer »,
  « nettoyer ») ;
- un plan d'action détaillé, étape par étape ;
- les risques, et ce dont l'agent a besoin de la part du propriétaire.

> **>>> ARRÊT. Attente de validation explicite du propriétaire. <<<**
> Ceci n'est pas une formalité : l'agent **ne crée aucune branche, n'écrit
> aucun code applicatif, ne modifie aucune donnée** tant que le propriétaire
> n'a pas validé explicitement l'objectif et le plan. Si l'agent se surprend
> à commencer une implémentation avant cette validation, il s'arrête.

### Étape 4 — Mise en œuvre, vérification, mémoire

**Seulement après validation explicite du propriétaire** à l'étape 3.

- Implémenter sur une **branche dédiée** : `cycle-N-<chantier>`
  (ex. `cycle-3-C4-stock`, `cycle-7-C9-ecran-vente`), à la portée strictement
  limitée au plan validé.
- Migrations de schéma numérotées, jamais de modification manuelle de la base.
- **Prouver par exécution réelle** que chaque critère de sortie est atteint :
  rejouer exactement la commande / le scénario, joindre la preuve (sortie de
  test, capture, journal, résultat de requête, avant/après), et rejouer un
  test de non-régression minimal sur le chantier voisin le plus exposé. Si
  la preuve n'est pas concluante, revenir en arrière dans l'implémentation —
  **une correction non exécutée est réputée non faite**.
- Mettre à jour `RAPPORT AVANCEMENT/loop-state.md` : nouveau score du
  chantier, date, preuve, reste à faire.
- **Committer** sur la branche, message en français décrivant le chantier,
  le critère et la preuve. **Ouvrir la PR** vers `main`.
- Le **propriétaire** décide de la fusion (après relecture, ou après le
  diagnostic du cycle suivant à l'étape 1) — l'agent ne fusionne pas de sa
  propre initiative.
- Retour à l'étape 1 pour le cycle suivant : diagnostic de CE cycle, avant
  toute nouvelle proposition.

---

## Format d'un cycle dans `loop-state.md`

```
## Cycle N — <Code chantier> <titre>
- Date : AAAA-MM-JJ
- Étape 1 — Diagnostic du cycle précédent : <suites rejouées, écarts trouvés
  vs. rapport précédent, honnêteté des scores corrigée le cas échéant,
  verdict fusionnable ou non de la PR précédente>
- Étape 2 — Propositions : <options envisagées, apport/coût/blocage de
  chacune, blocages connus rappelés>
- Étape 3 — Objectif retenu et plan : <critère de sortie vérifiable, plan
  d'action> — VALIDÉ PAR LE PROPRIÉTAIRE le AAAA-MM-JJ (référence du message
  ou de la décision)
- Étape 4 — Branche : cycle-N-<chantier>
  — Vérification : <commande rejouée + résultat + preuve>
  — Score : <ancien> % -> <nouveau> % | PR #<n> ouverte le AAAA-MM-JJ
- Reste à faire : <points ouverts, renvois addendum>
```

## Définition de « fini » pour un chantier

Un chantier est à **100 %** quand :

1. tous ses critères de sortie sont **prouvés par exécution** ;
2. il a une **couverture de test** rejouable (C13) ;
3. il est **documenté** (C14) ;
4. aucune décision métier le concernant n'est en attente dans l'addendum.
