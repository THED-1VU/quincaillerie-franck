# État du cycle de finalisation — Akuma (Ets Quincaillerie Franck)

Référentiel fixe `C0`–`C14` — **ne jamais renuméroter**.
Cycle décrit dans `.agents/skills/finalisation-loop/SKILL.md`.

- Date d'initialisation : **2026-09-10**
- Dernier cycle fusionné : **Cycle 33 — rangement : clôture de
  cycle-29-hygiene-inventaire + CI GitHub Actions minimale** (PR #38,
  rebase, 2026-09-20). Précédé des **Cycles 31/32 — C0-C premier compte
  responsable + C2 gestion des comptes** (PR #33 et #36, rebase), du
  **Cycle 30 — C0-A : l'exécutable ouvre l'écran de connexion** (PR #31)
  et de la **Documentation : décision du 2026-09-20 sur la gestion des
  comptes** (PR #32), 2026-09-20. Précédé des
  **Cycles 24/25/26 — travail en parallèle, trois
  pistes simultanées** (voir `RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`),
  2026-09-14 → 2026-09-18 : **Cycle 24 — piste UX, corrections
  `UX_BASELINE.md` §4 bis, C9/C10** (PR #28, fusionnée en premier —
  branche `piste-ux-corrections`), **Cycle 25 — piste C6, clôture de
  caisse par site, addendum point g** (PR #27 — branche
  `piste-c6-comptabilite-rh`, rebasée sur `main` après la fusion de la
  PR #28, conflits résolus sur 3 fichiers d'infrastructure de test
  partagés — voir note ci-dessous), **Cycle 26 — piste C12, automatisation
  et durcissement de la sauvegarde, addendum point i** (PR #26 — branche
  `piste-c12-sauvegarde`, rebasée sur `main` après la fusion de la PR #27,
  2 fichiers en conflit résolus). Les trois PR ont été fusionnées dans
  l'ordre décidé à l'avance (UX → C6 → C12), chacune rebasée sur `main`
  juste avant sa fusion, jamais deux fusions en même temps. **Chaque
  fusion a été revérifiée par ré-exécution réelle par la session qui
  fusionne**, pas seulement en relisant le rapport de la piste : base
  reconstruite depuis zéro (schéma + migrations 000→019 + jeu d'essai),
  suite pytest complète rejouée (163/163 à chaque étape — dépôt principal
  compris, base `quincaillerie_test`), 9 suites Playwright rejouées
  (`cablage` 87/87, `caisse` 24/24, `echappement` 11/11, `vente` 12/12,
  `inventaire` 17/17, `stock` 26/26, `rapports` 29/29, `rh` 21/21,
  `ux-corrections` 27/27 — nouveau), route `GET /exploitation/derniere-
  sauvegarde` et sauvegarde réelle de C12 revérifiées par requêtes HTTP
  directes après la fusion. Voir le détail complet, diagnostic et preuves
  de chaque piste dans `RAPPORT AVANCEMENT/cycles/piste-ux.md`,
  `piste-c6.md`, `piste-c12.md`. Précédé du
  **Cycle 23 — bascule vue consolidée/site, C8**,
  2026-09-13 (PR #25, fast-forward, commit `87603d4`) ; précédé du
  **Cycle 22 — sécurité applicative, C11** (PR #24, commit `58d3845`), du
  **Cycle 21 — sauvegarde et restauration, C12** (PR #23, commit
  `debd7b5`) et du **Cycle 20 — correction diagnostic C13, C13** (PR #22,
  commit `9a466a6`) — lot de 4 PR empilées (#23 sur #22, #24 sur #23, #25
  sur #24), chacune retargée vers `main` avant fusion de sa base pendant
  qu'elle était encore ouverte (même règle que pour le lot précédent) :
  les quatre fusions et suppressions de branche se sont enchaînées sans
  accroc. Précédé du **Cycle 19 — reçu de vente imprimable, C5**,
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
| C0 | Infrastructure et dépôt | **70 %** | Cycle 4. `server/fabrication/` : `QuincaillerieFranck.exe` produit par PyInstaller (`construire.ps1`, un humain n'a besoin d'aucune connaissance de PyInstaller), 17,9 Mo, autonome. **Vérifié par exécution depuis un dossier totalement isolé du dépôt** : démarrage, config chargée, `/sante` répond, connexion + hachage bcrypt + jeton fonctionnent — aucune dépendance Python résiduelle. Garde-fous C11 (refus `postgres`, refus clé d'exemple) confirmés survivre à l'empaquetage. **Cycle 30 (correctif C0-A, 2026-09-20)** : l'exécutable ouvre désormais l'écran de connexion réel et non plus `/docs` — `CHEMIN_A_OUVRIR = "/app/connexion.html"` (`lanceur.py`), la maquette est embarquée dans le paquet (`quincaillerie_franck.spec`, section `datas` — seuls les fichiers servis, jamais les artefacts de test) et `main.py` la résout en mode figé via `sys._MEIPASS`. **Prouvé par exécution réelle** : `Akuma.exe` reconstruit (26,4 Mo) et lancé — le navigateur ouvert charge `/app/connexion.html` en 200 (journal : 200 sur connexion.html, theme.css, styles.css, akuma-logo.png, api.js, favicon.ico) ; avant correctif, ce même chemin répondait 404 et `/docs` 200. **Cycle 31 (C0-C, 2026-09-20)** : outil de création du **premier compte responsable** livré — migration 023 (`creer_premier_responsable()`, `SECURITY DEFINER`, réservée à `qf_app`, hache elle-même le mot de passe en bcrypt `$2a$` 12 tours, refuse si un responsable existe déjà, trace `journal_comptes`) + `db/outils/creer_compte_responsable.ps1` (console, mot de passe masqué, lecture `config.ini`, mode de vérification automatisée par variables d'environnement). **Prouvé par exécution réelle** : base vierge `quincaillerie_c0c` reconstruite (schéma d'origine + migrations 000-023) — le script a créé le compte `premier.resp` (id 1, hash `$2a$12$`, actif, changement imposé), un second appel a été refusé (« Un compte responsable existe déjà »), la connexion réelle via `verifier_connexion()` a répondu `ok=t` (et `ok=f` pour un mauvais mot de passe) ; 7/7 tests pytest dédiés. **Cycle 33 (2026-09-20)** : **CI GitHub Actions minimale livrée** (`.github/workflows/ci.yml`) — service `postgres:17` mappé sur 127.0.0.1:5433, schéma d'origine + migrations + jeu d'essai rejoués, suite pytest complète exécutée sur chaque push/PR vers `main` ; premier « vert/rouge » réel sur GitHub. Reste : **mode kiosque (plein écran), lockfile figé avec hachages** — tous deux ouverts, chacun son chantier. |
| C1 | Base de données et intégrité | **87 %** | Cycle 2. 9 migrations numérotées (`db/migrations/`) + inverses, appliquées et annulées par exécution réelle sur PostgreSQL 17.11. Corrigés et **prouvés** : contraintes de domaine, cohérence inter-tables, **écart d'inventaire calculé par la base** (et quantité attendue figée par déclencheur), historique non effaçable (`RESTRICT` + verrous de suppression + suppression logique), journaux de connexion et de comptes, annulation tracée et irréversible, table de paramètres avec sentinelle « à décider », index de recherche, **4 rôles non superutilisateurs à privilèges par colonne** + RLS par site. **100 contrôles, 0 échec** (`db/tests/DERNIER_RESULTAT.md` — figé au cycle 2, obsolète : compte réel aujourd'hui 50/53/4, voir `db/tests/executer_tests.sh`). Reste : crédit client (point b, décidé le 2026-09-19, non construit — le plus gros levier restant), décisions métier (points d q3, g), reprise sur une base contenant de vraies données. **Cycle 35 (13b, 2026-09-21)** : une fiche, un stock par site — table `stocks_sites` (PK article+site), `site_id` explicite sur mouvements/comptages/écarts, FK `ventes_lignes(article, site) → stocks_sites`, migrations 026-031 + inverses, suite SQL 000-031 verte. **Cycle 39 (point f, sous-chantier 1, 2026-09-22)** : quantités décimales par article — colonnes de quantité `INTEGER` → `NUMERIC(12,3)` (`stocks_sites`, `mouvements_stock`, `comptages_stock`, `ventes_lignes`, `ecarts_stock_ventes`), 4 déclencheurs de garde au niveau base (refuse une décimale si l'article ne l'autorise pas — testé en contournant l'API), migration 034 + inverse (réversibilité prouvée, refuse bruyamment si des données décimales réelles existent plutôt que d'arrondir en silence). |
| C2 | Authentification et comptes | **77 %**  **Cycle 38 (2026-09-22)** : durée de session DÉCIDÉE en base (8 h / 480 min — plus `a_definir`), lue à chaque connexion via `duree_session_minutes_decidee()` (`SECURITY DEFINER`, repli config.ini) ; réinitialisation du mot de passe d'un agent par le responsable : route `PATCH /admin/comptes/{id}/mot-de-passe` + bouton dans `comptes.html`, mot de passe saisi (>= 8 caractères) jamais restitué, changement forcé à la première connexion, trace dans `journal_comptes`, refuse un compte responsable. Prouvé : pytest 224/224 (6 dédiés), suite SQL 000-033 + inverses verte, Playwright comptes 13/13 et câblage 94/94. Reste : limiteur de débit partagé (C11). | Cycle 3. Noyau serveur (`server/`, FastAPI) : connexion via `verifier_connexion()` (fonction PostgreSQL `SECURITY DEFINER`, migration 009, seule à lire le hachage, jamais restitué) ; verrouillage après 5 échecs, déverrouillage réservé au responsable, obligation de changement à la première connexion, libre-service limité à sa propre ligne, limitation de débit ; révocation de session (cycle 21). **Cycle 32 (gestion des comptes, 2026-09-20)** : routes `/admin/comptes` (GET liste, POST création d'un agent stock/comptabilité avec site obligatoire, PATCH actif) réservées au responsable, écran `maquette/comptes.html` ; règles du propriétaire : auto-désactivation refusée, dernier responsable actif protégé, session d'un compte désactivé **coupée immédiatement** (migration 024 `compte_est_actif()` vérifiée par `deps.obtenir_session` à chaque requête) ; le hachage n'est jamais lu ni restitué. **Prouvé par exécution** : 10/10 tests pytest dédiés (liste sans hash, création + connexion réelle du nouveau compte, refus doublon / mot de passe court / rôle responsable / site invalide, désactivation → session 401 immédiate → réactivation → connexion OK, auto-désactivation refusée), suite Playwright `verifier-comptes-reel.mjs` **21/21**, `verifier-cablage.mjs` **94/94** (lien Comptes ajouté au bandeau), suite SQL complète (migrations 000-024 + inverses) OK, suite pytest complète **200/200**.
| C3 | Habilitations et cloisonnement des rôles | **72 %** | Cycle 3, **rôle caissier (addendum point h) vérifié au cycle 27** : diagnostic par exécution réelle, aucun code nécessaire — `qf_agent_comptabilite` remplit déjà les deux fonctions décidées le 2026-09-13 (encaisse ET saisit) : `POST /ventes` l'autorise déjà, `vente.html` est son écran d'accueil par défaut. **Correction d'une inexactitude du diagnostic d'origine** (même esprit que C6/C13) : le cloisonnement RH **est** déjà testé par une route (`GET /rh/employes` avec un jeton `agent_comptabilite` → 403, `server/tests/test_rh.py`), contrairement à ce que ce tableau affirmait. Fournisseurs : pas un vrai manque — la table n'a pas de `site_id` (partagée entre les deux sites par construction) et aucune route `/fournisseurs` n'existe (`404` vérifié). Habilitations appliquées **au niveau des requêtes SQL** : privilèges par colonne + RLS par site posés au cycle 2, exploités par `BaseDeDonnees.connexion_pour()`. Prouvé par exécution en **contournant l'API** : `SELECT ... WHERE site_id=2` sous `qf_agent_stock` renvoie 0 ligne même en le demandant explicitement (`server/tests/test_cloisonnement_site.py`). Reste ouvert : question 3 de l'addendum h (le caissier voit-il le détail des prix ou seulement le total ?, non tranchée), pas d'écran dédié à un profil « caissier » distinct de `vente.html`. **Cycle 35 (13b)** : RLS/GRANT révisés — catalogue commun aux deux sites (politique permissive sur `articles`), quantité cloisonnée sur `stocks_sites` (RLS par site, aucune écriture directe pour aucun rôle), comptage à l'aveugle avec `site_id` ; prouvé en SQL direct hors API (`test_cloisonnement_site.py`) et par `verifier-cablage.mjs` 94/94. |
| C4 | Articles et stock | **83 %** | Cycles 9, 11 et 13. Six opérations réelles, chacune une fonction PostgreSQL `SECURITY DEFINER`, toutes câblées sur un vrai écran (`maquette/stock.html`, cycle 11). **Constats n°2 et n°3 corrigés (cycle 13)** : un retour client ou fournisseur ne peut plus dépasser, en article et en quantité (cumul de plusieurs retours compris), ce que la vente ou la réception d'origine porte réellement (migration 016) ; `PUT /articles/{id}` ne trace plus de changement de prix dans `historique_prix_articles` quand le prix soumis est identique à l'actuel. `quantite_stock` volontairement jamais modifiable par fiche. **Aucun montant FCFA, aucun champ de prix n'atteint la page ni les réponses réseau de l'agent stock**. Vérifié par exécution : 104/104 tests pytest (100 + 4 nouveaux), suite SQL à jour (44/44, 52/52, 6/6, réversibilité de la migration 016 confirmée, vérifiée en SQL direct avant tout code Python), 6 suites Playwright — 0 régression (aucun écran touché par la correction). Manquent : volumétrie/reprise du stock initial (addendum j, non tranché côté code — décidé le 2026-09-19, débloqué par le cycle 35), export dédié à C4, remises et article offert (point f, sous-chantiers 3-4, non construits). **Cycle 35 (13b)** : modèle multi-site livré — `enregistrer_entree_stock` ouvre la ligne du site (première réception), `transferer_stock` = UN article + deux sites (ligne de destination créée), casse/retours sur (article, site), `annuler_vente` restitue par site ; écran `stock.html` adapté ; `verifier-stock-reel.mjs` 26/26, `test_stock.py` 16/16. **Cycle 39 (point f, sous-chantier 1, 2026-09-22)** : quantités décimales par article — `articles.quantite_decimale_autorisee`, les 6 fonctions de stock réécrites en `NUMERIC(12,3)` (mêmes règles, mêmes verrous), `GET/POST/PUT /articles` exposent et acceptent le nouveau champ. **Prouvé par exécution** : suite SQL 000-034 + inverses verte (5 contrôles dédiés : refus/acceptation/non-arrondi), pytest 224/224, `verifier-cablage.mjs` 94/94. **Reste (point f)** : écran non câblé (case à cocher sur la fiche article, `stock.html`) ; retours enrichis (issue échange/avoir/remboursement), remises (par ligne/vente, seuil `a_definir`) et article offert (sous-chantiers 2 à 4 du plan, non commencés). |
| C5 | Ventes et facturation | **72 %** | Cycle 6, durci par le cycle de correction après C7, complété par les cycles 17, 19 et **27** (addendum point c, décidé le 2026-09-13). **Cycle 27, périmètre volontairement réduit au socle décidé** (`db/migrations/020_facturier_vendeur.sql`) : `numero_facturier` (référence du carnet PAPIER, transcrite par le comptable — jamais générée par le logiciel, préfixe `MAG-`/`CPT-` vérifié par site) et `vendeur_id` (qui a négocié le prix, distinct de qui saisit/encaisse) obligatoires sur toute nouvelle vente ; nouvelle route `GET /ventes/vendeurs` (comptes actifs du site + responsable) pour le menu déroulant de l'écran ; affiché sur le reçu PDF et dans l'export `/rapports/ventes`. **PAS construits ce cycle** (questions non tranchées à l'époque) : rapport « écarts de prix par vendeur » et son seuil de validation (question 5), liste de vendeurs sans compte (question 3). **Question 5 tranchée le 2026-09-18** : seuil de 10 % sous le prix catalogue, en configuration, signale sans jamais bloquer (voir `ADDENDUM_CAHIER_DES_CHARGES.md`, point c) — **le rapport lui-même reste à construire** (chantier non démarré), toujours retenu par la question 3 (vendeur sans compte), encore ouverte. Décisions antérieures (points b/d/e) inchangées : régime réel, TVA 19,25 % sur prix TTC, une vente déjà encaissée n'est jamais bloquée, crédit client désactivé. `POST /ventes/{id}/annuler` (cycle 17), `GET /ventes/{id}/recu` (cycle 19, PDF). Vérifié par exécution : 33/33 tests pytest dédiés à C5 (172/172 au total, 9 nouveaux pour le point c), suite SQL à jour, 12/12 + 94/94 + 27/27 contrôles Playwright (vente, câblage, corrections UX — tous rejoués avec le nouveau formulaire). Manquent : rapport d'écarts de prix par vendeur (seuil désormais connu, question 3 encore ouverte), vendeurs sans compte, ticket thermique/code-barres (non demandés), impression physique sur une imprimante réelle (non vérifiable par l'agent). |
| C6 | Comptabilité et RH | **85 %** | Cycle 16, complété au cycle 18, puis au **cycle 25** (piste C6, travail en parallèle, addendum point g). `transactions` (recette/dépense **hors vente**, historique filtrable par période), `employes`/`absences_conges`/`avances_salaire` (responsable seul, CDC §3.5). **Cycle 25** : clôture de caisse **par site** (décision du 2026-09-13) — migration 019, table `clotures_caisse` **totalement immuable** (`UPDATE`/`DELETE` refusés même pour `postgres` en direct), seul point d'écriture `cloturer_caisse()` (`SECURITY DEFINER`, aucun `GRANT` même au responsable), attendu calculé serveur (`calculer_attendu_caisse()`, exclut le crédit client), écart calculé serveur, clôture rectificative tracée en cas d'erreur. Seuil de tolérance d'écart (`seuil_ecart_caisse_tolere`) amorcé à `a_definir` (question 5 non tranchée) : tolérance **nulle** appliquée tant que le propriétaire ne fixe pas de valeur — pas de chiffre inventé, mécanique déjà prête pour le jour où il le fera. Écran dédié `maquette/cloture-caisse.html` (aperçu de l'attendu avant saisie, historique). Vérifié par exécution, **rejoué intégralement par la session qui fusionne** (pas seulement le rapport de la piste) : 163/163 tests pytest (144 + 19 dédiés à la caisse), `verifier-cablage.mjs` 87/87, `verifier-rh-reel.mjs` 21/21, `verifier-caisse-reel.mjs` 24/24 (SQL direct et API réelle : refus d'écart sans commentaire, acceptation avec commentaire, clôture rectificative, cloisonnement par rôle prouvé aux deux niveaux — 403 API + `InsufficientPrivilege` SQL). Manquent : lien depuis `tableau-bord.html` (réservé à la piste UX ce tour, maintenant fusionnée — reste à câbler), fond de caisse initial (question 2, absent du modèle, sous-estime l'attendu en espèces s'il en existe un réellement), rattachement d'une vente saisie en retard (question 3), rapprochement Mobile Money exact (question 4), seuil d'écart à fixer par le propriétaire (question 5), blocage d'une saisie après clôture (question 6), rôle caissier (point h, chantier C3 séparé). |
| C7 | Inventaire et écarts | **60 %** | Cycle 7, durci par le cycle de correction qui a suivi. Comptage à l'aveugle câblé de bout en bout : `GET /inventaire/articles-a-compter` (liste sans aucune quantité, articles déjà comptés aujourd'hui exclus, `site_id` distingue les deux sites pour le responsable) et `POST /inventaire/comptages` (n'accepte que la quantité comptée, ne renvoie jamais l'écart ni la quantité attendue — figée et calculée par la base depuis le cycle 2, **y compris si le client les injecte lui-même dans la requête**). Faille trouvée et corrigée par exécution : l'agent stock pouvait lire `ecart`/`quantite_attendue` en SQL direct malgré la discipline applicative (`GRANT` sans restriction de colonne, migration 008) — colonnes retirées par la migration 012, comme pour les prix d'`articles`. Tableau de bord du responsable câblé sur `GET /inventaire/ecarts` (écarts de comptage) **et** `GET /inventaire/ecarts-ventes` (écarts de vente à découvert, chantier C5) — les deux étaient invisibles avant ce cycle. Vérifié par exécution : 11/11 tests pytest dédiés (55/55 au total, 0 régression), 17/17 contrôles Playwright bout-en-bout (`verifier-inventaire-reel.mjs`) dont le contrôle le plus critique repris du cycle 5 — quantité attendue absente de la page/réseau/code source même après un comptage produisant un écart réel — et une double soumission (panne réseau simulée) qui n'immobilise plus l'agent. **+5 points (cycle de correction)** : fuseau horaire de la base fixé à Africa/Douala à deux niveaux indépendants (base et application) au lieu d'hériter d'un réglage faux ; écarts affichés au tableau de bord sans construire le HTML par concaténation non échappée, vérifié par un essai d'injection réel (11/11, `verifier-echappement-html.mjs`). Manquent : régularisation d'un écart, plafond de vraisemblance, historique au-delà du jour courant, export/rapport. **Cycle 35 (13b)** : comptage par (article, site) — un même article peut être compté le même jour une fois par site (index unique révisé), `articles-a-compter` liste les fiches ayant un stock au site de l'appelant, écarts/historique lisent `comptages.site_id` ; `verifier-inventaire-reel.mjs` 17/17.  **Cycle 36 (2026-09-22)** : régularisation d'un écart de comptage livrée — 4 types de résolution (erreur_de_comptage, retrouve, vol_presume, casse_deja_enregistree), motif obligatoire sauf erreur_de_comptage, traçabilité PURE (jamais d'effet sur le stock, décision propriétaire), migration 032 + route + bouton « Régulariser » au tableau de bord ; plafond de vraisemblance mécanisé (paramètre `a_definir` — aucun blocage tant que le propriétaire ne fixe pas). Prouvé : pytest 218/218, suite SQL 000-032 verte, Playwright inventaire 17/17 et câblage 94/94. Reste : valeur du plafond à fixer par le propriétaire. |
| C8 | Tableaux de bord et rapports | **72 %** | Cycles 10, 12, 14 et 23. Alertes de stock, historique des comptages et deux exports Excel/PDF, tous câblés sur un vrai écran (`maquette/rapports.html`, cycle 12). **Gating du prix par rôle posé en SQL**, prouvé en relisant le contenu réel du fichier produit pour les 3 rôles au niveau API (cycle 10) et par un vrai téléchargement de navigateur intercepté depuis l'écran (cycle 12). **Cycle 14** : cloisonnement par site des exports, 2 tests dédiés. **Cycle 23** : bascule vue consolidée/par site sur `tableau-bord.html` — chaque route renvoyait déjà `site_id` par ligne, la bascule est un filtre purement d'affichage (aucune route ni migration nouvelle, aucun appel réseau au changement de vue). Vérifié par exécution : `verifier-cablage.mjs` +7 (87/87) — filtrer sur un site recalcule le total exactement (8 500 / 3 200 FCFA) et fait disparaître l'autre site de chaque carte, retour à « Les deux sites » retrouve le total consolidé identique (11 700 FCFA). Manquent : clôture de caisse (point g, non tranché), numéro de facturier (point c, non tranché — `numero_facture` restitué tel quel). **Cycle 35 (13b)** : alertes de stock par (article, site) sur `stocks_sites`, exports du catalogue par rôle (responsable : une ligne par article+site ; agent stock : quantité de son site ; comptabilité : sans quantité) ; `verifier-rapports-reel.mjs` 29/29. |
| C9 | Ergonomie et UI *(priorité 1)* | **60 %** | Cycle 5, réévalué à la baisse le 2026-09-13 par la première campagne humaine réelle, puis **à la hausse au cycle 24** (piste UX, travail en parallèle) : 4 des 6 constats de cette catégorie corrigés et **vérifiés par exécution réelle** — UX-1 (ajouter un article en ≤ 2 actions **quelle que soit la quantité**, un nombre en tête de la recherche fixe la quantité dès l'ajout), UX-2 (vente entière au clavier seul **avec un prix négocié**, nouveau raccourci `F3`), UX-9 (le prix affiché en gris précise désormais explicitement « indicatif », « PAS le prix qui sera facturé »), UX-10 (avertissement toujours visible : un comptage validé est définitif, sans dialogue bloquant supplémentaire). Rejoué par la session qui fusionne : `verifier-ux-corrections.mjs` 27/27, aucune régression sur les 8 suites existantes. **Cycle 37 (2026-09-22)** : UX-8 (bouton de retrait du panier introuvable seul, ~20 s de recherche) — cause trouvée : `.panier__sup` (`maquette/vente.html`) n'avait fond/bordure **qu'au survol** (`:hover`), invisible au doigt sur téléphone. Fond et bordure de couleur d'alerte rendus **permanents** (`maquette/styles.css`), `title` ajouté en complément de l'`aria-label` déjà présent ; prouvé par `verifier-cablage.mjs` 94/94 + `verifier-vente-reelle.mjs` 12/12 (0 régression) et un relevé Playwright dédié (style calculé au repos passé de transparent à un fond/bordure visibles, clic toujours fonctionnel). **Reste ouvert** : UX-0 (le désaccord de méthode lui-même — pire des 3 essais vs 3ᵉ essai — reste à trancher par le propriétaire, aucun code n'y répond ; méthodologie tranchée le 2026-09-19, campagne elle-même non lancée). **Important : l'objectif chronométré principal (vente de 3 articles < 60 s, pire des 3 essais) n'a PAS été re-mesuré avec un vrai testeur humain**, et la discoverabilité réelle du bouton de retrait (UX-8) non plus — seules des frictions structurelles ont été supprimées et prouvées par exécution automatisée réelle (Playwright + backend réel), pas par une campagne humaine. Une deuxième campagne réelle reste nécessaire avant de considérer C9 proche de 100 %. |
| C10 | Mobile et API web *(priorité 1)* | **58 %** | Cycle 5, complété au cycle 15, réévalué à la hausse le 2026-09-13 par la première campagne sur un vrai téléphone physique, puis **de nouveau à la hausse au cycle 24** (piste UX, travail en parallèle) : 3 des 5 constats mobiles corrigés et vérifiés par exécution réelle — UX-3 (débordement du tableau de bord : cause CSS identifiée et corrigée — `grid-template-columns` sans `minmax(0, ...)` laissait un contenu long, non couvert par le jeu d'essai de test, pousser la grille hors écran ; 0 px de débordement mesuré aux 5 largeurs avec un nom d'article réellement long et non sécable), UX-4 (taille de police minimale garantie sur les chiffres des cartes, mesurée ≥ 16px à 360/390px), UX-7 — **le plus sérieux constat de la campagne** — (coupure réseau en cours de requête : `AbortController` à 20 s autour de `fetch()`, message français affiché, formulaire réutilisable sans recharger la page). UX-6 (clavier numérique) était en réalité **déjà correct** à l'inspection (`type="number"` + `inputmode="numeric"` déjà posés) — pas un vrai défaut, confirmé par lecture directe du DOM rendu. **Honnêteté conservée sur UX-3/4** : l'identité exacte du téléphone/navigateur du testeur original n'a jamais été renseignée ; un facteur non reproductible propre à cet appareil n'est pas formellement exclu comme cause additionnelle — seule la cause CSS a pu être diagnostiquée et corrigée par exécution. **Cycle 36 (2026-09-22)** : UX-5 (saisie d'une recette au téléphone, 1 min 02 mesuré contre un objectif de 45 s) — cause structurelle probable corrigée : la carte « Saisie rapide » de `tableau-bord.html`, 5e sur 7 sous 3 listes de longueur variable, est remontée en tête **uniquement sous 700px** (`order: -1`, DOM inchangé, PC de caisse non affecté) ; prouvé par `verifier-cablage.mjs` 94/94 et un relevé Playwright dédié (ordre visuel confirmé aux deux largeurs). **La cible < 45 s elle-même reste à reconfirmer par un vrai testeur humain** — ce n'est pas une nouvelle mesure humaine, seulement une friction structurelle plausible supprimée. Une deuxième campagne sur un vrai téléphone physique reste nécessaire pour confirmer UX-3/4/5 dans les conditions réelles d'origine. Reste aussi : API dédiée si un jour distincte de l'appli web, usage hors ligne, notifications. |
| C11 | Sécurité applicative | **68 %** | Cycle 3, complété au cycle 22. Le « Sécurité : 100 % » du diagnostic d'origine était un artefact (mots-clés trouvés dans le script de diagnostic lui-même) — désormais vérifié réellement : démarrage refuse `postgres` et toute clé d'exemple, requêtes systématiquement paramétrées (injection SQL testée), jetons signés HMAC vérifiés à temps constant, aucun hachage ne fuit dans aucune réponse, erreurs SQL jamais renvoyées telles quelles au client. **Cycle 22** : révocation de session (migration 018, `POST /auth/deconnexion`, `deps.obtenir_session()` vérifie la révocation à chaque requête — un jeton révoqué signature-valide et non expiré est quand même refusé, prouvé en le rejouant après déconnexion) ; en-têtes HTTP de sécurité (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) sur toute réponse. Vérifié par exécution : 4/4 tests pytest dédiés (144/144 au total, 0 régression, coût mesuré ~13 % de temps d'exécution en plus), `verifier-cablage.mjs` +3 (80/80, jeton intercepté avant déconnexion puis rejoué → refusé). Reste : limiteur de débit partagé entre processus (délibérément pas fait ce cycle — mérite sa propre vérification, pas glissé à la suite de deux autres changements de sécurité), audit plus large (dépendances, TLS — hors périmètre local de dev). |
| C12 | Sauvegarde et exploitation | **92 %** | Cycle 21, complété au cycle 26 (piste C12, travail en parallèle, addendum point i — RPO cible 1 heure décidé le 2026-09-13). `sauvegarder.ps1` étendu : `-DossierDistant` (copie hors-site vérifiée par `Test-Path` après copie), `-RetentionJours` (purge glissante, testée avec des fichiers réellement vieillis), **fichier d'état daté** (`dernier_etat_sauvegarde.json`, écrasé à chaque tentative succès/échec — durcissement explicitement exigé : « une sauvegarde qui échoue en silence est pire que pas de sauvegarde »), **trace dans le journal d'événements Windows** (source dédiée si enregistrée par un administrateur, repli sur la source générique sinon — vérifié dans le XML brut de l'événement). `planifier_sauvegarde.ps1` : tâche planifiée Windows, deux déclencheurs (horaire pendant les heures d'ouverture + un déclenchement de fin de journée), **déclenchement réel prouvé** (pas seulement l'enregistrement de la tâche — fichiers produits par CE déclenchement, tâche de test supprimée après preuve). Route `GET /exploitation/derniere-sauvegarde` (réservée au responsable) : **donnée prête pour le voyant du tableau de bord**, câblée visuellement au cycle 27. Exécutable reconstruit (26 Mo, `openpyxl`/`reportlab`/`pypdf`), testé **isolé** (dossier hors dépôt) : export Excel et PDF réels, reçu de vente PDF relu avec son contenu vérifié. **Preuve de restauration non négociable** : sauvegarde avec copie hors-site puis restauration **depuis la copie hors-site elle-même** (pas le fichier local) — comptes de lignes et droits par colonne identiques, contenu réel vérifié ligne à ligne, base de preuve supprimée après coup. **Cycle 28** — trois manques identifiés comme bloquant une mise en service réelle, réglés : **chiffrement du fichier de sauvegarde** (AES-256-CBC + HMAC-SHA256, PowerShell/.NET natif, phrase de passe saisie par le responsable et jamais versionnée — inclut désormais le logo de la boutique, cf. ci-dessous) ; **sauvegarde sans session Windows ouverte** (`planifier_sauvegarde.ps1 -CompteSysteme`, tâche sous `NT AUTHORITY\SYSTEM`) ; **PostgreSQL enregistré comme service Windows** avec redémarrage automatique après un arrêt brutal (`enregistrer_service_pg.ps1`, mécanisme écrit et vérifié syntaxiquement, **enregistrement réel non exécuté faute de droits administrateur dans cette session** — reste à faire exécuter par le propriétaire). Diagnostic par exécution réelle (PostgreSQL arrêté/relancé avec autorisation explicite) : une requête vers une base injoignable restait bloquée **2 min 10 s** avant d'échouer, faute de `connect_timeout` — corrigé (`connect_timeout=5`) — et affichait une erreur technique brute ; remplacé par un message français clair, sans jargon ni code visible, satisfaisant les quatre exigences posées (base non jointe, pas la faute du vendeur, saisie non perdue, qui prévenir). Manquent : **enregistrement réel du service PostgreSQL et de la tâche planifiée sous compte SYSTEM** (scripts prêts, admin requis) ; cause racine des plantages PostgreSQL non éliminée (seul le redémarrage automatique l'est) ; alerte WhatsApp/e-mail réelle (hors de portée sans compte réel à notifier) ; test de restauration sur un second poste physique ; onduleur, mise à jour des postes (addendum i) ; un risque opérationnel découvert par exécution (disparition répétée du script de sauvegarde sur ce poste de dev, très probablement la protection anti-rançongiciel de Windows — voir `db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`) reste à surveiller sur le poste réel de la boutique. |
| C13 | Tests automatisés et qualité | **60 %** | Cycle 20, complété au **cycle 27** : **172 tests pytest**, une **suite SQL complète** (44+52+6 contrôles + réversibilité) et **9 suites Playwright** (261 contrôles) existent et sont rejouées à chaque cycle qui touche le code correspondant. `db/outils/verifier_tout.sh` enchaîne les trois couches en une seule commande. **Cycle 27** : un des deux points bloquant une CI Linux, cité depuis le cycle 20, est corrigé — `server/tests/conftest.py` cherchait `psql.exe` en dur dans `_pgdev/pgsql/bin/` (distribution portable Windows, absente de tout runner CI) ; cherche désormais `psql` sur le `PATH` en premier (`shutil.which`), ne retombant sur le chemin Windows que s'il est introuvable — comportement du poste de développement inchangé (vérifié : aucun `psql` sur son `PATH`, le repli s'active toujours), 172/172 tests toujours au vert. Reste, non traité ce cycle : `PGHOST`/`PGPORT` (5433, instance portable) et le mot de passe de test en dur restent, eux aussi, propres à ce poste — un runner CI aurait besoin de ses propres variables d'environnement ; aucun pipeline CI (fichier de workflow) n'existe encore. Couverture des parcours nécessitant une imprimante ou un téléphone réels toujours hors de portée d'une suite automatisée. |
| C14 | Documentation et livrables | **40 %** | Évalué sur pièces. Documentation d'usage/recette solide : CDC détaillé, 2 guides testeur, dossier de recette, guide d'installation. `MODELE_DONNEES.md`, `PERIMETRE_LIVRE.md`, `ADDENDUM_CAHIER_DES_CHARGES.md` produits dans ce cycle. Manquent (CDC §7) : code source, scripts de fabrication des exécutables, scripts + guide de sauvegarde/restauration. |

**Moyenne indicative après le cycle 39 (C1/C4, point f, quantités décimales) : ≈ 70 %** (C0 70, C1 87, C2 77, C3 72, C4 83, C5 72, C6 85, C7 60, C8 72, C9 60, C10 58, C11 68, C12 92, C13 60, C14 40).
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
  a été consolidée et outillée d'une commande unique. Commit, PR #22 sur
  `cycle-20-c13-suite-verification-unifiee`, **fusionnée le 2026-09-13**
  sur instruction explicite du propriétaire (commit de fusion `9a466a6`,
  fast-forward, branche supprimée).
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

### Cycle 21 — Sauvegarde et restauration : C12 — 2026-09-13

Deuxième des quatre chantiers de ce lot (C13, C12, C11, C8) — 0 %
aujourd'hui, aucun script ni procédure détectable dans le livré d'origine
(CDC §4.3, testé au DR §6).

- **Objectif** : poser le **mécanisme** de sauvegarde/restauration, sans
  trancher la politique (fréquence, conservation, RPO/RTO — addendum,
  point i, non tranché).
- **Mise en œuvre** : branche `cycle-21-c12-sauvegarde-restauration`,
  empilée sur `cycle-20-c13-suite-verification-unifiee` (aucune
  dépendance de CODE entre les deux, mais toutes deux touchent le même
  tableau de scores dans ce fichier — empilée pour éviter un conflit de
  fusion sur la ligne « moyenne indicative », pas pour une raison
  technique).
  - `db/outils/sauvegarder.ps1` (nouveau) : `pg_dump -Fc` (contenu de la
    base) + `pg_dumpall --roles-only` (rôles applicatifs, **globaux au
    serveur**, absents de tout dump d'une seule base — nécessaires pour
    restaurer sur un nouveau serveur). Deux fichiers horodatés.
  - `db/outils/restaurer.ps1` (nouveau) : restaure **toujours** vers une
    base séparée (`-NomBaseCible`), refuse d'écraser une base existante
    sauf `-Forcer` explicite — prouver une restauration veut dire la
    rejouer à côté, jamais par-dessus.
- **Trois pièges rencontrés et corrigés en écrivant ces scripts** :
  1. Deux fichiers `.ps1` d'abord écrits avec des caractères accentués —
     exactement le piège déjà documenté dans `demarrer_pg.ps1` (parseur
     PowerShell 5.1 désynchronisé). Réécrits en **ASCII pur** avant tout
     test, cette fois sans attendre de le découvrir à l'exécution.
  2. `$var = & commande` : quand la commande native ne produit **aucune**
     ligne de sortie (ex. `psql -tAc` sur une requête à zéro résultat),
     PowerShell capture une valeur interne distincte d'un `$null`
     ordinaire — `.GetType()`/`.Trim()` échouent dessus **même après un
     cast `[string]`**. Seule une comparaison explicite (`$null -eq
     $var`) la détecte de façon fiable ; trouvé par exécution réelle,
     pas anticipé à l'écriture.
  3. `[int]$texte` lève une exception sur une chaîne vide plutôt que de
     s'évaluer à 0 — remplacé par `[int]::TryParse()`.
- **Vérification par exécution** (aucun test automatisé dédié, chantier
  hors périmètre de pytest — vérifié directement en SQL/PowerShell) :
  sauvegarde réelle de `quincaillerie_test` (5 utilisateurs, 4 articles,
  1 fournisseur), restaurée dans une base séparée
  (`quincaillerie_test_restauration`) — comptes de lignes identiques sur
  les trois tables vérifiées, **et les droits par colonne survivent**
  (`qf_agent_stock` relit `articles.nom` mais toujours pas
  `articles.prix_vente`, avant et après restauration,
  `has_column_privilege()`). Base de test nettoyée après vérification.
- **Documentation** : `db/README.md` (nouvelle section « Sauvegarde et
  restauration », correction d'une ligne devenue fausse sur
  `boutique_numero_contribuable` depuis le reçu PDF du cycle 19),
  `PERIMETRE_LIVRE.md` (ligne §4 et contradiction n°7 passées de « Non
  couvert » à « Confirmé (test) », ligne « Livrables manquants »
  actualisée), `loop-state.md`.
- **Score** : C12 **0 % → 45 %**. Commit, PR #23 sur
  `cycle-21-c12-sauvegarde-restauration`, **fusionnée le 2026-09-13** sur
  instruction explicite du propriétaire (commit de fusion `debd7b5`,
  fast-forward, branche supprimée).
- **Reste ouvert** : fréquence de sauvegarde, durée de conservation,
  RPO/RTO cible (point i, décision du propriétaire) ; pas de
  planification automatique (Tâches planifiées Windows) ; pas de test de
  restauration sur un **second poste physique** (seulement sur le même
  serveur, faute d'un second poste disponible pour l'agent) ; guide
  utilisateur (quand/comment lancer ces scripts sur un poste réel,
  addendum point l) pas encore écrit — relève de C14.

---

### Cycle 22 — Révocation de session et en-têtes HTTP : C11 — 2026-09-13

Troisième des quatre chantiers de ce lot (C13, C12, C11, C8) — deux des
trois lacunes de sécurité documentées de longue date, la troisième
(limiteur de débit partagé) volontairement laissée de côté ce cycle.

- **Objectif** : fermer « révocation de session » et « en-têtes HTTP »
  sans toucher au limiteur de débit — trois changements de sécurité dans
  le même cycle mériteraient chacun sa propre vérification, pas un
  empilement sous pression de temps.
- **Mise en œuvre** : branche `cycle-22-c11-securite-applicative`,
  empilée sur `cycle-21-c12-sauvegarde-restauration` (même raison que
  l'empilement précédent : pas de dépendance de CODE, mais le même
  tableau de scores dans ce fichier).
  - `db/migrations/018_revocation_jetons.sql` (+ inverse) :
    `jetons_revoques` (table) + `revoquer_jeton()`/`jeton_est_revoque()`
    (`SECURITY DEFINER`, sous `qf_app` directement — comme
    `verifier_connexion()`, pas une donnée cloisonnée par site).
  - `server/app/securite.py` : chaque jeton porte désormais un `jti`
    aléatoire (16 octets). Un jeton émis avant ce cycle a `jti=""` — reste
    vérifiable jusqu'à sa propre expiration, simplement jamais révocable
    a posteriori (aucune régression).
  - `server/app/deps.py` : `obtenir_session()` vérifie la révocation à
    **chaque** requête authentifiée, après la signature/expiration.
  - `server/app/routes/auth.py` : `POST /auth/deconnexion` (nouveau).
  - `server/app/main.py` : middleware global posant 3 en-têtes HTTP
    (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) sur
    toute réponse. `Strict-Transport-Security` volontairement **pas**
    posé : le serveur de dev répond en clair, l'annoncer mentirait sur ce
    que le navigateur reçoit.
  - `maquette/api.js` : `deconnecter()` appelle `POST /auth/deconnexion`
    avant d'effacer la session locale (meilleur effort — une coupure
    réseau n'empêche jamais de quitter l'écran).
- **Piège trouvé en écrivant la migration, avant tout code Python** :
  `NOW() + interval '1 hour'` renvoie un `TIMESTAMPTZ`, pas un
  `TIMESTAMP` — la fonction attendait `TIMESTAMP`, échec de résolution de
  surcharge au premier appel réel. Corrigée pour recevoir l'expiration en
  **secondes Unix** (`BIGINT`, comme le champ `exp` du jeton lui-même),
  `to_timestamp()` faisant la conversion dans le fuseau de la connexion
  (Africa/Douala) — l'appelant Python n'a alors plus aucun fuseau à gérer.
- **Piège d'exécution rencontré (pas un bug de code)** : le premier
  passage complet de la suite pytest a produit 75 échecs et 45 erreurs en
  cascade, disparus au second passage sans changer une ligne — un
  processus Python d'un lancement précédent en arrière-plan tournait
  encore et se disputait la même base de test avec le nouveau lancement
  (rechargements de jeu d'essai concurrents). Processus tué, suite
  rejouée proprement. Leçon retenue pour la suite : vérifier qu'aucun
  processus Python ne tourne encore avant de rejouer une suite après un
  lancement en arrière-plan.
- **Vérification par exécution** :
  - Fonctions de révocation vérifiées en SQL direct avant tout code
    Python : jeton non révoqué, révocation, double révocation
    idempotente, jeton vide refusé, `qf_agent_stock` ne peut pas appeler
    ces fonctions directement (réservées à `qf_app`).
  - `test_securite.py` : **4/4** nouveaux.
  - Suite pytest complète : **144/144**, 0 régression (coût mesuré :
    ~305 s contre ~270 s avant — un aller-retour PostgreSQL de plus par
    requête authentifiée).
  - `verifier-cablage.mjs` étendu (+3) : **80/80** — un jeton intercepté
    AVANT la déconnexion, rejoué directement contre l'API après coup, est
    refusé (401), preuve d'une révocation réelle côté serveur.
  - 5 autres suites Playwright rejouées sans régression : **12/12**,
    **17/17**, **26/26**, **29/29**, **11/11**, **21/21**.
- **Documentation** : `db/README.md` (ligne migration 018),
  `server/README.md` (section C11 étendue), `server/tests/
  DERNIER_RESULTAT.md`, `loop-state.md`.
- **Score** : C11 **55 % → 68 %**. Commit, PR #24 sur
  `cycle-22-c11-securite-applicative`, **fusionnée le 2026-09-13** sur
  instruction explicite du propriétaire (commit de fusion `58d3845`,
  fast-forward, branche supprimée).
- **Reste ouvert** : limiteur de débit partagé entre processus
  (délibérément pas fait ce cycle — mérite sa propre vérification) ;
  audit de sécurité plus large (dépendances, TLS — hors périmètre local
  de dev) ; `Strict-Transport-Security` une fois un déploiement réel en
  TLS.

---

### Cycle 23 — Bascule vue consolidée / par site : C8 — 2026-09-13

Quatrième et dernier chantier de ce lot (C13, C12, C11, C8).

- **Objectif** : le gap identifié depuis le cycle 10 — « les données
  portent déjà `site_id`, la bascule elle-même n'a pas d'écran ».
- **Constat qui a simplifié le chantier** : chaque route du tableau de
  bord (`/ventes/synthese-jour`, `/tableau-bord/alertes-stock`,
  `/inventaire/ecarts`, `/inventaire/ecarts-ventes`) renvoie **déjà**
  `site_id` sur chaque ligne pour un responsable (vue non filtrée côté
  RLS). La bascule est donc un **filtre purement d'affichage** — aucune
  route, aucune migration, aucun appel réseau supplémentaire au
  changement de vue.
- **Mise en œuvre** : branche `cycle-23-c8-bascule-vue-site`, empilée sur
  `cycle-22-c11-securite-applicative` (même raison que les empilements
  précédents : pas de dépendance de code, mais le même tableau de scores).
  - `maquette/tableau-bord.html` : sélecteur (« Les deux sites » /
    « Magasin de stock » / « Comptoir ») près du titre. Chaque carte
    garde ses données BRUTES en mémoire et se redessine entièrement au
    changement de site — jamais un nouveau `fetch()`. Le libellé du
    total (« consolidé » / « du site ») change avec la vue, pour ne
    jamais laisser croire qu'un total filtré reste consolidé.
  - `verifier-cablage.mjs` étendu (+7) : réutilise les ventes déjà
    semées par la suite elle-même (6500 FCFA site 1, 3200 FCFA site 2)
    + la vente réelle créée plus tôt dans le même run (2000 FCFA site 1)
    pour vérifier des totaux filtrés exacts, pas seulement une présence
    de texte.
- **Vérification par exécution** : `verifier-cablage.mjs` **87/87**
  (80 + 7 nouveaux) — filtrer sur Magasin fait disparaître Comptoir et
  recalcule le total à 8 500 FCFA exactement ; filtrer sur Comptoir
  donne 3 200 FCFA et fait disparaître l'alerte « Article rare »
  (au Magasin) ; revenir à « Les deux sites » retrouve 11 700 FCFA,
  identique à avant tout filtrage. `verifier-echappement-html.mjs`
  (11/11) et les 5 autres suites Playwright (12/12, 17/17, 26/26,
  29/29, 21/21) rejouées sans régression. Aucun code serveur touché,
  suite pytest inchangée (144/144).
- **Documentation** : `server/README.md` (section C8 étendue),
  `maquette/verification/DERNIER_RESULTAT.md`, `loop-state.md`.
- **Score** : C8 **62 % → 70 %**. Commit, PR #25 sur
  `cycle-23-c8-bascule-vue-site`, **fusionnée le 2026-09-13** sur
  instruction explicite du propriétaire (commit de fusion `87603d4`,
  fast-forward, branche supprimée).
- **Reste ouvert** : clôture de caisse (point g, non tranché), numéro de
  facturier (point c, non tranché).

---

Le lot de 4 chantiers (cycles 20 à 23 — correction diagnostic C13,
sauvegarde/restauration C12, sécurité applicative C11, bascule vue C8)
est **terminé et fusionné** (PR #22/#23/#24/#25, empilées dans l'ordre,
retargées vers `main` avant chaque fusion de leur base pendant qu'elles
étaient encore ouvertes — les quatre fusions et suppressions de branche
se sont enchaînées sans accroc).

---

### Campagne UX réelle n°1 — 2026-09-13 (aucun code, mesure humaine seule)

Première campagne humaine réelle sur `UX_BASELINE.md` (§4 bis) — la
seule voie documentée depuis le cycle 1 pour lever le plafond de 60 %
sur C9/C10. Transmise par le propriétaire, intégrée **sans aucune
modification des valeurs mesurées**. Aucune correction faite : les
échecs sont consignés comme constats (UX-0 à UX-10), le choix du cycle
qui les traite revient au propriétaire.

- **Écart de méthode trouvé en intégrant les mesures (constat UX-0)** :
  le protocole documenté depuis le cycle 1 (§1) retient **le pire des 3
  essais** pour juger la conformité d'une mesure chronométrée ; le
  testeur a retenu **le 3ᵉ essai** (usage pratiqué plutôt que première
  découverte). Sous la lecture du protocole, 4 des 7 mesures
  chronométrées changent de conclusion, y compris **l'objectif
  principal** (vente de 3 articles < 60 s : 2 min 10 au pire essai, 58 s
  au 3ᵉ). Les deux lectures répondent à des questions différentes,
  légitimes toutes les deux — le score ci-dessous retient celle du
  protocole déjà documenté, pas celle du testeur, par cohérence avec ce
  qui était promis depuis le cycle 1 (« sans arrondir en faveur » de
  qui que ce soit, y compris de l'agent qui a écrit le protocole).
- **Section A (PC, 7 mesures)** : **1/7 conforme** (protocole) — seule la
  correction d'une quantité sans changer d'écran passe. Échouent :
  connexion, vente de 3 articles, ajout au panier (3-4 actions au lieu
  de ≤ 2), suppression d'une ligne, vente au clavier seul, comptage de
  10 articles.
- **Section B (téléphone réel, 9 contrôles)** : **4/9 conforme** —
  connexion, boutons au pouce, confidentialité des montants pour l'agent
  stock et mode paysage fonctionnent réellement. Échouent : débordement
  d'environ 40 px du tableau de bord (jamais détecté par les suites
  automatisées aux 5 largeurs standard — écart non diagnostiqué),
  chiffres illisibles sans zoom, saisie d'une recette trop lente,
  clavier numérique qui ne s'ouvre pas seul pour un comptage, et surtout
  **une coupure Wi-Fi en cours de saisie laisse l'écran tourner
  indéfiniment sans aucun message** — le constat le plus sérieux de la
  campagne, une vraie violation du principe « jamais un message brut »
  jamais testée jusqu'ici pour une coupure réseau en cours de requête.
- **Section C (compréhension, 4 questions, sans aide)** : **1/4
  conforme** — un utilisateur non formé ne trouve pas seul comment
  annuler une ligne (~20 s de recherche), confond le prix négocié
  affiché en gris avec le prix à facturer, et ignore qu'un comptage
  devient définitif une fois validé.
- **Score** : C9 **50 % → 40 %** (baisse — l'objectif principal n'est
  pas atteint au pire essai, la compréhension est nettement en dessous
  de ce que les vérifications automatiques laissaient supposer). C10
  **38 % → 42 %** (hausse — la preuve manquante depuis le cycle 15, un
  vrai téléphone, existe enfin et confirme l'essentiel, même si elle
  révèle des défauts réels).
- **Documentation** : `UX_BASELINE.md` (§4 bis, nouveau ; callout de tête
  mis à jour), `loop-state.md`.
- **Reste ouvert** : 11 constats (UX-0 à UX-10), aucun corrigé — le
  propriétaire choisira le cycle qui les traite. Le choix de convention
  (pire des 3 essais vs 3ᵉ essai) reste lui-même à trancher explicitement
  avant la prochaine campagne.

---

### Cycles 24/25/26 — Travail en parallèle : trois pistes simultanées — 2026-09-14 → 2026-09-18

Première exécution de trois sessions Claude Code **réellement simultanées**
sur ce dépôt, chacune dans son propre worktree Git, sur sa propre base
PostgreSQL (`quincaillerie_ux`/`_c6`/`_c12`, même instance partagée
127.0.0.1:5433, isolation prouvée par exécution — voir `db/README.md`,
`RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`). Coordination : plan de
non-collision écrit et validé avant démarrage (périmètre de fichiers
exclusif par piste, fichiers transversaux gelés, convergence obligatoire
sur un même motif de variable d'environnement pour les fichiers de test
partagés, ordre de fusion décidé à l'avance UX → C6 → C12).

**Consigne de sécurité relayée aux trois pistes** : aucune ne devait
arrêter, redémarrer ou reconfigurer PostgreSQL (instance partagée,
redémarrer coupe les deux autres en plein test) — respectée par les trois
sans exception. Un crash PostgreSQL réel (« could not reserve shared
memory region », bug Windows connu, sans rapport avec ce travail) est
survenu en cours de route : signalé par la piste concernée sans action de
sa part, corrigé par la session de coordination (`demarrer_pg.ps1`,
reprise WAL automatique), intégrité vérifiée (comptes de tables/lignes
identiques sur les 4 bases) avant de reprendre les trois pistes.

#### Cycle 24 — Piste UX : corrections `UX_BASELINE.md` §4 bis (C9, C10)

Détail complet, diagnostic et preuves : `RAPPORT AVANCEMENT/cycles/piste-ux.md`.
Résumé : 7 des 8 constats confiés corrigés et vérifiés par exécution
réelle (UX-1, UX-2, UX-3, UX-4, UX-7, UX-9, UX-10), UX-6 confirmé déjà
correct à l'inspection. UX-0 (méthodologie), UX-5, UX-8 restent hors
périmètre. Nouvelle suite `verifier-ux-corrections.mjs` (27/27). Adaptation
convergée avec les deux autres pistes sur `server/tests/conftest.py` et
les suites Playwright partagées (variable d'environnement, défaut
inchangé). Fragilité intermittente pré-existante trouvée dans
`verifier-inventaire-reel.mjs` (course dans le script de test lui-même,
sans rapport avec ce chantier), signalée sans être corrigée (fichier
commun, règle « ajout seulement »).

- **Score** : C9 **40 % → 58 %**, C10 **42 % → 55 %** (détail par constat
  dans le tableau des scores ci-dessus — **une deuxième campagne humaine
  réelle reste nécessaire** avant de considérer ces deux chantiers proches
  de 100 %, les preuves de ce cycle sont automatisées, pas humaines).
- PR #28, fusionnée en premier dans `main` (commit de fusion `95d4ede`).

#### Cycle 25 — Piste C6 : clôture de caisse par site (addendum point g)

Détail complet, diagnostic et preuves : `RAPPORT AVANCEMENT/cycles/piste-c6.md`.
Résumé : migration 019 (`clotures_caisse`, immuable, seul point d'écriture
`cloturer_caisse()` `SECURITY DEFINER`), écran `cloture-caisse.html`, 19
tests pytest dédiés, 24 contrôles Playwright (`verifier-caisse-reel.mjs`).
Seuil d'écart toléré amorcé à `a_definir` (tolérance nulle appliquée,
aucun chiffre inventé). Rebasée sur `main` après la fusion de la PR #28 :
3 fichiers en conflit (`server/tests/conftest.py`,
`maquette/verification/verifier-cablage.mjs`,
`maquette/verification/verifier-rh-reel.mjs`), tous la même cause (deux
implémentations indépendantes du même motif convergé) — résolus en
gardant la version déjà fusionnée de la piste UX, confirmée sans perte de
contenu propre à C6 (`git diff` ciblé avant résolution).

- **Score** : C6 **55 % → 85 %**. Détail dans le tableau des scores
  ci-dessus.
- PR #27, fusionnée en second (commit de fusion `250f5b6`).

#### Cycle 26 — Piste C12 : automatisation et durcissement de la sauvegarde (addendum point i)

Détail complet, diagnostic et preuves : `RAPPORT AVANCEMENT/cycles/piste-c12.md`.
Résumé : `sauvegarder.ps1` étendu (copie hors-site vérifiée, rétention,
fichier d'état daté, journal d'événements Windows — durcissement exigé
explicitement en cours de cycle après le constat que « une sauvegarde qui
échoue en silence est pire que pas de sauvegarde »), `planifier_sauvegarde.ps1`
(nouveau, déclenchement réel prouvé), route `GET /exploitation/derniere-
sauvegarde`, exécutable reconstruit et testé isolé, restauration prouvée
depuis la copie hors-site elle-même. Rebasée sur `main` après la fusion de
la PR #27 : 2 fichiers en conflit (`server/tests/conftest.py` — même cause
que ci-dessus, résolu pareil ; `server/app/main.py` — deux routeurs
distincts à enregistrer, fusion additive des deux imports).

- **Score** : C12 **45 % → 80 %**. Détail dans le tableau des scores
  ci-dessus.
- PR #26, fusionnée en dernier (commit de fusion `ecc9967`).

#### Vérification finale, par la session de coordination (pas par les pistes)

Après les trois fusions : worktrees et branches de piste supprimés, les
trois bases de piste supprimées (jeu d'essai uniquement, plus nécessaires),
`quincaillerie_test` reconstruite intégralement (schéma + migrations
000→019 + jeu d'essai) et **revérifiée de bout en bout sur le dépôt
principal fusionné** : suite pytest complète **163/163**, 8 suites
Playwright obligatoires (`db/outils/verifier_tout.sh`) toutes au vert
(`cablage` 87/87, `caisse` 24/24, `echappement` 11/11, `vente` 12/12,
`inventaire` 17/17, `stock` 26/26, `rapports` 29/29, `rh` 21/21) plus la
nouvelle `ux-corrections` 27/27 — **0 régression sur l'intégration des
trois pistes**. Route `GET /exploitation/derniere-sauvegarde` revérifiée
par requêtes HTTP réelles après fusion (fichier absent puis présent,
cloisonnement par rôle). `quincaillerie_test` laissée dans un état de jeu
d'essai propre.

- **Reste ouvert, signalé mais non traité ce cycle** (nécessite son propre
  diagnostic/plan avant tout code, comme d'habitude) : lien visuel
  `cloture-caisse.html` ↔ `tableau-bord.html` (C6), voyant visuel
  « dernière sauvegarde » sur `tableau-bord.html` (C12) — les deux étaient
  explicitement reportés par leur piste jusqu'à la fusion de la piste UX,
  **maintenant fusionnée** : les deux ne sont plus bloqués.

---

### Cycle 27 — Lot sans nouvelle décision : voyants, portabilité C13, rôle caissier C3, numéro de facturier C5 — 2026-09-18

Quatre points validés en un seul lot, choisis précisément parce qu'aucun ne
dépend d'une décision non encore obtenue du propriétaire.

- **Voyants de tableau de bord (C6 + C12)** : lien « Clôture de caisse »
  ajouté au bandeau de `tableau-bord.html` ; nouvelle carte « Dernière
  sauvegarde » lisant `GET /exploitation/derniere-sauvegarde` (route déjà
  livrée au cycle 26, jamais câblée visuellement faute d'accès au fichier
  ce tour-là). Les trois états réels (aucune sauvegarde, succès, échec)
  vérifiés par exécution avec un vrai fichier d'état écrit/effacé pour
  chaque cas — jamais silencieux sur un échec, comme exigé. Piège trouvé
  et corrigé : la classe `pastille--neutre` était déjà réservée, par
  `verifier-cablage.mjs`, au marquage d'une carte de DONNÉE SIMULÉE
  (avant le câblage réel du chantier C8) — la réutiliser pour « aucune
  sauvegarde pas encore lancée » aurait fait croire à une régression de
  simulation ; `pastille--info` utilisée à la place.
- **C13 (portabilité CI)** : `PSQL_EXE` dans `server/tests/conftest.py`
  cherche désormais `psql` sur le `PATH` (`shutil.which`) avant de retomber
  sur le chemin Windows `_pgdev/pgsql/bin/psql.exe` — un seul des deux
  points bloquants cités depuis le cycle 20, l'autre (`PGHOST`/`PGPORT`
  propres au poste, mot de passe de test en dur) reste ouvert, comme le
  pipeline CI lui-même (aucun fichier de workflow n'existe).
- **C3 (rôle caissier, addendum point h)** : diagnostic par exécution
  révèle que l'architecture existante satisfait déjà la décision du
  2026-09-13 — `qf_agent_comptabilite` encaisse ET saisit depuis le cycle
  6, aucun code nécessaire. Corrige au passage une affirmation devenue
  inexacte de ce tableau (le cloisonnement RH était déjà testé par une
  route, pas seulement en SQL direct).
- **C5 (numéro de facturier + vendeur, addendum point c)** : périmètre
  volontairement réduit au socle décidé après qu'un diagnostic plus
  approfondi a révélé plusieurs questions non tranchées (format exact du
  numéro, vendeurs sans compte, seuil de validation d'un écart de prix,
  rapport associé) — voir `db/migrations/020_facturier_vendeur.sql` pour
  le détail de ce qui est fait et explicitement pas fait. `numero_facturier`
  (carnet papier, jamais généré par le logiciel) et `vendeur_id`
  obligatoires sur toute nouvelle vente, préfixe par site vérifié en base
  (`MAG-`/`CPT-`), nouvelle route `GET /ventes/vendeurs`. Ajusté un
  commentaire de `server/app/routes/ventes.py` devenu inexact : l'attribution
  systématique de l'encaissement au responsable (jamais à l'agent qui
  saisit réellement) est maintenant en désaccord visible avec la décision
  du point h ci-dessus — signalé, pas corrigé ce cycle (hors périmètre du
  point c).
- **27 nouveaux tests pytest** (9 pour le point c, 18 patchés dans les
  suites existantes pour fournir les deux champs désormais obligatoires —
  `numero_facturier`/`vendeur_id` avec le bon préfixe selon le site
  effectif de chaque vente, pas celui du corps de la requête quand un
  agent l'ignore). **7 suites Playwright ajustées** pour remplir le
  formulaire de vente avant validation (`verifier-cablage.mjs`,
  `verifier-vente-reelle.mjs`, `verifier-caisse-reel.mjs`,
  `verifier-ux-corrections.mjs`, `verifier-echappement-html.mjs`,
  `verifier-inventaire-reel.mjs`), plus les deux nouveaux contrôles de
  voyant dans `verifier-cablage.mjs`.
- **Incidents d'orchestration signalés pour mémoire** (aucun n'est un bug
  de ce cycle) : lancer la suite pytest et la suite SQL complète en
  parallèle sur `quincaillerie_test` corrompt les deux (leçon déjà
  documentée ailleurs dans ce projet, reconfirmée) — toujours les
  enchaîner, jamais les paralléliser, sur une base partagée. La suite SQL
  complète (`executer_tests.sh`) réinitialise le mot de passe du rôle
  cluster-wide `qf_app` en rejouant les migrations inverses puis directes
  (`definir_mot_de_passe_app.sql` n'est délibérément pas versionné) — déjà
  documenté au cycle 20, reconfirmé ici : à rejouer après chaque suite SQL
  complète.
- **Vérifié par exécution, intégralement rejoué après les quatre
  changements** : 172/172 tests pytest, suite SQL complète (protections,
  habilitations, concurrence, réversibilité — 0 échec), 9 suites
  Playwright (94+24+11+12+17+26+29+21+27 = 261 contrôles, 0 échec réel —
  une unique reprise nécessaire sur `verifier-inventaire-reel.mjs`,
  fragilité intermittente déjà diagnostiquée par la piste UX, sans rapport
  avec ce cycle).
- **Score** : voyants → C6 et C12 inchangés (l'intégration visuelle ne
  change pas ce qui était déjà prouvé côté serveur). C13 **55 % → 60 %**.
  C3 **60 % → 68 %**. C5 **62 % → 72 %**.

---

### Cycle 28 — Exploitation C12 (trois manques bloquants), identité visuelle Akuma, logo du client — 2026-09-19

Chantier choisi par le propriétaire lui-même (C12, « le seul lot qui
bloque une mise en service réelle »), avec deux tâches transverses
greffées dans le même cycle : le nommage de l'application (Akuma, marque
de la gamme logicielle — « Ets Quincaillerie Franck » reste le nom du
client) et une nouvelle fonction (logo de la boutique téléversable par le
responsable).

- **Diagnostic par exécution réelle, autorisé explicitement par le
  propriétaire** (arrêt/relance de PostgreSQL, poste de développement,
  aucune donnée de production) : une requête vers une base injoignable
  restait bloquée **2 min 10,1 s** avant d'échouer — aucun `connect_timeout`
  n'était posé sur les connexions psycopg — et l'écran affichait une erreur
  technique brute au lieu de se figer proprement. Découverte plus grave que
  les plantages eux-mêmes, élevée par le propriétaire au même rang que la
  sauvegarde sans session : **PostgreSQL n'était pas enregistré comme
  service Windows**, donc rien ne le relançait après un arrêt brutal.
- **C12 — trois manques réglés** : (1) chiffrement du fichier de sauvegarde
  lui-même (AES-256-CBC + HMAC-SHA256, PowerShell/.NET natif, sans
  dépendance externe ni installation sur le poste boutique — BitLocker To
  Go écarté, il exige Windows Pro/Enterprise ; phrase de passe saisie par
  le responsable, jamais versionnée, stockée comme les autres secrets ;
  HMAC vérifié en temps constant **avant** toute tentative de déchiffrement,
  après avoir constaté par un essai réel qu'une mauvaise phrase pouvait
  parfois passer la validation du remplissage AES seule) ; (2) sauvegarde
  sans session Windows ouverte (`planifier_sauvegarde.ps1 -CompteSysteme`,
  tâche sous `NT AUTHORITY\SYSTEM`) ; (3) PostgreSQL enregistré comme
  service Windows avec redémarrage automatique après échec
  (`enregistrer_service_pg.ps1` — **écrit et vérifié syntaxiquement,
  enregistrement réel non exécuté faute de droits administrateur dans
  cette session**, reste à faire confirmer par le propriétaire).
  `connect_timeout=5` posé, et le message affiché au vendeur quand la base
  devient injoignable refait en français simple, sans jargon ni code
  visible, revu une fois après un premier essai trop spécifique à l'écran
  de caisse (le gestionnaire s'applique à toute route) : la base ne
  répond pas, ce n'est pas la faute du vendeur, la saisie en cours n'est
  pas perdue, qui prévenir (`contact_support_technique`, nouveau paramètre,
  `a_definir` — décision du propriétaire encore attendue).
- **Logo du client (nouvelle fonction)** : `POST/DELETE/GET
  /configuration/logo`, réservé au rôle responsable **prouvé au niveau de
  la requête** (403 testé pour les deux rôles agents), PNG/JPEG uniquement
  vérifiés par **signature réelle du fichier** (pas l'extension), décodage
  + réencodage serveur avant écriture sur disque (élimine les fichiers
  polyglottes), taille maximale 2 Mo documentée, stocké hors base
  (`server/donnees/logo_boutique/`, jamais versionné) — la base ne garde
  que l'extension présente. Sans logo téléversé, l'application fonctionne
  normalement avec le seul nom de la boutique : jamais d'image cassée,
  jamais d'espace vide (vérifié). Inclus dans la sauvegarde/restauration
  (chiffré comme le reste). Le logo Akuma (éditeur) reste, lui, non
  remplaçable par l'utilisateur.
- **Identité visuelle Akuma** : logo officiel (fourni par le propriétaire)
  décliné en trois formats (complet, compact sans baseline/cachet, icône
  carrée) par analyse réelle du fichier source (canal alpha pour détecter
  les zones à recadrer, échantillonnage des couleurs dominantes plutôt que
  choisies à l'œil) ; le logo complet ne descend jamais sous 120 px de
  large (`connexion.html`), vérifié par capture aux 5 largeurs habituelles
  (360/390/768/1366/1920 px). Thème central aligné sur les deux couleurs du
  logo (`--c-primaire` remplacé par le bleu échantillonné, nouvel accent or
  `--c-accent-or` — **seul** le montant total à payer de `vente.html`
  l'utilise, usage volontairement restreint, aucune refonte d'écran).
  `boutique_nom` inchangé sur les reçus ; aucun renommage du dépôt Git, des
  bases de données ni des dossiers (validé explicitement par le
  propriétaire). Renommage de surface : titres de fenêtres/onglets,
  bandeau de chaque écran, exécutable (`Akuma.exe`, icône propre),
  documentation listée par le propriétaire (`README.md`, `server/README.md`,
  `maquette/README.md`, `SKILL.md`, `loop-state.md` — jamais le récit
  historique des cycles passés).
- **Incident d'infrastructure signalé pour mémoire** (aucun n'est un bug de
  ce cycle) : `sauvegarder.ps1` a disparu du disque à trois reprises durant
  les essais, chaque fois ~10-15 s après une exécution **réussie** —
  cohérent avec la protection anti-rançongiciel de Windows (Contrôle
  d'accès aux dossiers) réagissant au motif lire-chiffrer-supprimer
  l'original, plutôt qu'avec Defender lui-même (protection en temps réel
  confirmée désactivée). Contourné en committant après chaque petit
  changement vérifié ; non éliminable depuis l'intérieur du script —
  documenté comme risque opérationnel réel dans
  `db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`, avec la remédiation
  standard (autoriser `powershell.exe`/`Akuma.exe` dans les paramètres
  Windows). Deuxième incident, sans rapport avec ce cycle : une reprise
  unique de `verifier-inventaire-reel.mjs` (déjà signalée fragile aux
  cycles précédents) — reproduite puis expliquée par un enchaînement de
  suites tombant par malchance à cheval sur le changement de jour à
  Batouri (`Africa/Douala`, UTC+1) pendant les essais ; rejouée à distance
  de toute frontière de jour, 17/17 à chaque fois.
- **Vérifié par exécution, intégralement rejoué après tous les
  changements** (`db/outils/verifier_tout.sh`, base reconstruite depuis
  zéro) : suite SQL complète (0 échec), **183/183 tests pytest** (172 +
  11 nouveaux pour le logo), **9 suites Playwright, 210 contrôles, 0
  échec** (`cablage` 94/94, `vente` 12/12, `inventaire` 17/17, `stock`
  26/26, `rapports` 29/29, `echappement` 11/11, `rh` 21/21), base laissée
  dans un jeu d'essai propre.
- **Score** : C12 **80 % → 92 %**. Aucun autre chantier du référentiel
  touché — l'identité visuelle et le logo du client sont des tâches
  transverses, hors `C0`–`C14`.

---

### Cycle 33 — Rangement : clôture de cycle-29 + CI minimale — 2026-09-20

- **Chantier de rangement** (décision propriétaire) : clôturer
  `cycle-29-hygiene-inventaire` et poser une CI GitHub Actions minimale,
  avant le prochain chantier de fond.
- **Clôture de cycle-29, par fusion réelle** : `VISION_PRODUIT.md` (décisions
  d'éditeur 2026-09-19 : UX-0, point k, multi-site point a, crédit client
  point b, fiscalité, import point j + recensement des 10 éléments codés en
  dur) ; ~12 décisions 2026-09-19 réconciliées dans l'addendum avec la
  décision 2026-09-20 déjà sur main ; candidats de cycle-29 renumérotés
  **13** (multi-site), **14** (crédit client), **15** (import stock),
  références internes corrigées. **Scores C0-C14 inchangés** (vérifié :
  aucun `%` modifié par le merge). Trois correctifs de code de la branche
  reportés (validés par le propriétaire) : `Cache-Control: no-store` sur le
  JSON de l'API (`server/app/main.py`), attente des vraies réponses réseau
  dans `verifier-inventaire-reel.mjs` et `verifier-echappement-html.mjs`.
- **CI minimale** : `.github/workflows/ci.yml` — sur chaque push/PR vers
  `main`, service `postgres:17` mappé sur 127.0.0.1:5433, schéma d'origine
  + migrations 000-024 + jeu d'essai rejoués, suite pytest complète. Le
  « vert/rouge » existe enfin sur GitHub, sans dépendre de la vérification
  manuelle du poste de développement. **Premier run réel : rouge**, pour
  deux causes hors dépôt par conception (`server/config.ini` gitignoré,
  `qf_app` sans mot de passe tant que `definir_mot_de_passe_app.sql` n'a pas
  tourné) — corrigées dans le workflow lui-même, **second run vert**
  (suite pytest 200/200 sur runner Ubuntu). La CI a donc prouvé dès son
  premier jour qu'elle attrape les erreurs.
- **Score** : C0 **65 % → 70 %** (CI automatisée livrée et verte ; reste
  kiosque et lockfile). Moyenne indicative ≈ 67 %.

---

### Cycle 34 — Candidat 13a : rapprochement des fiches homonymes — 2026-09-20

- **Décisions du propriétaire verrouillées** : suggestion automatique sur
  nom strictement identique (après `btrim`), validation humaine **une par
  une**, jamais de fusion automatique ; prix et fournisseur communs à la
  fiche unique ; catalogue visible aux deux sites, seule la quantité reste
  cloisonnée.
- **Livré** : migration 025 — table `rapprochements_articles` (décisions
  définitives `fusionner`/`distincts`), fonction `candidats_rapprochement()`
  et `enregistrer_rapprochement()` (`SECURITY DEFINER`, réservées à
  `qf_app`, fenêtre étroite sans jamais exposer d'autre colonne d'articles)
  + vue miroir ; outil console `db/outils/rapprocher_articles.ps1`
  (liste, puis décision une par une ; mode automatisé par variables
  d'environnement).
- **Preuves par exécution réelle** : jeu d'essai (4 articles, aucun
  homonyme) → « Aucune paire homonyme à traiter » ; paire synthétique
  injectée (même nom, sites 1 et 2) → script en mode automatisé enregistre
  `fusionner` pour la paire 5|6, plus aucune paire restante, décision
  relue en base ; 10/10 tests pytest dédiés ; suite complète (voir CI).
- **Scores** : aucun score C0-C14 modifié (13a est une préparation, la
  migration 13b portera les scores).
- **Reste (13b)** : la migration elle-même, plan validé en 6 phases
  (schéma → données → fonctions → RLS/GRANT → routes/écrans → suites).

---

### Cycle 35 — Candidat 13b : migration article/stock multi-site — 2026-09-21

- **Décisions consommées** : une fiche, un stock par site ; catalogue
  (nom, catégorie, unité, prix) commun aux deux sites ; seule la quantité
  est cloisonnée par site ; première réception = ouverture de la ligne du
  site ; transfert = UN article, deux sites, destination créée si absente ;
  décisions de fusion du cycle 13a consommées pendant la migration.
- **Livré** : migrations 026-031 + inverses — `stocks_sites`
  (PK article+site), `site_id` explicite sur mouvements/comptages/écarts,
  FK `ventes_lignes(article, site) → stocks_sites` (plus forte que
  l'ancienne), fonctions de stock réécrites (site explicite ou dérivé du
  document d'origine), `annuler_vente` et le rapprochement d'homonymes
  adaptés, RLS/GRANT révisés (catalogue permissif, quantité cloisonnée,
  aucune écriture directe du stock pour aucun rôle) ; routes (`articles`,
  `stock`, `inventaire`, `tableau_bord`, `ventes`, `demonstration`,
  `rapports`) ; écrans (`stock.html`, `inventaire.html`) ; tests.
- **Preuves par exécution réelle** : pytest **209/209** ; suite SQL
  **000-031 + inverses** verte ; Playwright réel — stock **26/26**,
  inventaire **17/17**, vente **12/12**, rapports **29/29**, caisse
  **24/24**, rh **21/21**, câblage **94/94** (catalogue commun vérifié) ;
  transfert prouvé en SQL direct : ligne de destination créée, mouvements
  sités, concurrence toujours correcte (verrou par (article, site)).
- **Scores** : C1 **80 → 85**, C3 **68 → 72**, C4 **72 → 80**,
  C7 **50 → 55**, C8 **70 → 72**. Moyenne indicative ≈ 69 %.
- **Reste** : import du stock initial multi-site (candidat 15), remises et
  conversions d'unités (addendum f), régularisation d'écart d'inventaire.

---

### Cycle 36 — C10 : carte « Saisie rapide » remontée en tête sur mobile — 2026-09-22

- **Étape 1 — Diagnostic** : audit lecture seule du dépôt (état Git,
  PostgreSQL, tâches admin) puis des 3 chantiers les moins avancés hors
  inventaire/Playwright et hors C12 : C14 (40 %, score stale — recoupé
  avec preuve fichier:ligne, voir plus bas), C10 (55 %) et C9 (58 %).
  Root cause d'UX-5 trouvée par lecture du code (jamais diagnostiquée
  avant) : la carte « Saisie rapide » de `tableau-bord.html` est la 5e
  sur 7, sous 3 listes de longueur variable — sur téléphone (colonne
  unique), le responsable doit tout faire défiler avant un formulaire de
  3 champs.
- **Étape 3 — Objectif validé par le propriétaire** : remonter la carte
  en tête **uniquement** sur mobile (sous 700px, seuil où `.tb-grille`
  repasse à une colonne), sans toucher le PC de caisse ni réordonner le
  DOM (lecteur d'écran/tabulation inchangés). Priorité de coordination
  explicite du propriétaire : terminer et fusionner ce chantier sur
  `tableau-bord.html` en premier, avant que deepcode (chantier C7
  parallèle, bouton « Régulariser » sur le même fichier) ne commence à y
  toucher.
- **Étape 4 — Branche** `cycle-36-c10-saisie-rapide-mobile`. Un seul
  fichier applicatif touché : `maquette/tableau-bord.html` — classe
  `.carte--saisie-rapide` posée sur la section, règle
  `@media (max-width: 699px) { .carte--saisie-rapide { order: -1; } }`
  scopée dans le `<style>` déjà présent en tête du fichier (même
  convention que la règle UX-4 juste au-dessus).
  — **Vérification par exécution réelle** : `verifier-cablage.mjs`
  **94/94, 0 échec** (aucune régression — dont les 5 contrôles de
  non-débordement de `tableau-bord.html` aux 5 largeurs, et le contrôle
  « saisie rapide d'une recette réellement enregistrée »). Script
  Playwright dédié (jetable, non committé) : à 390px, ordre visuel des
  cartes = **Saisie rapide en premier**, avant Ventes du jour ; à
  1366px, ordre identique à avant (Ventes du jour en premier, Saisie
  rapide en 5e position) — confirme que le PC de caisse n'est pas
  affecté. Aucun débordement horizontal aux deux largeurs.
  — **Score** : C10 **55 % → 58 %**. Pas de hausse plus franche : la
  cible chiffrée du point k (< 45 s, usage courant, bloquant) n'a pas
  été reconfirmée par un vrai testeur humain sur un téléphone réel — ce
  correctif supprime une friction structurelle plausible, ce n'est pas
  une nouvelle mesure humaine (même réserve posée pour UX-3/UX-4 au
  cycle 24). Détail dans `UX_BASELINE.md`, entrée UX-5 mise à jour.
- **Reste (C10)** : reconfirmer B5 (< 45 s) avec un vrai testeur sur
  téléphone réel ; API dédiée / usage hors ligne / notifications restent
  hors décision propriétaire à ce jour.
- **Note C14** (relevé pendant l'audit, non corrigé ce cycle — hors
  scope validé) : le tableau de score `loop-state.md` et
  `server/README.md:909-919` contredisent le code actuel
  (`lanceur.py:73`, corrigé au cycle 30) et l'état réel des livrables
  (guide de fabrication `server/README.md:869-944`, guide de sauvegarde
  `db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`, 375 lignes) — score 40 %
  probablement sous-évalué. À traiter dans un cycle dédié.

---

### Cycle 37 — C9 : bouton de retrait du panier rendu visible sans survol — 2026-09-22

- **Diagnostic** : UX-8 (`UX_BASELINE.md`, « un utilisateur non formé ne
  trouve pas seul comment annuler une ligne du panier, ~20 s de
  recherche »), jamais retouché depuis le diagnostic d'origine. Cause
  trouvée par lecture du code (`maquette/vente.html:388-392`,
  `maquette/styles.css:233-238`) : le bouton de retrait est un « × » nu
  (`textContent = "×"`), sans fond ni bordure au repos — visible
  **seulement au survol** (`:hover`), donc invisible au doigt sur
  téléphone (pas d'état hover tactile). Correspond exactement au critère
  qualitatif bloquant du point k (`VISION_PRODUIT.md:89`) : « retour en
  arrière compréhensible sans aide extérieure ».
- **Objectif validé par le propriétaire** : rendre le bouton visuellement
  identifiable au repos, sans dépendre du survol, sans refonte d'écran.
- **Branche** `cycle-37-c9-bouton-retrait-panier`. Deux fichiers touchés :
  - `maquette/styles.css` : `.panier__sup` reçoit un fond
    (`var(--c-alerte-clair)`) et une bordure (`var(--c-alerte)`)
    **permanents**, au lieu de n'apparaître qu'au survol
    (`border: none; background: transparent` par défaut) ;
    `:hover`/`:focus-visible` inversent les couleurs (fond plein, texte
    blanc) pour le retour visuel clavier/souris.
  - `maquette/vente.html` : `title="Retirer cette ligne du panier"`
    ajouté sur le bouton, en complément (pas en remplacement) de
    l'`aria-label` déjà présent — infobulle native au survol souris,
    sans effet sur mobile.
  — **Vérification par exécution réelle** : `verifier-cablage.mjs`
  **94/94** et `verifier-vente-reelle.mjs` **12/12**, 0 échec (aucune
  régression). Script Playwright dédié (jetable, non committé) : à 390px
  et 1366px, style calculé du bouton au repos = fond `rgb(251, 231, 225)`
  + bordure `rgb(168, 50, 10)` (avant : transparent/aucune bordure) ;
  clic sur le bouton retire bien la ligne (0 ligne de panier après clic,
  vérifié aux deux largeurs) — aucune régression fonctionnelle.
  — **Score** : C9 **58 % → 60 %**. Prudent : la discoverabilité réelle
  pour un utilisateur non formé n'a pas été reconfirmée par un vrai
  testeur (même réserve que pour C10/UX-5 au cycle 36) — ce correctif
  rend le bouton identifiable sans interaction, ce n'est pas une
  nouvelle mesure humaine. Détail dans `UX_BASELINE.md`, entrée UX-8
  mise à jour.
- **Reste (C9)** : UX-0 (2e campagne humaine réelle, 3 testeurs dont un
  nouveau, méthodologie tranchée le 2026-09-19) reste une action externe,
  non codable ; reconfirmer UX-8 avec un vrai testeur.

---

### Cycle 36 — C7 : régularisation d'un écart de comptage — 2026-09-22

- **Décisions du propriétaire** (2026-09-22) : 4 types de résolution
  (`erreur_de_comptage`, `retrouve`, `vol_presume`, `casse_deja_enregistree`),
  motif obligatoire sauf `erreur_de_comptage` ; la régularisation est une
  **traçabilité pure** (jamais d'effet sur le stock — la correction physique
  passe par les fonctions C4) ; plafond de vraisemblance amorcé à `a_definir`
  (aucun comptage refusé tant que le propriétaire ne fixe pas de valeur).
- **Coordination** : partie serveur développée d'abord sans toucher
  `tableau-bord.html` (C10 en cours chez un autre agent), puis bouton ajouté
  après feu vert explicite.
- **Livré** : migration 032 (+ inverse) — table `regularisations_ecarts_comptage`
  (UNIQUE par comptage, CHECK type + motif, RLS responsable), fonction
  `regulariser_ecart_comptage()` `SECURITY DEFINER` réservée à `qf_responsable`,
  paramètre `plafond_vraisemblance_comptage` ; route
  `POST /inventaire/ecarts/{id}/regulariser` ; contrôle du plafond dans
  `POST /inventaire/comptages` (inactif tant que `a_definir`) ; bouton
  « Régulariser » avec mini-formulaire sur chaque écart du tableau de bord ;
  `GET /inventaire/ecarts` exclut les comptages déjà régularisés.
- **Preuves** : pytest **218/218** (9 tests dédiés), suite SQL
  **000-032 + inverses** verte (5 contrôles ajoutés), Playwright
  `verifier-inventaire-reel.mjs` **17/17** et `verifier-cablage.mjs`
  **94/94**.
- **Score** : C7 **55 % → 60 %**. Moyenne indicative ≈ 70 %.
- **Reste (C7)** : valeur du plafond à fixer par le propriétaire
  (paramètre `a_definir`).

---

### Cycle 38 — C2 : durée de session décidée + réinitialisation de mot de passe — 2026-09-22

- **Décisions du propriétaire** (2026-09-22) : session = **8 heures**
  (480 min, valeur DÉCIDÉE en base — plus `a_definir`) ; réinitialisation =
  le responsable **saisit** le nouveau mot de passe (>= 8 caractères),
  jamais restitué, changement forcé à la première connexion.
- **Livré** : migration 033 (+ inverse) — `duree_session_minutes` décidée
  et tracée ; `duree_session_minutes_decidee()` (`SECURITY DEFINER`, fenêtre
  minimale pour `qf_app`, NULL si non décidée) ; `reinitialiser_mot_de_passe_agent()`
  (`SECURITY DEFINER`, réservée à `qf_responsable` : bcrypt `$2a$` 12 tours,
  `doit_changer_mot_de_passe` forcé, `tentatives_echouees` remises à zéro,
  trace dans `journal_comptes`, refuse un compte responsable) ;
  `auth.py`/`securite.py` : durée lue en base à chaque connexion (repli
  config.ini) ; route `PATCH /admin/comptes/{id}/mot-de-passe` + bouton
  « Réinitialiser le mot de passe » dans `comptes.html` ; jeu d'essai et
  suite SQL étendus ; `verifier-comptes-reel.mjs` étendu (parcours réel
  ancien mdp refusé / nouveau accepté).
- **Preuves** : pytest **224/224** (6 tests dédiés), suite SQL
  **000-033 + inverses** verte (3 contrôles ajoutés), Playwright
  `verifier-comptes-reel.mjs` **13/13**, `verifier-cablage.mjs` **94/94**.
- **Score** : C2 **72 % → 77 %**. Moyenne indicative ≈ 70 %.
- **Reste (C2)** : limiteur de débit partagé (rattaché à C11).

---

### Cycle 39 — C1/C4, point f sous-chantier 1 : quantités décimales par article — 2026-09-22

- **Diagnostic** : audit lecture seule des chantiers les moins avancés
  hors inventaire/Playwright et hors C12 (C14, C10, C9 traités aux
  cycles 36-37), puis diagnostic C1/C4 avec preuve fichier:ligne. Point
  f de l'addendum (remises, casse, unités de vente, articles offerts)
  identifié comme condition bloquante pour dépasser ≈ 90-92 % sur C4 —
  5 questions posées au propriétaire, réponses reçues et consignées
  dans `ADDENDUM_CAHIER_DES_CHARGES.md` (PR #44), plan en 4
  sous-chantiers validé, unités décimales retenues comme premier
  (prérequis technique des 3 autres).
- **Livré (sous-chantier 1 seulement)** : `articles.quantite_decimale_autorisee`
  (BOOLEAN, défaut FALSE — entier seulement par défaut) ; colonnes de
  quantité `INTEGER` → `NUMERIC(12,3)` sur `stocks_sites`,
  `mouvements_stock`, `comptages_stock` (dont la colonne générée `ecart`),
  `ventes_lignes`, `ecarts_stock_ventes.quantite_manquante` (valeur
  dérivée, trouvée par relecture exhaustive d'`information_schema.columns`
  — sinon arrondie en silence à l'insertion) ; `candidats_rapprochement()`
  (migration 030) redéfinie pour la même raison ; 4 déclencheurs
  `SECURITY DEFINER` refusant une quantité non entière si l'article ne
  l'autorise pas (`SECURITY DEFINER` nécessaire — trouvé par exécution
  que `qf_agent_stock` n'a pas de `GRANT SELECT` sur la nouvelle
  colonne) ; les 6 fonctions de stock (migration 028) réécrites en
  `NUMERIC(12,3)`, mêmes règles métier, mêmes verrous `FOR UPDATE` ;
  `GET/POST/PUT /articles` exposent et acceptent le nouveau champ pour
  les rôles autorisés. Schémas Pydantic : quantités **requête** en
  `Decimal` (indispensable pour que psycopg envoie un type `NUMERIC`
  compatible avec la signature des fonctions — un `float` est envoyé en
  `double precision`, non résolu automatiquement contre `NUMERIC`,
  trouvé par exécution), quantités **réponse** en `float` (JSON propre,
  cohérent avec les prix).
- **Migration renumérotée 033 → 034** : le numéro 033 a été pris par le
  chantier C2 (cycle 38, ci-dessus) pendant que ce travail était en
  cours — branche rebasée sur `main` après fusion de C7 (migration 032)
  et C2 (migration 033), un conflit textuel dans
  `db/tests/01_protections.sql` (sections numérotées) résolu par simple
  concaténation dans l'ordre 7/8/9.
- **Vérifié par exécution réelle**, rejoué intégralement après le rebase
  sur une base et un serveur dédiés (`quincaillerie_point_f`, port 8020,
  worktree `_worktrees/piste-point-f`, pour ne pas perturber le travail
  en parallèle) : suite SQL **000-034 + inverses** verte (protections
  50/50, habilitations 53/53, concurrence, réversibilité — 5 contrôles
  dédiés au point f : entrée/casse/comptage décimal refusés sur un
  article entier-seul, acceptés une fois autorisé, valeur exacte non
  arrondie) ; pytest complet **224/224**, 0 régression ;
  `verifier-cablage.mjs` **94/94** (contrôle anti-fuite de quantité pour
  l'agent comptabilité affiné pour exclure ce booléen de configuration,
  qui n'est pas une quantité réelle).
- **Score** : C1 **85 % → 87 %**, C4 **80 % → 83 %**. Moyenne indicative
  ≈ 70 %.
- **Reste** : écran non câblé (case à cocher sur la fiche article,
  `stock.html`) ; sous-chantiers 2 à 4 du point f (retours enrichis,
  remises, article offert), non commencés ; `db/tests/DERNIER_RESULTAT.md`
  reste figé au cycle 2 (signalé, non corrigé ce cycle — hors scope) ;
  crédit client (C1, point b) toujours le plus gros levier non construit.

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
branche se sont enchaînées sans accroc cette fois). Le lot de 4 chantiers
suivant (cycles 20 à 23 — correction diagnostic C13, sauvegarde/
restauration C12, sécurité applicative C11, bascule vue C8) est
**terminé et fusionné** (PR #22/#23/#24/#25, empilées dans l'ordre,
mêmes garanties que ci-dessus). Le **travail en parallèle** (cycles 24 à
26 — corrections UX C9/C10, clôture de caisse C6, sauvegarde C12) est
**terminé et fusionné** (PR #28/#27/#26, dans l'ordre décidé à l'avance,
chacune rebasée sur `main` juste avant sa fusion — voir le journal
ci-dessus pour le détail des conflits résolus et la revérification
complète effectuée par la session de coordination).

### Décisions du propriétaire obtenues le 2026-09-13 (hors cycle de code)

Cinq points de l'addendum tranchés dans leur décision structurante, sans
qu'aucun code n'ait encore été écrit pour les appliquer — chacun reste un
chantier à part entière, avec son propre diagnostic et son propre plan
avant tout code (voir `ADDENDUM_CAHIER_DES_CHARGES.md`, callouts
« Décidé (2026-09-13) » sous chaque point pour le détail complet) :

- **Point c** (numéro facturier + vendeur) : un facturier **par site**
  (préfixe `MAG-`/`CPT-`), les deux obligatoires sur chaque vente. Débloque
  un chantier C5.
- **Point g** (clôture de caisse) : une clôture **par site**, écran de
  rapprochement espèces/recettes tel que proposé dans l'addendum.
  **Livré au cycle 25** (C6 85 %) — reste le lien visuel depuis le tableau
  de bord et les sous-questions non bloquantes (fond de caisse initial,
  seuil d'écart à fixer).
- **Point h** (rôle caissier) : créé, **fusionné** avec le périmètre de
  l'agent comptabilité (encaisse ET saisit) — la cohérence exacte avec le
  rôle `agent_comptabilite` existant (fusion des deux, ou rôle distinct à
  droits identiques) reste à trancher au diagnostic du chantier. Débloque
  un chantier C3.
- **Point i** (RPO/RTO) : RPO cible **1 heure**. Livré au cycle 26
  (planification automatique réelle, fichier d'état daté, journal
  d'événements Windows), voyant câblé au cycle 27, chiffrement des
  sauvegardes + sauvegarde sans session Windows + PostgreSQL comme service
  livrés au **cycle 28** (C12 92 %) ; reste l'enregistrement réel du
  service PostgreSQL et de la tâche planifiée (admin requis, scripts
  prêts) et un test de restauration sur un second poste physique.
- **Point l** (propriété du code) : déjà résolu en pratique, formalisé
  dans `OWNERSHIP.md` (nouveau) — audit de l'historique Git complet
  confirmant qu'aucun secret réel n'y a jamais été committé. **Clos**, ne
  débloque aucun chantier de code.

### Décisions du propriétaire obtenues le 2026-09-19 (hors cycle de code)

Trois décisions supplémentaires, sans code écrit — consignées dans
`VISION_PRODUIT.md` (les deux premières, valables pour toute la gamme
Akuma) et dans `ADDENDUM_CAHIER_DES_CHARGES.md` (la troisième, qui touche
le modèle de données du premier client) :

- **UX-0** (méthodologie de mesure) : deux critères distincts — **prise en
  main** (1ᵉʳ essai d'un testeur naïf) et **usage courant** (3ᵉ essai du
  même testeur) — relevés séparément ; une campagne exige 3 testeurs
  différents dont au moins un jamais impliqué dans le projet. Débloque la
  2ᵉ campagne humaine réelle de C9/C10 (candidat 6 ci-dessous).
- **Point k** (cibles d'acceptation) : chiffré pour chaque parcours, deux
  temps (usage courant bloquant, prise en main indicateur) + critères
  qualitatifs (débordement, message technique, confirmation, retour
  arrière). Deux valeurs transmises méritent une re-confirmation avant
  toute campagne (incohérence relevée dans `VISION_PRODUIT.md`, non
  corrigée d'elle-même).
- **C5, question 3** (le vendeur) : le champ vendeur pointera une **fiche
  employé** (`employes`, C6), jamais un compte utilisateur — un employé
  peut vendre sans jamais se connecter. Débloque le rapport « écarts de
  prix par vendeur » (devient un rapport par employé), mais exige d'abord
  une migration de `ventes.vendeur_id` (`utilisateurs` → `employes`) et la
  réécriture de `GET /ventes/vendeurs` — chantier à part entière, non
  démarré.

### Décisions du propriétaire obtenues le 2026-09-19, seconde série (hors cycle de code)

Cinq décisions supplémentaires le même jour, toujours sans code écrit :

- **Point a, question 4 — DÉCISION STRUCTURELLE** : une seule fiche article
  par boutique, le stock réparti par site (jamais une fiche par site) ;
  transfert qui crée l'emplacement de destination s'il n'existe pas —
  **inverse l'implémentation actuelle**. Impact précis sur C1/C3/C4/C7/C8 et
  plan de migration consignés dans `ADDENDUM_CAHIER_DES_CHARGES.md`, point
  a ; principe gamme dans `VISION_PRODUIT.md`. **Confirmé comme cycle à
  part entière, à mener avant l'import du stock initial (point j).**
  Sous-question laissée ouverte : règle de rapprochement pour fusionner les
  fiches homonymes existantes (un article par site aujourd'hui) — à
  trancher avant d'écrire cette migration.
- **Point d, question 1** (régime fiscal) : seuil légal >50 M FCFA/an ⇒
  régime réel, TVA 19,25 % — confirme la valeur déjà appliquée depuis le
  cycle 6. Question 3 (prix saisis HT ou TTC) reste ouverte, hypothèse de
  travail (TTC) non validée par le comptable — **aucun code à écrire tant
  qu'elle n'est pas confirmée**.
- **Point b** (crédit client) : tranché en détail (créance jamais recette,
  identification nom+téléphone, plafond par défaut 100 000 FCFA pour
  Franck configurable par boutique, dépassable au cas par cas, règlements
  partiels, tableau de bord avec échéancier 30/60/90 jours, aucune relance
  ni intérêt en v1, fonction togglable par boutique dans la gamme). Reprise
  de 15 à 25 clients depuis un cahier de crédit, à charger avec le stock.
  Paiements mixtes (question 3) et qui enregistre un règlement (question 5,
  partiel) restent sans réponse explicite.
- **Point j** (volumétrie) : 800-1 200 références, 40-120 ventes/jour selon
  affluence, comptage par le responsable et les vendeurs sur 3-5 jours,
  boutique ouverte, par zones puis catégories. Outil d'import repensé :
  chargements partiels et successifs obligatoires (un import global ne
  convient pas), sans duplication, articles trouvés hors cahier créés après
  validation du responsable. Dépend du point a (migration article/stock
  d'abord).
- **Vendeurs** : confirmation du point c (fiche employé, jamais compte) —
  4 à 6 vendeurs réels dont des aides occasionnels sans contrat, besoin
  quotidien du responsable de savoir qui a vendu quoi.

Restent réellement non tranchés : les paiements mixtes et l'enregistrement
d'un règlement (sous-questions du point b), la confirmation HT/TTC par le
comptable (point d, question 3), la règle de rapprochement des fiches
homonymes (point a). Le point **k** reste tranché depuis la première série
du jour.

### Candidats

1. ~~**Vérification C10 depuis un vrai téléphone physique**~~ — **fait**
   le 2026-09-13 (campagne UX ci-dessus, section B).
2. ~~**Mesures humaines de `UX_BASELINE.md`**~~ — **fait** le 2026-09-13.
3. ~~**C6 (clôture de caisse, point g)**~~ et ~~**C12 (automatisation des
   sauvegardes, point i)**~~ — **faits** aux cycles 25 et 26 (travail en
   parallèle, ci-dessus).
4. ~~**Corriger les constats UX les plus gênants (§4 bis)**~~ — **fait
   partiellement** au cycle 24 : 7 des 11 constats corrigés ou confirmés
   non défectueux (UX-1, UX-2, UX-3, UX-4, UX-6, UX-7, UX-9, UX-10).
5. ~~**Câblage visuel des deux voyants de tableau de bord**~~ — **fait** au
   cycle 27 : lien vers `cloture-caisse.html` et carte « Dernière
   sauvegarde » (3 états réels vérifiés).
6. **Deuxième campagne humaine réelle** (`UX_BASELINE.md`, à mettre à jour
   avec le protocole ci-dessous avant de la lancer), pour confirmer dans
   les conditions d'origine ce que le cycle 24 a corrigé par preuve
   automatisée seule : les cibles chiffrées de C9/C10 (point k, tranché le
   2026-09-19 — voir `VISION_PRODUIT.md`), mesurées séparément en prise en
   main (1ᵉʳ essai) et en usage courant (3ᵉ essai), sur 3 testeurs
   différents dont au moins un nouveau. ~~Nécessite de trancher UX-0~~ —
   **fait le 2026-09-19**, ne bloque plus le lancement de la campagne.
7. **Constats UX restants, non traités par le cycle 24** : UX-5 (saisie
   d'une recette au téléphone toujours trop lente), UX-8 (annuler une
   ligne du panier toujours introuvable seul par un utilisateur non
   formé). ~~UX-0~~ **tranché le 2026-09-19** (voir ci-dessus).
8. ~~**C3 (rôle caissier, point h)**~~ — **fait** au cycle 27 : diagnostic
   par exécution, aucun code nécessaire, architecture déjà conforme.
   ~~**C5 (numéro facturier + vendeur, point c)**~~ — **fait au cycle 27,
   périmètre réduit au socle décidé** : numéro + vendeur obligatoires,
   préfixe par site. **Question 5 (seuil) tranchée le 2026-09-18** : 10 %
   sous le prix catalogue, en configuration, signale sans bloquer.
   **Rapport « écarts de prix par vendeur » toujours à construire**
   (chantier non démarré, candidat pour un prochain cycle), devenu un
   **rapport par employé** suite à la question 3, **tranchée le
   2026-09-19** (voir le callout du point c dans l'addendum) : le vendeur
   est une fiche employé (`employes`, C6), jamais un compte utilisateur.
   Ne peut pas encore être codé : exige d'abord une migration de
   `ventes.vendeur_id` (`utilisateurs` → `employes`) et la réécriture de
   `GET /ventes/vendeurs`, non démarrées.
9. **Sous-questions non bloquantes du point g** (fond de caisse initial,
   rattachement d'une vente saisie en retard, rapprochement Mobile Money
   exact, seuil d'écart de caisse à fixer, blocage d'une saisie après
   clôture) — chacune peut être tranchée indépendamment, sans bloquer le
   reste.
10. **C13 — reste de la portabilité CI** (`PGHOST`/`PGPORT` et mot de passe
    de test propres au poste de développement, lisibles par variables
    d'environnement plutôt que figés dans `conftest.py`). Le pipeline CI
    (fichier de workflow) est **livré au cycle 33** (`.github/workflows/ci.yml`,
    vert sur GitHub) ; ce reste-ci est un confort de portabilité, plus
    bloquant.
11. ~~**C0-C — outil de création du premier compte responsable**~~ — **fait
    au cycle 31** (2026-09-20) : migration 023 (`creer_premier_responsable()`,
    `SECURITY DEFINER`, réservée à `qf_app`) + `db/outils/creer_compte_responsable.ps1`.
    Prouvé par exécution sur une base vierge : création du compte, refus si un
    responsable existe, connexion réelle via `verifier_connexion()`, 7/7 tests
    dédiés, suite pytest complète 190/190. Reste du périmètre C0 : kiosque,
    CI, lockfile.
12. ~~**C2 — gestion des comptes depuis l'application**~~ — **fait au cycle 32**
    (2026-09-20) : routes `/admin/comptes` + écran `maquette/comptes.html`,
    migration 024 (`compte_est_actif()`) pour couper immédiatement la session
    d'un compte désactivé. Prouvé : 10/10 tests dédiés, Playwright
    `verifier-comptes-reel.mjs` 21/21, `verifier-cablage.mjs` 94/94, SQL
    000-024 + inverses OK, pytest 200/200. Reste C2 : durée de session
    définitive, réinitialisation de mot de passe par le responsable (hors
    périmètre), limiteur de débit partagé.
13. **Migration article/stock multi-site (point a, décidé le 2026-09-19)** —
    cycle à part entière, le plus lourd des candidats non encore démarré :
    touche C1 (nouvelle table de stock par site), C3 (RLS repensée), C4
    (fonctions de stock réécrites), C7 (comptage par article+site), C8
    (alertes/totaux par site). Impact détaillé et plan de migration dans
    `ADDENDUM_CAHIER_DES_CHARGES.md`, point a. **Doit précéder** le
    candidat 15 (import du stock initial) — ordre non négociable, confirmé
    par le propriétaire. (Anciennement candidat 11 du cycle 29.)
    **13a livré au cycle 34 (2026-09-20)** : mécanisme de rapprochement des
    fiches homonymes prêt et prouvé — migration 025 (`rapprochements_articles`,
    `candidats_rapprochement()`, `enregistrer_rapprochement()`) +
    `db/outils/rapprocher_articles.ps1` (suggestion automatique nom strict,
    validation humaine une par une, jamais de fusion aveugle) ; preuve réelle :
    jeu d'essai sans homonyme → « aucune paire », paire synthétique injectée →
    décision `fusionner` enregistrée, plus aucune paire restante ; 10/10 tests
    dédiés. **13b livré au cycle 35 (2026-09-21)** : migrations 026-031 +
    inverses, fonctions de stock sur `stocks_sites`, RLS/GRANT révisés,
    routes et écrans adaptés — pytest 209/209, suite SQL 000-031 verte,
    7 suites Playwright réelles vertes (stock 26/26, inventaire 17/17,
    vente 12/12, rapports 29/29, caisse 24/24, rh 21/21, câblage 94/94).
    **Reste pour ce candidat** : import du stock initial multi-site
    (désormais le candidat 15), régularisation d'écart d'inventaire.
14. **Crédit client (point b, décidé le 2026-09-19)** — chantier C5/C1 non
    démarré : table clients, créance vs. recette, plafond configurable,
    règlements partiels, tableau de bord avec échéancier 30/60/90 jours,
    activable/désactivable par boutique. Reprise de 15-25 clients à charger
    avec le stock (candidat 15). Paiements mixtes et qui enregistre un
    règlement restent à préciser si le besoin se confirme en pratique.
    (Anciennement candidat 12 du cycle 29.)
15. **Import du stock initial et volumétrie (point j, décidé le
    2026-09-19)** — outil à chargements partiels/successifs, sans
    duplication, création d'articles non répertoriés après validation du
    responsable ; charge aussi les 15-25 clients à crédit du candidat 14.
    **Bloqué tant que le candidat 13 n'est pas livré** (importer dans
    l'ancien modèle doublerait le travail). (Anciennement candidat 13 du
    cycle 29.)
