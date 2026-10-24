# LOT B — C8 : Interfaces et parcours — audit et preuves (2026-10-23)

Chantier confié à Qoder (Opération 100 % / Lot B). Base de preuve :
**exécution réelle**, jamais de lecture seule — chaque ligne ci-dessous
renvoie à un journal d'exécution daté.

---

## 0. Périmètre et environnement

- **Code testé** : branche `operation-100-lot-b`, commit de base `2dae406`
  (cycle 75 fusionné), worktree `QuincaillerieFranck_Test_LotB`.
- **Base** : `quincaillerie_lotb` (PostgreSQL 17 portable, port 5433) —
  base DÉDIÉE au Lot B, jamais `quincaillerie_test` (Codex), jamais une
  base de production. Reconstruction complète avant la régression
  (schéma d'origine + 52 migrations + jeu d'essai).
- **Serveur** : uvicorn sur le port 8020, configuration éphémère
  (`QF_CONFIG` vers un fichier temporaire, jamais le vrai `config.ini`,
  supprimé en fin de script — correctif d'isolation du Lot B dans
  `db/outils/verifier_tout.sh`).
- **Journaux** :
  - régression complète : `%TEMP%\lotb_regress4.log` (run 4, 2026-10-23) ;
  - campagne contre l'exécutable : §3 (reconstruction de l'exe sur le
    même code).

---

## 1. Régression d'interface complète — 13 suites Playwright, 505 contrôles

Exécutées par `db/outils/verifier_tout.sh` (run 4, 2026-10-23) contre le
serveur uvicorn ET la base `quincaillerie_lotb`. **13/13 suites OK,
505 contrôles, 0 échec.**

| # | Suite | Contrôles | Ce qu'elle prouve pour C8 |
|---|-------|-----------|---------------------------|
| 1 | routes | 65 | Chaque route du serveur répond et la matrice rôle×route est respectée (refus 403 côté API) |
| 2 | cablage | 101 | Connexion réelle des 3 rôles, redirection vers l'écran d'accueil du rôle ; cloisonnement du contenu (agent stock sans prix, comptable sans quantités) ; messages d'erreur serveur en français près du champ concerné ; 4 écrans sans débordement aux 5 largeurs |
| 3 | vente | 63 | Parcours de vente au comptoir de bout en bout : recherche article, panier, prix négocié, remises, encaissement, messages de confirmation |
| 4 | stock | 49 | Parcours agent stock : entrées, transferts, liste, mention quantités décimales |
| 5 | rapports | 52 | Consultation des rapports par rôle autorisé, montants cohérents avec les ventes créées |
| 6 | inventaire | 17 | Comptage et régularisation (responsable) |
| 7 | ux | 27 | Correctifs UX-1/2/3/4/6/7/9/10 : vente au clavier SANS AUCUN clic, messages d'indisponibilité en français, aucun débordement 360→1920, police ≥ 16 px, `type=number`/`inputmode=numeric`, avertissement « comptage définitif » visible |
| 8 | comptes | 26 | Parcours responsable de gestion des comptes : création, rôles cumulés, désactivation/réactivation, réinitialisation, refus de connexion d'un compte désactivé |
| 9 | caisse | 24 | Parcours clôture de caisse : attendu par mode, écart, commentaire, deuxième clôture refusée |
| 10 | rh | 21 | Parcours RH : employés, avances de salaire, remboursements |
| 11 | exploitation | 14 | Alertes d'exploitation : voyant sauvegarde « Réussie le … » servi par la route réelle, bandeau masqué quand tout va bien, carte ventes du jour, logo téléversé/supprimé depuis l'écran ; refus 403 agent stock |
| 12 | echappement | 11 | Aucune injection HTML : article au nom piégé rendu comme du texte |
| 13 | roles | 35 | Matrice complète : captures par rôle, refus d'une page interdite = redirection vers l'accueil du rôle (jamais une erreur nue), mot de passe provisoire forcé, cumul de rôles D7 (bandeau = UNION des permissions, aucun écran responsable) |

**Total : 505 contrôles, 0 échec** (journal `lotb_regress4.log`,
verdicts `>>> suite X : OK` pour les 13).

À cela s'ajoute la suite pytest du serveur (369 tests, couche API qui
porte les mêmes parcours) : **369 passed au run 3** (2026-10-23) ; au
run 4, 368 passed + 1 échec transitoire `psycopg.ConnectionTimeout` à
97 % du run ( PostgreSQL joignable et opérationnel avant et après ;
rejeu immédiat dans le même run : la suite Playwright `roles` qui suit
exécute 35 connexions réelles sans un seul échec — flake
d'infrastructure, pas un défaut de code).

---

## 2. Exigences C8 du propriétaire → preuve correspondante

| Exigence (ordre de mission) | Preuve d'exécution |
|------------------------------|--------------------|
| Parcours Responsable | suites comptes (26), caisse (24), rh (21), exploitation (14), inventaire (17), rapports — accueil tableau-bord, navigation bandeau, création de comptes, clôture, alertes |
| Parcours Caissier (agent comptabilité) | suites vente (63), cablage (101), caisse (24) — vente au clavier seule, encaissement, clôture |
| Parcours Agent stock | suites stock (49), cablage (101) — jamais un prix affiché, mentions décimales |
| Parcours Comptable | suites rapports (52), vente — montants TTC, jamais de quantités |
| Rôles cumulés | suite roles (35) : compte `agent_stock + agent_comptabilite` → bandeau union D7, `vente.html` atteignable en bandeau ET deep-link, aucun écran responsable |
| Menus et permissions | suite roles : refus d'une page interdite → redirection accueil du rôle ; suite routes : 403 API systématiques |
| Formulaires et validation | suites vente/comptes/rh : champs vides, valeurs invalides refusées avec message français près du champ (suite cablage, contrôle dédié) |
| Messages d'erreur | suite cablage : « messages d'erreur serveur s'affichent en français, près du champ concerné (jamais un message brut) » ; suite ux UX-7 : message serveur injoignable en français, bouton réactivé sans rechargement |
| Accessibilité élémentaire | suite ux : police pastilles ≥ 16 px (lu 17 px), `type="number"` et `inputmode="numeric"` rendus réellement, vente complète sans AUCUN clic de souris, F3 focus prix |
| Adaptation aux résolutions | suites cablage + ux : 5 largeurs **360 / 390 / 768 / 1366 / 1920 px**, débordement mesuré = 0 px sur toutes |
| Parcours vente et clôture | suites vente (63) + caisse (24) : de la recherche article au reçu, de l'attendu par mode à l'écart commenté |
| Alertes d'exploitation | suite exploitation (14) : voyant sauvegarde réel, bandeau d'alerte visible si échec/absence (C12-02), masqué si succès, cartes du tableau de bord alimentées par des données réelles |
| Compatibilité exécutable Windows | §3 ci-dessous |

---

## 3. Compatibilité exécutable Windows — reconstruction et campagne contre l'exe

### 3.1 Reconstruction (2026-10-23)

Reconstruit depuis LE MÊME code que la régression ci-dessus (branche
`operation-100-lot-b`, worktree Lot B — le `.spec` résout tous ses
chemins depuis `SPECPATH`, le paquet fige donc bien le code du worktree) :

```
construction : python -m PyInstaller server/fabrication/quincaillerie_franck.spec
               --distpath dist --workpath build --noconfirm
résultat     : server/fabrication/dist/Akuma.exe
taille       : 30 224 147 octets (28,8 Mo)
SHA-256      : df936f62a4aa18283f7c671688273c0fe68f736289226ae71dc9cb8499ed8597
```

Vérification de complétude du paquet AVANT la campagne : aucun fichier
servi par la maquette n'a été ajouté depuis le build du cycle 73
(`git diff --name-status d0fa264..HEAD -- maquette` : uniquement des
MODIFICATIONS d'écrans déjà embarqués — `vente.html`,
`tableau-bord.html`, `stock.html`, `declarations.html`, `api.js`,
`styles.css` — aucun fichier nouveau) ; la liste `FICHIERS_MAQUETTE`
du `.spec` reste donc complète (piège du cycle 63 : un écran nouveau
non listé serait servi en 404 par l'exe).

### 3.2 Campagne contre l'exe (exécutée le 2026-10-23)

Script : `db/outils/campagne_exe_lotb.sh` (procédure des cycles 63/73,
journal `%TEMP%\lotb_campagne_exe.log`). Environnement isolé — aucune
installation réelle : base jetable dédiée `quincaillerie_lotbexe`
(schéma d'origine + 52 migrations + jeu d'essai + mot de passe
`qf_app`, supprimée en fin de campagne — vérifié), `Akuma.exe
--sans-navigateur` sur le port 8000, configuration éphémère
`QF_CONFIG` (jamais `dist/config.ini` rempli), `QF_FICHIER_ETAT_
SAUVEGARDE` vers `_pgdev/sauvegardes/dernier_etat_sauvegarde.json`
(exigence documentée du cycle 63 : en mode figé, le voyant ne peut pas
deviner le dossier de sauvegarde du déploiement).

```
BILAN : toutes les étapes sont passées (base quincaillerie_lotbexe, exe 8000)
13/13 suites OK — 505 contrôles, 0 échec
  (routes 65, cablage 101, vente 63, stock 49, rapports 52, inventaire 17,
   ux 27, comptes 26, caisse 24, rh 21, exploitation 14, echappement 11,
   roles 35 — comptages identiques au run uvicorn 4)
```

Journal de l'exe (`server/fabrication/dist/campagne_lotb_exe.log`) :
2 248 lignes, **0 erreur** ; les 404 consignés sont les sondes
négatives volontaires de la suite routes (routes inexistantes devant
répondre 404). Exe arrêté, base jetable supprimée après la campagne
(piège mémoire du cycle 71 : un serveur orphelin fausse la campagne
suivante).

**Conclusion C8 §3** : le code du Lot B est prouvé compatible
exécutable Windows — même nombre de contrôles verts que la régression
uvicorn (505), aucun défaut de packaging (aucun 404 d'écran : la
complétude du paquet vérifiée en §3.1 était correcte).

---

## 4. Scénarios exigeant une recette humaine (non automatisables)

Référence : fiches existantes du cycle 73 (`CYCLE_73_FICHES_RECETTE.md`),
reprises telles quelles — les 13 suites automatisées couvrent le
reproductible ; ce qui suit exige une main et un œil humains :

| Fiche | Contenu C8 | Pourquoi pas automatisable |
|-------|------------|----------------------------|
| **R1** — 2ᵉ campagne UX tous parcours | Navigation réelle à la souris et au clavier sur le poste du comptoir, lisibilité à l'écran du magasin, impression ticket et reçu papier (58 mm) | Rendu papier, confort visuel, matériel réel |
| **R2** — recette 3 rôles | Un responsable, un caissier, un agent stock utilisent l'application en parallèle sur leurs écrans respectifs | Comportement humain simultané, jugement de confort |
| **R5** — recette fonctionnelle finale GO/NO-GO | Vérification humaine des parcours principaux avant mise en production | Décision du propriétaire |
| Exécutable sur poste réel | Double-clic `Akuma.exe` sur le poste cible (mode kiosque Edge/Chrome), résolution RÉELLE de l'écran du magasin, impression depuis l'exe | Matériel du magasin, mode kiosque plein écran, périphériques |

Aucun de ces points ne peut être déclaré 100 % par Qoder : les suites
prouvent le comportement dans un navigateur piloté sur les largeurs
360→1920, pas le confort réel d'un humain sur le poste de la boutique.

---

## 5. Score justifié

| Critère C8 | État | Preuve |
|-------------|------|--------|
| 13 suites × 505 contrôles verts | ✔ | run 4, §1 |
| 5 rôles + cumul D7 | ✔ | suites roles + cablage + routes |
| 5 largeurs sans débordement | ✔ | suites cablage + ux |
| Alertes d'exploitation | ✔ | suite exploitation |
| Exécutable Windows reconstruit sur le code Lot B | ✔ | §3.1, SHA-256 consigné |
| Campagne 13 suites CONTRE l'exe | ✔ | §3.2 : 13/13 suites, 505 contrôles, 0 échec, journal exe 0 erreur |
| Recettes humaines (R1/R2/R5, poste réel) | ☐ propriétaire | §4 |

**Score C8 : non déclaré à 100 %** — le déclarer exigera les fiches
humaines signées (§4) sur le poste réel du magasin. Le score
d'automatisation (parcours reproductibles, exécutable compris) est en
revanche complet et prouvé par exécution : **505/505 contrôles sur le
code du Lot B, en uvicorn ET dans l'exécutable Windows reconstruit**.
