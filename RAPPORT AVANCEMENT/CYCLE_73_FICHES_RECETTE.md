# CYCLE 73 — Fiches de recette prêtes à l'emploi (campagnes humaines)

**Date :** 2026-10-23 (cycle 73). **But :** chaque campagne humaine restante
(carta D12 du registre des décisions) dispose d'un support **immédiatement
utilisable** : scénario, résultats attendus, cases de validation, preuves à
collecter, critères GO/NO-GO. Aucune campagne n'est lancée par le
développement : chaque fiche attend le feu vert du propriétaire.

**Version à recetter :** `main` = `d745ead` (mise à jour du 2026-10-23 par le
contre-audit indépendant : cycle 75 et lots Codex C1/C2/C3 fusionnés, donc
décisions D2, D4, D6, D7, D9 et C12-02 incluses — la version `d0fa264`
citée à l'origine de cette fiche ne les contenait pas). **Avant chaque
campagne :** rejouer la régression automatisée (`bash db/outils/verifier_tout.sh`
ou, séparément, `pytest server/tests` puis les 13 suites Playwright) — dernière
preuve : contre-audit du 2026-10-23 sur `d745ead`, 394 pytest et 13/13
suites, voir `AUDIT_INDEPENDANT_d745ead.md`.

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
| 13 | Vente mixte (D2) — comptoir.compta : 1 article à 6 500 FCFA réglé 4 000 espèces + 2 500 Mobile Money | vente acceptée ; reçu PDF « Mode de paiement : mixte » avec la décomposition ; UNE seule recette de 6 500 ; une décomposition qui ne totalise pas 6 500 est refusée | ☐ | |
| 14 | Clôture de caisse du jour après la vente 13 | attendu espèces +4 000 et attendu Mobile Money +2 500 (ventilation par mode) | ☐ | |
| 15 | Remise (D4) — comptoir.compta : une ligne à −10 % puis une ligne à −11 % | −10 % accepté ; −11 % refusé avec le message « seul un compte responsable peut enregistrer cette vente » ; `resp` peut enregistrer −11 % | ☐ | |
| 16 | Remises CUMULÉES (D4) — comptoir.compta : remise de ligne −10 % ET remise globale −10 % sur la même vente | **à consigner tel quel et à faire trancher** : au 2026-10-23 la vente est acceptée (≈ −19 % cumulés sans validation du responsable) — voir « Défauts nouveaux » dans `AUDIT_INDEPENDANT_d745ead.md` ; le propriétaire dit si le seuil de 10 % s'applique au cumul | ☐ | |
| 17 | Session (D6) — se connecter, noter l'heure, se déconnecter, tenter de rouvrir une page protégée | retour à l'écran de connexion ; l'ancienne session ne revit pas. L'expiration à 480 minutes n'est PAS rejouable en séance : elle est prouvée par des contrôles automatiques (jeton à 481 min refusé, session échue refusée) | ☐ | |
| 18 | Compte cumulé (D7) — compte stock+comptabilité créé par `resp` | le bandeau de chaque page liste TOUS les écrans des deux rôles (vente, clients, inventaire, stock, rapports) ; comptes, RH, clôture et tableau de bord restent refusés | ☐ | |
| 19 | Alerte de sauvegarde (C12-02) — tableau de bord de `resp`, aucune sauvegarde encore tournée sur le poste | bandeau d'alerte visible « Aucune sauvegarde n'a encore tourné… » ; jamais un voyant vert sans sauvegarde datée | ☐ | |
| 20 | Deux postes en même temps (C10-02, volet applicatif) — deux navigateurs ouvrent chacun une vente du MÊME article au même instant | les deux ventes sont enregistrées, aucun message d'erreur, le stock baisse de 2. (Épreuve à DEUX postes physiques : fiche R4/R3, hors de cette fiche.) | ☐ | |
| 21 | Encaisseur (D9) | **non vérifiable à l'écran** : aucun écran ni rapport n'affiche aujourd'hui qui a encaissé. La preuve est faite par requête de lecture sur `ventes.utilisateur_caisse_id` (développeur) — à noter au PV ; si le propriétaire veut le voir à l'écran, c'est une demande d'évolution, non un défaut | ☐ | |

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
| 9 | Compte cumulé stock+comptabilité (créé par resp) | UI = UNION des rôles, API = tous rôles (D7 option 2, validée le 2026-10-23 : le bandeau liste tous les écrans autorisés par l'ensemble des rôles ; comptes, RH, clôture et tableau de bord restent refusés) | — | ✔ union | ✔ union |

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

- [ ] Régression automatisée fraîche sur la version testée : pytest + 13 suites Playwright (dernière preuve : contre-audit du 2026-10-23 sur `main` = `d745ead`, 394 pytest, 13/13 suites)
- [ ] Fiche R1 (campagne UX n°2) : GO
- [ ] Fiche R2 (3 rôles) : GO
- [ ] Fiche R3 (restauration 2ᵉ PC) : GO
- [ ] Fiche R4 (installation) : GO
- [ ] Décisions **bloquantes GO** : D2 (paiements mixtes, option 2), D4 (remises ≤ 10 % / validation du responsable au-delà), D5 (TTC conservé), D6, D7, D8, D9, D10 sont **validées le 2026-10-23** (voir `DECISIONS_PROPRIETAIRE.md`) ; restent à trancher : D1 (prix caissier), D3 (fond de caisse / seuil d'écart), D11 (Kaspersky) — et, pour D5, les réponses du comptable Q1-Q6 avant tout import réel ; pour D4, la question du cumul remise de ligne + remise globale (fiche R1 ligne 16)
- [ ] Confirmations paramètres faites : les 6 lignes `a_decider` (`boutique_numero_contribuable`, `boutique_telephone`, `contact_support_technique`, `seuil_alerte_plancher`, `seuil_ecart_caisse_tolere`, `tentatives_max_connexion`) + la confirmation écrite du `plafond_vraisemblance_comptage` (C7-01)
- [ ] Décision sur la PR #60 consignée (« fusionner ou fermer »)

**Contenu du PV (à remplir pendant la séance de validation) :**

1. Version testée : sha de `main` + empreinte SHA-256 d'Akuma.exe + date.
2. Résultats des fiches R1-R4 (tableaux signés, anomalies relevées et leur sort :
   corrigé / accepté / reporté avec cycle dédié).
3. Risques résiduels acceptés par le propriétaire (liste écrite — ex. :
   2FA reportée après la V1 avec mesures compensatoires D10, `sauvegarder.ps1`
   toujours dépendant de l'exclusion antivirus D11, alerte de sauvegarde C12-02
   limitée à l'écran du responsable — elle prévient d'un échec ou d'une absence
   de sauvegarde, pas d'une sauvegarde qui ne tourne plus : voir « Défauts
   nouveaux » dans `AUDIT_INDEPENDANT_d745ead.md`).
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
