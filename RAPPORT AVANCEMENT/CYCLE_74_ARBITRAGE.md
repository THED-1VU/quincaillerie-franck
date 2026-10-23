# CYCLE 74 — Tableau d'arbitrage : 27 écarts ouverts, décisions D1–D13, priorisation P1

**Date :** 2026-10-23 (préparé au cycle 73, à exécuter dès les réponses du
propriétaire). **Base :** `REGISTRE_ECARTS_100.md` après cycle 73 — 13 écarts
CLOS, **27 ouverts** (15 P1, 10 P2, 2 P3). **Constat central : plus aucune
tâche technique indépendante n'est actionnable sans décision** — la dernière
(correctif durable du chemin PSQL dans `verifier_tout.sh`) a été traitée au
cycle 73. Le cycle 74 démarre dès qu'une seule réponse arrive.

**Légende impact :** **GO** = bloque la mise en production · **Score** =
bloque la qualification 99-100 % d'un chantier · **Qualité** = amélioration
sans blocage.

---

## 1. Les décisions (aucune ligne de code ne peut les remplacer)

| Priorité | Décision | Écart(s) | Question posée (réponse attendue en une ligne) | Impact | Ce que ça débloque |
|----------|----------|----------|--------------------------------------------------|--------|--------------------|
| **1** | **D11** Kaspersky | C11-01 | « Posez-vous l'exclusion ciblée de `db\outils\sauvegarder.ps1` (ou du dossier `_pgdev\sauvegardes\`) dans Kaspersky ? » — **action sur votre poste, droits admin** | **GO** — la sauvegarde chiffrée est à l'arrêt sur votre poste (reproduit au cycle 73) | C11, C12 ; condition préalable de la fiche R4 (installation) |
| **2** | **D1** prix caissier | C3-01 | « Option 1 confirmée : le caissier voit le prix de vente, jamais le prix d'achat (état actuel vérifié) ? » | GO + Score C3 | fermeture C3-01 ; variante d'écran seulement si vous répondez autre chose |
| **3** | **D4** seuil remises | C5-02 | « Quel pourcentage déclenche l'alerte/validation (ex. 10 %), et alerte ou blocage ? » | **GO** | C5-02 : paramétrage + tests (mécanisme déjà livré, inactif) |
| **4** | **D5** HT/TTC | C1-02 | « Prix saisis TTC confirmé (hypothèse en place depuis le cycle 6) ? Faut-il la colonne HT par ligne sur les documents ? » | **GO** | C1-02 ; **à trancher avant tout import réel** (fiche R5) |
| **5** | **D2** paiements mixtes | C1-01 | « Une vente peut-elle combiner espèces + Mobile Money ? Si oui (rare/frequent ?) » | **GO** | C1-01 : table `ventes_paiements` (migration 051+) ou statu quo accepté |
| **6** | **D9** `utilisateur_caisse_id` | C5-01 | « L'encaissement est tracé au nom du responsable même quand un agent saisit — conserver (option 1) ou tracer l'agent réel (option 2, correctif court) ? » | Score C5 | C5-01 : correctif prêt à coder dès réponse |
| **7** | **D3** fond de caisse | C6-01 | « Fond de caisse initial : montant ? par site ou par session ? seuil d'écart toléré (FCFA) ? qui régularise ? » | Score C6 | C6-01 : modèle + écran + tests |
| **8** | **C6-02** règles marginales | C6-02 | « Vente après minuit = jour précédent ? Mobile Money confirmé hors-ligne ? ventes bloquées après clôture ? » (3 sous-réponses) | Score C6 | C6-02 : règles + tests ciblés |
| **9** | **C2-01** 5 paramètres | C2-01 | Confirmer : `tentatives_max_connexion=5`, `duree_session_minutes=480` (décidé 2026-09-22), `boutique_numero_contribuable`, `boutique_telephone`, `seuil_alerte_plancher` | Score C2 | bascule `a_decider=FALSE` + seed |
| **10** | **D6** confirmation session | C2-01 (volet D6) | « 8 h de session fixes pour la v1 (recommandé), paramètre non modifiable ? » | Score C2 | avec C2-01 → **C2 à 100 %** |
| **11** | **D7** cumul rôles UI | C3-03 | « Confirmer : un compte cumulé ne voit que son rôle principal à l'écran (API accepte tout) ? » | Qualité | avec D8 et D1 → **C3 à 100 %** |
| **12** | **D8** comptage responsable | C3-02 | « Confirmer : le comptage reste une tâche d'agent stock, le responsable supervise ? » | Qualité | idem |
| **13** | **C7-01** plafond comptage | C7-01 | « Confirmer le plafond de vraisemblance 10 000 unités/article ? » | Score C7 | confirmation écrite |
| **14** | **C12-02** alerte sauvegarde | C12-02 | « Échec de sauvegarde : alerte visible dans l'app (mécanisme minimal à construire) ou limite acceptée par écrit ? » | Score C12 | décision + éventuel petit mécanisme |
| **15** | **D10** 2FA | C2-02 | « 2FA : reportée après la v1 (recommandé, TOTP si retenu) ? » | Qualité | réponse → C2-02 accepté ou chantier |
| **16** | **PR #60** | — | « Fusionner ou fermer la PR #60 (doc chantier C, recommandation : fusionner) ? » | — | dernière PR ouverte |

**Réponses à coût nul (aucun développement) : D1, D6, D7, D8, C2-01, C7-01,
C12-02 « limite acceptée », D10 « reportée », PR #60 → suffisent à porter
C2, C3 à 100 % et à faire bouger C7.**

---

## 2. Les campagnes humaines (fiches prêtes — `CYCLE_73_FICHES_RECETTE.md`)

| Priorité | Campagne | Fiche | Écart(s) | Dépendance | Chantiers vers 100 % |
|----------|----------|-------|----------|------------|----------------------|
| **A** | 2ᵉ campagne UX (tous parcours) — **débloquée : la version fusionnée existe** | R1 | C9-01 (+ échos C4-03, C7-04) | aucune (testeur + temps) | C9, C10 |
| **B** | Recette 3 rôles | R2 | (recette générale) | A conseillé | C3 (terrain), C10 |
| **C** | Impression ticket réelle | R1 §2 | C5-03 | imprimante | C5 |
| **D** | 2ᵉ campagne comptage physique | R1 §6 élargie | C7-04 | stock physique | C7 |
| **E** | Installation réelle 2ᵉ poste (**sur autorisation explicite**) | R4 | C0-02, C0-03, C11-02, C12-03 | **D11 d'abord** + matériel + autorisation | C0, C11, C12 |
| **F** | Restauration sur 2ᵉ PC (RTO 2 h) | R3 | C12-01 | E fait | C12 |
| **G** | Test multi-postes simultané | (R3/R4 extension) | C10-02 | E fait | C10 |
| **H** | Import du stock réel (**sur autorisation explicite**) | protocole C1-03 | C1-03 | D5 tranché + D11 | C1, jour J |
| **I** | PV de recette + GO/NO-GO | R5 | C10-01, C14-02 | tout ce qui précède | C10, C14, GO |

---

## 3. Ordre de fermeture des chantiers (propositions)

1. **Sans aucune ligne de code** (réponses §1 coût nul) : **C2 → 100 %**
   (C2-01 + D6 + D10 « reportée »), **C3 → 100 %** (D1 + D7 + D8),
   C7 progresse (C7-01).
2. **Avec correctifs courts après décision** : C5 (D4 + D9 + C5-03),
   C6 (D3 + C6-02), C1 (D2 + D5 — l'import C1-03 restant au jour J).
3. **Avec campagnes** : C9, C10 (A → B → H selon calendrier),
   C4 (campagne stock R1 §4-5), C7 (D).
4. **Au jour J** (autorisations) : C0, C11, C12, C14 (E → F → I).

Moyenne indicative si toutes les réponses coût nul tombent + campagne A
réalisée : ≈ 85-87 % ; les 13-15 points restants sont les validations
physiques (E, F, G, H, I) et leurs correctifs dérivés.

---

## 4. Ce que le développement fera automatiquement dès réponse

| Réponse reçue | Travail lancé | Livrable |
|---------------|---------------|----------|
| D2 « multi-modes » | migration 051 `ventes_paiements` + route + écran + tests | PR dédiée |
| D2 « mono-mode » | tracé d'acceptation au registre | rien à coder |
| D4 (pourcentage + mode) | activation `seuil_remise_validation_pct` + alerte/blocage + pytest + Playwright | PR dédiée |
| D9 « option 2 » | correctif `ventes.py` (id du compte authentifié) + tests | PR dédiée |
| D3 (montants) | modèle fond de caisse + écran clôture + tests | PR dédiée |
| C6-02 (règles) | ajustements ciblés + pytest 23 h 59/00 h 01 | PR dédiée |
| C1-02 « colonne HT » | ventilation HT ligne à ligne (reçu + rapports) | PR dédiée |
| C12-02 « mécanisme » | alerte échec sauvegarde (carte tableau de bord) + test échec simulé | PR dédiée |
| D1/D2 variante | écran caissier « total seul » + tests par rôle | PR dédiée |

Toute variante de réponse est traitée de la même façon : le constat
technique est prêt, seul le choix métier manque.

---

*Généré au cycle 73 pour le cycle 74. Aucune de ces lignes n'engage une
décision métier : les recommandations restent celles, argumentées, du
`CYCLE_73_ANALYSE_REGISTRE.md` §4.*
