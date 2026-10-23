# CYCLE 74 — Calendrier des 9 campagnes humaines, regroupement par postes/testeurs, PV

**Date :** 2026-10-23 (cycle 74). **But :** rendre le tronçon humain
exécutable dans l'ordre et sans préparation supplémentaire. Les fiches de
scénario détaillées (cases à cocher, preuves, critères GO/NO-GO) sont dans
`CYCLE_73_FICHES_RECETTE.md` (R1-R5) — ce document ajoute **le quand, le où,
le qui, et les modèles de PV**.

**Version à recetter :** `main` = **`37b7b79`** (PR #91 fusionnée au cycle 74
— contient d0fa264 + correctifs régression/exe du cycle 73). Empreinte de
l'exe de référence : SHA-256
`15a355e932b1510f5437bd2b2ae44b4c252573878013b8b75a33b6998d249bd3`
(30 215 772 octets, construit au cycle 73). Avant chaque campagne sur le
poste principal : rejouer `bash db/outils/verifier_tout.sh` (13/13, EXIT=0).

---

## 1. Les 9 campagnes regroupées par poste et testeur

### Groupe 1 — Poste principal (la boutique), campagnes débloquées DÈS VOTRE ACCORD
*Testeurs : le responsable (vous) + 1 agent stock + 1 agent comptabilité.
Matériel : une imprimante pour C, le stock physique pour D.*

| Campagne | Fiche | Durée estimée | Dépendance | Pré-requis matériel |
|----------|-------|---------------|------------|---------------------|
| **A** — 2ᵉ campagne UX, tous parcours | R1 | 2-3 h (peut être coupée en 2 séances) | aucune | aucun |
| **C** — impression ticket réelle | R1 §2 | 30 min | aucune | **imprimante réelle** branchée au poste |
| **D** — 2ᵉ campagne comptage physique | R1 §6 (élargie) | 1-2 h | aucune | stock physique réel d'un échantillon d'articles |
| **B** — recette 3 rôles | R2 | 1-2 h | A conseillé avant | 3 comptes de travail (créés par vous, `comptes.html`) |

**Ordre conseillé dans la même semaine : A → C → D → B** (A et B partagent
les comptes ; D consomme un stock préparé ; C peut se glisser pendant A).

### Groupe 2 — Poste cible (le futur poste de caisse), campagnes séquentielles
*Testeur : vous seul (droits administrateur). Ces campagnes nécessitent
l'autorisation explicite « installation réelle » + le matériel.*

| Campagne | Fiche | Durée estimée | Dépendance |
|----------|-------|---------------|------------|
| **E** — installation réelle 2ᵉ poste | R4 | 3-4 h (incl. redémarrage du poste) | **D11 traité d'abord** + autorisation explicite + poste cible |
| **F** — restauration sur 2ᵉ PC (RTO 2 h) | R3 | 2 h chronométrées | E fait (il faut une installation qui a produit des données) |
| **G** — test multi-postes simultané | extension R3/R4 | 1 h | E et F faits |

**Ordre impératif : E → F → G** (chaque étape sert de socle à la suivante).

### Groupe 3 — Jour J (boutique réelle, sur autorisation explicite)

| Campagne | Support | Durée estimée | Dépendance |
|----------|---------|---------------|------------|
| **H** — import du stock réel | protocole C1-03 | 1-2 h | **D5 (HT/TTC) tranché** + D11 + sauvegarde pré-import (E/F prouvent la chaîne) |
| **I** — PV de recette + GO/NO-GO | R5 | 1 h de séance | TOUT ce qui précède est vert |

---

## 2. Calendrier réaliste proposé (les dates réelles restent à vous)

Semaine-type, en comptant des séances de 2-3 h autour des heures d'ouverture
de la boutique :

| Semaine | Contenu | Résultat attendu en fin de semaine |
|---------|---------|-------------------------------------|
| **S1** | Groupe 1 : A, C, D, B (3 séances courtes) | C9/C10 qualifiés terrain ; C5-03, C7-04 prouvés ; C3 confirmé terrain |
| **S2** | **D11 exécuté par vous** (procédure `CYCLE_74_D11_KASPERSKY_PROCEDURE.md`) **puis**, sur votre autorisation : E | installation validée, service PG survit au redémarrage, sauvegarde hors quarantaine |
| **S3** | F puis G | RTO ≤ 2 h prouvé ; multi-postes prouvé |
| **S4** | Préparation de H (protocole C1-03, fichier source, sauvegarde de précaution) + rattrapages éventuels | plan d'import figé |
| **Jour J** | H puis I, même matinée de préférence | PV signé, GO/NO-GO daté |

**Points de vigilance du calendrier :**
- D11 est la **seule dépendance à dates flottantes** : tant qu'il n'est pas
  traité, S2-S3 et le Jour J sont bloqués ; S1 reste possible immédiatement.
- Si A relève des anomalies bloquantes, un cycle correctif s'intercale — le
  reste du calendrier glisse d'une semaine, l'ordre ne change pas.
- Les campagnes C et D dépendent du matériel/stock, pas de décisions : si
  l'imprimante ou l'échantillon de stock manque en S1, elles glissent seules
  en S2 sans affecter A ni B.

---

## 3. Fiches de preuve par campagne

Chaque campagne produit un dossier de preuves déposé dans
`RAPPORT AVANCEMENT/cycles/` (sous-dossier daté, ex. `2026-11-04_campagne_A/`) :

| Campagne | Fiche | Preuves à collecter |
|----------|-------|----------------------|
| A | R1 | tableau des 12 parcours rempli et daté + captures des anomalies + réponses écrites aux 5 questions « VOS RETOURS » |
| B | R2 | captures par rôle + tableau 9 contrôles rempli + version testée |
| C | R1 §2 | photo/scan du ticket imprimé + copie du PDF correspondant |
| D | R1 §6 | relevé papier des comptages + export écarts du jour (xlsx) + comparaison écran |
| E | R4 | checklist 11 points signée + captures (services.msc, planificateur, Get-FileHash de l'exe) + journal de la première sauvegarde |
| F | R3 | chronométrage écrit (début copie → fin contrôles) + relevés avant/après des 3 contrôles + captures de `restaurer.ps1` |
| G | extension | captures des 2 postes connectés simultanément + vente inter-postes tracée |
| H | protocole C1-03 | fichier source d'import archivé + journal d'import + totaux avant/après + sauvegarde pré-import référencée |
| I | R5 | PV final signé (modèle §5) |

---

## 4. Critères d'acceptation par campagne (résumé GO/NO-GO)

| Campagne | GO si… | NO-GO si… |
|----------|--------|-----------|
| A | aucun blocage des parcours 1-10, anomalies non bloquantes seulement | vente/encaissement impossible, total faux, perte de données, accès hors rôle réussi |
| B | 100 % des refus attendus observés, prix d'achat jamais visible hors responsable | un écran ou une donnée accessible hors périmètre |
| C | ticket imprimé lisible, montants = la vente | ticket illisible ou montants faux |
| D | comptages acceptés, écarts calculés = réalité, alertes conformes aux seuils | écart faux ou comptage perdu |
| E | 11 points OK, surtout service PG après redémarrage + sauvegarde sans quarantaine | service absent après redémarrage, sauvegarde requarantainée, exe non démarrable |
| F | restauration complète, données identiques, RTO ≤ 2 h | restauration en échec, données manquantes, RTO > 2 h |
| G | deux postes simultanés sans conflit, traçabilité correcte | écrasement de données, verrou fatal, incohérence |
| H | totaux import = totaux source, aucun rejet silencieux | écart de totaux, rejet sans message |
| I | toutes les cases pré-requis de R5 cochées | un seul pré-requis rouge → séance reportée avec liste des écarts |

---

## 5. Modèles de procès-verbaux

### 5.1 Mini-PV de campagne (un par campagne A-H)

```text
PV DE CAMPAGNE DE RECETTE — Akuma (Quincaillerie Franck)
Campagne : [A … H]        Fiche appliquée : [R1 … R5 / protocole C1-03]
Date : ____ /____ /2026    Lieu : [poste principal / poste cible / boutique]
Version testée : main = 37b7b79 — Akuma.exe SHA-256 :
15a355e932b1510f5437bd2b2ae44b4c252573878013b8b75a33b6998d249bd3 (si exe)

Déroulement : la fiche [R_] a été exécutée intégralement.
Résultats : ____ points OK / ____ points KO (détail en annexe ou verso)
Anomalies relevées (numéro, description, bloquant oui/non) :
  1. ______________________________________________________________
  2. ______________________________________________________________
Décision de campagne : [ GO ]  [ NO-GO ]  [ GO avec réserves : ______ ]
Preuves jointes : [captures / chronos / exports — lister]
Signé (testeur) : ____________________     Heure : ______
```

### 5.2 PV final (campagne I — reprend la structure R5)

```text
PROCÈS-VERBAL DE RECETTE FONCTIONNELLE FINALE — Akuma
Date : ____ /____ /2026    Signataire : (propriétaire) ____________________

1. Version validée : main = 37b7b79 — exe SHA-256 15a355e9…98d249bd3 —
   régression automatisée : verifier_tout.sh 13/13 suites, EXIT=0 (date : ______)
2. Campagnes A-H : PV individuels joints, bilan : ____ GO / ____ réserves
3. Anomalies relevées et leur sort : corrigé / accepté / reporté (cycle ___)
   1. ______________________________________________________________
4. Risques résiduels ACCEPTÉS par écrit (ex. C12-02 journal local, D10 2FA
   reportée, D2 paiements mixtes si option 1) :
   ______________________________________________________________
5. Plan de retour arrière : dernière sauvegarde du ____/____ (fichier
   ____________, phrase secrète conservée ____________), déclencheur : ______
6. Décision : [ GO ]  [ GO CONDITIONNEL — conditions : ____________ ]
   [ NO-GO — écart bloquant : ____________ ]
```

**Où déposer :** `RAPPORT AVANCEMENT/cycles/<date>_<campagne>/` ; le PV final
rejoint en outre la racine du dossier de mise en production (note de
transfert C14-03 déjà prête, contacts à compléter par vous).

---

## 6. Ce que le développement fait en parallèle (sans attendre les campagnes)

- Toute réponse de décision (D1-D10, C2-01, C6-02, C7-01, C12-02, PR #60)
  déclenche son correctif/documenté selon le tableau « Ce que le développement
  fera automatiquement dès réponse » de `CYCLE_74_ARBITRAGE.md` §4.
- Chaque mini-PV reçu entraîne la mise à jour du registre (`REGISTRE_ECARTS_100.md`)
  et du tableau de pilotage (`CYCLE_74_PILOTAGE_CHANTIERS.md`) — aucun score
  n'est relevé sans preuve datée.
- Aucune campagne n'est lancée par le développement ; les exécutions réelles
  (installation, import, production) restent sous votre autorisation explicite.
