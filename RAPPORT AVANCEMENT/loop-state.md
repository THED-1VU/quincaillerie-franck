# État du cycle de finalisation — Quincaillerie Franck

Référentiel fixe `C0`–`C14` — **ne jamais renuméroter**.
Cycle décrit dans `.agents/skills/finalisation-loop/SKILL.md`.

- Date d'initialisation : **2026-09-10**
- Dernier cycle fusionné : **Cycle 6 — première route de vente, C5**, 2026-09-12
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
| C0 | Infrastructure et dépôt | **55 %** | Cycle 4. `server/fabrication/` : `QuincaillerieFranck.exe` produit par PyInstaller (`construire.ps1`, un humain n'a besoin d'aucune connaissance de PyInstaller), 17,9 Mo, autonome. **Vérifié par exécution depuis un dossier totalement isolé du dépôt** : démarrage, config chargée, `/sante` répond, connexion + hachage bcrypt + jeton fonctionnent — aucune dépendance Python résiduelle. Garde-fous C11 (refus `postgres`, refus clé d'exemple) confirmés survivre à l'empaquetage. Reste : CI automatisée, outil de création du premier compte responsable (CDC §7, second exécutable), mode kiosque et écran réel une fois C9/C10 fait, dépendances encore installées manuellement (pas de lockfile figé au-delà de `requirements.txt`). |
| C1 | Base de données et intégrité | **80 %** | Cycle 2. 9 migrations numérotées (`db/migrations/`) + inverses, appliquées et annulées par exécution réelle sur PostgreSQL 17.11. Corrigés et **prouvés** : contraintes de domaine, cohérence inter-tables, **écart d'inventaire calculé par la base** (et quantité attendue figée par déclencheur), historique non effaçable (`RESTRICT` + verrous de suppression + suppression logique), journaux de connexion et de comptes, annulation tracée et irréversible, table de paramètres avec sentinelle « à décider », index de recherche, **4 rôles non superutilisateurs à privilèges par colonne** + RLS par site. **100 contrôles, 0 échec** (`db/tests/DERNIER_RESULTAT.md`). Reste : décisions métier de l'addendum (points b, d, e, g), fonction d'authentification (C2), exploitation de la RLS (C3), reprise sur une base contenant de vraies données. |
| C2 | Authentification et comptes | **65 %** | Cycle 3. Noyau serveur (`server/`, FastAPI) : connexion via `verifier_connexion()` (fonction PostgreSQL `SECURITY DEFINER`, migration 009, seule à lire le hachage, jamais restitué) ; verrouillage après 5 échecs, déverrouillage réservé au responsable, obligation de changement à la première connexion, libre-service limité à sa propre ligne, limitation de débit. **36/36 tests, 0 échec** (`server/tests/DERNIER_RESULTAT.md`). Reste : session à durée limitée = choix technique temporaire (`duree_session_minutes` reste `a_definir` en base — décision propriétaire) ; pas de révocation de jeton avant expiration (limite technique documentée) ; pas d'écran, pas de création de compte via API (hors périmètre du cycle). |
| C3 | Habilitations et cloisonnement des rôles | **60 %** | Cycle 3. Habilitations appliquées **au niveau des requêtes SQL** (pas de vérification applicative dispersée) : privilèges par colonne + RLS par site posés au cycle 2, exploités par `BaseDeDonnees.connexion_pour()` (point de bascule de rôle unique). Prouvé par exécution en **contournant l'API** : `SELECT ... WHERE site_id=2` sous `qf_agent_stock` renvoie 0 ligne même en le demandant explicitement (`server/tests/test_cloisonnement_site.py`). Rôle « caissier » toujours non tranché (addendum h) — non traité ce cycle. Reste : cloisonnement RH/fournisseurs non testé par une route, pas encore d'écran. |
| C4 | Articles et stock | **0 %** | Non vérifié. Règle des 20 %, seuil non modifiable, mouvements tracés : présents au CDC, absents de la base (défaut `seuil_alerte = 5`, aucun trigger). Pas de transfert inter-sites (addendum a), pas de retours/casse (addendum f). |
| C5 | Ventes et facturation | **40 %** | Cycle 6. Décisions du propriétaire obtenues et appliquées (addendum, points b/d/e) : régime réel, TVA 19,25 % sur prix TTC, arrondi arithmétique sur le total ; une vente déjà encaissée n'est **jamais bloquée**, l'écart de stock est consigné et réservé au responsable ; crédit client explicitement désactivé. `POST /ventes` (`server/app/routes/ventes.py`) enregistre une vraie vente : décrément atomique anti-survente, une recette par vente, calcul de TVA faisant foi côté serveur. Vérifié par exécution : 8/8 tests pytest dédiés (44/44 au total, 0 régression), suite SQL du cycle 2 rejouée à jour (44/44 protections, 52/52 habilitations, **6/6 concurrence — réécrite pour le nouveau comportement anti-survente**, réversibilité des migrations confirmée), et 10/10 contrôles Playwright bout-en-bout sur l'écran de vente réellement câblé (`verifier-vente-reelle.mjs`) : vente normale (aperçu affiché AVANT validation identique à la confirmation serveur), vente à découvert acceptée avec écart affiché, crédit client absent des choix, responsable contraint de choisir un site. Manquent : n° facturier + vendeur obligatoires (addendum c, non tranché — objectif anti-vol volontairement incomplet), annulation d'une vente, régularisation d'un écart, documents imprimés (ticket/facture), écarts de stock pas encore affichés au tableau de bord (prévu chantier C7). |
| C6 | Comptabilité et RH | **0 %** | Non vérifié. `transactions`, `employes`, `absences_conges`, `avances_salaire` présents. Manquent : clôture de caisse (addendum g), contre-passation d'annulation, `transactions.vente_id` non unique, audit des corrections. |
| C7 | Inventaire et écarts | **0 %** | Non vérifié. `comptages_stock` + comptage à l'aveugle modélisés. `ecart` stocké et non contraint (faille anti-vol) ; pas d'unicité par créneau ; pas de rattachement des écarts de survente au comptage (addendum e). |
| C8 | Tableaux de bord et rapports | **0 %** | Non vérifié. Exigés au CDC (consolidé/par site, alertes, exports Excel/PDF avec gating du prix par rôle) ; aucune preuve d'exécution. |
| C9 | Ergonomie et UI *(priorité 1)* | **50 %** | Cycle 5. Les 4 écrans ne sont plus une maquette isolée : connexion réelle (`POST /auth/connexion`), jeton, `GET /articles`, `GET /ventes/synthese-jour`, servis par le noyau serveur sous `/app` (même origine). Vérifié par exécution (`verifier-cablage.mjs`, 73/73) : les 3 rôles reçoivent réellement des réponses différentes (aucun prix pour l'agent stock, aucune quantité pour le comptable), la quantité attendue d'un comptage n'apparaît nulle part (page, réseau, code source), messages d'erreur toujours en français près du champ, cibles ≥ 44 px conservées, 36/36 tests serveur toujours au vert. Ce qui n'a pas de route métier encore décidée (validation de vente, alertes stock, écarts d'inventaire, liste à compter) reste **explicitement** simulé à l'écran plutôt qu'inventé. **Toujours plafonné à 60 %** : le tableau de mesures humaines de `UX_BASELINE.md` §4 reste vide (vitesse, compréhension des erreurs par une personne non formée, confort sur téléphone physique). |
| C10 | Mobile et API web *(priorité 1)* | **30 %** | Cycle 5. Les deux écrans mobile-first (tableau de bord responsable, comptage d'inventaire) sont désormais **la même application web**, session réelle, testée et capturée à 360/390/768 px avec de vrais comptes — première preuve d'exécution sur ce chantier (`verifier-cablage.mjs`). Reste : accès démontré depuis un **téléphone physique** sur le LAN ou via tunnel (seules des largeurs de navigateur ont été testées ici, pas un appareil réel), API dédiée si un jour distincte de l'appli web, usage hors ligne, notifications. |
| C11 | Sécurité applicative | **55 %** | Cycle 3. Le « Sécurité : 100 % » du diagnostic d'origine était un artefact (mots-clés trouvés dans le script de diagnostic lui-même) — désormais vérifié réellement : démarrage refuse `postgres` et toute clé d'exemple, requêtes systématiquement paramétrées (injection SQL testée), jetons signés HMAC vérifiés à temps constant, aucun hachage ne fuit dans aucune réponse (vérifié par expression régulière), erreurs SQL jamais renvoyées telles quelles au client. Reste : révocation de session, limiteur de débit partagé (multi-processus), audit de sécurité plus large (dépendances, en-têtes HTTP, TLS — hors périmètre local de dev). |
| C12 | Sauvegarde et exploitation | **0 %** | Diagnostic : « Backup and restore procedure : Not found ». Aucun script, aucune procédure. Onduleur, RPO/RTO, mise à jour des postes : à définir (addendum i). |
| C13 | Tests automatisés et qualité | **0 %** | Aucun test automatisé détecté (« Tests identifiable : Found » = simple présence du mot « test » dans les guides). Aucune suite exécutable. |
| C14 | Documentation et livrables | **40 %** | Évalué sur pièces. Documentation d'usage/recette solide : CDC détaillé, 2 guides testeur, dossier de recette, guide d'installation. `MODELE_DONNEES.md`, `PERIMETRE_LIVRE.md`, `ADDENDUM_CAHIER_DES_CHARGES.md` produits dans ce cycle. Manquent (CDC §7) : code source, scripts de fabrication des exécutables, scripts + guide de sauvegarde/restauration. |

**Moyenne indicative après cycle 6 : ≈ 32 %** (C0 55, C1 80, C2 65, C3 60, C5 40, C9 50, C10 30, C11 55, C14 40, autres 0).
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

### Cycle 4 — Fabrication de l'exécutable (C0) — 2026-09-12

- **Phase 1 — Diagnostic** : aucun script de fabrication n'existait ;
  `pyinstaller` absent de l'environnement.
- **Phase 2 — Objectif** : empaqueter le noyau serveur (cycle 3) en un `.exe`
  Windows autonome via PyInstaller, avec un lanceur qui démarre le serveur
  et ouvre un navigateur. Critère de sortie : l'exécutable, copié seul dans
  un dossier sans lien avec le dépôt, démarre, sert `/sante`, et une route
  qui touche réellement la base (connexion, hachage bcrypt) fonctionne.
- **Phase 3 — Action** : branche `cycle-4-fabrication-exe`.
  - `server/app/config.py` : résolution de `config.ini` adaptée au mode
    "figé" (`sys.frozen`) — à côté de l'exécutable réel, jamais dans le
    dossier temporaire d'extraction de PyInstaller.
  - `server/fabrication/lanceur.py` : démarre le serveur (port 8000, ou un
    port libre si occupé), attend qu'il réponde, ouvre le navigateur.
    Message d'erreur lisible + pause si la configuration est invalide (une
    fenêtre de console se ferme sinon instantanément sur Windows).
  - `server/fabrication/quincaillerie_franck.spec` : configuration
    PyInstaller (mode un seul fichier, hidden-imports pour uvicorn/psycopg).
  - `server/fabrication/construire.ps1` : script humain, ASCII pur (même
    discipline que `db/outils/*.ps1`).
- **Phase 4 — Vérification par exécution réelle** :
  - Construction : `QuincaillerieFranck.exe`, 17,9 Mo.
  - **Exécuté depuis un dossier totalement isolé du dépôt** (Bureau, aucun
    fichier du projet à proximité, seulement l'exe + `config.ini`) : démarrage,
    `GET /sante` → `{"etat":"ok","base":"joignable"}`, `POST
    /auth/connexion` → `200` avec jeton, `POST /auth/changer-mot-de-passe`
    (hachage bcrypt réel) → `204`, reconnexion avec le nouveau mot de passe
    → `200`. **Aucun Python résiduel nécessaire.**
  - Garde-fous C11 testés dans l'exécutable : `config.ini` absent → message
    clair ; `user = postgres` → refusé explicitement. Les deux survivent à
    l'empaquetage.
  - Non-régression : suite pytest du cycle 3 rejouée après les changements
    de `config.py` — toujours **36/36**.
- **Bugs trouvés PAR l'exécution et corrigés pendant le cycle** :
  1. Le dossier de fabrication s'appelait d'abord `server/build/` —
     `.gitignore` exclut tout dossier nommé `build/`, donc **Git ignorait
     aussi mes fichiers sources**, sans le signaler (`git status` ne les
     montre simplement jamais). Détecté par `git check-ignore -v`, pas par
     relecture. Corrigé en renommant en `server/fabrication/`, en gardant
     les noms `dist/`/`build/` uniquement pour les *sous-dossiers de
     sortie* de PyInstaller (déjà couverts par les règles génériques
     existantes — aucune nouvelle entrée `.gitignore`).
  2. Messages d'erreur affichés avec des caractères accentués corrompus
     dans la console Windows (« d�marr� ») — cosmétique, corrigé en forçant
     l'UTF-8 sur la sortie standard (`sys.stdout.reconfigure`).
  3. Deux avertissements de construction (`_cffi_backend`,
     `psycopg_binary._uuid` introuvables) examinés et confirmés
     **inoffensifs** par les tests ci-dessus, plutôt que supposés sans
     vérifier : `bcrypt` 4.x n'utilise plus `cffi` (extension Rust), et
     aucune colonne UUID n'existe dans ce projet.
- **Phase 5 — Mémoire** : C0 **10 % → 55 %**. Commit, PR, fusion.
- **Reste à faire (C0)** : CI automatisée ; outil de création du premier
  compte responsable (CDC §7, second exécutable — chicken-and-egg du tout
  premier compte, non traité ce cycle) ; mode kiosque et écran réel une
  fois C9/C10 câblés (`CHEMIN_A_OUVRIR` dans `lanceur.py` pointe pour
  l'instant sur `/docs`, un placeholder documenté) ; dépendances encore
  installées à la main (`requirements.txt` figé, mais pas de lockfile avec
  hachages).

### Cycle 5 — Câblage de la maquette sur le noyau serveur : C9, C10 — 2026-09-12

- **Phase 1 — Diagnostic** : la maquette du cycle 1 (4 écrans) et le noyau
  serveur du cycle 3 existaient séparément — aucun des deux ne parlait à
  l'autre. Les décisions du propriétaire sur l'addendum (points b, d, e)
  restant à prendre, aucune route métier de vente/stock n'existe encore côté
  serveur.
- **Phase 2 — Objectif** : les 4 écrans consomment de vraies données du
  noyau serveur (connexion, jeton, `/articles`, `/ventes/synthese-jour`) là
  où une route existe déjà ; là où elle n'existe pas, la donnée reste
  simulée et **signalée explicitement à l'écran**, sans inventer de route
  métier. Critère de sortie : les 3 rôles voient réellement des choses
  différentes (prouvé par inspection du contenu des réponses, pas
  seulement du code HTTP) ; la quantité attendue d'un comptage n'atteint
  jamais le navigateur ; les erreurs serveur s'affichent toujours en
  français près du champ ; 0 régression sur les 36 tests du cycle 3 ;
  captures aux 5 largeurs ; `UX_BASELINE.md` mis à jour avec le protocole
  exact à chronométrer par un humain.
- **Phase 3 — Action** : branche `cycle-5-cablage-ux`.
  - `server/app/main.py` : montage `StaticFiles(html=True)` sous `/app`,
    pour servir `maquette/` **depuis le même serveur et la même origine**
    que l'API — aucune configuration CORS à gérer.
  - `maquette/api.js` (nouveau) : session (`sessionStorage`), `appelApi()`
    (jeton, erreurs réseau en français), `exigerSession(rôles)` (vérifie la
    session côté serveur via `/moi`, redirige vers l'écran du bon rôle).
  - `connexion.html` : connexion réelle (`POST /auth/connexion`), plus de
    couple identifiant/mot de passe en dur.
  - `vente.html` : catalogue et prix réels (`GET /articles`, filtré par
    rôle et par site) ; validation de vente **explicitement** annoncée
    « SIMULATION » (aucune route d'écriture n'existe : chantier C5, en
    attente des décisions du propriétaire).
  - `tableau-bord.html` : ventes du jour réelles et consolidées
    (`GET /ventes/synthese-jour`) ; alertes de stock et écarts d'inventaire
    laissés simulés, marqués « donnée simulée » (chantiers C7/C8).
  - `inventaire.html` : session réelle, mais liste d'articles à compter
    **délibérément laissée simulée** — la route `/articles` existante
    inclut la quantité en stock (légitime pour l'agent stock au quotidien),
    ce qui violerait le comptage à l'aveugle si elle servait ici. Une route
    dédiée sans cette colonne reste à construire (chantier C7).
  - `maquette/verification/verifier-cablage.mjs` (nouveau) : script
    Playwright auto-suffisant (réinitialise sa propre base de test),
    couvrant les 3 parcours de rôle, l'inspection du **contenu** des
    réponses réseau, et les captures aux 5 largeurs.
- **Phase 4 — Vérification par exécution réelle** :
  - `verifier-cablage.mjs` : **73/73**, 0 échec — détail complet dans
    `maquette/verification/DERNIER_RESULTAT.md`. Notamment : agent stock
    sans aucun champ de prix dans `/articles`, comptable sans aucun champ
    de quantité ; après rechargement de la page d'inventaire, aucune trace
    de « quantité attendue » dans la page, le réseau ou le code source ;
    messages d'erreur (champ vide, mot de passe erroné, panne réseau
    simulée) toujours en français, jamais bruts.
  - Suite pytest du serveur rejouée après le montage `StaticFiles` :
    **toujours 36/36**, 0 échec — aucune régression.
  - Captures régénérées aux 5 largeurs (360/390/768/1366/1920) sur les 4
    écrans réellement câblés, dans `maquette/captures/`.
- **Bugs trouvés PAR l'exécution et corrigés pendant le cycle** :
  1. Les boutons de déconnexion ajoutés aux 3 écrans protégés portaient un
     style en ligne (`min-height:auto`) qui écrasait le minimum de 44 px
     imposé par le thème sur `.btn` — cible tactile mesurée à 32 px sur
     mobile. Supprimé (le thème suffit).
  2. La bannière d'avertissement de l'écran d'inventaire contenait
     elle-même, en toutes lettres, la phrase « la quantité attendue »
     (en expliquant qu'elle n'existe pas...) — auto-déclenchait le contrôle
     qu'elle décrivait. Reformulée sans cette phrase littérale, sens
     inchangé ; confirmé par relecture du regex de contrôle contre le
     fichier corrigé (aucune correspondance).
  3. Une instabilité Playwright a d'abord fait échouer les 3 parcours de
     connexion (`waitForLoadState("networkidle")` ne détectait pas de façon
     fiable une redirection JS enchaînée après un `fetch` déjà attendu) —
     remplacé par une attente explicite de la réponse HTTP puis de l'URL
     finale (`waitForResponse` + `waitForURL`).
- **Phase 5 — Mémoire** : C9 **25 % → 50 %** (plafond 60 % maintenu,
  `UX_BASELINE.md` §4 toujours vide), C10 **0 % → 30 %**. Commit, PR,
  fusion.
- **Reste à faire (C9/C10)** : faire remplir le tableau de mesures humaines
  de `UX_BASELINE.md` §4 (protocole de démarrage exact ajouté au §1 bis) ;
  démontrer l'accès depuis un téléphone physique sur le réseau de la
  boutique ; câbler les routes encore manquantes une fois les décisions du
  propriétaire prises (addendum b, d, e) et les chantiers C5/C7/C8 ouverts.

### Cycle 6 — Première route de vente : C5 — 2026-09-12

- **Phase 1 — Diagnostic** : C5 était à 0 %, entièrement bloqué — aucune
  route d'écriture des ventes n'existait, faute de décisions du propriétaire
  sur l'addendum (points b, d, e). `decrementer_stock_vente()` (cycle 2)
  existait déjà mais REFUSAIT explicitement toute vente à découvert de
  stock, avec un `HINT` renvoyant justement au point e.
- **Phase 2 — Objectif** : obtenir du propriétaire les décisions
  structurantes de d et e (et le périmètre du b pour ce cycle), puis
  construire `POST /ventes` sans inventer aucune règle non tranchée. Critère
  de sortie : une vente s'enregistre réellement, décrémente le stock de
  façon atomique et jamais bloquante, calcule une TVA faisant foi, et le
  crédit client reste explicitement désactivé — prouvé par exécution, sans
  régression sur l'existant (cycles 2, 3, 5).
- **Décisions obtenues du propriétaire ce cycle** (voir
  `ADDENDUM_CAHIER_DES_CHARGES.md`, encarts « Décidé ») :
  - **d (fiscalité)** : régime du réel, TVA 19,25 %, prix négociés TTC,
    arrondi arithmétique sur le total de la vente.
  - **e (anti-survente)**, question 1 : une vente déjà encaissée n'est
    **jamais** bloquée ; l'écart est consigné, réservé au responsable.
  - **b (crédit client)** : reste désactivé ce cycle (statu quo explicite,
    pas une décision sur le fond — les 6 questions restent posées).
- **Phase 3 — Action** : branche `cycle-6-vente-fiscalite-antisurvente`.
  - `db/migrations/011_ventes_fiscalite_anti_survente.sql` (+ inverse) :
    paramètres fiscaux décidés (table `parametres`) ; nouvelle table
    `ecarts_stock_ventes` (RLS, lecture réservée au responsable) ;
    `decrementer_stock_vente()` réécrite (signature élargie avec
    `p_vente_id`, ne lève plus jamais d'exception pour stock insuffisant).
  - `server/app/routes/ventes.py` (nouveau) : `POST /ventes` (calcule TVA,
    insère `ventes`/`ventes_lignes`/`transactions`, décrémente le stock ligne
    par ligne, collecte les écarts) et `GET /ventes/parametres` (taux de TVA
    en vigueur, jamais une constante côté écran).
  - `maquette/vente.html` : câblé sur la vraie route — panier vide au
    départ (un panier pré-rempli créerait une vraie vente), sélecteur de
    site pour le responsable (qui couvre les deux sites), crédit client
    retiré des choix de paiement, message de succès réel (numéro de vente,
    TVA, écart éventuel signalé).
  - `db/tests/00_jeu_essai.sql`, `01_protections.sql`, `03_concurrence.sh` :
    mis à jour pour refléter les paramètres désormais décidés et le nouveau
    comportement anti-survente (voir Phase 4).
- **Phase 4 — Vérification par exécution réelle** :
  - Fonction SQL testée isolément avant tout code Python (comme au cycle 3) :
    vente de 5 sur un stock de 1 -> aucune exception, stock à 0, écart de 4
    consigné ; vente de 5 sur un stock de 30 -> aucun écart créé.
  - **8/8 tests pytest dédiés** (`test_ventes.py`) : TVA calculée à la main
    et comparée (2000 FCFA TTC -> 323 FCFA de TVA, valeur indépendante de la
    route) ; vente à découvert jamais refusée ; crédit client refusé avec
    message explicite ; agent stock sans aucun droit sur la route ; un
    comptable ne peut pas vendre pour l'autre site (même en forçant
    `site_id` dans le corps) ; un responsable doit préciser un site.
    **Suite complète : 44/44, 0 régression.**
  - Suite SQL du cycle 2 rejouée en entier
    (`db/tests/executer_tests.sh`) : protections **44/44**, habilitations
    **52/52**, concurrence **6/6** (réécrite : les deux ventes concurrentes
    réussissent désormais toutes les deux, une seule marchandise réelle
    sort, un seul écart d'1 unité consigné — plus de « perdante »),
    réversibilité des migrations 000-011 confirmée.
  - **10/10 contrôles Playwright** sur l'écran réel (`verifier-vente-reelle.mjs`,
    nouveau) : vente normale (message avec numéro de vente serveur, aucune
    mention « SIMULATION », **aperçu affiché avant validation identique au
    montant confirmé par le serveur** — un bug d'arrondi trouvé et corrigé
    pendant ce cycle, voir ci-dessous), vente à découvert acceptée avec écart affiché à
    l'écran, crédit client absent des options, responsable bloqué tant qu'il
    n'a pas choisi de site.
  - Non-régression du cycle 5 : `verifier-cablage.mjs` mis à jour (la
    validation étant désormais réelle, plus « SIMULATION ») et rejoué —
    **74/74**.
- **Bugs trouvés PAR l'exécution et corrigés pendant le cycle** :
  1. `db/tests/00_jeu_essai.sql` réamorçait `taux_tva`/`regime_fiscal`/... à
     leurs valeurs « a_definir » d'origine à CHAQUE test (copie figée de la
     migration 006) — les décisions du cycle 6 étaient invisibles côté tests
     tant que ce fichier n'a pas été mis à jour en conséquence.
  2. `db/tests/01_protections.sql` utilisait `regime_fiscal`/`taux_tva`
     comme EXEMPLES d'un paramètre « non tranché » — désormais faux depuis
     la décision d. Basculé sur `duree_session_minutes`, toujours réellement
     indécis.
  3. Capturer un `RETURNING id` avec `psql -At -c` inclut aussi la ligne de
     statut `INSERT 0 1` dans la sortie capturée par `$(...)` en bash — sans
     `-q`, la variable shell contenait les deux, cassant le SQL généré
     ensuite.
  4. `executer_tests.sh` supprime délibérément `quincaillerie_test` à
     l'étape 7 (comparaison aller-retour) sans la recréer : après l'avoir
     exécuté, il faut reconstruire la base avant de rejouer `pytest` —
     comportement pré-existant du cycle 2, pas une régression de ce cycle,
     mais qui a fait échouer 37 tests par « database does not exist » avant
     d'être compris.
  5. **Trouvé en relisant l'écran, avant même le contrôle Playwright** :
     `vente.html` calculait l'aperçu du total en AJOUTANT la TVA par-dessus
     le sous-total (`sous-total + TVA`), comme au temps où `TAUX_TVA` valait
     0 (aucune différence visible alors). Or les prix saisis sont **TTC**
     (décision d) : la TVA doit s'EXTRAIRE du total, pas s'y ajouter, sous
     peine d'afficher au comptable un total supérieur à celui que le
     serveur confirmera. Corrigé pour utiliser exactement la même formule
     que `server/app/routes/ventes.py`. Un contrôle dédié a été ajouté à
     `verifier-vente-reelle.mjs` (compare l'aperçu affiché avant validation
     au montant renvoyé par `POST /ventes`) pour qu'une régression future
     soit détectée par exécution, pas seulement par relecture.
- **Phase 5 — Mémoire** : C5 **0 % → 40 %**. Commit, PR, fusion.
- **Reste à faire (C5)** : numéro de facturier + vendeur obligatoires
  (addendum point c, non tranché — l'objectif anti-vol reste volontairement
  incomplet) ; annulation d'une vente ; régularisation d'un écart de stock ;
  documents imprimés (ticket/facture) ; afficher les écarts de stock des
  ventes au tableau de bord (chantier C7) ; le reste du point b si le crédit
  client doit un jour être réellement proposé.

---

## Prochain cycle — proposition (non démarré, choix laissé au propriétaire)

1. **C7 (inventaire et écarts)** : indépendant des points a/c/f encore
   ouverts. Permettrait de construire la route dédiée au comptage à
   l'aveugle (sans quantité en stock, remplaçant les données simulées
   d'`inventaire.html`), et de brancher au tableau de bord à la fois les
   écarts de comptage ET les écarts de stock issus des ventes à découvert
   (`ecarts_stock_ventes`, nouveau ce cycle) — aujourd'hui simulés ou
   invisibles.
2. **C4 (articles/stock)** : nécessite au préalable les décisions du
   propriétaire sur les points a (transfert inter-sites) et f (retours,
   casse, remises, unités) — sans elles, une route de mouvement de stock
   exposée inventerait une règle métier.
3. **Mesures humaines de `UX_BASELINE.md`** : ne nécessite aucun
   développement — un testeur humain, chronomètre en main, sur le serveur
   désormais câblé pour de vrai jusqu'à l'enregistrement d'une vente
   (protocole exact au §1 bis). Lèverait le plafond de 60 % sur C9 et C10 si
   les résultats sont conformes. Peut se faire à tout moment, en parallèle
   d'un autre cycle.
