# État du cycle de finalisation — Quincaillerie Franck

Référentiel fixe `C0`–`C14` — **ne jamais renuméroter**.
Cycle décrit dans `.agents/skills/finalisation-loop/SKILL.md`.

- Date d'initialisation : **2026-09-10**
- Dernier cycle fusionné : **Cycle 19 — reçu de vente imprimable, C5**,
  2026-09-13 (PR #21, fast-forward, commit `6b9acad`) ; précédé du
  **Cycle 18 — écran dédié RH, C6** (PR #20, fast-forward, commit
  `b5919ca`) et du **Cycle 17 — annulation de vente et régularisation
  d'écart, C5** (PR #19, fast-forward, commit `40c41a8`) — lot de 3 PR
  empilées (#20 sur #19, #21 sur #20), chacune retargée vers `main` avant
  fusion de sa base pendant qu'elle était encore ouverte (règle issue de
  l'incident de la PR #16, ci-dessous) : les trois fusions et suppressions
  de branche se sont enchaînées sans accroc. Précédé du
  **Cycle 15 — accès réseau local, C10** (PR #18 — réouverture propre de
  la PR #16, close automatiquement par GitHub après suppression de sa
  branche de base ; leçon retenue : ne plus supprimer une branche de base
  d'une PR empilée avant d'avoir retargé la suivante), du **Cycle 14 —
  test cloisonnement exports, C8** (PR #15, commit `d7e3f44`), du
  **Cycle 13 — correction des constats n°2 et n°3, C4** (PR #14, commit
  `d0c2ad5`), du **Cycle 12 — écran de rapports, C8** (PR #13, commit
  `75d461e`), du
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
| C4 | Articles et stock | **72 %** | Cycles 9, 11 et 13. Six opérations réelles, chacune une fonction PostgreSQL `SECURITY DEFINER`, toutes câblées sur un vrai écran (`maquette/stock.html`, cycle 11). **Constats n°2 et n°3 corrigés (cycle 13)** : un retour client ou fournisseur ne peut plus dépasser, en article et en quantité (cumul de plusieurs retours compris), ce que la vente ou la réception d'origine porte réellement (migration 016) ; `PUT /articles/{id}` ne trace plus de changement de prix dans `historique_prix_articles` quand le prix soumis est identique à l'actuel. `quantite_stock` volontairement jamais modifiable par fiche. **Aucun montant FCFA, aucun champ de prix n'atteint la page ni les réponses réseau de l'agent stock**. Vérifié par exécution : 104/104 tests pytest (100 + 4 nouveaux), suite SQL à jour (44/44, 52/52, 6/6, réversibilité de la migration 016 confirmée, vérifiée en SQL direct avant tout code Python), 6 suites Playwright — 0 régression (aucun écran touché par la correction). Manquent : volumétrie/reprise du stock initial (addendum j, non tranché), remises et conversion d'unités (addendum f, volet non tranché), export dédié à C4. |
| C5 | Ventes et facturation | **62 %** | Cycle 6, durci par le cycle de correction après C7, complété par les cycles 17 et 19. Décisions du propriétaire obtenues et appliquées (addendum, points b/d/e) : régime réel, TVA 19,25 % sur prix TTC, arrondi arithmétique sur le total ; une vente déjà encaissée n'est **jamais bloquée**, l'écart de stock est consigné et réservé au responsable ; crédit client explicitement désactivé. `POST /ventes` enregistre une vraie vente : décrément atomique anti-survente, une recette par vente, calcul de TVA faisant foi côté serveur. **Cycle 17** : `POST /ventes/{id}/annuler` (migration 017) restitue le stock RÉELLEMENT décrémenté, contre-passe la recette, régularise d'office l'écart devenu sans objet ; `POST /inventaire/ecarts-ventes/{id}/regulariser` marque un écart traité. Faille trouvée par exécution : `decrementer_stock_vente()` (cycle 6) ne renseignait jamais `mouvements_stock.vente_id`, corrigée dans la même migration. **Cycle 19** : `GET /ventes/{id}/recu` — reçu PDF (`reportlab`) téléchargeable depuis l'écran de vente (CDC §3.3/§7.1) ; n'affiche que ce qui est décidé (téléphone/n° contribuable omis tant que `a_definir`, aucun numéro de facturier fabriqué) ; une vente annulée porte une mention explicite. Vérifié par exécution : 24/24 tests pytest dédiés (140/140 au total, 0 régression), suite SQL à jour (44/44/52/52/6/6, réversibilité confirmée), 12/12 + 17/17 contrôles Playwright (dont un vrai téléchargement PDF intercepté après la vente). Manquent : n° facturier + vendeur obligatoires (addendum c, non tranché), ticket thermique / code-barres (non demandés), impression physique sur une imprimante réelle (non vérifiable par l'agent). |
| C6 | Comptabilité et RH | **55 %** | Cycle 16, complété au cycle 18. `transactions` (recette/dépense **hors vente**, historique filtrable par période), `employes`/`absences_conges`/`avances_salaire` (responsable seul, CDC §3.5) — tables et `GRANT` existant depuis les cycles 1/2, jamais exposés avant le cycle 16. `POST /transactions`, `POST/GET /rh/employes\|absences-conges\|avances-salaire`, `POST /rh/avances-salaire/{id}/rembourser`. La carte « Saisie rapide » de `tableau-bord.html` (simulée depuis le cycle 5) câble un vrai formulaire. **Cycle 18** : `maquette/rh.html`, écran dédié pour les trois routes RH (employés, absences/congés, avances sur salaire), lien ajouté au tableau de bord. **Correction d'une inexactitude du diagnostic d'origine** (cycle 16) : `transactions.vente_id` porte déjà un index unique partiel (`uq_transactions_recette_par_vente`, cycle 2) empêchant une double recette pour la même vente. Vérifié par exécution : 18/18 tests pytest dédiés (135/135 au total, 0 régression), `verifier-cablage.mjs` 77/77, `verifier-rh-reel.mjs` 21/21 (nouveau — employé/absence/avance créés depuis l'écran et retrouvés en base, remboursement réel). Manquent : clôture de caisse (point g, non tranché), contre-passation d'annulation, audit des corrections. |
| C7 | Inventaire et écarts | **50 %** | Cycle 7, durci par le cycle de correction qui a suivi. Comptage à l'aveugle câblé de bout en bout : `GET /inventaire/articles-a-compter` (liste sans aucune quantité, articles déjà comptés aujourd'hui exclus, `site_id` distingue les deux sites pour le responsable) et `POST /inventaire/comptages` (n'accepte que la quantité comptée, ne renvoie jamais l'écart ni la quantité attendue — figée et calculée par la base depuis le cycle 2, **y compris si le client les injecte lui-même dans la requête**). Faille trouvée et corrigée par exécution : l'agent stock pouvait lire `ecart`/`quantite_attendue` en SQL direct malgré la discipline applicative (`GRANT` sans restriction de colonne, migration 008) — colonnes retirées par la migration 012, comme pour les prix d'`articles`. Tableau de bord du responsable câblé sur `GET /inventaire/ecarts` (écarts de comptage) **et** `GET /inventaire/ecarts-ventes` (écarts de vente à découvert, chantier C5) — les deux étaient invisibles avant ce cycle. Vérifié par exécution : 11/11 tests pytest dédiés (55/55 au total, 0 régression), 17/17 contrôles Playwright bout-en-bout (`verifier-inventaire-reel.mjs`) dont le contrôle le plus critique repris du cycle 5 — quantité attendue absente de la page/réseau/code source même après un comptage produisant un écart réel — et une double soumission (panne réseau simulée) qui n'immobilise plus l'agent. **+5 points (cycle de correction)** : fuseau horaire de la base fixé à Africa/Douala à deux niveaux indépendants (base et application) au lieu d'hériter d'un réglage faux ; écarts affichés au tableau de bord sans construire le HTML par concaténation non échappée, vérifié par un essai d'injection réel (11/11, `verifier-echappement-html.mjs`). Manquent : régularisation d'un écart, plafond de vraisemblance, historique au-delà du jour courant, export/rapport. |
| C8 | Tableaux de bord et rapports | **62 %** | Cycles 10, 12 et 14. Alertes de stock, historique des comptages et deux exports Excel/PDF, tous câblés sur un vrai écran (`maquette/rapports.html`, cycle 12). **Gating du prix par rôle posé en SQL**, prouvé en relisant le contenu réel du fichier produit pour les 3 rôles au niveau API (cycle 10) et par un vrai téléchargement de navigateur intercepté depuis l'écran (cycle 12). **Cycle 14** : le cloisonnement par site des deux exports (déjà vérifié deux fois par exécution directe, jamais couvert par un test) a désormais 2 tests dédiés dans `test_rapports.py` — un agent stock du Magasin n'exporte aucun article du Comptoir, un agent comptabilité du Magasin n'exporte aucune vente du Comptoir. Vérifié par exécution : 106/106 pytest (104 + 2 nouveaux), aucun écran ni migration touchés. Manquent : bascule vue consolidée/par site (les données portent déjà `site_id`, la bascule elle-même n'a pas d'écran), clôture de caisse (point g, non tranché), numéro de facturier (point c, non tranché — `numero_facture` restitué tel quel). |
| C9 | Ergonomie et UI *(priorité 1)* | **50 %** | Cycle 5. Les 4 écrans ne sont plus une maquette isolée : connexion réelle (`POST /auth/connexion`), jeton, `GET /articles`, `GET /ventes/synthese-jour`, servis par le noyau serveur sous `/app` (même origine). Vérifié par exécution (`verifier-cablage.mjs`, 73/73) : les 3 rôles reçoivent réellement des réponses différentes (aucun prix pour l'agent stock, aucune quantité pour le comptable), la quantité attendue d'un comptage n'apparaît nulle part (page, réseau, code source), messages d'erreur toujours en français près du champ, cibles ≥ 44 px conservées, 36/36 tests serveur toujours au vert. Ce qui n'a pas de route métier encore décidée (validation de vente, alertes stock, écarts d'inventaire, liste à compter) reste **explicitement** simulé à l'écran plutôt qu'inventé. **Toujours plafonné à 60 %** : le tableau de mesures humaines de `UX_BASELINE.md` §4 reste vide (vitesse, compréhension des erreurs par une personne non formée, confort sur téléphone physique). |
| C10 | Mobile et API web *(priorité 1)* | **38 %** | Cycle 5, complété au cycle 15. Les deux écrans mobile-first sont **la même application web**, testée à 360/390/768 px. **Cycle 15** : trouvé par exécution — le serveur (dev ET paquet Windows) n'écoutait que sur `127.0.0.1`, **injoignable depuis n'importe quel autre appareil**, téléphone compris, même sur le même réseau. Corrigé (`--host 0.0.0.0` en dev, `server/fabrication/lanceur.py` pour le paquet, qui affiche désormais sa propre adresse réseau locale à l'utilisateur). Vérifié par exécution, dev et paquet Windows reconstruit : requête réelle vers l'adresse réseau locale de la machine (pas `127.0.0.1`) répondant correctement sur `/sante` et `/app/connexion.html`. **Non fermé** : la preuve manquante reste un **véritable téléphone physique** — ce que l'agent n'a pas — la couche réseau est prouvée, pas le rendu sur un vrai appareil. Reste aussi : API dédiée si un jour distincte de l'appli web, usage hors ligne, notifications. |
| C11 | Sécurité applicative | **55 %** | Cycle 3. Le « Sécurité : 100 % » du diagnostic d'origine était un artefact (mots-clés trouvés dans le script de diagnostic lui-même) — désormais vérifié réellement : démarrage refuse `postgres` et toute clé d'exemple, requêtes systématiquement paramétrées (injection SQL testée), jetons signés HMAC vérifiés à temps constant, aucun hachage ne fuit dans aucune réponse (vérifié par expression régulière), erreurs SQL jamais renvoyées telles quelles au client. Reste : révocation de session, limiteur de débit partagé (multi-processus), audit de sécurité plus large (dépendances, en-têtes HTTP, TLS — hors périmètre local de dev). |
| C12 | Sauvegarde et exploitation | **0 %** | Diagnostic : « Backup and restore procedure : Not found ». Aucun script, aucune procédure. Onduleur, RPO/RTO, mise à jour des postes : à définir (addendum i). |
| C13 | Tests automatisés et qualité | **55 %** | Cycle 20 — correction d'une inexactitude du diagnostic d'origine (comme pour C6 au cycle 16) : le score restait à 0 % alors que **140 tests pytest**, une **suite SQL complète** (44+52+6 contrôles + réversibilité) et **7 suites Playwright** (193 contrôles) existent et sont rejouées à chaque cycle qui touche le code correspondant — jamais reflété dans le score. `db/outils/verifier_tout.sh` (nouveau) enchaîne les trois couches en une seule commande, vérifié par exécution (exit code 0, 0 échec). Deux pièges trouvés en l'écrivant : la limite de connexion de `config.ini` (10/min) fait échouer les suites en cascade au-delà de la première ; l'étape de réversibilité SQL recrée `qf_app` sans mot de passe. Manquent : CI automatisée sur chaque push (`server/tests/conftest.py` appelle un chemin Windows en dur, non portable vers un runner Linux sans correction dédiée — chantier à part), couverture des parcours nécessitant une imprimante ou un téléphone réels. |
| C14 | Documentation et livrables | **40 %** | Évalué sur pièces. Documentation d'usage/recette solide : CDC détaillé, 2 guides testeur, dossier de recette, guide d'installation. `MODELE_DONNEES.md`, `PERIMETRE_LIVRE.md`, `ADDENDUM_CAHIER_DES_CHARGES.md` produits dans ce cycle. Manquent (CDC §7) : code source, scripts de fabrication des exécutables, scripts + guide de sauvegarde/restauration. |

**Moyenne indicative après le cycle 20 : ≈ 53 %** (C0 55, C1 80, C2 65, C3 60, C4 72, C5 62, C6 55, C7 50, C8 62, C9 50, C10 38, C11 55, C13 55, C14 40, C12 0).
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
- **Score** : C8 **45 % → 60 %**. Commit, PR #13 sur `cycle-12-ecran-rapports`,
  **fusionnée le 2026-09-13** sur instruction explicite du propriétaire
  (commit de fusion `75d461e`, fast-forward, branche supprimée) après le
  contrôle de boucle ci-dessous.
- **Reste ouvert** : bascule vue consolidée/par site (pas d'écran),
  clôture de caisse (point g) et numéro de facturier (point c) non
  tranchés, absence persistante d'un test dédié au cloisonnement par site
  des exports (constat du contrôle de boucle après cycle 10, toujours pas
  traité), constats n°2 et n°3 de C4 (leur propre cycle de correction).

---

### Contrôle de boucle — après cycle 12, avant la correction des constats de C4 (2026-09-13, sans code)

Diagnostic par exécution, avant tout choix pour le cycle suivant. Le
propriétaire a demandé un bilan complet des 15 chantiers et un plan
hiérarchisé (donnés directement en réponse, hors journal), puis a validé
la fusion de la PR #13 et le lancement, en séquence, de plusieurs cycles
du plan — en commençant par la correction des constats n°2 et n°3 de C4.

- **Suites rejouées, toutes identiques au rapport du cycle 12** : suite
  pytest complète **100/100** ; `db/tests/executer_tests.sh` (base
  recréée de zéro) protections **44/44**, habilitations **52/52**,
  concurrence **6/6**, réversibilité confirmée ; les 6 suites Playwright
  **76/76**, **10/10**, **17/17**, **11/11**, **26/26**, **29/29**. **0
  écart avec le rapport initial.**
- **Relecture du code comme un tiers, aucun nouveau constat** : essai
  spécifique d'une période inversée (`date_debut` postérieure à
  `date_fin`) sur l'historique des comptages ET sur l'export des ventes
  depuis l'écran réel — les deux affichent le message d'erreur du serveur
  correctement, en français, près du bon champ. Rien à signaler sur
  `telechargerFichier()`/`appelApiBrut()` (cycle 12) ni sur le repli CSS
  `.bandeau--vente`.
- **Verdict** : aucune régression, aucune faille. Cycle 12 tient sans
  réserve supplémentaire.

---

### Cycle 13 — Correction des constats n°2 et n°3 : C4 — 2026-09-13

Cinquième cycle mené sous le processus corrigé en 4 étapes de `SKILL.md`.
Validé par le propriétaire dans le même message que la fusion de la
PR #13, avec une planification explicite pour la suite : « ensuite la
fusion et la planification suivante sur l'exécution de 2 ou 3 chantiers
en même temps » — voir la note de clarification donnée avant ce cycle
(SKILL.md interdit qu'un cycle traite plus d'un chantier ; la demande est
donc traitée comme un carnet de cycles validés, exécutés l'un après
l'autre, chacun avec son diagnostic et son point d'arrêt).

- **Étape 1 — Diagnostic du cycle précédent (cycle 12, C8)** : voir
  « Contrôle de boucle — après cycle 12 » ci-dessus. Tout rejoué à
  l'identique (100/100 pytest, 44/44+52/52+6/6 SQL, 6 suites Playwright),
  essai spécifique d'une période inversée sur l'écran réel : aucun
  nouveau constat.
- **Étape 2 — Propositions** : une seule option, déjà retenue par le
  propriétaire — correction des constats n°2 (contrôle de boucle après
  le cycle 9) et n°3 (contrôle de boucle après le cycle 11) de C4.
- **Étape 3 — Objectif et plan** : fermer les deux failles d'audit sans
  toucher à aucun écran. **Validé explicitement par le propriétaire**
  (« je valide tout »).
- **Étape 4 — Mise en œuvre** : branche `cycle-13-correction-c4`.
  - `db/migrations/016_retours_coherence_document_origine.sql`
    (+ inverse) : `enregistrer_retour_client()` refuse désormais un
    article qui ne fait pas partie de la vente référencée
    (`ventes_lignes`), et refuse un retour qui dépasserait — cumul des
    retours déjà faits contre CETTE vente précise compris — la quantité
    réellement vendue. `enregistrer_retour_fournisseur()` refuse de même
    un retour qui dépasserait — cumul compris — la quantité réellement
    reçue par CE mouvement de réception précis. Vérifié en SQL direct
    avant tout code Python (comme la migration 014) : retour exact
    accepté, un de plus refusé, deuxième retour cumulé qui dépasse après
    un premier retour valide refusé, article non vendu dans la vente
    indiquée refusé — pour le client comme pour le fournisseur ; les
    vérifications préexistantes (site, existence, nature du mouvement,
    stock suffisant) revérifiées intactes après réordonnancement des
    contrôles dans `enregistrer_retour_fournisseur()`.
  - `server/app/routes/articles.py` : la condition d'écriture dans
    `historique_prix_articles` compare désormais réellement l'ancien et
    le nouveau prix — en `float` des deux côtés (l'ancien est un
    `Decimal` lu en base, le nouveau un `float` Pydantic ; comparer leurs
    représentations en chaîne les aurait distingués à tort, contrairement
    au motif `str(...) != str(...)` déjà utilisé pour les autres champs).
  - `server/tests/test_stock.py` : +3 tests (article non vendu dans la
    vente, quantité cumulée dépassée côté client, côté fournisseur).
    `server/tests/test_articles.py` : +1 test (aucune ligne d'historique
    pour un prix identique, un vrai changement reste tracé).
- **Vérification par exécution** :
  - `test_stock.py` + `test_articles.py` : **32/32** (28 hérités + 4
    nouveaux dans ces deux fichiers).
  - Suite pytest complète : **104/104**, 0 régression.
  - `db/tests/executer_tests.sh` (migrations 000 à 016) : protections
    **44/44**, habilitations **52/52**, concurrence **6/6**, réversibilité
    de la migration 016 confirmée (aucune trace résiduelle au-delà des 2
    écarts déjà documentés et pré-existants).
  - 0 régression sur les 6 suites Playwright existantes (aucun écran
    touché ce cycle) : **76/76**, **10/10**, **17/17**, **11/11**,
    **26/26**, **29/29**.
- **Documentation** : `db/README.md` (migration 016), `server/README.md`
  (section cycle 13 sous C4), `server/tests/DERNIER_RESULTAT.md`,
  `db/tests/DERNIER_RESULTAT.md`, `loop-state.md`.
- **Score** : C4 **68 % → 72 %**. Commit, PR sur `cycle-13-correction-c4`
  — **non fusionnée**, sur instruction du propriétaire (fusion à
  confirmer dans le bilan qui suit, comme demandé).
- **Reste ouvert** : points j et f (volet remises/unités) toujours non
  tranchés, aucun export dédié à C4. Les points 2, 4 et 5 du plan
  hiérarchisé restent à traiter (C6 hors clôture de caisse, test dédié au
  cloisonnement par site des exports, décisions du propriétaire).

---

### Cycle 14 — Test dédié au cloisonnement par site des exports : C8 — 2026-09-13

Premier des 3 chantiers d'un lot exécuté en cycles rapprochés, à la
demande explicite du propriétaire (« planification suivante sur
l'exécution de 2 ou 3 chantiers en même temps ») après le bilan complet
donné après le cycle 13. Les 3 chantiers du lot sont **indépendants**
(fichiers disjoints, aucun ne nécessite de migration) et chacun garde son
propre diagnostic, sa propre branche, sa propre PR — SKILL.md continue
d'exiger qu'une PR ne traite qu'un seul chantier ; c'est le rythme entre
les cycles qui est resserré, pas leur contenu.

- **Diagnostic** : le cycle 13 venait d'être vérifié par exécution
  quelques minutes avant (104/104 pytest, suite SQL, 6 suites Playwright)
  — non rejoué une seconde fois sans rien de nouveau entre les deux.
- **Objectif** : combler le seul manque de couverture resté ouvert depuis
  le contrôle de boucle après le cycle 10 — le cloisonnement par site des
  exports fonctionne (RLS du cycle 2), vérifié deux fois par exécution
  directe, mais jamais par un test automatisé.
- **Mise en œuvre** : branche `cycle-14-test-cloisonnement-exports`.
  `server/tests/test_rapports.py` : +2 tests —
  `test_export_articles_agent_stock_limite_a_son_site` (un agent stock du
  Magasin n'exporte aucun article du Comptoir),
  `test_export_ventes_agent_comptabilite_limite_a_son_site` (une vente du
  Comptoir, créée exprès pour le test, n'apparaît jamais dans l'export
  d'un agent comptabilité du Magasin).
- **Vérification** : `test_rapports.py` **13/13** (11 hérités + 2
  nouveaux). Suite pytest complète : **106/106**, 0 régression. Aucune
  migration ni écran touchés — les 6 suites Playwright et la suite SQL ne
  peuvent pas être affectées, non rejouées pour ce chantier précis.
- **Score** : C8 **60 % → 62 %**.
- **Documentation** : `loop-state.md` uniquement (pas de section dédiée
  dans `server/README.md`, le changement est un simple ajout de tests).

---

### Cycle 15 — Accès réseau local pour C10 — 2026-09-13

Deuxième chantier du lot. **Précision assumée dès le plan** : l'agent n'a
pas de téléphone physique — ce cycle prouve la couche réseau, pas le
rendu sur un vrai appareil, et le dit sans détour dans le score.

- **Objectif** : lever le blocage technique trouvé en creusant le retard
  de C10 — le serveur n'écoutait que sur `127.0.0.1`.
- **Mise en œuvre** : branche `cycle-15-c10-acces-lan`.
  - `server/fabrication/lanceur.py` : sépare l'adresse d'ÉCOUTE
    (`HOTE_ECOUTE = "0.0.0.0"`, toutes les interfaces réseau) de l'adresse
    ouverte dans le navigateur LOCAL (`HOTE = "127.0.0.1"`, inchangée) —
    une même constante servait aux deux avant ce cycle, ce qui rendait
    l'une des deux forcément fausse. `_adresse_lan()` (nouveau) : découvre
    l'adresse IPv4 locale de la machine par l'astuce du socket UDP non
    connecté (aucune donnée réellement envoyée), affichée au démarrage
    avec l'URL à donner à un téléphone et un rappel sur le pare-feu
    Windows (profil réseau, autorisation entrante).
  - `server/README.md` : section dédiée, `--host 0.0.0.0` ajouté à la
    commande de lancement documentée.
- **Vérification par exécution** :
  - Serveur de développement lancé avec `--host 0.0.0.0` : `curl` depuis
    la même machine vers sa propre adresse réseau locale (`10.204.63.36`,
    pas `127.0.0.1`) répond correctement sur `/sante` **et**
    `/app/connexion.html` (200) — la maquette est bien servie, pas
    seulement l'API.
  - `lanceur.py` exécuté directement : le message affiché donne la bonne
    adresse et le bon port ; la même vérification `curl` réussit sur
    l'URL exacte affichée.
  - **Paquet Windows reconstruit** (`construire.ps1`) et testé à froid
    dans un dossier isolé : le message d'adresse réseau s'affiche, le
    serveur écoute bien sur `0.0.0.0` (confirmé dans les journaux
    `uvicorn`), `curl` vers l'adresse réseau locale répond sur `/sante`.
  - Aucun test pytest n'exerçait `lanceur.py` (aucun avant, aucun après) ;
    import du module vérifié sain. Suite pytest complète non rejouée :
    aucun fichier qu'elle couvre n'a changé.
- **Score** : C10 **30 % → 38 %** — une preuve partielle et honnête, pas
  un chantier fermé.
- **Reste ouvert** : la vérification depuis un **vrai téléphone physique**
  reste entièrement à faire par le propriétaire ou un testeur ; API
  dédiée, usage hors ligne, notifications.

---

### Cycle 16 — Comptabilité et RH : C6 — 2026-09-13

Troisième et dernier chantier du lot validé après le cycle 13.

- **Objectif** : rendre réelles la saisie de recette/dépense et la
  gestion RH, sur des tables prêtes depuis les cycles 1/2, sans inventer
  la clôture de caisse (point g, non tranché).
- **Mise en œuvre** : branche `cycle-16-c6-comptabilite-rh`.
  - `server/app/routes/transactions.py` (nouveau) : `POST`/`GET
    /transactions` — recette/dépense **hors vente** (une vente crée déjà
    sa propre recette), historique filtrable par période, site venant de
    la RLS (`p_transactions_site`, cycle 1) pour la liste, du même
    principe que les autres routes (session ou paramètre pour un
    responsable) pour la création.
  - `server/app/routes/rh.py` (nouveau, **responsable seul**, CDC §3.5) :
    `POST`/`GET /rh/employes`, `/rh/absences-conges`,
    `/rh/avances-salaire`, et `POST /rh/avances-salaire/{id}/rembourser`
    (marque un remboursement, jamais l'inverse).
  - `maquette/tableau-bord.html` : la carte « Saisie rapide »
    (recette/dépense), simulée depuis le cycle 5, câble désormais un vrai
    formulaire vers `POST /transactions`.
  - `verifier-cablage.mjs` : +1 contrôle — une recette réellement
    enregistrée depuis l'écran, retrouvée en base après validation.
  - **Correction d'une inexactitude du diagnostic d'origine**, trouvée en
    lisant le schéma avant de coder : `transactions.vente_id` porte déjà
    un index unique partiel (`uq_transactions_recette_par_vente`, cycle 2)
    empêchant une double recette pour la même vente — le score de départ
    listait ça comme un manque ; ce n'en était pas un.
  - `server/tests/test_transactions.py` (8) et `server/tests/test_rh.py`
    (10).
- **Vérification par exécution** :
  - `test_transactions.py` + `test_rh.py` : **18/18**.
  - Suite pytest complète : **124/124**, 0 régression.
  - `verifier-cablage.mjs` : **77/77** (76 + 1 nouveau).
  - 0 régression sur les 5 autres suites Playwright : **10/10**, **17/17**,
    **11/11**, **26/26**, **29/29**.
  - Aucune migration : les 4 tables et leurs `GRANT` existaient déjà.
- **Score** : C6 **0 % → 45 %**.
- **Reste ouvert** : clôture de caisse (point g), écran dédié pour la RH
  (API + tests seulement ce cycle, comme C4 au cycle 9), contre-passation
  d'annulation, audit des corrections.

---

### Cycle 17 — Annulation de vente, régularisation d'écart : C5 — 2026-09-13

Premier des trois nouveaux chantiers lancés après la fusion du lot de 3
(cycles 14-16) et le diagnostic complet rejoué (pytest 124/124, suite SQL
44/44/52/52/6/6, 6 suites Playwright — 0 régression, voir contrôle de
boucle ci-après).

- **Objectif** : compléter deux mécanismes déjà **décidés** mais jamais
  finis — l'annulation d'une vente (CDC §3.3, mécanique de statut posée
  depuis la migration 005, cycle 2, mais rien ne restituait le stock ni ne
  contre-passait la recette) et la régularisation d'un écart de vente à
  découvert (`ecarts_stock_ventes.regularise` posé depuis le cycle 6, sans
  qu'aucune fonction ne l'ait jamais fait passer à `TRUE`). Aucune règle
  métier nouvelle inventée — les deux complètent une trace déjà tranchée
  par le propriétaire.
- **Mise en œuvre** : branche `cycle-17-c5-annulation-regularisation`.
  - `db/migrations/017_annulation_vente_regularisation_ecart.sql` (+
    inverse) : `annuler_vente()` (restitue le stock réellement décrémenté,
    contre-passe la recette par une dépense, régularise d'office l'écart
    devenu sans objet) et `regulariser_ecart_vente()` — toutes deux
    `SECURITY DEFINER`, réservées à `qf_responsable`.
  - `server/app/routes/ventes.py` : `POST /ventes/{vente_id}/annuler`.
  - `server/app/routes/inventaire.py` : `POST
    /inventaire/ecarts-ventes/{ecart_id}/regulariser`.
  - `maquette/tableau-bord.html` : la carte « Écarts de stock (ventes) »
    (réelle depuis le cycle 8) gagne un bouton « Régulariser » par ligne
    non régularisée.
  - `server/tests/test_ventes.py` (6) et `server/tests/test_inventaire.py`
    (5) — 11 nouveaux tests.
- **Faille trouvée par exécution en écrivant ce cycle, avant tout code
  Python** : `decrementer_stock_vente()` (cycle 6) recevait bien
  `p_vente_id` en paramètre mais ne l'écrivait **jamais** dans
  `mouvements_stock.vente_id` — seul un motif texte (« vente #123 »)
  portait ce lien, jamais une vraie clé étrangère. Sans correction,
  `annuler_vente()` n'aurait rien trouvé à restituer pour aucune vente
  réelle. Corrigée dans la migration 017 même (`CREATE OR REPLACE`,
  comportement inchangé sinon) ; colonne laissée NULLABLE pour la
  catégorie « vente » — aucun moyen fiable de reconstruire ce lien pour
  les mouvements d'avant ce cycle.
- **Vérification par exécution** :
  - Migration 017 vérifiée en SQL direct (annulation normale, annulation
    à découvert restituant EXACTEMENT le stock réel et non la quantité
    facturée, double annulation refusée, motif blanc refusé,
    régularisation refusée si déjà faite, permissions par rôle) avant tout
    code Python.
  - `test_ventes.py` + `test_inventaire.py` : **11/11** nouveaux.
  - Suite pytest complète : **135/135**, 0 régression.
  - Suite SQL rejouée à jour (000 à 017) : **44/44** protections, **52/52**
    habilitations, **6/6** concurrence, réversibilité de la migration 017
    confirmée.
  - 6 suites Playwright rejouées sans régression : `cablage` **77/77**,
    `inventaire` **17/17** (le bouton « Régulariser » apparaît bien dans la
    ligne rendue), `vente` **10/10**, `stock` **26/26**, `rapports`
    **29/29**, `echappement` **11/11** (nom d'article malveillant toujours
    échappé avec le bouton ajouté).
  - **Piège rencontré et corrigé en cours de route** : le mot de passe du
    rôle `qf_app` sur l'instance PostgreSQL locale ne correspondait plus à
    `server/config.ini` (`ALTER ROLE ... WITH PASSWORD` corrigé — mot de
    passe de développement local, jamais un secret réel, voir
    `db/README.md`) ; la base `quincaillerie_test` doit être reconstruite
    à la main (schéma d'origine + migrations + jeu d'essai) après le passage
    de `db/tests/executer_tests.sh`, qui la supprime délibérément à l'étape
    7 (comparaison de réversibilité).
- **Documentation** : `db/README.md` (ligne migration 017),
  `db/tests/DERNIER_RESULTAT.md`, `server/README.md` (section C5 étendue),
  `server/tests/DERNIER_RESULTAT.md`, `loop-state.md`.
- **Score** : C5 **43 % → 55 %**. Commit, PR #19 sur
  `cycle-17-c5-annulation-regularisation`, **fusionnée le 2026-09-13**
  sur instruction explicite du propriétaire (commit de fusion `40c41a8`,
  fast-forward, branche supprimée).
- **Reste ouvert** : n° facturier + vendeur obligatoires (addendum point
  c, non tranché — objectif anti-vol volontairement incomplet), documents
  imprimés (ticket/facture), régularisation des écarts de COMPTAGE
  (`comptages_stock`, distincts des écarts de vente traités ici —
  volontairement pas touchés, inventer un mécanisme de correction de
  quantité y serait une règle métier nouvelle, non demandée).

---

### Cycle 18 — Écran dédié pour la RH : C6 — 2026-09-13

Deuxième des trois nouveaux chantiers, repris directement du candidat n°2
listé après le cycle 16 : les routes RH existaient depuis le cycle 16
sans aucune interface.

- **Objectif** : donner un écran au responsable pour `employes`,
  `absences_conges` et `avances_salaire` (CDC §3.5), sans inventer aucune
  route ni migration.
- **Mise en œuvre** : branche `cycle-18-c6-ecran-rh`, ouverte depuis
  `cycle-17-c5-annulation-regularisation` (PR empilée — voir la leçon
  retenue après la PR #16 : le retargage vers `main` se fera à la fusion
  de la PR #19, jamais avant).
  - `maquette/rh.html` (nouveau) : trois cartes (Employés,
    Absences/congés, Avances sur salaire), un panneau unique partagé pour
    les trois formulaires (même principe que `stock.html`, cycle 11).
  - `maquette/tableau-bord.html` : lien « Ressources humaines » ajouté au
    bandeau (responsable seul).
  - `maquette/verification/verifier-rh-reel.mjs` (nouveau) : accès refusé
    aux deux rôles agents, mise en page aux 5 largeurs, employé/absence/
    avance créés depuis l'écran et retrouvés réellement en base,
    remboursement d'avance réel (bouton disparaît ensuite).
- **Piège rencontré et corrigé** : le 3e lien de navigation faisait
  déborder le bandeau partagé de `tableau-bord.html` entre 720px et
  ~820px (la règle générique de `styles.css` ne repasse en colonne qu'en
  dessous de 719px) — corrigé par un `<style>` scopé à cet écran, sans
  toucher au seuil partagé des autres écrans.
- **Vérification par exécution** :
  - `verifier-rh-reel.mjs` : **21/21**, nouveau.
  - `verifier-cablage.mjs` rejoué après la correction du bandeau :
    **77/77**, 0 régression.
  - `verifier-echappement-html.mjs` rejoué (tableau-bord.html touché) :
    **11/11**, 0 régression.
  - Suite pytest complète inchangée : **135/135** (aucun code serveur
    touché ce cycle).
- **Documentation** : `server/README.md` (section C6 étendue),
  `server/tests/DERNIER_RESULTAT.md`, `PERIMETRE_LIVRE.md` (3 lignes
  §3.12 passées de « Spécifié » à « Confirmé (test) »), `loop-state.md`.
- **Score** : C6 **45 % → 55 %**. Commit, PR #20 sur `cycle-18-c6-ecran-rh`,
  **fusionnée le 2026-09-13** sur instruction explicite du propriétaire
  (commit de fusion `b5919ca`, fast-forward, branche supprimée).
- **Reste ouvert** : clôture de caisse (point g, non tranché),
  contre-passation d'annulation, audit des corrections.

---

### Cycle 19 — Reçu de vente imprimable : C5 — 2026-09-13

Troisième et dernier des trois chantiers de ce lot.

- **Objectif** : CDC §3.3/§7.1, « imprimer / réimprimer le reçu » — un PDF
  téléchargeable depuis l'écran de vente, sans inventer le numéro de
  facturier (point c, non tranché) ni les mentions légales non décidées
  (téléphone, n° contribuable — point d).
- **Mise en œuvre** : branche `cycle-19-c5-recu-vente-pdf`, ouverte depuis
  `cycle-18-c6-ecran-rh` (empilée comme les deux précédentes — `ventes.py`
  porte déjà la route d'annulation du cycle 17, une vraie dépendance de
  code, pas seulement de discipline « une PR par chantier »).
  - `server/app/routes/ventes.py` : `GET /ventes/{vente_id}/recu`, mêmes
    rôles que `POST /ventes`. PDF A4 (`reportlab`, comme
    `/rapports/*`, cycle 10) — nom/ville/téléphone/contribuable de la
    boutique (les deux derniers omis tant que `a_definir`), n° de vente,
    date, mode de paiement, lignes, TVA, total. Une vente annulée porte
    une mention rouge explicite + motif.
  - Texte non fixe (paramètres de boutique, motif d'annulation) échappé
    (`xml.sax.saxutils.escape`) avant d'entrer dans un `Paragraph`
    reportlab, qui interprète un sous-ensemble XML — même discipline que
    l'échappement HTML des écrans.
  - `maquette/vente.html` : bouton « Imprimer le reçu » après chaque
    vente réussie (`telechargerFichier()`), masqué à nouveau dès la vente
    suivante.
  - `server/tests/test_ventes.py` (5 nouveaux) ; `conftest.py` : compte
    de test `comptoir.compta` ajouté (mot de passe dédié) pour prouver le
    cloisonnement par site, jusqu'ici inutilisé dans la suite.
  - `verifier-vente-reelle.mjs` étendu (+2) : un vrai téléchargement PDF
    intercepté après la vente, pas seulement la présence du bouton.
- **Vérification par exécution** :
  - `test_ventes.py` (reçu) : **5/5** nouveaux.
  - Suite pytest complète : **140/140**, 0 régression.
  - `verifier-vente-reelle.mjs` : **12/12** (10 + 2 nouveaux).
  - `verifier-cablage.mjs` (77/77) et `verifier-echappement-html.mjs`
    (11/11) rejoués : 0 régression.
- **Documentation** : `server/README.md` (section C5 étendue),
  `server/tests/DERNIER_RESULTAT.md`, `PERIMETRE_LIVRE.md` (section 3.15
  « Impression » mise à jour honnêtement : PDF confirmé par test, mais
  format A4 — pas un ticket thermique — et aucun code-barres),
  `loop-state.md`.
- **Score** : C5 **55 % → 62 %**. Commit, PR #21 sur
  `cycle-19-c5-recu-vente-pdf`, **fusionnée le 2026-09-13** sur
  instruction explicite du propriétaire (commit de fusion `6b9acad`,
  fast-forward, branche supprimée).
- **Reste ouvert** : n° facturier + vendeur obligatoires (point c, non
  tranché), impression physique sur une imprimante réelle (non
  vérifiable par l'agent), ticket thermique / code-barres (non demandés
  explicitement, non ajoutés).

---

### Cycle 20 — Correction du diagnostic C13 + suite de vérification unifiée — 2026-09-13

Premier des quatre chantiers choisis par le propriétaire pour ce nouveau
lot (C12, C11, C8, C13) — traité en premier car il ne touche aucun code
applicatif, juste la documentation et l'outillage de test.

- **Constat** : le score C13 (« Tests automatisés et qualité ») restait à
  **0 %** dans le tableau depuis l'initialisation du projet — évalué
  uniquement sur le diagnostic d'ORIGINE (« aucune suite exécutable »).
  C'était déjà faux dès le cycle 2 : **140 tests pytest, une suite SQL
  complète (44+52+6 contrôles + réversibilité), et 7 suites Playwright
  (193 contrôles)** existent et sont rejoués à chaque cycle qui touche le
  code qu'ils couvrent — jamais reflété dans le score. Aggravé par un vrai
  trou documentaire trouvé en creusant : `maquette/verification/
  DERNIER_RESULTAT.md` n'avait plus été mis à jour depuis le **cycle 5**
  (2026-09-12), silencieux sur 6 suites entières écrites depuis.
- **Mise en œuvre** : branche `cycle-20-c13-suite-verification-unifiee`.
  - `db/outils/verifier_tout.sh` (nouveau) : enchaîne, en une seule
    commande, la suite SQL, la suite pytest, puis 7 des 8 suites
    Playwright (toutes sauf `affichage`/`flux`, qui exigent un second
    serveur **statique** séparé, jamais automatisé) contre un serveur
    temporaire — jusqu'ici, cet enchaînement se faisait à la main,
    cycle après cycle, jamais écrit nulle part comme UNE procédure.
  - `maquette/verification/DERNIER_RESULTAT.md` : section « État actuel »
    ajoutée en tête, récapitulant les 7 suites vivantes et leur dernier
    résultat connu, sans réécrire l'historique existant.
  - `db/README.md` : section dédiée à la nouvelle commande unique.
- **Deux pièges trouvés EN ÉCRIVANT ce script, avant de le considérer
  fini** :
  1. `config.ini` de dev limite à 10 connexions/minute (anti-force-brute,
     `securite.py`) — largement dépassé en enchaînant 7 suites qui se
     reconnectent chacune plusieurs fois en quelques minutes ; les suites
     suivant la première échouaient TOUTES avec une session nulle, sans
     aucun message explicite. Corrigé par une copie **temporaire** de
     `config.ini` (limite relevée à 1000/min, comme `conftest.py` pour
     pytest), jamais le vrai fichier.
  2. L'étape 7 de la suite SQL (réversibilité) `DROP` puis recrée les
     rôles applicatifs — **globaux au serveur**, pas propres à une base —
     et `qf_app` retrouve un mot de passe VIDE après recréation
     (`CREATE ROLE ... LOGIN`, sans `PASSWORD`). Sans correction, pytest
     ET Playwright échouent en cascade juste après, pour une raison
     invisible dans leurs propres messages (« authentification
     refusée »). Corrigé : le mot de passe (relu dans `config.ini`, jamais
     dupliqué en dur) est reposé après reconstruction de la base — exactement
     le piège qui m'avait forcé à une correction manuelle identique en
     tout début du cycle 17, jamais consigné comme un problème récurrent
     jusqu'à devoir l'automatiser ici.
- **Vérification par exécution** : `bash db/outils/verifier_tout.sh`
  rejoué en entier, propre, **exit code 0** — suite SQL (44/44 + 52/52 +
  6/6 + réversibilité), pytest **140/140**, 7 suites Playwright
  **193/193** (77+12+17+26+29+11+21). Base laissée dans l'état du jeu
  d'essai à la fin.
- **Documentation** : `db/README.md`, `maquette/verification/
  DERNIER_RESULTAT.md`, `loop-state.md`.
- **Score** : C13 **0 % → 55 %** — corrige une inexactitude du diagnostic
  d'origine (comme pour C6 au cycle 16), ne prétend pas à un chiffre plus
  haut : rien de nouveau n'a été TESTÉ ce cycle, seule la trace existante
  a été consolidée et outillée d'une commande unique.
- **Reste ouvert** : **CI automatisée sur chaque push/PR** (mentionnée de
  longue date comme un manque de C0) — délibérément **pas** tentée ce
  cycle : `server/tests/conftest.py` appelle un chemin Windows en dur
  (`_pgdev/pgsql/bin/psql.exe`) pour recharger le jeu d'essai entre deux
  tests, ce qui rend la suite non portable telle quelle vers un runner
  Linux sans une correction dédiée (rendre ce chemin résolu par variable
  d'environnement, avec repli sur `psql` du `PATH`) — un vrai chantier en
  soi, pas glissé ici sans validation séparée. Couverture manuelle des
  parcours nécessitant une vraie imprimante ou un vrai téléphone,
  toujours hors de portée de l'agent.

---

## Candidats pour un cycle ultérieur (non démarrés, choix laissé au propriétaire)

Le lot de 3 chantiers validé après le cycle 13 (cycles 14, 15, 16) est
terminé et fusionné (PR #15, #18, #17 — voir la note sur la PR #16, close
automatiquement lors de l'empilage, dans l'en-tête de ce document). Le lot
de 3 chantiers suivant (cycles 17, 18, 19 — annulation/régularisation C5,
écran RH C6, reçu de vente PDF C5) est **terminé et fusionné** (PR
#19/#20/#21, empilées dans l'ordre — retargées vers `main` avant chaque
fusion de leur base pendant qu'elles étaient encore ouvertes, comme la
leçon de la PR #16 le prescrit ; les trois fusions et suppressions de
branche se sont enchaînées sans accroc cette fois).

1. **Vérification C10 depuis un vrai téléphone physique** : la couche
   réseau est prouvée (cycle 15) — reste la dernière étape, qui doit être
   faite par le propriétaire ou un testeur muni d'un téléphone.
2. **Mesures humaines de `UX_BASELINE.md`** : ne nécessite aucun
   développement — un testeur humain, chronomètre en main, sur le serveur
   désormais câblé pour de vrai jusqu'au comptage d'inventaire (protocole
   exact au §1 bis). Lèverait le plafond de 60 % sur C9 et C10 si les
   résultats sont conformes. **Ne peut pas être exécuté par l'agent**
   (mesure humaine).
3. **C3 (numéro facturier, addendum c)** ou **C6 (clôture de caisse,
   addendum g)** : nécessitent au préalable une décision du propriétaire,
   non tranchée à ce jour. **Ne peut pas être tranché par l'agent** —
   décision métier, comme les points h, i et l évoqués dans le bilan
   donné après le cycle 12.
