# État du cycle de finalisation — Quincaillerie Franck

Référentiel fixe `C0`–`C14` — **ne jamais renuméroter**.
Cycle décrit dans `.agents/skills/finalisation-loop/SKILL.md`.

- Date d'initialisation : **2026-09-10**
- Dernier cycle fusionné : **Cycle 12 — écran de rapports, C8**,
  2026-09-13 (PR #13, fast-forward, commit `75d461e`) ; précédé du
  **Cycle 11 — écran des opérations de stock, C4** (PR #12, commit
  `4728683`), du **Cycle 10 — tableaux de bord et rapports, C8** (PR #11,
  commit `5aba09b`), du **Cycle 9 — articles et stock, C4** (PR #10, commit
  `a0195be`), du **Cycle 7 — inventaire et écarts, C7** et d'un **cycle de
  correction transverse**, 2026-09-12 — voir le journal, après les
  contrôles de boucle qui ont suivi chacun
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
| C4 | Articles et stock | **68 %** | Cycles 9 et 11. Six opérations réelles (création, modification, réception, transfert inter-sites, casse, retours client/fournisseur), chacune une fonction PostgreSQL `SECURITY DEFINER` et une vraie route API, **désormais toutes câblées sur un vrai écran** (`maquette/stock.html`, cycle 11) pour le responsable et l'agent stock. Modification tracée dans `historique_modifications_articles`/`historique_prix_articles` (existaient sans une seule ligne depuis le cycle 1) ; `quantite_stock` volontairement jamais modifiable par fiche, même si le `GRANT` du cycle 2 le permettrait à un agent stock. **Aucun montant FCFA, aucun champ de prix n'atteint la page ni les réponses réseau de l'agent stock** — prouvé par capture et par inspection du DOM/réseau (cycle 11). Correctif du constat n°1 du contrôle de boucle après le cycle 9 (`POST /articles` : 500 générique → 422 clair sur un `site_id`/`fournisseur_id` invalide). Vérifié par exécution : 100/100 tests pytest (90 + 10 nouveaux), suite SQL à jour (44/44, 52/52, 6/6, réversibilité de la migration 015 confirmée), 5 suites Playwright dont `verifier-stock-reel.mjs` (nouveau, 26/26) — 0 régression. Manquent : volumétrie/reprise du stock initial (addendum j, non tranché), remises et conversion d'unités (addendum f, volet non tranché), export, le **constat n°2** (cohérence article/quantité d'un retour) et le **constat n°3** trouvé au contrôle de boucle après le cycle 11 (`PUT /articles/{id}` trace un changement de prix dans `historique_prix_articles` même quand le prix soumis est identique à l'actuel — se déclenche dans l'usage ordinaire de l'écran, puisque le formulaire pré-remplit toujours les prix). |
| C5 | Ventes et facturation | **43 %** | Cycle 6, durci par le cycle de correction après C7. Décisions du propriétaire obtenues et appliquées (addendum, points b/d/e) : régime réel, TVA 19,25 % sur prix TTC, arrondi arithmétique sur le total ; une vente déjà encaissée n'est **jamais bloquée**, l'écart de stock est consigné et réservé au responsable ; crédit client explicitement désactivé. `POST /ventes` (`server/app/routes/ventes.py`) enregistre une vraie vente : décrément atomique anti-survente, une recette par vente, calcul de TVA faisant foi côté serveur. Vérifié par exécution : 8/8 tests pytest dédiés (55/55 au total, 0 régression), suite SQL du cycle 2 rejouée à jour (44/44 protections, 52/52 habilitations, **6/6 concurrence — réécrite pour le nouveau comportement anti-survente**, réversibilité des migrations confirmée), et 10/10 contrôles Playwright bout-en-bout sur l'écran de vente réellement câblé (`verifier-vente-reelle.mjs`) : vente normale (aperçu affiché AVANT validation identique à la confirmation serveur), vente à découvert acceptée avec écart affiché, crédit client absent des choix, responsable contraint de choisir un site. **+3 points (cycle de correction)** : fuseau horaire de `/ventes/synthese-jour` fixé à Africa/Douala au lieu d'hériter d'un réglage faux (Europe/Paris) — le « jour » des ventes dépendait silencieusement de l'horloge du poste serveur ; recherche/panier de `vente.html` ne construisent plus le HTML par concaténation non échappée (nom d'article), vérifié par un essai d'injection réel. Manquent : n° facturier + vendeur obligatoires (addendum c, non tranché — objectif anti-vol volontairement incomplet), annulation d'une vente, régularisation d'un écart, documents imprimés (ticket/facture), écarts de stock pas encore affichés au tableau de bord (prévu chantier C7). |
| C6 | Comptabilité et RH | **0 %** | Non vérifié. `transactions`, `employes`, `absences_conges`, `avances_salaire` présents. Manquent : clôture de caisse (addendum g), contre-passation d'annulation, `transactions.vente_id` non unique, audit des corrections. |
| C7 | Inventaire et écarts | **50 %** | Cycle 7, durci par le cycle de correction qui a suivi. Comptage à l'aveugle câblé de bout en bout : `GET /inventaire/articles-a-compter` (liste sans aucune quantité, articles déjà comptés aujourd'hui exclus, `site_id` distingue les deux sites pour le responsable) et `POST /inventaire/comptages` (n'accepte que la quantité comptée, ne renvoie jamais l'écart ni la quantité attendue — figée et calculée par la base depuis le cycle 2, **y compris si le client les injecte lui-même dans la requête**). Faille trouvée et corrigée par exécution : l'agent stock pouvait lire `ecart`/`quantite_attendue` en SQL direct malgré la discipline applicative (`GRANT` sans restriction de colonne, migration 008) — colonnes retirées par la migration 012, comme pour les prix d'`articles`. Tableau de bord du responsable câblé sur `GET /inventaire/ecarts` (écarts de comptage) **et** `GET /inventaire/ecarts-ventes` (écarts de vente à découvert, chantier C5) — les deux étaient invisibles avant ce cycle. Vérifié par exécution : 11/11 tests pytest dédiés (55/55 au total, 0 régression), 17/17 contrôles Playwright bout-en-bout (`verifier-inventaire-reel.mjs`) dont le contrôle le plus critique repris du cycle 5 — quantité attendue absente de la page/réseau/code source même après un comptage produisant un écart réel — et une double soumission (panne réseau simulée) qui n'immobilise plus l'agent. **+5 points (cycle de correction)** : fuseau horaire de la base fixé à Africa/Douala à deux niveaux indépendants (base et application) au lieu d'hériter d'un réglage faux ; écarts affichés au tableau de bord sans construire le HTML par concaténation non échappée, vérifié par un essai d'injection réel (11/11, `verifier-echappement-html.mjs`). Manquent : régularisation d'un écart, plafond de vraisemblance, historique au-delà du jour courant, export/rapport. |
| C8 | Tableaux de bord et rapports | **60 %** | Cycles 10 et 12. Alertes de stock, historique des comptages et deux exports Excel/PDF, **désormais tous câblés sur un vrai écran** (`maquette/rapports.html`, cycle 12) : historique filtré par période (responsable), export du catalogue (les 3 rôles), export des ventes (responsable, agent comptabilité). **Gating du prix par rôle posé en SQL**, prouvé en relisant le contenu réel du fichier produit (`openpyxl`, `pypdf`) pour les 3 rôles au niveau API (cycle 10) **et** par un vrai téléchargement de navigateur intercepté depuis l'écran (cycle 12, en-têtes de fichier relus : `PK`/`%PDF`). `telechargerFichier()` (nouveau, `api.js`) : un `<a href>` nu ne peut pas porter le jeton de session, contournement par lecture en `blob()`. Vérifié par exécution : 90/90 pytest (aucune route serveur changée ce cycle), 6 suites Playwright dont `verifier-rapports-reel.mjs` (nouveau, 29/29) — 0 régression après correction d'un débordement à 768 px trouvé en ajoutant un lien de navigation à `vente.html` (repli scopé à cet écran, cycle 12). Manquent : bascule vue consolidée/par site (les données portent déjà `site_id`, la bascule elle-même n'a pas d'écran), clôture de caisse (point g, non tranché), numéro de facturier (point c, non tranché — `numero_facture` restitué tel quel). **Reste du constat du contrôle de boucle après cycle 10** (n'entame pas le score) : le cloisonnement par site des deux exports fonctionne mais n'a toujours pas de test dédié dans `test_rapports.py`. |
| C9 | Ergonomie et UI *(priorité 1)* | **50 %** | Cycle 5. Les 4 écrans ne sont plus une maquette isolée : connexion réelle (`POST /auth/connexion`), jeton, `GET /articles`, `GET /ventes/synthese-jour`, servis par le noyau serveur sous `/app` (même origine). Vérifié par exécution (`verifier-cablage.mjs`, 73/73) : les 3 rôles reçoivent réellement des réponses différentes (aucun prix pour l'agent stock, aucune quantité pour le comptable), la quantité attendue d'un comptage n'apparaît nulle part (page, réseau, code source), messages d'erreur toujours en français près du champ, cibles ≥ 44 px conservées, 36/36 tests serveur toujours au vert. Ce qui n'a pas de route métier encore décidée (validation de vente, alertes stock, écarts d'inventaire, liste à compter) reste **explicitement** simulé à l'écran plutôt qu'inventé. **Toujours plafonné à 60 %** : le tableau de mesures humaines de `UX_BASELINE.md` §4 reste vide (vitesse, compréhension des erreurs par une personne non formée, confort sur téléphone physique). |
| C10 | Mobile et API web *(priorité 1)* | **30 %** | Cycle 5. Les deux écrans mobile-first (tableau de bord responsable, comptage d'inventaire) sont désormais **la même application web**, session réelle, testée et capturée à 360/390/768 px avec de vrais comptes — première preuve d'exécution sur ce chantier (`verifier-cablage.mjs`). Reste : accès démontré depuis un **téléphone physique** sur le LAN ou via tunnel (seules des largeurs de navigateur ont été testées ici, pas un appareil réel), API dédiée si un jour distincte de l'appli web, usage hors ligne, notifications. |
| C11 | Sécurité applicative | **55 %** | Cycle 3. Le « Sécurité : 100 % » du diagnostic d'origine était un artefact (mots-clés trouvés dans le script de diagnostic lui-même) — désormais vérifié réellement : démarrage refuse `postgres` et toute clé d'exemple, requêtes systématiquement paramétrées (injection SQL testée), jetons signés HMAC vérifiés à temps constant, aucun hachage ne fuit dans aucune réponse (vérifié par expression régulière), erreurs SQL jamais renvoyées telles quelles au client. Reste : révocation de session, limiteur de débit partagé (multi-processus), audit de sécurité plus large (dépendances, en-têtes HTTP, TLS — hors périmètre local de dev). |
| C12 | Sauvegarde et exploitation | **0 %** | Diagnostic : « Backup and restore procedure : Not found ». Aucun script, aucune procédure. Onduleur, RPO/RTO, mise à jour des postes : à définir (addendum i). |
| C13 | Tests automatisés et qualité | **0 %** | Aucun test automatisé détecté (« Tests identifiable : Found » = simple présence du mot « test » dans les guides). Aucune suite exécutable. |
| C14 | Documentation et livrables | **40 %** | Évalué sur pièces. Documentation d'usage/recette solide : CDC détaillé, 2 guides testeur, dossier de recette, guide d'installation. `MODELE_DONNEES.md`, `PERIMETRE_LIVRE.md`, `ADDENDUM_CAHIER_DES_CHARGES.md` produits dans ce cycle. Manquent (CDC §7) : code source, scripts de fabrication des exécutables, scripts + guide de sauvegarde/restauration. |

**Moyenne indicative après le cycle 12 : ≈ 44 %** (C0 55, C1 80, C2 65, C3 60, C4 68, C5 43, C7 50, C8 60, C9 50, C10 30, C11 55, C14 40, autres 0).
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

### Cycle 7 — Inventaire et écarts : C7 — 2026-09-12

- **Phase 1 — Diagnostic** : C7 était à 0 % — le socle existait déjà en
  base depuis le cycle 2 (`comptages_stock`, `ecart` généré, `quantite_
  attendue` figée par déclencheur, un seul comptage par article/moment/jour,
  immuable) mais n'était exposé par aucune route ; `inventaire.html` restait
  simulé (décision explicite du cycle 5, faute de route dédiée) et le
  tableau de bord n'affichait aucun écart réel. Avant d'écrire une route,
  vérification par exécution : sous `qf_agent_stock`, `SELECT ecart,
  quantite_attendue FROM comptages_stock` était **accepté** — la migration
  008 accordait un `SELECT` sans restriction de colonne, contrairement à ce
  qui avait été fait pour les prix d'`articles`.
- **Phase 2 — Objectif** : câbler le comptage à l'aveugle et les écarts sans
  attendre aucune décision du propriétaire (chantier indépendant des points
  encore ouverts). Critère de sortie : liste à compter sans aucune quantité,
  quantité attendue absente de l'écran/réseau/code source même après un
  comptage réel produisant un écart, écarts de comptage ET de vente à
  découvert visibles au tableau de bord du seul responsable — le tout
  prouvé par exécution, sans régression.
- **Phase 3 — Action** : branche `cycle-7-inventaire-ecarts`.
  - `db/migrations/012_comptage_aveugle_colonnes.sql` (+ inverse) : retire
    le `SELECT` sans restriction sur `comptages_stock` pour `qf_agent_stock`,
    le remplace par une liste de colonnes excluant `ecart` et `quantite_
    attendue` — défense en profondeur, la base protège même si une route
    future oubliait de filtrer.
  - `server/app/routes/inventaire.py` (nouveau) : `GET /inventaire/
    articles-a-compter` (liste par site, exclut les articles déjà comptés
    aujourd'hui pour le moment demandé), `POST /inventaire/comptages`
    (n'accepte que `article_id`/`moment`/`quantite_comptee`, ne renvoie que
    cela), `GET /inventaire/ecarts` et `GET /inventaire/ecarts-ventes`
    (réservées au responsable).
  - `maquette/inventaire.html` : réécrit pour consommer les routes
    ci-dessus. Chaque article est soumis dès qu'on avance (« Suivant »),
    jamais différé jusqu'à la fin : un comptage est un fait immuable
    (migration 003), une saisie « en brouillon modifiable jusqu'au bout »
    aurait été trompeuse. « Précédent » redevient un simple retour en
    lecture sur un article déjà soumis. Choix du moment (matin/soir) ajouté
    à l'écran, présélectionné selon l'heure.
  - `maquette/tableau-bord.html` : cartes « Écarts d'inventaire du jour » et
    nouvelle « Écarts de stock (ventes) » câblées sur les deux routes de
    lecture ; seule « Alertes de stock faible » reste simulée (C8).
- **Phase 4 — Vérification par exécution réelle** :
  - Fonction/politiques testées en SQL direct avant tout code Python (comme
    aux cycles 3 et 6) : après la migration 012, `SELECT ecart FROM
    comptages_stock` sous `qf_agent_stock` est refusé (`permission denied`) ;
    les colonnes autorisées restent lisibles ; l'INSERT normal fonctionne
    toujours ; compter l'article d'un autre site échoue proprement (« introuvable »,
    la RLS d'`articles` rend l'article invisible au déclencheur) ; un second
    comptage du même article/moment/jour est rejeté par la contrainte
    d'unicité.
  - **9/9 tests pytest dédiés** (`test_inventaire.py`) : liste à compter
    strictement limitée à `{id, nom, unite}` ; réponse d'un comptage
    strictement limitée à ce que le client a envoyé ; lecture directe de
    `ecart`/`quantite_attendue` refusée à l'agent stock (preuve la plus
    forte, hors API) ; article déjà compté absent de la liste et second
    envoi refusé (409) ; comptage d'un article de l'autre site refusé
    (422) ; comptabilité totalement exclue de l'inventaire (403) ; écarts
    réservés au responsable, avec un écart de comptage réel vérifié
    (30 en stock, 22 comptés → écart **-8**, valeur exacte) ; un écart de
    vente à découvert (chantier C5) retrouvé tel quel dans `/inventaire/
    ecarts-ventes`, prouvant que C5 et C7 se relient correctement.
    **Suite complète : 53/53, 0 régression.**
  - Suite SQL du cycle 2 rejouée en entier : protections **44/44**,
    habilitations **52/52**, concurrence **6/6**, réversibilité des
    migrations 000-012 confirmée.
  - **12/12 contrôles Playwright** sur les écrans réels
    (`verifier-inventaire-reel.mjs`, nouveau) : liste à compter réelle
    affichée, comptage produisant un écart de -8 sans que « quantité
    attendue » n'apparaisse dans la page, le code source ou les 3 réponses
    réseau observées après rechargement ; article compté absent de la liste
    au rechargement ; tableau de bord affichant l'écart de comptage exact
    (-8) et l'écart de vente à découvert exact (manque 2), les deux
    invisibles avant ce cycle.
  - Non-régression des cycles précédents : `verifier-cablage.mjs` (cycle 5)
    et `verifier-vente-reelle.mjs` (cycle 6) rejoués à jour — **74/74** et
    **10/10**.
- **Bugs/faille trouvés PAR l'exécution et corrigés pendant le cycle** :
  1. **Faille de confidentialité, présente depuis le cycle 2** : `qf_agent_stock`
     pouvait lire `ecart` et `quantite_attendue` de `comptages_stock` en SQL
     direct — jamais exploitée par une route (aucune n'existait), mais la
     protection reposait sur une absence de code, pas sur la base. Corrigée
     par la migration 012, sur le même principe que les prix d'`articles`.
  2. Le test Playwright combinant deux connexions successives dans le même
     contexte navigateur échouait (`connexion.html` redirige immédiatement
     si une session valide existe déjà, empêchant même l'affichage du
     formulaire) — corrigé en isolant chaque rôle dans son propre contexte,
     comme le fait déjà `verifier-cablage.mjs`.
- **Phase 5 — Mémoire** : C7 **0 % → 45 %**. Commit, PR, fusion.
- **Reste à faire (C7)** : régularisation d'un écart (qui a le droit, addendum
  point e question 3, non tranché) ; plafond de vraisemblance sur une
  quantité comptée ; historique des écarts au-delà du jour courant ; export
  ou rapport imprimable ; lien explicite entre un écart de vente à découvert
  et le prochain comptage (la donnée existe dans `ecarts_stock_ventes`, le
  rapprochement automatique reste à construire).

---

### Contrôle de boucle — après cycle 7, avant de démarrer un cycle 8 (2026-09-12, sans code)

Fait à la demande explicite du propriétaire, qui a constaté que la règle
« un chantier par cycle, avec validation du propriétaire avant mise en
œuvre » n'avait pas été respectée sur les cycles 4 à 7 (chantiers enchaînés
sans arrêt intermédiaire). Deux actions : corriger `SKILL.md` (fait, voir
plus haut — 4 étapes, arrêt obligatoire à l'étape 3) et rejouer le cycle 7
comme un relecteur extérieur, sans se fier au rapport que le cycle 7
avait lui-même produit.

**Chiffres annoncés par le cycle 7, tous rejoués indépendamment et
retrouvés identiques** : suite pytest 53/53 (dont 9/9 `test_inventaire.py`) ;
suite SQL du cycle 2 — protections 44/44, habilitations 52/52, concurrence
6/6, réversibilité des migrations 000-012 confirmée ; `verifier-cablage.mjs`
74/74 ; `verifier-vente-reelle.mjs` 10/10 ; `verifier-inventaire-reel.mjs`
12/12. **Aucun écart entre les chiffres annoncés et les chiffres obtenus.**

**Vérification renforcée, au-delà de la suite de tests existante**, sur le
point le plus sensible du chantier (la quantité attendue et l'écart ne
doivent jamais atteindre l'agent stock) :
- `SELECT ecart`, `SELECT quantite_attendue` et `SELECT *` sous
  `qf_agent_stock`, chacun dans sa propre transaction fraîche : **les trois
  refusés** (`permission denied for table comptages_stock`).
- `qf_agent_comptabilite` et `qf_agent_stock` sur `ecarts_stock_ventes` :
  **refusés** également (`permission denied`).
- Requête brute (`curl`, sans passer par le code du client) sur
  `GET /inventaire/articles-a-compter` : réponse strictement limitée à
  `{id, nom, unite}`.
- **Essai non couvert par la suite de tests existante** : `POST
  /inventaire/comptages` avec des champs `quantite_attendue` et `ecart`
  injectés volontairement dans le corps de la requête (un client
  malveillant qui tenterait de les imposer). Résultat : la réponse ne les
  contient pas, et la ligne enregistrée en base porte la vraie valeur
  (`quantite_attendue = 30`, la valeur réelle en stock), pas la valeur
  injectée (`999`) — Pydantic ignore silencieusement les champs inconnus, et
  le déclencheur de la migration 003 écrase de toute façon toute valeur
  fournie. **Cette garantie tient donc à deux niveaux indépendants**
  (schéma applicatif ET déclencheur base), pas à un seul.

**Relecture du code de la PR #8 comme un relecteur extérieur — 5 constats,
aucun ne remet en cause la garantie ci-dessus, mais aucun n'était consigné
dans le rapport du cycle 7** :

1. **Fuseau horaire de la base de données : `Europe/Paris`, pas
   `Africa/Douala`** (Batouri, Cameroun). Actuellement (heure d'été
   européenne) la base est en avance d'environ 1 heure sur l'heure réelle
   de la boutique. `CURRENT_DATE`, utilisé pour « un seul comptage par
   article/moment/**jour** » (migration 003) et pour les deux écrans
   « écarts **du jour** » (C5 et C7), suit l'horloge de la base, pas
   l'heure de Batouri. Fenêtre de risque étroite (une comptage fait très
   tard le soir pourrait être daté du lendemain côté base), mais réelle et
   non détectée avant ce contrôle. Ce n'est pas un bug de code : c'est une
   configuration d'environnement à corriger (hors périmètre d'un chantier
   applicatif — plutôt C0/C12).
2. **`tableau-bord.html` construit deux nouvelles listes avec
   `innerHTML` sans échapper `article_nom`** (nom d'article, une donnée
   modifiable par le personnel, pas un texte fixe). Un nom d'article
   contenant des caractères HTML s'exécuterait dans le navigateur du
   responsable. Le motif existait déjà ailleurs dans la maquette avant ce
   cycle (`vente.html`, liste de suggestions) ; ce cycle l'a étendu à deux
   emplacements de plus sans le corriger. Pas exploitable par un tiers
   extérieur (il faut un compte avec droit de nommer un article), mais une
   vraie faiblesse à traiter au chantier C11 ou lors d'un prochain passage
   sur l'ergonomie.
3. **`maquette/inventaire.html` : une panne réseau pendant l'enregistrement
   d'un comptage, suivie d'une nouvelle tentative, aboutit à une impasse
   d'ergonomie.** Si la première requête a en réalité réussi côté serveur
   mais que la réponse n'est jamais arrivée au navigateur, la deuxième
   tentative reçoit un 409 (« déjà compté »), traité comme une erreur
   générique : l'agent reste bloqué sur cet article, sans pouvoir avancer
   autrement qu'en cliquant « Passer » (qui abandonne silencieusement ce
   comptage-là de son point de vue, alors qu'il est bien enregistré). Aucun
   risque pour l'intégrité des données ; un vrai risque de confusion pour
   l'agent.
4. **`GET /inventaire/articles-a-compter` n'a pas de comportement défini
   pour un responsable** (le rôle est accepté par la route, mais aucun écran
   ne l'utilise pour ce rôle) : la réponse ne porte pas de `site_id`, alors
   qu'un responsable verrait les articles des DEUX sites mélangés sans
   pouvoir les distinguer. Sans conséquence aujourd'hui (aucune interface ne
   l'expose), mais une route ne devrait pas avoir un comportement non défini
   pour un rôle qu'elle accepte explicitement.
5. **Aucun test, avant ce contrôle, n'essayait d'injecter
   `quantite_attendue`/`ecart` dans le corps d'une requête `POST
   /inventaire/comptages`** — c'est ce contrôle qui l'a fait pour la
   première fois (constat ci-dessus). La suite `test_inventaire.py` devrait
   intégrer ce cas pour qu'une régression future (par exemple si le schéma
   `DemandeComptage` gagnait un jour ce champ par erreur) soit détectée
   automatiquement plutôt que par une relecture occasionnelle.

**Honnêteté des scores** : les nombres cités par `loop-state.md` pour le
cycle 7 (53/53, 44/44, 52/52, 6/6, 74/74, 10/10, 12/12) sont **tous
vérifiés, exacts, et même dépassés** par les contrôles supplémentaires
ci-dessus. Le score **C7 45 % n'est pas revu à la baisse** : la garantie la
plus critique du chantier (aucune fuite de la quantité attendue) est
confirmée par des essais plus durs que ceux déjà écrits, à deux niveaux de
défense indépendants. En revanche, la liste « Reste à faire (C7) »
ci-dessus était **incomplète** : les 5 constats ne remettent pas en cause le
score mais auraient dû y figurer. Ils sont ajoutés ici plutôt que
silencieusement absorbés dans un score inchangé.

**Verdict sur la PR #8** : **fusionnable en l'état** — aucune régression,
aucune preuve manquante, la garantie centrale du chantier tient sous
contrainte. Les 5 constats ci-dessus ne sont pas des motifs de blocage ; ce
sont des corrections mineures à trancher (les proposer maintenant ou les
reporter) plutôt que des raisons de ne pas fusionner un travail qui fait ce
qu'il annonce.

**PR #8 fusionnée** le 2026-09-12 (commit de fusion `dd84dcd`, puis un
second commit pour intégrer le diagnostic ci-dessus, poussé sur la branche
juste avant la fusion et resté hors du premier commit de fusion — les deux
réconciliés sur `main`, commit `b55a375`).

---

### Cycle de correction après le cycle 7 — 2026-09-12 (aucun chantier créé)

Suit le processus corrigé de `SKILL.md` (voir le commit séparé sur `main`,
`59d270c`) : les étapes 1 à 3 ont eu lieu dans l'échange avec le
propriétaire, avant tout code — reprises ici pour mémoire, en plus du
détail déjà consigné dans le contrôle de boucle ci-dessus.

- **Étape 1 — Diagnostic** : voir « Contrôle de boucle — après cycle 7 »
  ci-dessus. 5 constats trouvés, aucun ne remettant en cause le score ou la
  garantie centrale du chantier C7, mais absents du rapport initial.
- **Étape 2 — Propositions** : corriger les 5 constats (sans risque métier,
  ne débloque rien de nouveau mais fiabilise l'existant) présentée en
  option principale, à côté de C4 (tranche sans a/f), C6 (tranche sans g),
  C8 (tableaux de bord) et des mesures humaines de `UX_BASELINE.md`.
- **Étape 3 — Objectif retenu et plan** : corriger les 5 constats, sans
  créer de nouveau chantier. **Validé explicitement par le propriétaire**,
  avec trois précisions : fuseau horaire Africa/Douala fixé à la fois côté
  base et côté application (jamais hérité du système d'exploitation) ;
  `site_id` ajouté à la liste à compter du responsable plutôt que de lui
  retirer l'accès à la route ; ce cycle reste transverse, sans score de
  chantier C0–C14 propre — seuls C7 et C5 (touché par le fuseau horaire)
  sont mis à jour.
- **Étape 4 — Mise en œuvre** : branche `cycle-8-corrections-c7`.
  - `db/migrations/013_fuseau_horaire_boutique.sql` (+ inverse) : fixe le
    fuseau **au niveau de la base** (`ALTER DATABASE ... SET timezone`,
    appliqué dynamiquement à la base courante — pas de nom de base en dur,
    valable en dev comme en production).
  - `server/app/database.py` : `FUSEAU_HORAIRE_BOUTIQUE = "Africa/Douala"`,
    imposé à **chaque connexion** (`connexion_anonyme()` et
    `connexion_pour()`) — défense en profondeur, vérifiée par exécution en
    réglant délibérément la base sur `UTC` : l'application a quand même
    imposé `Africa/Douala`.
  - Recensement de **toutes** les occurrences d'`innerHTML` dans les 5
    écrans de la maquette : **5 dangereuses** (interpolation de données non
    échappées — 2 dans `vente.html`, 3 dans `tableau-bord.html`), 7 autres
    littérales ou des vidages, non concernées. Les 5 corrigées : `api.js`
    gagne `creerLigneListe()` (construction DOM, jamais d'`innerHTML`) pour
    les 3 de `tableau-bord.html` ; `vente.html` reconstruit ses deux listes
    (suggestions, panier) par le DOM — la plus grave incluait le nom
    d'article dans un attribut `aria-label` construit par concaténation,
    une injection y aurait aussi pu casser l'attribut lui-même.
  - `maquette/inventaire.html` : un 409 (« déjà compté ») après l'envoi
    d'un comptage est désormais traité comme un succès local (le comptage
    est en réalité déjà enregistré), pas comme une erreur bloquante.
  - `server/app/routes/inventaire.py` : `site_id` ajouté à la réponse de
    `GET /inventaire/articles-a-compter`.
  - `server/tests/test_inventaire.py` : +2 tests — injection de champs
    interdits dans le corps de la requête (sans effet, ni sur la réponse ni
    en base) ; liste à compter du responsable distinguant les deux sites.
  - `maquette/verification/verifier-echappement-html.mjs` (nouveau) : essai
    d'injection réel (nom d'article `<img src=x onerror="...">`) sur les
    deux écrans concernés.
  - `maquette/verification/verifier-inventaire-reel.mjs` : +5 contrôles
    (double soumission à deux onglets, simulant une panne réseau suivie
    d'une nouvelle tentative).
- **Vérification par exécution, les deux suites de non-régression
  demandées** (C7, directement corrigé, et C5, touché par le fuseau
  horaire) :
  - `server/tests/test_inventaire.py` : **11/11** (9 existants + 2 nouveaux).
  - Suite complète pytest : **55/55**, 0 régression.
  - `db/tests/executer_tests.sh` (migrations 000 à 013) : protections
    **44/44**, habilitations **52/52**, concurrence **6/6**, réversibilité
    confirmée.
  - `verifier-cablage.mjs` (C9/C10) : **74/74**, 0 régression.
  - `verifier-vente-reelle.mjs` (**C5**, rejouée spécifiquement à cause du
    fuseau horaire) : **10/10**, 0 régression.
  - `verifier-inventaire-reel.mjs` (**C7**) : **17/17** (12 + 5 nouveaux).
  - `verifier-echappement-html.mjs` (nouveau) : **11/11** — le nom
    malveillant ne s'exécute nulle part, s'affiche comme texte partout,
    aucune balise `<img>` réelle créée dans le DOM.
  - Garantie centrale de C7 revérifiée une dernière fois après toutes ces
    migrations : `SELECT ecart`, `SELECT quantite_attendue`, `SELECT *`
    sous `qf_agent_stock` — toujours refusés (`permission denied`).
- **Bug trouvé par l'exécution en écrivant la vérification** (pas en la
  concevant) : `verifier-inventaire-reel.mjs` supposait le moment par
  défaut de l'écran ("matin" avant 13h) figé dans le temps — le correctif
  de fuseau horaire a changé l'heure locale réellement utilisée par la
  page au moment du contrôle, faisant basculer ce défaut à "soir" et
  cassant une assertion qui comparait deux sections sous une hypothèse de
  moment différente. Corrigé en forçant explicitement le moment dans le
  script (bouton « Matin ») plutôt que de dépendre de l'heure du jour —
  confirme, par la pratique, le risque même que ce cycle corrigeait.
- **Score** : C7 **45 % → 50 %**, C5 **40 % → 43 %** (fuseau horaire de
  `/ventes/synthese-jour`, échappement HTML de `vente.html`). **Aucun
  chantier créé.** Commit, PR sur `cycle-8-corrections-c7` — **non
  fusionnée**, sur instruction explicite du propriétaire.
- **Reste ouvert** : le cinquième constat du contrôle de boucle (absence de
  test d'injection) est la correction elle-même, ci-dessus. Rien d'autre
  en suspens sur ce cycle de correction.

---

### Cycle 9 — Articles et stock : C4 — 2026-09-13

Premier cycle mené sous le processus corrigé en 4 étapes de `SKILL.md`
(commit `59d270c`), avec arrêt réel à l'étape 3 et validation explicite du
propriétaire avant tout code.

- **Étape 1 — Diagnostic du cycle précédent (cycle de correction après C7)** :
  rejoué avant tout code sur la base fusionnée (PR #9) : suite pytest
  complète **55/55**, `db/tests/executer_tests.sh` **44/44 + 52/52 + 6/6**,
  réversibilité confirmée, `verifier-cablage.mjs` **74/74**,
  `verifier-vente-reelle.mjs` **10/10**, `verifier-inventaire-reel.mjs`
  **17/17**, `verifier-echappement-html.mjs` **11/11** — tout identique aux
  chiffres annoncés, 0 écart. Garantie centrale de C7 revérifiée une
  dernière fois (`ecart`/`quantite_attendue` toujours inaccessibles à
  `qf_agent_stock`, y compris en SQL direct).
- **Étape 2 — Propositions** : le propriétaire ayant tranché les points a et
  f de l'addendum entre-temps, une seule option a été présentée :
  **C4 (articles et stock) en entier**, les deux blocages métier ayant
  disparu. Aucun autre chantier n'a été proposé, conformément à la
  décision déjà prise par le propriétaire de traiter C4 en entier et non
  en tranche.
- **Étape 3 — Objectif retenu et plan** : livrer C4 en entier — création
  d'article, entrée de stock (réception fournisseur), transfert inter-sites,
  casse, retour client, retour fournisseur — chacune par une vraie route
  API et une vraie fonction PostgreSQL, sans inventer de règle au-delà de
  ce que les points a et f du propriétaire précisent. **Validé
  explicitement par le propriétaire** (« je valide »), sans réserve
  supplémentaire.
- **Étape 4 — Mise en œuvre** : branche `cycle-9-c4-articles-stock`.
  - `db/migrations/014_articles_stock_transferts_retours.sql` (+ inverse) :
    colonne `categorie` sur `mouvements_stock` (le « pourquoi » du
    mouvement, orthogonale au `type` déjà existant qui reste le « sens »),
    colonnes `vente_id` et `mouvement_origine_id` (auto-référence,
    réutilisée pour relier un retour fournisseur à sa réception d'origine
    et les deux moitiés d'un transfert). Quatre fonctions
    `SECURITY DEFINER` nouvelles : `transferer_stock` (atomique,
    sortie+entrée même transaction donc même horodatage, ne recalcule pas
    le seuil, verrouillage des deux lignes `articles` dans un ordre fixe
    pour éviter tout interblocage), `enregistrer_casse` (réservée au
    responsable par `GRANT`, pas seulement par convention), `retour_client`
    (rattaché à la vente d'origine, refusé si vente d'un autre site) et
    `retour_fournisseur` (rattaché à la réception d'origine, refusé si le
    mouvement visé n'en est pas une). `enregistrer_entree_stock` et
    `decrementer_stock_vente` (fonctions déjà existantes depuis les cycles
    2 et 6/7) mises à jour pour renseigner `categorie` sans changer leur
    comportement par ailleurs.
  - **Faille systémique trouvée et corrigée par exécution, pas par
    lecture** : `current_user`/`session_user` à l'intérieur d'une fonction
    `SECURITY DEFINER` reflètent le **propriétaire** de la fonction, pas
    l'appelant — vérifié avec une fonction jetable dédiée. Une première
    version de `transferer_stock` s'appuyait sur `current_user` pour
    limiter un agent stock à son propre site : la restriction ne
    s'appliquait jamais. Corrigée en utilisant `qf_site_courant()` (réglage
    de session, non affecté par l'élévation `SECURITY DEFINER`). Le même
    contrôle manquant a ensuite été **recherché volontairement** dans les
    autres fonctions exposées par ce cycle et trouvé dans deux endroits de
    plus, jamais exploités jusqu'ici faute de route : `enregistrer_entree_stock`
    (un agent stock pouvait réceptionner pour n'importe quel site) et
    `enregistrer_retour_client`/`enregistrer_retour_fournisseur` (même
    faille dans le code neuf, corrigée avant tout test). Documenté en détail
    dans `db/README.md`.
  - `server/app/schemas.py` : `DemandeArticle`, `ReponseArticle`,
    `DemandeEntreeStock`, `ReponseMouvementStock`, `DemandeTransfert`,
    `ReponseTransfert`, `DemandeCasse`, `DemandeRetourClient`,
    `DemandeRetourFournisseur`.
  - `server/app/routes/articles.py` (nouveau) : `POST /articles`
    (responsable, agent stock). Un agent stock ne peut jamais fixer de prix
    ni choisir un autre site que le sien (ignoré silencieusement côté
    construction de la requête SQL, pas seulement côté validation) ; un
    responsable doit préciser un site. Jamais de quantité de stock à la
    création (défaut base à 0).
  - `server/app/routes/stock.py` (nouveau) : `POST /stock/entrees`,
    `POST /stock/transferts`, `POST /stock/casse` (responsable seul),
    `POST /stock/retours-client`, `POST /stock/retours-fournisseur`. Les
    erreurs métier de la base (`RAISE EXCEPTION`, toujours un message
    français écrit par le projet) sont renvoyées telles quelles en 422 ;
    `InsufficientPrivilege` n'est délibérément pas intercepté ici et
    remonte au gestionnaire global existant de `main.py` (403 « Accès
    refusé. »), par cohérence avec le reste du serveur.
  - `server/tests/test_articles.py` (5 tests) et `server/tests/test_stock.py`
    (13 tests, dont un essai explicite de motif blanc — accepté par Pydantic
    mais refusé par la base, preuve de la défense en profondeur).
- **Vérification par exécution** :
  - Migration 014 vérifiée en SQL direct avant tout code Python, en trois
    passes de correction : cas normal de transfert (seuil inchangé,
    montants corrects, lien `mouvement_origine_id` correct), transfert
    refusé même site / stock insuffisant / motif blanc / mauvais site pour
    un agent stock (succès pour le bon site, succès sans restriction pour
    le responsable) ; casse réservée au responsable (`GRANT`, pas
    seulement une vérification applicative) ; retour client sur le bon
    site / refusé sur le mauvais site de la vente / refusé si appelé par
    un agent d'un autre site ; retour fournisseur sur une vraie réception /
    refusé sur un mouvement qui n'en est pas une ; réception recalculant
    toujours le seuil et refusée pour un article d'un autre site (faille
    latente ci-dessus).
  - `server/tests/test_articles.py` + `test_stock.py` : **18/18**.
  - Suite pytest complète : **73/73**, 0 régression.
  - `db/tests/executer_tests.sh` (migrations 000 à 014) : protections
    **44/44**, habilitations **52/52**, concurrence **6/6**, réversibilité
    de la migration 014 confirmée (aucune trace résiduelle au-delà des 2
    écarts déjà documentés et pré-existants).
  - `01_protections.sql` : cassé par la contrainte `NOT NULL` sur
    `categorie` (deux `INSERT` directs sans cette colonne) — trouvé par
    l'échec du script complet, corrigé en ajoutant `categorie` aux deux
    insertions.
  - `verifier-cablage.mjs` **74/74**, `verifier-vente-reelle.mjs` **10/10**,
    `verifier-inventaire-reel.mjs` **17/17**, `verifier-echappement-html.mjs`
    **11/11** — 0 régression sur les écrans existants (aucun nouvel écran
    n'a été construit pour C4 dans ce cycle, conformément au plan validé).
- **Documentation** : `db/README.md` (nouvelle section sur `categorie` et le
  piège `current_user` en `SECURITY DEFINER`, table des décisions
  volontairement non prises mise à jour), `server/README.md` (nouvelle
  section C4), `ADDENDUM_CAHIER_DES_CHARGES.md` (décisions a et f
  consignées à leur place, tableau récapitulatif mis à jour),
  `server/tests/DERNIER_RESULTAT.md` et `db/tests/DERNIER_RESULTAT.md`.
- **Score** : C4 **0 % → 55 %** (création d'article, 5 opérations de
  mouvement de stock toutes vraies et vérifiées par exécution ; manquent :
  volumétrie/reprise de stock initial — point j, non tranché —, remises et
  conversion d'unités — point f, volet non tranché —, écran dédié, export).
  Commit, PR #10 sur `cycle-9-c4-articles-stock`, **fusionnée le
  2026-09-13** sur instruction explicite du propriétaire (commit de fusion
  `a0195be`, fast-forward, branche supprimée) après le contrôle de boucle
  ci-dessous.
- **Reste ouvert** : points a (questions 1, 4, 5), f (remises, unités), j
  (volumétrie/reprise/formation) toujours sans réponse ; aucun écran ne
  couvre encore C4 (hors périmètre validé de ce cycle) ; voir aussi les 2
  constats du contrôle de boucle ci-dessous.

---

### Contrôle de boucle — après cycle 9, avant de démarrer le cycle 10 (2026-09-13, sans code)

Diagnostic par exécution, avant fusion de la PR #10 puis avant tout choix
pour le cycle suivant (C8, maintenu par le propriétaire).

- **Suites rejouées, toutes identiques au rapport du cycle 9** : suite
  pytest complète **73/73** ; `db/tests/executer_tests.sh` (migrations 000
  à 014) protections **44/44**, habilitations **52/52**, concurrence
  **6/6**, réversibilité confirmée (seuls les 2 écarts déjà documentés et
  pré-existants — ordre des `CREATE EXTENSION`, ordre de deux colonnes de
  `comptages_stock`) ; les 4 suites Playwright **74/74**, **10/10**,
  **17/17**, **11/11**. Garantie centrale de C7 revérifiée une dernière
  fois : `ecart`/`quantite_attendue` toujours inaccessibles à
  `qf_agent_stock`. **0 écart avec le rapport initial.**
- **Relecture du code comme un tiers, 2 constats trouvés par exécution,
  absents du rapport du cycle 9** :
  1. `POST /articles` n'a **aucune** gestion d'erreur métier, contrairement
     à `stock.py` (qui traduit chaque refus de la base en 422 clair via
     `_erreur_metier`). Un `site_id` ou un `fournisseur_id` invalide envoyé
     par un responsable lève une `ForeignKeyViolation` non interceptée, qui
     remonte au gestionnaire générique de `main.py` : **500 « Erreur
     interne. »** au lieu d'un message compréhensible. Vérifié par
     exécution (requête réelle avec `site_id: 999`). Pas une fuite
     d'information (le message générique ne révèle rien), mais une
     incohérence de qualité par rapport au reste de C4.
  2. **Plus sérieux** : ni `enregistrer_retour_client` ni
     `enregistrer_retour_fournisseur` ne vérifient que l'article et la
     quantité retournés correspondent réellement à ce qui a été vendu (table
     `ventes_lignes`, qui existe et porte `article_id`/`quantite` par
     vente) ou reçu dans le mouvement d'origine référencé — seules la
     cohérence de site et, pour le retour fournisseur, la nature du
     mouvement (bien une réception) sont vérifiées. Prouvé par exécution :
     un retour client de **500 unités d'un article jamais vendu** a été
     accepté contre une vente n'ayant réellement vendu qu'un **tout autre
     article, en quantité 3** ; un retour fournisseur de **10 unités** a
     été accepté contre une réception de seulement **3 unités**. Le
     rattachement « à la vente/réception d'origine » n'est donc qu'un lien
     de traçabilité (clé étrangère + même site), pas une garantie de
     cohérence quantité/article — aucun des 18 tests de C4 ne couvre ce
     cas.
- **Verdict** : les deux constats sont réels et honnêtes à consigner, mais
  ne remettent pas en cause le socle du chantier C4 (les 5 opérations de
  mouvement de stock sont réellement câblées, la faille systémique
  `SECURITY DEFINER`/`current_user` trouvée et corrigée au cycle 9 reste un
  vrai progrès, aucune fuite de rôle ou de site n'est en cause ici). **C4
  n'est pas revu à la baisse** — les deux constats sont ajoutés aux
  manques déjà listés pour ce chantier (ci-dessus) plutôt que traités comme
  une régression du score. **PR #10 fusionnée en l'état** sur instruction
  du propriétaire. Une correction de ces deux points reste un candidat
  raisonnable pour un futur cycle transverse (dans l'esprit du cycle 8),
  au choix du propriétaire — non traitée ici, le prochain chantier étant
  C8, maintenu par le propriétaire.

---

### Cycle 10 — Tableaux de bord et rapports : C8 — 2026-09-13

Deuxième cycle mené sous le processus corrigé en 4 étapes de `SKILL.md`.

- **Étape 1 — Diagnostic du cycle précédent (cycle 9, C4)** : voir
  « Contrôle de boucle — après cycle 9 » ci-dessus. Tout rejoué à
  l'identique du rapport (73/73 pytest, 44/44+52/52+6/6 SQL, 4 suites
  Playwright), 2 constats trouvés par relecture du code (gestion d'erreur
  de `POST /articles`, cohérence article/quantité des retours) — n'entament
  pas le score de C4, consignés comme candidats pour un futur cycle de
  correction.
- **Étape 2 — Propositions** : une seule option, le propriétaire ayant
  déjà maintenu **C8** avant même le diagnostic.
- **Étape 3 — Objectif et plan** : rendre réelles, à partir des seules
  données déjà décidées et déjà en base, les trois briques de C8 —
  alertes de stock faible, historique des comptages filtrable par
  période, deux exports (Excel/PDF) avec gating du prix appliqué en SQL —
  sans toucher à la clôture de caisse (point g) ni au numéro de facturier
  (point c), non tranchés. **Validé explicitement par le propriétaire**
  (« je valide »), sans réserve supplémentaire.
- **Étape 4 — Mise en œuvre** : branche `cycle-10-c8-tableaux-bord-rapports`.
  - Aucune nouvelle migration : `seuil_alerte`/`quantite_stock` (C1/C4),
    `comptages_stock` (C7), `ventes`/`ventes_lignes` (C5) portaient déjà
    tout ce dont ce cycle avait besoin.
  - Nouvelles dépendances (`server/requirements.txt`) : `openpyxl`
    (Excel, production ET tests), `reportlab` (PDF, production),
    `pypdf` (PDF, **test seul** — relit le contenu produit, jamais utilisé
    par le serveur lui-même).
  - `server/app/colonnes.py` (nouveau) : la liste blanche de colonnes par
    rôle pour `articles`, déplacée hors de `routes/demonstration.py` (où
    elle vivait depuis le cycle 3) pour être **partagée** avec les
    exports — un seul point de vérité pour le gating du prix, jamais deux
    listes qui pourraient diverger.
  - `server/app/routes/tableau_bord.py` (nouveau) : `GET
    /tableau-bord/alertes-stock` (responsable, tous sites).
  - `server/app/routes/inventaire.py` : `GET
    /inventaire/historique-comptages` (responsable, tous sites,
    `date_debut`/`date_fin` validés côté application avant d'atteindre la
    base — comme `moment` pour `/articles-a-compter`).
  - `server/app/routes/rapports.py` (nouveau) : `GET /rapports/articles`
    (3 rôles, colonnes issues de `colonnes.py` — **le prix n'est jamais lu
    par PostgreSQL pour un agent stock : rien à retirer du fichier après
    coup, parce que la valeur n'existe jamais dans les lignes en
    mémoire**) et `GET /rapports/ventes` (responsable, agent
    comptabilité — un agent stock est refusé par `exiger_role` avant
    d'atteindre la base, comme `/ventes/synthese-jour` depuis le cycle 3).
    `numero_facture` restitué tel quel (y compris `NULL`) : le point c
    n'est pas tranché, ce module n'invente aucune numérotation.
  - `maquette/tableau-bord.html` + `donnees-simulees.js` : la carte
    « Alertes de stock faible », dernière donnée simulée de l'écran,
    câblée sur `GET /tableau-bord/alertes-stock` via `creerLigneListe()`
    (jamais `innerHTML`, comme depuis le correctif du cycle 8) ; bandeau
    et pastille « donnée simulée » retirés.
  - `server/tests/test_tableau_bord.py` (6 tests) et
    `server/tests/test_rapports.py` (11 tests) : ces derniers relisent le
    **contenu réel** du fichier produit (`openpyxl.load_workbook`,
    `pypdf.PdfReader`) pour chacun des trois rôles — jamais seulement le
    code HTTP ou le type MIME.
- **Vérification par exécution** :
  - `test_tableau_bord.py` + `test_rapports.py` : **17/17**.
  - Suite pytest complète : **90/90**, 0 régression.
  - `verifier-cablage.mjs` étendu (2 contrôles de plus sur la carte
    réellement câblée, plus aucune pastille « donnée simulée » sur
    l'écran) : **76/76** (74 existants + 2 nouveaux).
  - `verifier-vente-reelle.mjs` **10/10**, `verifier-inventaire-reel.mjs`
    **17/17**, `verifier-echappement-html.mjs` **11/11** — 0 régression.
  - Aucune migration à vérifier par exécution SQL directe (pas de
    migration ce cycle) ; la suite `db/tests/executer_tests.sh` reste à
    l'état déjà revérifié pendant le diagnostic du cycle précédent
    (contrôle de boucle ci-dessus), inchangée par ce cycle.
- **Documentation** : `server/README.md` (nouvelle section C8, tables des
  tests mises à jour), `server/tests/DERNIER_RESULTAT.md`,
  `PERIMETRE_LIVRE.md` (4 lignes §3.3/§3.14 passées de « Spécifié » à
  « Confirmé (test) »), `loop-state.md`.
- **Score** : C8 **0 % → 45 %**. Commit, PR sur
  `cycle-10-c8-tableaux-bord-rapports` — **non fusionnée**, sur
  instruction du propriétaire (à confirmer avant fusion, comme pour les
  cycles précédents).
- **Reste ouvert** : bascule vue consolidée/par site (pas d'écran),
  écran dédié pour l'historique des comptages et les exports, clôture de
  caisse (point g) et numéro de facturier (point c) non tranchés, paquet
  Windows (.exe) non re-fabriqué avec les 3 nouvelles dépendances — risque
  documenté, pas vérifié ce cycle.

---

### Contrôle de boucle — après cycle 10, avant de démarrer le cycle 11 (2026-09-13, sans code)

Diagnostic par exécution, avant fusion de la PR #11 puis avant tout choix
pour le cycle suivant (écrans manquants, maintenu par le propriétaire).

- **Suites rejouées, toutes identiques au rapport du cycle 10** : suite
  pytest complète **90/90** ; `db/tests/executer_tests.sh` (base recréée de
  zéro pour l'occasion) protections **44/44**, habilitations **52/52**,
  concurrence **6/6**, réversibilité confirmée ; les 4 suites Playwright
  **76/76**, **10/10**, **17/17**, **11/11**. **0 écart avec le rapport
  initial.**
- **Relecture du code comme un tiers, vérifications supplémentaires par
  exécution directe** (au-delà des tests déjà écrits) :
  - Le cloisonnement par site des deux exports (`/rapports/articles`,
    `/rapports/ventes`) repose entièrement sur la RLS posée au cycle 2 —
    jamais testé explicitement pour la route d'export elle-même dans
    `test_rapports.py`. Vérifié manuellement par exécution : un agent
    stock du Magasin n'obtient, dans son export, que les articles de son
    site (« Clou 5 cm », Comptoir, absent) ; un agent comptabilité du
    Magasin n'obtient, dans son export de ventes, que les ventes de son
    site (une vente créée sur le Comptoir n'apparaît pas). Ça fonctionne
    — parce que c'est la même RLS déjà éprouvée depuis le cycle 2 — mais
    ce n'est écrit nulle part comme un test dédié à l'export : un manque
    de couverture honnête à consigner, pas un défaut de comportement.
  - Vérifié aussi, positivement : le nom d'article malveillant du jeu
    d'essai (`<img src=x onerror=...>`, chantier C7) ressort **littéral**
    dans le PDF exporté par un responsable (`pypdf` le confirme) —
    `reportlab.platypus.Table` ne traite pas une chaîne Python brute comme
    du balisage (contrairement à `Paragraph`, qui interprète un
    mini-XML) : aucun risque d'injection dans l'export PDF, confirmé par
    exécution plutôt que supposé.
- **Verdict** : aucune régression, aucune faille trouvée. Le manque de
  test dédié au cloisonnement par site des exports est consigné aux
  manques déjà listés pour C8 — **C8 n'est pas revu à la baisse**. **PR
  #11 fusionnée en l'état** sur instruction du propriétaire.

---

### Cycle 11 — Écran des opérations de stock : C4 — 2026-09-13

Troisième cycle mené sous le processus corrigé en 4 étapes de `SKILL.md`.

- **Étape 1 — Diagnostic du cycle précédent (cycle 10, C8)** : voir
  « Contrôle de boucle — après cycle 10 » ci-dessus. Tout rejoué à
  l'identique (90/90 pytest, 44/44+52/52+6/6 SQL sur une base recréée de
  zéro, 4 suites Playwright), 2 vérifications supplémentaires trouvées non
  couvertes par un test dédié (cloisonnement par site des exports) mais
  fonctionnant correctement à l'exécution ; une confirmation positive
  (`reportlab.platypus.Table` ne traite pas une chaîne brute comme du
  balisage). Aucune régression, C8 non revu à la baisse.
- **Étape 2 — Propositions** : une seule option validée par avance par le
  propriétaire (option 4, « les écrans manquants »), avec un ordre de
  priorité explicite : (1) les 6 opérations de stock du cycle 9, (2)
  l'historique des comptages et les exports du cycle 10.
- **Étape 3 — Objectif et plan, avec découpage proposé** : en concevant
  l'écran, deux découvertes ont changé la taille réelle du chantier — la
  modification d'article n'avait aucune route (seule la création
  existait), et un agent stock n'avait aucun moyen de lire le catalogue
  de l'autre site pour choisir la destination d'un transfert (la RLS le
  lui interdit, à raison). Un risque latent trouvé en lisant les `GRANT`
  du cycle 2 : `qf_agent_stock` a techniquement le droit PostgreSQL de
  modifier `quantite_stock` par un `UPDATE` direct (accordé avant que
  l'audit par `mouvements_stock` n'existe) — la future route devait
  explicitement l'exclure. Le périmètre complet (écrans + historique/
  exports + 2 points annexes) étant trop large pour un cycle honnête,
  découpage proposé et **validé explicitement par le propriétaire** :
  - **Cycle 11 (celui-ci)** : écran de stock (priorité 1), + les deux
    points annexes traités dans ce cycle même — refabrication du paquet
    Windows à la fin, correctif du seul constat n°1 de C4 (le n°2,
    trop lourd, reporté à son propre cycle).
  - **Cycle 12 (proposé, non démarré)** : historique des comptages et
    exports (priorité 2).
  - **Cycle de correction (proposé, non démarré)** : constat n°2 de C4.
- **Étape 4 — Mise en œuvre** : branche `cycle-11-ecran-stock`.
  - `db/migrations/015_articles_autre_site.sql` (+ inverse) : une fonction
    `SECURITY DEFINER`, `articles_autre_site()`, listant pour un agent
    stock les articles de l'AUTRE site (id/nom/unité/site seulement,
    jamais prix ni quantité) — pour le sélecteur de destination d'un
    transfert. Vérifiée par exécution directe avant tout code applicatif :
    agent du Magasin ne voit que « Clou 5 cm » (Comptoir), agent du
    Comptoir ne voit que les 3 articles du Magasin, responsable refusé au
    niveau du `GRANT` (il n'en a pas besoin, `GET /articles` lui montre
    déjà les deux sites).
  - `server/app/erreurs.py` (nouveau) : `erreur_metier()`, extrait de
    `stock.py` pour être partagé avec `articles.py` — un seul point de
    vérité pour traduire un refus métier de la base en 422 clair.
  - `server/app/routes/articles.py` : `POST /articles` intercepte
    désormais `ForeignKeyViolation` (correctif du **constat n°1**, trouvé
    au contrôle de boucle après le cycle 9) ; `PUT /articles/{id}`
    (nouveau) — modification par rôle (nom/catégorie/unité pour les deux ;
    + prix/fournisseur pour le responsable), **`quantite_stock` et
    `seuil_alerte` jamais acceptés, quel que soit le rôle**, malgré le
    risque latent trouvé à l'étape 3 ; chaque champ changé tracé dans
    `historique_modifications_articles`, un changement de prix en plus
    dans `historique_prix_articles` (première ligne réelle de ces deux
    tables depuis le cycle 1) ; `GET /articles/autre-site` (nouveau).
  - `maquette/stock.html` (nouveau) : câble les 6 opérations pour le
    responsable et l'agent stock (jamais l'agent comptabilité) — liste et
    recherche d'articles, un panneau unique par action (jamais deux
    formulaires ouverts en même temps, ergonomie mobile). Conçu 390 px
    d'abord, aucune largeur fixe au-delà de 1300 px (réutilise
    `.contenu`/`.tb-grille` déjà conformes depuis le cycle 1). Liens
    d'accès ajoutés au bandeau de `tableau-bord.html` et `inventaire.html`.
  - `maquette/api.js` : `fcfa()` déplacé depuis `donnees-simulees.js` (un
    utilitaire d'affichage partagé n'est pas une donnée simulée) —
    `stock.html` n'a besoin que d'`api.js`, jamais de `donnees-simulees.js`.
  - `maquette/verification/verifier-stock-reel.mjs` (nouveau) : les 6
    opérations exécutées réellement par un agent stock et un responsable,
    chaque montant de stock revérifié en base après chaque étape ; aucune
    occurrence de « FCFA » ni champ de prix dans la page ou les réponses
    réseau vues par l'agent stock (avant ET après les opérations) ; aucun
    bouton « Casse » pour lui ; captures aux 5 largeurs, cibles ≥ 44 px.
    **Piège trouvé en écrivant ce script** : un sélecteur Playwright
    `text=Transférer` matchait aussi le libellé « Quantité à transférer »
    — le premier match (le libellé, pas le bouton) était cliqué en
    silence, sans erreur ni effet ; corrigé en ciblant le dernier bouton
    du panneau plutôt qu'un texte non ancré.
  - `server/tests/test_articles.py` : +10 tests (modification par rôle,
    historique réellement écrit, refus propre d'un site/fournisseur
    invalide, sélection inter-site).
  - **Refabrication du paquet Windows** (les deux points annexes
    demandés) : `fabrication/quincaillerie_franck.spec` — aucun import
    caché supplémentaire nécessaire (`openpyxl`, `reportlab`, `pypdf`
    n'utilisent pas d'import dynamique qui échapperait à l'analyse
    statique de PyInstaller). Exécutable reconstruit et testé à froid
    dans un dossier isolé : démarrage, `/sante`, connexion, **et un
    export réel** (`GET /rapports/articles?format=xlsx`) pour prouver que
    les 3 dépendances du cycle 10 survivent à l'empaquetage — jamais
    vérifié depuis leur ajout, trois cycles plus tôt.
- **Vérification par exécution** :
  - `test_articles.py` : **15/15** (5 hérités + 10 nouveaux).
  - Suite pytest complète : **100/100**, 0 régression.
  - `db/tests/executer_tests.sh` (migrations 000 à 015) : protections
    **44/44**, habilitations **52/52**, concurrence **6/6**, réversibilité
    de la migration 015 confirmée.
  - `verifier-stock-reel.mjs` (nouveau) : **26/26**.
  - 0 régression sur les 4 suites Playwright existantes : `verifier-cablage.mjs`
    **76/76**, `verifier-vente-reelle.mjs` **10/10**,
    `verifier-inventaire-reel.mjs` **17/17**, `verifier-echappement-html.mjs`
    **11/11**.
  - Exécutable Windows : démarrage isolé, `/sante`, connexion et export
    Excel réel tous confirmés fonctionner dans le paquet fabriqué.
- **Documentation** : `server/README.md` (section C4 étendue),
  `server/tests/DERNIER_RESULTAT.md`, `db/README.md`, `db/tests/
  DERNIER_RESULTAT.md`, `maquette/verification/README.md`,
  `PERIMETRE_LIVRE.md` (2 lignes §3.8 corrigées : la modification par
  l'agent stock exclut désormais explicitement la quantité, l'historique
  de prix/modifications est réellement câblé pour la première fois),
  `loop-state.md`.
- **Score** : C4 **55 % → 68 %**. Commit, PR #12 sur `cycle-11-ecran-stock`,
  **fusionnée le 2026-09-13** sur instruction explicite du propriétaire
  (commit de fusion `4728683`, fast-forward, branche supprimée) après le
  contrôle de boucle ci-dessous.
- **Reste ouvert** : volumétrie/reprise du stock initial (point j),
  remises et conversion d'unités (point f, volet), le **constat n°2** de
  C4 (cohérence article/quantité d'un retour), export dédié pour C4,
  et le cycle 12 proposé (historique des comptages + exports, priorité 2) ;
  voir aussi le **constat n°3** du contrôle de boucle ci-dessous.

---

### Contrôle de boucle — après cycle 11, avant de démarrer le cycle 12 (2026-09-13, sans code)

Diagnostic par exécution, avant tout choix pour le cycle suivant. Le
propriétaire a demandé un bilan complet des 15 chantiers puis a validé
**Cycle 12 — écran pour C8** (déjà proposé au cycle 11).

- **Suites rejouées, toutes identiques au rapport du cycle 11** : suite
  pytest complète **100/100** ; `db/tests/executer_tests.sh` (base
  recréée de zéro, migrations 000 à 015) protections **44/44**,
  habilitations **52/52**, concurrence **6/6**, réversibilité confirmée ;
  les 5 suites Playwright **76/76**, **10/10**, **17/17**, **11/11**,
  **26/26**. **0 écart avec le rapport initial.**
- **Relecture du code comme un tiers, 1 constat trouvé par exécution,
  absent du rapport du cycle 11** : dans `PUT /articles/{id}`, la
  traçabilité d'un changement de prix (`historique_prix_articles`) ne
  vérifie PAS que le prix a réellement changé — contrairement à la boucle
  sur `nom`/`categorie`/`unite`/`fournisseur_id`, qui compare explicitement
  l'ancienne et la nouvelle valeur. Conséquence vérifiée par exécution :
  soumettre `{"prix_vente": 6500}` sur un article déjà à 6500 crée quand
  même une ligne d'historique « 6500,00 → 6500,00 ». **Plus grave qu'un
  cas limite** : `stock.html` pré-remplit toujours les champs de prix
  avec la valeur actuelle dans le panneau « Modifier » — un responsable
  qui corrige seulement le nom d'un article et valide déclenche cette
  fausse entrée à chaque fois, dans l'usage le plus ordinaire de l'écran.
  Aucun test ne couvre ce cas (les tests existants changent toujours
  réellement le prix).
- **Verdict** : un défaut de qualité de l'audit (une trace créée sans
  changement réel), jamais une fuite de rôle ou de site — **C4 n'est pas
  revu à la baisse**. Consigné comme **constat n°3**, à traiter avec le
  constat n°2 dans le même futur cycle de correction (les deux touchent
  `PUT /articles/{id}` et l'audit des articles).

---

### Cycle 12 — Écran de rapports : C8 — 2026-09-13

Quatrième cycle mené sous le processus corrigé en 4 étapes de `SKILL.md`.
Précédé d'une demande explicite du propriétaire : bilan complet des 15
chantiers (donné en pourcentage, avec preuve pour chacun) et plan
d'exécution hiérarchisé pour les cycles suivants — ce bilan est resté hors
du journal (donné directement en réponse), le propriétaire ayant ensuite
choisi l'option qu'il contenait.

- **Étape 1 — Diagnostic du cycle précédent (cycle 11, C4)** : voir
  « Contrôle de boucle — après cycle 11 » ci-dessus. Tout rejoué à
  l'identique (100/100 pytest, 44/44+52/52+6/6 SQL, 5 suites Playwright),
  1 constat trouvé (n°3, traçabilité de prix sans changement réel) —
  n'entame pas le score de C4, regroupé avec le constat n°2 pour un futur
  cycle de correction.
- **Étape 2 — Propositions** : une seule option, déjà retenue par le
  propriétaire dans le plan hiérarchisé qu'il avait demandé — Cycle 12,
  écran pour C8 (historique des comptages + exports), priorité 2 du
  découpage proposé au cycle 11.
- **Étape 3 — Objectif et plan** : donner une interface aux deux briques
  de C8 sans écran depuis le cycle 10, sans toucher au code serveur sauf
  découverte en cours de route. **Validé explicitement par le
  propriétaire** (« je valide »).
- **Étape 4 — Mise en œuvre** : branche `cycle-12-ecran-rapports`.
  - `maquette/api.js` : `appelApiBrut()` (nouveau, factorise la requête
    authentifiée et la traduction d'erreur, partagée par `appelApi()` et
    la nouveauté ci-dessous) ; `telechargerFichier()` (nouveau) — un
    `<a href>` nu ne peut pas porter le jeton de session, contournement
    par lecture de la réponse en `blob()` et clic simulé sur une ancre
    temporaire ; `fcfa()` inchangé.
  - `maquette/rapports.html` (nouveau) : trois sections gatées par rôle —
    historique des comptages (responsable, période choisie, tableau),
    export du catalogue (les 3 rôles, Excel/PDF), export des ventes
    (responsable, agent comptabilité, période + Excel/PDF). Aucune
    nouvelle route serveur nécessaire : les trois existaient et étaient
    déjà testées depuis le cycle 10.
  - Liens d'accès ajoutés au bandeau de `tableau-bord.html`, `stock.html`
    et `vente.html` (ce dernier n'avait jusqu'ici aucun lien vers un
    second écran, pour l'agent comptabilité).
  - **Régression trouvée et corrigée en écrivant ce cycle** : le lien
    ajouté au bandeau déjà chargé de `vente.html` (titre, badge de rôle,
    note du facturier papier) faisait déborder l'écran horizontalement à
    768 px — juste sous le seuil de retour à la ligne commun (719 px,
    `styles.css`), jamais atteint par les bandeaux plus courts des autres
    écrans. Trouvé par `verifier-cablage.mjs` (0 échec attendu, 1 obtenu),
    corrigé par un repli CSS scopé à cet écran seul (`.bandeau--vente`),
    sans toucher au seuil partagé.
  - `maquette/verification/verifier-rapports-reel.mjs` (nouveau) :
    historique filtré par période avec un vrai écart affiché (comptage
    semé à l'avance) ; sections visibles/absentes vérifiées pour les 3
    rôles ; **un clic sur un bouton d'export intercepte le vrai
    téléchargement de navigateur** (`page.waitForEvent("download")`) et
    relit les premiers octets du fichier obtenu (`PK` pour un `.xlsx`,
    `%PDF` pour un `.pdf`) — pas seulement un code HTTP 200 ; aucune
    occurrence de « FCFA » sur l'écran de l'agent stock ; captures aux
    5 largeurs.
- **Vérification par exécution** :
  - `verifier-rapports-reel.mjs` (nouveau) : **29/29**, réussi dès la
    première exécution complète (aucun aller-retour de débogage sur le
    script lui-même, contrairement au cycle 11).
  - Suite pytest complète : **100/100**, inchangée (aucune route serveur
    modifiée ce cycle).
  - 0 régression sur les 5 suites Playwright existantes une fois le
    débordement de `vente.html` corrigé : `verifier-cablage.mjs` **76/76**,
    `verifier-vente-reelle.mjs` **10/10**, `verifier-inventaire-reel.mjs`
    **17/17**, `verifier-echappement-html.mjs` **11/11**,
    `verifier-stock-reel.mjs` **26/26**.
  - Aucune migration à vérifier par exécution SQL directe (aucun
    changement de schéma) ; la suite `db/tests/executer_tests.sh` reste à
    l'état déjà revérifié pendant le diagnostic du cycle précédent.
- **Documentation** : `server/README.md` (section cycle 12 ajoutée sous
  C8), `maquette/verification/README.md`, `loop-state.md`.
- **Score** : C8 **45 % → 60 %**. Commit, PR sur `cycle-12-ecran-rapports`
  — **non fusionnée**, sur instruction du propriétaire.
- **Reste ouvert** : bascule vue consolidée/par site (pas d'écran),
  clôture de caisse (point g) et numéro de facturier (point c) non
  tranchés, absence persistante d'un test dédié au cloisonnement par site
  des exports (constat du contrôle de boucle après cycle 10, toujours pas
  traité), constats n°2 et n°3 de C4 (leur propre cycle de correction).

---

## Candidats pour un cycle ultérieur (non démarrés, choix laissé au propriétaire)

1. **Correction des constats n°2 et n°3 de C4** : n°2 (contrôle de boucle
   après cycle 9) — absence de vérification de cohérence article/quantité
   sur les retours client et fournisseur contre le document d'origine
   réellement référencé (`ventes_lignes`, quantité reçue), exige une
   nouvelle migration modifiant deux fonctions `SECURITY DEFINER` ; n°3
   (contrôle de boucle après cycle 11) — `PUT /articles/{id}` trace un
   changement de prix même sans changement réel, se déclenche dans l'usage
   ordinaire de l'écran (formulaire pré-rempli). Les deux touchent l'audit
   des articles, un travail de fond distinct de l'ergonomie d'écran.
2. **C6 (comptabilité/RH)**, hors clôture de caisse : reste entièrement à
   0 %, sans blocage connu par une décision non tranchée.
3. **Mesures humaines de `UX_BASELINE.md`** : ne nécessite aucun
   développement — un testeur humain, chronomètre en main, sur le serveur
   désormais câblé pour de vrai jusqu'au comptage d'inventaire (protocole
   exact au §1 bis). Lèverait le plafond de 60 % sur C9 et C10 si les
   résultats sont conformes. Peut se faire à tout moment, en parallèle d'un
   autre cycle.
4. **Test dédié au cloisonnement par site des exports** (constat du
   contrôle de boucle après cycle 10, toujours ouvert) : `test_rapports.py`
   ne teste pas explicitement que l'export d'un agent ne contient que son
   propre site — ça fonctionne (vérifié par exécution directe deux fois),
   mais ce n'est pas dans la suite automatisée.
5. **C3 (numéro facturier, addendum c)** ou **C6 (clôture de caisse,
   addendum g)** : nécessitent au préalable une décision du propriétaire,
   non tranchée à ce jour.
