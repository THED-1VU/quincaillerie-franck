# État du cycle de finalisation — Quincaillerie Franck

Référentiel fixe `C0`–`C14` — **ne jamais renuméroter**.
Cycle décrit dans `.agents/skills/finalisation-loop/SKILL.md`.

- Date d'initialisation : **2026-09-10**
- Dernier cycle fusionné : **Cycle 3 — noyau serveur, C2/C3/C11**, 2026-09-12
- Décision d'architecture (précisée 2026-09-11) : **un seul code applicatif web**,
  mais **livré et exécuté comme une application Windows (.exe)** sur les postes de
  la boutique — l'exécutable embarque le serveur local et ouvre l'interface web en
  plein écran / mode kiosque ; **aucune installation de Python sur les postes**,
  double-clic comme aujourd'hui. Les **téléphones Android et iPhone** utilisent la
  **même** application dans un navigateur (usage **et** suivi), via le réseau local
  ou un tunnel. **Pas d'interface de bureau PyQt6** : le .exe est le véhicule de
  livraison du PC, pas une seconde UI native.
- Règle : un score ne monte que sur **preuve d'exécution réelle**.

---

## Scores de départ

| Code | Chantier | Score | Base d'évaluation |
|------|----------|:-----:|-------------------|
| C0 | Infrastructure et dépôt | **10 %** | Dépôt Git + GitHub privé créés dans ce cycle de cadrage ; `.gitignore` en place. Pas encore de CI, **pas de script de fabrication de l'exécutable Windows** (le livrable final est un `.exe` qui embarque le serveur web + le mode kiosque), pas d'environnement reproductible, pas de migrations. |
| C1 | Base de données et intégrité | **80 %** | Cycle 2. 9 migrations numérotées (`db/migrations/`) + inverses, appliquées et annulées par exécution réelle sur PostgreSQL 17.11. Corrigés et **prouvés** : contraintes de domaine, cohérence inter-tables, **écart d'inventaire calculé par la base** (et quantité attendue figée par déclencheur), historique non effaçable (`RESTRICT` + verrous de suppression + suppression logique), journaux de connexion et de comptes, annulation tracée et irréversible, table de paramètres avec sentinelle « à décider », index de recherche, **4 rôles non superutilisateurs à privilèges par colonne** + RLS par site. **100 contrôles, 0 échec** (`db/tests/DERNIER_RESULTAT.md`). Reste : décisions métier de l'addendum (points b, d, e, g), fonction d'authentification (C2), exploitation de la RLS (C3), reprise sur une base contenant de vraies données. |
| C2 | Authentification et comptes | **65 %** | Cycle 3. Noyau serveur (`server/`, FastAPI) : connexion via `verifier_connexion()` (fonction PostgreSQL `SECURITY DEFINER`, migration 009, seule à lire le hachage, jamais restitué) ; verrouillage après 5 échecs, déverrouillage réservé au responsable, obligation de changement à la première connexion, libre-service limité à sa propre ligne, limitation de débit. **36/36 tests, 0 échec** (`server/tests/DERNIER_RESULTAT.md`). Reste : session à durée limitée = choix technique temporaire (`duree_session_minutes` reste `a_definir` en base — décision propriétaire) ; pas de révocation de jeton avant expiration (limite technique documentée) ; pas d'écran, pas de création de compte via API (hors périmètre du cycle). |
| C3 | Habilitations et cloisonnement des rôles | **60 %** | Cycle 3. Habilitations appliquées **au niveau des requêtes SQL** (pas de vérification applicative dispersée) : privilèges par colonne + RLS par site posés au cycle 2, exploités par `BaseDeDonnees.connexion_pour()` (point de bascule de rôle unique). Prouvé par exécution en **contournant l'API** : `SELECT ... WHERE site_id=2` sous `qf_agent_stock` renvoie 0 ligne même en le demandant explicitement (`server/tests/test_cloisonnement_site.py`). Rôle « caissier » toujours non tranché (addendum h) — non traité ce cycle. Reste : cloisonnement RH/fournisseurs non testé par une route, pas encore d'écran. |
| C4 | Articles et stock | **0 %** | Non vérifié. Règle des 20 %, seuil non modifiable, mouvements tracés : présents au CDC, absents de la base (défaut `seuil_alerte = 5`, aucun trigger). Pas de transfert inter-sites (addendum a), pas de retours/casse (addendum f). |
| C5 | Ventes et facturation | **0 %** | Non vérifié. Workflow `en_attente/payee/annulee` modélisé. Manquent : n° facturier + vendeur (addendum c), créance client (addendum b), audit d'annulation, cohérence des montants, génération du n° de facture, arbitrage saisie a posteriori vs blocage (addendum e). |
| C6 | Comptabilité et RH | **0 %** | Non vérifié. `transactions`, `employes`, `absences_conges`, `avances_salaire` présents. Manquent : clôture de caisse (addendum g), contre-passation d'annulation, `transactions.vente_id` non unique, audit des corrections. |
| C7 | Inventaire et écarts | **0 %** | Non vérifié. `comptages_stock` + comptage à l'aveugle modélisés. `ecart` stocké et non contraint (faille anti-vol) ; pas d'unicité par créneau ; pas de rattachement des écarts de survente au comptage (addendum e). |
| C8 | Tableaux de bord et rapports | **0 %** | Non vérifié. Exigés au CDC (consolidé/par site, alertes, exports Excel/PDF avec gating du prix par rôle) ; aucune preuve d'exécution. |
| C9 | Ergonomie et UI *(priorité 1)* | **25 %** | Cycle 1. Maquette non câblée des 4 écrans clés (`maquette/`), thème unique, données simulées isolées. Vérifié par exécution : 20/20 captures aux 5 largeurs sans débordement, 0 erreur console, cibles ≥ 44 px, ajout au panier en 2 actions, comptage à l'aveugle sans quantité attendue dans la page (`maquette/verification/`, 14/14). **Plafonné à 60 %** tant que le tableau de mesures humaines de `UX_BASELINE.md` §4 n'est pas rempli (vitesse, compréhension des erreurs, clavier réel). Reste : implémentation réelle des écrans, câblage, mesures chronométrées. |
| C10 | Mobile et API web *(priorité 1)* | **0 %** | Diagnostic : « Web API or mobile interface : Not found ». Aucune interface mobile dans le livré. Cible : **la même application web** ouverte dans le navigateur d'un **Android / iPhone**, pour **utiliser** (recettes, dépenses, inventaire) **et suivre** (tableau de bord, alertes, écarts), via LAN ou tunnel — jamais PostgreSQL exposé. Priorité n°2 du propriétaire, non couverte à ce jour. |
| C11 | Sécurité applicative | **55 %** | Cycle 3. Le « Sécurité : 100 % » du diagnostic d'origine était un artefact (mots-clés trouvés dans le script de diagnostic lui-même) — désormais vérifié réellement : démarrage refuse `postgres` et toute clé d'exemple, requêtes systématiquement paramétrées (injection SQL testée), jetons signés HMAC vérifiés à temps constant, aucun hachage ne fuit dans aucune réponse (vérifié par expression régulière), erreurs SQL jamais renvoyées telles quelles au client. Reste : révocation de session, limiteur de débit partagé (multi-processus), audit de sécurité plus large (dépendances, en-têtes HTTP, TLS — hors périmètre local de dev). |
| C12 | Sauvegarde et exploitation | **0 %** | Diagnostic : « Backup and restore procedure : Not found ». Aucun script, aucune procédure. Onduleur, RPO/RTO, mise à jour des postes : à définir (addendum i). |
| C13 | Tests automatisés et qualité | **0 %** | Aucun test automatisé détecté (« Tests identifiable : Found » = simple présence du mot « test » dans les guides). Aucune suite exécutable. |
| C14 | Documentation et livrables | **40 %** | Évalué sur pièces. Documentation d'usage/recette solide : CDC détaillé, 2 guides testeur, dossier de recette, guide d'installation. `MODELE_DONNEES.md`, `PERIMETRE_LIVRE.md`, `ADDENDUM_CAHIER_DES_CHARGES.md` produits dans ce cycle. Manquent (CDC §7) : code source, scripts de fabrication des exécutables, scripts + guide de sauvegarde/restauration. |

**Moyenne indicative après cycle 3 : ≈ 22 %** (C0 10, C1 80, C2 65, C3 60, C9 25, C11 55, C14 40, autres 0).
Cette moyenne n'est pas un objectif : chaque chantier est mené à 100 % séparément.

---

## Journal des cycles

### Cycle 0 — Cadrage (2026-09-10)

- **Phase 1 — Constat** : code source inaccessible (audit antérieur, négatif).
  Matière disponible : `creation_base_donnees.sql`, `config.example.ini`, deux
  guides testeur, dossier de recette, cahier des charges, deux exécutables de
  référence. Diagnostic automatisé confirme : pas de sauvegarde, pas de script de
  build, pas d'interface mobile dans le livré.
- **Phase 2 — Objectif** : produire les 5 livrables de cadrage (rétro-spec du
  modèle de données, rétro-spec fonctionnelle, dépôt Git + GitHub privé,
  addendum au cahier des charges, cycle de finalisation + état initial).
  Critère de sortie : les 5 livrables existent, la branche `main` est poussée
  sur le dépôt privé `THED-1VU/quincaillerie-franck`, aucun secret ni exécutable
  versionné.
- **Phase 3 — Branche** : `main` (cycle de cadrage, pas de code applicatif).
- **Phase 4 — Vérification** : `git log` sur `main`, `git ls-files` ne contient
  ni `*.exe` ni `config.ini`, dépôt visible en privé sur GitHub.
- **Phase 5 — Score** : C0 0 % → 10 %, C1 0 % → 35 % (sur pièces),
  C14 0 % → 40 % (sur pièces). Aucun autre chantier touché.
- **Reste à faire** : obtenir du propriétaire les décisions des points **d**
  (fiscalité), **e** (saisie a posteriori vs blocage) et le choix
  d'**architecture cible** avant d'ouvrir les cycles C4 / C5 / C9 / C10.

### Cycle 1 — Maquette du parcours (C9) — 2026-09-11

- **Phase 1 — Diagnostic** : C9 à 0 %, aucune interface évaluable (audit statique
  « Ergonomie PC : 0 % » = non mesurable). Architecture désormais actée :
  application web unique servie sur le LAN.
- **Phase 2 — Objectif** : maquette **fonctionnelle mais non câblée** de 4 écrans
  (connexion, vente PC de caisse, tableau de bord responsable mobile, comptage
  d'inventaire à l'aveugle) en HTML/CSS/JS sans chaîne de build, thème unique,
  données simulées isolées. Critère de sortie : serveur qui démarre, 4 écrans
  affichés, captures aux 5 largeurs sans débordement, ajout au panier ≤ 2 actions,
  quantité attendue absente de l'écran **et** du code sur le comptage, +
  `UX_BASELINE.md` avec protocole de mesure humaine et plafond C9 à 60 % tant
  qu'il n'est pas rempli.
- **Phase 3 — Action** : branche `cycle-1-maquette-ux`. Créé `maquette/`
  (`theme.css`, `styles.css`, `donnees-simulees.js`, `index.html` + 4 écrans,
  `favicon.svg`, `README.md`) et `maquette/verification/` (2 scripts Playwright).
  Aucun code applicatif, aucune connexion base.
- **Phase 4 — Vérification par exécution** :
  - `py -m http.server 8080` → les 5 ressources et 4 écrans répondent `200`.
  - `maquette/verification/verifier-affichage.mjs` : **20/20** cas
    (4 écrans × 360/390/768/1366/1920 px), `débordement=false` partout,
    **0 erreur console**, cible tactile minimale **44 px**. 20 captures écrites
    dans `maquette/captures/`.
  - `maquette/verification/verifier-flux.mjs` : **14/14** contrôles — connexion
    (erreurs près du champ, couple valide → écran de vente), vente (« robi » +
    `Entrée` = +1 ligne en **2 actions** ; article déjà présent → quantité +1
    sans doublon ; focus qui revient sur la recherche ; `F4` change le paiement ;
    `F9` = **une** confirmation puis succès ; **0** fenêtre superposée),
    inventaire (tableau de données réduit à id/nom/unité ; champ vide au départ ;
    `Entrée` → article suivant, progression `2 / 5`).
  - Un débordement de 17 px détecté à la 1re passe (badge « facturier papier »
    sur l'écran de vente à 360 px) → corrigé (retour à la ligne du bandeau
    sous 720 px) → re-vérifié : 0 échec.
- **Phase 5 — Mémoire** : C9 **0 % → 25 %** (plafonné à 60 % via `UX_BASELINE.md`).
  Commit sur `cycle-1-maquette-ux`, PR vers `main`, fusion après vérification.
- **Reste à faire (C9)** : implémenter les écrans réels et les câbler ; faire
  remplir le tableau de mesures humaines de `UX_BASELINE.md` §4.

### Contrôle de boucle — après cycle 1 (2026-09-11, sans code)

- **SKILL.md** : présent, décrit bien les 5 phases (Diagnostic → Objectif →
  Action → Vérification → Mémoire).
- **loop-state.md** : présent, liste les 15 chantiers `C0`–`C14` avec un score
  chacun, entrée datée pour le cycle 1.
- **Score C9 (25 %)** : adossé à des preuves versionnées — 8 fichiers source de
  maquette, **20 captures** dans `maquette/captures/`, 2 scripts de vérification
  rejouables, et `maquette/verification/DERNIER_RESULTAT.md` (trace 20/20 + 14/14).
  Plafond 60 % maintenu (mesures humaines de `UX_BASELINE.md` §4 non faites).
  Score jugé **cohérent**, non revu à la baisse.
- **Git** : une seule branche (`main`), arbre propre, aucune branche orpheline,
  PR #1 **fusionnée** puis branche supprimée, aucun fichier non suivi.
- **.gitignore** : protège `config.ini` (y compris imbriqué), `*.exe`, `build/`,
  `dist/`, `__pycache__/`, `*.log`, et les dumps/sauvegardes `.sql` de données
  (`*dump*.sql`, `*backup*.sql`, `*sauvegarde*.sql`, `*_data.sql`, `*.dump`,
  `*.backup`) — plus `node_modules/`, `.playwright-mcp/`.
- **Secrets** : aucun mot de passe ni clé réels dans les fichiers suivis ;
  `config.example.ini` ne contient que des placeholders explicites ; aucun `.exe`
  versionné.
- **Précision d'architecture enregistrée ce jour** : livrable final = **`.exe`
  Windows embarquant le serveur web + mode kiosque** ; téléphones Android/iPhone
  sur la **même** application web (usage + suivi). Descriptions C0 et C10 mises à
  jour en conséquence.

**Verdict : la boucle a bien tourné sur le cycle 1 — les 5 phases ont été
parcourues, aucune n'a été sautée.** Seule faiblesse corrigée pendant ce
contrôle : la sortie d'exécution n'était pas archivée dans le dépôt →
`DERNIER_RESULTAT.md` ajouté.

### Cycle 2 — Durcissement de la base de données (C1) — 2026-09-11

- **Phase 1 — Diagnostic par exécution** : PostgreSQL absent de la machine
  (Docker inutilisable faute de WSL, winget en échec réseau) ; installé en
  **binaires portables PostgreSQL 17.11**, sans droits administrateur, sur le
  port 5433. Base créée à partir du seul `creation_base_donnees.sql`, puis
  `db/tests/diagnostic_schema_origine.sql` exécuté : **toutes** les écritures
  aberrantes ont été ACCEPTÉES — stock à −50, prix à −999, quantité vendue −5,
  comptage « attendu 10, compté 3, **écart déclaré 0** », vente « 1 + 1 =
  999999 », TVA à 500 %, agent sans site, congé finissant avant de commencer,
  deux recettes pour une vente, article d'un autre site dans une vente, seuil
  d'alerte remis à 0 ; supprimer un article a **effacé son historique de prix**
  (1 ligne → 0). Et : 0 table de journal, 0 table de paramètres, 0 déclencheur,
  0 colonne générée, aucun rôle non superutilisateur.
- **Phase 2 — Objectif** : corriger le schéma par migrations numérotées
  réversibles. Critère de sortie : les migrations s'appliquent sur une base
  issue du schéma d'origine ; une suite de tests prouve que chaque protection
  refuse ce qu'elle doit refuser ; les migrations inverses ramènent le schéma à
  son état initial.
- **Phase 3 — Action** : branche `cycle-2-base-donnees`. 9 migrations +
  9 inverses (`db/migrations/`), 3 outils (`db/outils/` : `migrer.sh`,
  `prevol.sql`, `definir_mot_de_passe_app.sql`), 5 fichiers de test
  (`db/tests/`), documentation complète des droits (`db/README.md`).
- **Phase 4 — Vérification par exécution réelle** (`bash db/tests/executer_tests.sh`) :
  - migrations **9/9** appliquées ;
  - `01_protections.sql` : **44/44** — dont le test décisif : le client envoie
    une quantité attendue de 999 alors que le stock réel est 30 ; la base
    **ignore** la valeur envoyée, retient 30 et calcule l'écart réel **−5** ;
  - `02_habilitations.sql` : **52/52** — `permission denied` de PostgreSQL
    lui-même sur les colonnes de prix pour l'agent stock, sur les quantités pour
    le comptable, sur le hachage de mot de passe pour tous, sur le seuil
    d'alerte pour tous ;
  - `03_concurrence.sh` : **4/4** — deux sessions simultanées sur un article à
    stock 1 : une seule aboutit, stock final 0 jamais négatif, un seul
    mouvement, message explicite à la perdante ;
  - migrations inverses : schéma restauré, **2 différences** connues et
    documentées (position de `comptages_stock.ecart`, extension `pg_trgm`
    conservée).
  - **Total : 100 contrôles, 0 échec.** Trace : `db/tests/DERNIER_RESULTAT.md`.
- **Trouvé par les tests, corrigé pendant le cycle** : (1) le responsable
  pouvait lire un hachage de mot de passe et modifier le seuil d'alerte — un
  `GRANT` au niveau table écrasait les restrictions de colonne ; (2) le script
  d'annulation cassait sur l'espace du chemin (« THED CONNECT ») ; (3) un
  `TRUNCATE … CASCADE` du jeu d'essai effaçait la table `parametres` ; (4) un
  rôle PostgreSQL étant global au serveur, son retrait doit être tolérant.
- **Phase 5 — Mémoire** : C1 **35 % → 80 %**. Commit, PR, fusion.
- **Reste à faire (C1)** : décisions métier de l'addendum (points b, d, e, g) ;
  fonction d'authentification pour que personne n'ait à lire un hachage
  (chantier C2) ; exploitation complète de la RLS (C3) ; reprise sur une base
  contenant de vraies données (`db/outils/prevol.sql` est prêt pour ça).

### Cycle 3 — Noyau serveur : C2, C3, C11 — 2026-09-12

- **Phase 1 — Diagnostic par exécution, avant tout code serveur** : deux
  briques testées en SQL direct d'abord.
  - **pgcrypto ne valide pas un hachage bcrypt `$2b$`** (défaut de la
    bibliothèque Python `bcrypt`) : `crypt('bon mdp', hash_2b)` renvoie
    **faux**. Testé aussi avec `$2a$` : accepte le bon mot de passe, rejette
    le mauvais. → tout hachage sera généré avec `prefix=b"2a"`.
  - Une fois les fonctions d'authentification écrites (migration 009),
    premier appel réel sous `qf_app` : `function verifier_connexion(...)
    does not exist` — alors que la fonction existe et que `qf_app` a reçu
    `EXECUTE` dessus. Cause : `qf_app` n'a jamais reçu `USAGE ON SCHEMA
    public` (oubli de la migration 008, déjà fusionnée) → migration
    corrective **010**.
- **Phase 2 — Objectif** : noyau serveur FastAPI en couches (config, accès
  base, sécurité, dépendances, routes), sans écran ni règle métier de
  vente/stock. Critère de sortie : serveur qui démarre et répond ; suite de
  tests d'autorisation par rôle inspectant le **contenu** des réponses (pas
  seulement le code HTTP) ; un test démontrant qu'un agent ne peut pas
  atteindre l'autre site en modifiant les paramètres de sa requête.
- **Phase 3 — Action** : branche `cycle-3-noyau-serveur`.
  - `db/migrations/009_authentification.sql` : extension `pgcrypto`,
    `verifier_connexion()` (`SECURITY DEFINER`, seule à lire le hachage,
    journalise systématiquement dans `journal_connexions`),
    `changer_mon_mot_de_passe()` (libre-service limité à sa propre ligne via
    `qf_utilisateur_courant()`), `qf_utilisateur_courant()`.
  - `db/migrations/010_correction_usage_qf_app.sql` : corrige l'oubli
    ci-dessus, sans modifier 008 rétroactivement.
  - `server/` : FastAPI (Python 3.13 — wheels disponibles pour `psycopg` et
    `bcrypt`, contrairement à 3.14). `database.py` est le **seul** point de
    bascule de rôle (`SET LOCAL ROLE` + `qf.site_id`/`qf.utilisateur_id` via
    `set_config(..., true)`) ; `securite.py` (hachage `$2a$`, jetons HMAC
    signés à temps constant, limiteur de débit) ; `deps.py`
    (`exiger_role(...)`) ; routes `auth` (connexion, changer-mot-de-passe,
    déverrouillage) et `demonstration` (`/articles`, `/ventes/synthese-jour`,
    `/moi`) ; gestion d'erreurs qui ne renvoie jamais le détail SQL au client.
- **Phase 4 — Vérification par exécution réelle** :
  - Fonctions SQL testées isolément avant tout code Python : verrouillage au
    5ᵉ échec, refus même avec le bon mot de passe tant que verrouillé,
    déverrouillage fonctionnel, libre-service confiné à sa propre ligne.
  - Serveur démarré réellement (`uvicorn`), parcours complet en HTTP réel
    (`curl`) : connexion réussie/échouée, `/articles` filtré par rôle et par
    site, `/ventes/synthese-jour` refusée à l'agent stock (403), `/moi` sans
    jeton (401), injection SQL dans l'identifiant neutralisée.
  - **Preuve la plus forte (C3)** : en SQL direct, hors API, sous
    `qf_agent_stock` avec `qf.site_id='1'`, `SELECT ... WHERE site_id = 2`
    renvoie **0 ligne** — la RLS bloque même une demande explicite de
    l'autre site, indépendamment de tout code applicatif.
  - Suite pytest : **36/36**, 0 échec (`server/tests/DERNIER_RESULTAT.md`).
  - Non-régression : suite complète du cycle 2 rejouée après les migrations
    009/010 — **toujours 100/100** (44 protections + 52 habilitations + 4
    concurrence), 0 échec.
  - **Total du cycle : 136 contrôles, 0 échec.**
- **Bugs trouvés PAR les tests et corrigés pendant le cycle** :
  1. `qf_app` sans `USAGE ON SCHEMA public` (voir Phase 1) ;
  2. deux routes (`changer-mot-de-passe`, `déverrouillage`) appelaient
     `conn.commit()` **à l'intérieur** d'une transaction déjà ouverte par
     `connexion_pour()` — psycopg3 l'interdit explicitement
     (`ProgrammingError: Explicit commit() forbidden within a Transaction
     context`) ; le commit est en réalité automatique à la sortie du bloc ;
  3. `subprocess.run(..., env={"PGPASSWORD": ...})` remplaçait tout
     l'environnement du sous-processus au lieu de le compléter — `psql.exe`
     échouait silencieusement (code 2) faute de `SystemRoot`/`PATH` ;
  4. `logger.exception()` appelé hors contexte d'exception active
     affichait « NoneType: None » au lieu de la vraie erreur (corrigé en
     `logger.error(..., exc_info=exc)`) ;
  5. `00_jeu_essai.sql` (cycle 2) ne pouvait pas être rejoué plusieurs fois
     de suite (plus de `TRUNCATE`, pour ne pas emporter `parametres` en
     cascade) — nécessaire pour que chaque test pytest reparte d'un état
     connu. Corrigé en incluant `parametres`/`historique_parametres` dans le
     même `TRUNCATE` puis en les ré-amorçant aussitôt ; testé idempotent sur
     3 exécutions consécutives.
- **Phase 5 — Mémoire** : C2 **0 % → 65 %**, C3 **0 % → 60 %**, C11 **0 % →
  55 %**. Commit, PR, fusion.
- **Reste à faire** : session à durée limitée = choix technique temporaire
  (politique définitive toujours `a_definir` en base — décision
  propriétaire) ; pas de révocation de jeton avant expiration ni de
  limiteur de débit partagé entre processus (limites techniques
  documentées, pas des décisions métier) ; rôle « caissier » toujours non
  tranché (addendum h) ; aucun écran, aucune règle métier de vente/stock
  exposée par une route (volontairement hors périmètre de ce cycle).

---

## Prochain cycle — sélection

1. **C0** — environnement reproductible + **script de fabrication du `.exe`**
   (PyInstaller : serveur web + lanceur kiosque en un exécutable autonome),
   dépendances figées, CI minimale : débloque la vérification automatisée et
   la livraison réelle aux postes.
2. **C4 (articles/stock) et C5 (ventes)** : nécessitent au préalable les
   décisions du propriétaire sur l'addendum, points b (créance client), d
   (fiscalité) et e (saisie a posteriori vs blocage) — sans elles, le
   décrément de stock exposé par une route inventerait une règle métier.
3. **C9/C10** : câbler réellement les écrans de la maquette du cycle 1 sur
   le noyau serveur du cycle 3 (connexion, jeton, appels `/articles` etc.),
   puis faire remplir le tableau de mesures humaines de `UX_BASELINE.md`.
