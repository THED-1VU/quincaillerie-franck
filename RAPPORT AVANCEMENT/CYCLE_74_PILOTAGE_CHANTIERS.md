# CYCLE 74 — Tableau de pilotage vers 99-100 % : les 15 chantiers

**Date :** 2026-10-23 (cycle 74). **Base :** `REGISTRE_ECARTS_100.md` après
fusion PR #91 (main = `37b7b79`) — 13 écarts CLOS, **27 ouverts** (15 P1,
10 P2, 2 P3). **Scores actuels = référence registre/loop-state après cycle
73 ; aucun score n'est relevé dans ce document sans preuve datée.**

**Lecture :** « Décisions » renvoie aux 16 lignes de
`CYCLE_74_ARBITRAGE.md` ; « Tests humains » renvoie aux campagnes A-I de
`CYCLE_74_CAMPAGNES_CALENDRIER.md` ; « Travaux » = ce que le développement
code DÈS la réponse (aucun travail lancé avant).

| Chantier | Score | Écarts restants | Décisions nécessaires | Tests humains | Travaux techniques éventuels | Condition exacte pour viser 99-100 % |
|----------|-------|-----------------|----------------------|---------------|------------------------------|--------------------------------------|
| **C0** Infrastructure | 90 % | C0-02, C0-03 | autorisation explicite d'installation réelle | campagne **E** (fiche R4, 11 points) | aucun | checklist R4 100 % OK sur le poste cible — en particulier service PG survivant au redémarrage (pts 4-5) et empreinte exe vérifiée (pt 9) |
| **C1** Base de données | 92 % | C1-01, C1-02, C1-03 | **D2** (paiements mixtes), **D5** (HT/TTC) | campagne **H** (import réel, jour J) | si D2 « multi » : migration 051 `ventes_paiements` + route + écran + tests ; si D5 retient la colonne HT : ventilation des documents | D2 + D5 tranchées, correctifs éventuels verts en CI, puis campagne H : totaux importés = fichier source, aucun rejet silencieux |
| **C2** Authentification | 82 % | C2-01, C2-02 | **C2-01** (5 confirmations), **D6** (session 8 h fixe), **D10** (2FA) | aucun (suites automatisées existantes) | bascule `a_decider=FALSE` + seed des valeurs confirmées ; rien pour D6 ; D10 « reportée » = acceptation écrite (sinon chantier TOTP dédié) | confirmations écrites C2-01 + D6 + D10 « reportée » → **C2 à 100 % sans une ligne de code** |
| **C3** Habilitations | 77 % | C3-01, C3-02, C3-03 | **D1**, **D8**, **D7** | campagne **B** (recette terrain 3 rôles, confirmative) | aucun — les options 1 recommandées sont déjà le comportement livré et testé | D1 + D7 + D8 confirmées par écrit → C3-01/02/03 CLOS → **C3 à 100 % sans code** ; campagne B consigne la confirmation terrain dans son PV |
| **C4** Articles et stock | 78 % | C4-03 | aucune | campagne **A** (volets stock, parcours 4-6) + campagne **D** | correctifs dérivés si A relève des anomalies bloquantes (cycle correctif dédié) | campagne A GO sur les volets stock → C4-03 CLOS ; campagne D confirme en conditions réelles |
| **C5** Ventes et facturation | 81 % | C5-01, C5-02, C5-03 | **D9** (`utilisateur_caisse_id`), **D4** (seuil remises) | campagne **C** (impression ticket réelle) + volets vente de A | D9 option 2 : correctif court ; D4 : activation du paramétrage + tests (mécanisme livré, inactif) | D4 + D9 tranchées, correctifs verts en CI, campagne C GO (ticket imprimé lisible, montants exacts) |
| **C6** Clôture de caisse | 85 % | C6-01, C6-02 | **D3** (4 sous-réponses), **C6-02** (3 sous-réponses) | parcours clôture de campagne **A** (n° 7) + re-test après correctifs | modèle fond de caisse + écran + tests (D3) ; règles marginales + tests (C6-02) | D3 + C6-02 entièrement tranchés, développement livré et vert, clôture re-testée après correctifs |
| **C7** Inventaire et comptage | 67 % | C7-01, C7-04 | **C7-01** (confirmation plafond 10 000) | campagne **D** (2ᵉ comptage physique réel) | aucun — historique (C7-02) et export (C7-03) déjà livrés | C7-01 confirmé par écrit + campagne D GO (écarts calculés = réalité) → **C7 à 100 %** |
| **C8** Interfaces | 86 % | aucun (C8-01, C8-02 CLOS) | aucune spécifique | campagnes **A/B** (confirmatives) | aucun | aucun écart restant à portée du développement ; relevage éventuel du score sur PV de campagne A/B (à votre appréciation) |
| **C9** Tests et recette | 60 % | C9-01 | aucune | campagne **A** | aucun | campagne A GO : tableau R1 rempli, aucun blocage des parcours 1-10, PV de campagne signé |
| **C10** Qualité et non-régression | 58 % | C10-01, C10-02 | signature du PV final (campagne **I**) | campagnes **B**, **G**, **I** | aucun | B OK + G OK (multi-postes sans conflit) + **PV final signé** (I) |
| **C11** Sécurité | 85 % | C11-01, C11-02 | **D11** (procédure prête : `CYCLE_74_D11_KASPERSKY_PROCEDURE.md`) | campagne **E** (pts 9-10 : empreinte exe, sauvegarde de contrôle) | aucun | D11 exécuté — sauvegarde sans quarantaine, empreinte `3684aae0…9607a2` vérifiée — puis checklist C11-02 sur le poste cible (jour J) |
| **C12** Sauvegarde et reprise | 95 % | C12-01, C12-02, C12-03 | **C12-02** (alerte dans l'app vs « limite acceptée ») | campagne **F** (restauration 2ᵉ PC, RTO 2 h) | si alerte retenue : mécanisme minimal + tests ; C12-03 (résilience service PG) : constat réel en campagne E | C12-02 tranché (+ dev éventuel vert) + campagne F GO (données identiques, RTO ≤ 2 h) + constat C12-03 consigné en E |
| **C13** Intégration continue | 100 % | aucun | aucune | aucun (le job CI joue à chaque push) | aucun — maintenir le job vert | — déjà au plafond, fondé sur run CI « 13/13 suites réussies » (39900668426) + 3 régressions locales |
| **C14** Dossier de recette | 76 % | C14-02 | GO/NO-GO final ; sort de la **PR #60** | campagne **I** | aucun — note de transfert C14-03 livrée (contacts à compléter par vous) | PV final signé + pré-requis R5 tous verts (R1-R4 GO, décisions bloquantes D1/D2/D4/D5/D11 tranchées, PR #60 soldée) |

---

## Lecture d'ensemble (ce qui rapproche la moyenne de 100 %)

1. **Sans une seule ligne de code** : les réponses D1, D6, D7, D8, C2-01,
   C7-01, C12-02 « limite acceptée », D10 « reportée » + fusion/fermeture
   de la PR #60 → **C2 et C3 passent à 100 %, C7 à 100 % après campagne D**,
   C14 avance.
2. **Correctifs courts après décision** : D4 + D9 (C5), D3 + C6-02 (C6),
   D2 + D5 (C1) — chaque correctif est prêt à être codé le jour de la
   réponse (migration 051 réservée).
3. **Campagnes terrain** : A (C9, C4), B (C10), C (C5), D (C7) — toutes
   débloquées dès votre accord, aucune décision technique en amont.
4. **Jour J (autorisations explicites)** : E → F → G puis H et I — portent
   C0, C11, C12, C10, C14 jusqu'au PV signé.

**Moyenne actuelle : ≈ 80,8 %.** Plafond atteignable sans campagnes :
≈ 85-87 % (réponses coût nul + correctifs courts). Les derniers 13-15
points sont uniquement des validations physiques (E, F, G, H, I) et leurs
correctifs dérivés.

*Règle inchangée : aucun score n'est relevé sans preuve d'exécution réelle
(PV signé, run CI, journal) — l'estimation ci-dessus ne vaut pas score.*
