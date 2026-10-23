# CYCLE 73 — Fiches de recette prêtes à l'emploi (campagnes humaines)

**Date :** 2026-10-23 (cycle 73). **But :** chaque campagne humaine restante
(carta D12 du registre des décisions) dispose d'un support **immédiatement
utilisable** : scénario, résultats attendus, cases de validation, preuves à
collecter, critères GO/NO-GO. Aucune campagne n'est lancée par le
développement : chaque fiche attend le feu vert du propriétaire.

**Version à recetter :** `main` = `d0fa264` (cycles 61-72 fusionnés) — la
première version candidate complète. **Avant chaque campagne :** rejouer
`bash db/outils/verifier_tout.sh` (13/13 suites, EXIT=0) — preuve fraîche
produite au cycle 73.

**Comptes du jeu d'essai** (`db/tests/00_jeu_essai.sql`) : `resp`
(responsable), `magasin.stock` / `comptoir.stock` (agent_stock, sites 1/2),
`magasin.compta` / `comptoir.compta` (agent_comptabilite, sites 1/2). Sites :
1 = magasin de stock, 2 = comptoir de vente. Pour une recette réaliste, le
responsable crée des comptes de travail depuis `comptes.html`
(provisioning : le responsable crée tous les comptes — décision 2026-10-20).

---

## Fiche R1 — 2ᵉ campagne UX, tous parcours (C9-01 ; échos C4-03, C7-04)

**Objectif :** recette humaine de bout en bout sur la version fusionnée —
vente, stock, inventaire, caisse, comptes, rapports — par une personne qui
travaille réellement à la boutique (pas le développeur).

**Pré-requis :** application lancée (Akuma.exe ou serveur de dev), base avec
jeu d'essai, guide de retours du testeur (section « VOS RETOURS » de
`GUIDE_TESTEUR_INSTALLATION.txt`), formulaire papier ou WhatsApp pour les
retours, captures d'écran possibles.

**Scénario et résultats attendus (cocher quand vérifié) :**

| # | Parcours | Résultat attendu | OK | Anomalie |
|---|----------|------------------|----|----------|
| 1 | Connexion `resp` puis déconnexion | connexion acceptée, écran d'accueil par rôle, session libérée à la déconnexion | ☐ | |
| 2 | Vente comptoir (comptoir.compta) : 3 articles dont une remise | prix = prix_vente, remise saisissable, total exact, reçu PDF généré, vente visible dans le journal du jour | ☐ | |
| 3 | Vente à crédit (client existant) | créance enregistrée, visible sur la fiche client | ☐ | |
| 4 | Stock magasin (magasin.stock) : réception + transfert vers comptoir | quantités sites 1→2 cohérentes, mouvement tracé | ☐ | |
| 5 | Stock : casse/perte déclarée | stock diminué, motif enregistré | ☐ | |
| 6 | Inventaire (agent stock) : comptage d'un article | comptage accepté, écart calculé et visible au responsable | ☐ | |
| 7 | Clôture de caisse (resp) : journée avec ventes espèces + Mobile Money | espèces attendues = ventes du jour, écart affiché, clôture verrouillée | ☐ | |
| 8 | Comptes (resp) : créer un agent, changer son mot de passe | compte créé, connexion de l'agent fonctionne, changement de mot de passe imposé si applicable | ☐ | |
| 9 | Rapports (resp) : export stock + export écarts de comptage (xlsx et PDF) | fichiers téléchargés, totaux = écran | ☐ | |
| 10 | Rapports : export ventes du jour | montants = ventes saisies en 2-3 | ☐ | |
| 11 | RH : déclaration d'un employé | déclaration enregistrée, visible dans la liste | ☐ | |
| 12 | Essayer d'accéder à un écran hors rôle (agent → comptes) | accès refusé avec message clair, pas d'écran d'erreur brut | ☐ | |

**Preuves à collecter :** ce tableau rempli + captures des anomalies + réponses
écrites aux 5 questions « VOS RETOURS » + date/version testée.

**Critères GO :** aucun blocage de parcours 1-10 ; les anomalies relevées sont
cosmétiques ou non bloquantes. **NO-GO :** un parcours de vente/encaissement
impossible, un total faux, une perte de données, un accès hors rôle réussi →
cycle correctif dédié avant toute poursuite.

---

## Fiche R2 — Recette 3 rôles (responsable / agent stock / agent comptabilité)

**Objectif :** confirmer **en conditions réelles** le périmètre de chaque
rôle — la matrice automatisée existe (`MATRICE_ROLES_AKUMA.md`, suites
`roles` + `cablage`) ; cette recette fait la même vérification à la main,
pour le PV humain.

**Pré-requis :** application lancée, les 3 types de comptes du jeu d'essai
(ou comptes de travail équivalents créés par le responsable).

**Scénario et résultats attendus :**

| # | Contrôle | Résultat attendu | resp | agent_stock | agent_compta |
|---|----------|------------------|------|-------------|--------------|
| 1 | Tableau de bord | visible | ✔ attendu | ✖ refusé | ✖ refusé |
| 2 | Écran vente | accessible | ✔ | ✖ refusé | ✔ |
| 3 | Écran stock + inventaire | périmètre stock | ✔ tableau seulement (pas de comptage) | ✔ comptage | ✖ refusé |
| 4 | Écran caisse (clôture) | clôture | ✔ | ✖ refusé | ✖ refusé |
| 5 | Écran comptes + RH | gestion | ✔ | ✖ refusé | ✖ refusé |
| 6 | Écran rapports | exports | ✔ (stock + écarts + ventes + caisse) | ✖ refusé | ✔ (ventes, sans prix d'achat) |
| 7 | Prix d'achat visible | confidentialité | ✔ | jamais | jamais (écran comme réseau) |
| 8 | API directe (requête hors écran, si testeur technique) | garde côté serveur | — | 403 hors périmètre | 403 hors périmètre |
| 9 | Compte cumulé stock+comptabilité (créé par resp) | UI = rôle principal, API = tous rôles (comportement D7 option 1) | — | — | — |

**Preuves à collecter :** captures par rôle (comparables à
`maquette/captures/roles/`), tableau ci-dessus rempli et daté, version testée.

**Critères GO :** 100 % des refus attendus observés ; aucun prix d'achat
visible hors responsable. **NO-GO :** tout écran ou donnée accessible hors
périmètre.

---

## Fiche R3 — Test de restauration sur 2ᵉ PC (C12-01, C0-03)

**Objectif :** prouver le RTO 2 h : une sauvegarde chiffrée du poste A se
restaure sur un poste B indépendant et l'application fonctionne avec.

**Pré-requis :** poste A installé et utilisé (quelques ventes réelles de test),
sauvegarde produite par `sauvegarder.ps1` (⚠ exclusions antivirus à poser
D'ABORD, voir fiche R4 / D11), poste B vierge avec le dossier livré
(`Akuma.exe`, `_pgdev\pgsql\`, outils), phrase secrète de la sauvegarde,
`restaurer.ps1`.

**Scénario et résultats attendus :**

| # | Étape | Résultat attendu | OK | Durée réelle |
|---|-------|------------------|----|--------------|
| 1 | Sur A : produire une sauvegarde chiffrée | fichier daté présent + `dernier_etat_sauvegarde.json` à jour, **aucune quarantaine antivirus** | ☐ | |
| 2 | Copier la sauvegarde sur B (clé USB) | fichier intact (taille identique) | ☐ | |
| 3 | Sur B : installer PostgreSQL portable + l'exe (fiche R4 §1-3) | service/base opérationnels | ☐ | |
| 4 | Sur B : lancer `restaurer.ps1` avec la sauvegarde | restauration « OK », base recréée | ☐ | |
| 5 | Lancer Akuma.exe et se connecter | comptes, articles, stocks, ventes du poste A **tous présents** | ☐ | |
| 6 | Contrôles de comptage : total ventes, quantités de 3 articles, solde client à crédit | identiques à A (relevés AVANT la copie) | ☐ | |
| 7 | Noter l'heure de début (étape 2) et de fin (étape 6) | durée totale ≤ 2 h (RTO) | ☐ | |

**Preuves à collecter :** photos/captures de chaque étape, relevé des
contrôles avant/après, durée chronométrée, PV signé.

**Critères GO :** étapes 1-6 toutes OK, RTO ≤ 2 h. **NO-GO :** restauration en
échec, données manquantes, durée > 2 h → investigation avant GO.

---

## Fiche R4 — Validation du processus d'installation (C0-02, C0-03, C11-02)

**Objectif :** exécuter pour de vrai le parcours décrit dans
`INSTALLATION/` (aujourd'hui prouvé **par simulation seulement**,
`PREUVE_SIMULATION.md`) et vérifier le poste cible (C11-02 : lockfile, venv,
empreinte).

**Pré-requis :** poste cible disponible (idéalement le futur poste de caisse),
dossier d'installation complet (`INSTALLATION/README.md` §« à copier » :
`Akuma.exe`, `config.example.ini`, `_pgdev\pgsql\` complet, outils),
droits administrateur, `GUIDE_TESTEUR_INSTALLATION.txt` comme témoin du
parcours « primo-utilisateur ».

**Scénario et résultats attendus (reprend point par point
`INSTALLATION/CHECKLIST_INSTALLATION.md`) :**

| # | Étape | Résultat attendu | OK |
|---|-------|------------------|----|
| 1 | Exclusions antivirus posées (`postgres.exe`, `_pgdev\`, `db\outils\sauvegarder.ps1`) **avant** tout le reste | exclusions actives (capture des réglages) | ☐ |
| 2 | Copier l'arborescence (exe + `_pgdev\pgsql\` + outils) | arborescence conforme au README | ☐ |
| 3 | Premier lancement : initdb dans `_pgdev\data` (mot de passe demandé) | base initialisée, PostgreSQL démarre | ☐ |
| 4 | Enregistrer PostgreSQL comme **service Windows** (`enregistrer_service_pg.ps1`) | service présent et démarré | ☐ |
| 5 | **Redémarrer le poste** | PostgreSQL redémarre seul (service) — l'application redevient accessible sans action manuelle | ☐ |
| 6 | Planifier la sauvegarde (`planifier_sauvegarde.ps1`) | tâche planifiée visible dans le Planificateur Windows | ☐ |
| 7 | Créer le premier compte responsable (`creer_compte_responsable.ps1` ou équivalent) | compte créé, connexion OK | ☐ |
| 8 | Lancer `Akuma.exe` | caisse ouverte en mode kiosque, aucune erreur au premier plan | ☐ |
| 9 | Empreinte de l'exe : `Get-FileHash Akuma.exe -Algorithm SHA256` | empreinte notée et comparée à celle du poste de construction | ☐ |
| 10 | Vérifier venv/lockfile de construction (`pip-compile --check` équivalent, cf. dossier cycle 63-64) | environnement issu du lockfile | ☐ |
| 11 | Tâche de sauvegarde : forcer une exécution | sauvegarde chiffrée produite, **pas de quarantaine** | ☐ |

**Preuves à collecter :** checklist signée, captures (services.msc,
planificateur, hash), journal de la première sauvegarde.

**Critères GO :** étapes 1-11 OK, en particulier 4-5 (service survit au
redémarrage) et 11 (sauvegarde hors quarantaine). **NO-GO :** service absent
après redémarrage, sauvegarde requarantainée (→ D11 non traité), exe non
démarrable.

**Note d'honnêteté :** le guide historique `GUIDE_TESTEUR_INSTALLATION.txt`
(dans le dossier de test de septembre) décrit l'ancien packaging
(`QuincaillerieFranck.exe` + `config.ini` + SQL manuel) ; la référence du
parcours actuel est `INSTALLATION/README.md`. Le garder comme matériel de
recette « première prise en main », pas comme procédure d'installation.

---

## Fiche R5 — Recette fonctionnelle finale + décision GO/NO-GO (C10-01, C14-02)

**Objectif :** produire le **PV de recette signé** et consigner la décision
GO/NO-GO — la dernière pièce du dossier de mise en production.

**Pré-requis (tout doit être VERT avant d'ouvrir cette fiche) :**

- [ ] Régression automatisée fraîche : `verifier_tout.sh` 13/13, EXIT=0 (fait au cycle 73 sur `main` = `d0fa264`)
- [ ] Fiche R1 (campagne UX n°2) : GO
- [ ] Fiche R2 (3 rôles) : GO
- [ ] Fiche R3 (restauration 2ᵉ PC) : GO
- [ ] Fiche R4 (installation) : GO
- [ ] Décisions **bloquantes GO** tranchées : D1 (prix caissier), D2 (paiements mixtes), D4 (seuil remises), D5 (HT/TTC), D11 (Kaspersky) — D3, D9 suivent le même calendrier si le propriétaire les juge bloquantes
- [ ] Confirmations paramètres (C2-01 : 5 lignes `a_decider`) faites
- [ ] Décision sur la PR #60 consignée (« fusionner ou fermer »)

**Contenu du PV (à remplir pendant la séance de validation) :**

1. Version testée : sha de `main` + empreinte SHA-256 d'Akuma.exe + date.
2. Résultats des fiches R1-R4 (tableaux signés, anomalies relevées et leur sort :
   corrigé / accepté / reporté avec cycle dédié).
3. Risques résiduels acceptés par le propriétaire (liste écrite — ex. :
   alerte échec de sauvegarde limitée au journal local C12-02, 2FA reportée
   D10, paiements mixtes reportés D2 si option 1).
4. Plan de retour arrière (restauration de la dernière sauvegarde + qui la
   déclenche + où est la phrase secrète).
5. Checklists J-1 (sauvegarde complète, poste figé, pas de fusion en cours)
   et Jour J (exclusions AV vérifiées, service PG démarré, import du stock
   réel selon protocole C1-03, première vente test, PV de bascule).
6. Décision : **GO** / **NO-GO** / **GO conditionnel** (conditions listées) —
   datée et signée du propriétaire.

**Critères GO :** toutes les cases pré-requis cochées + aucune anomalie
bloquante ouverte. **NO-GO :** un seul pré-requis rouge → le PV liste
l'écart et son cycle de correction, la séance est reportée.

**Où déposer les preuves :** `RAPPORT AVANCEMENT/cycles/` (PV daté), registre
mis à jour (C9-01, C10-01, C12-01, C14-02), journal du cycle correspondant.

---

*Conformité : aucune de ces fiches ne remplace les décisions du propriétaire ;
elles rendent chaque validation humaine exécutable sans préparation
supplémentaire. Le développement reste à l'écart des exécutions réelles
(installation, import, production) tant que l'autorisation explicite n'est
pas donnée.*
