# Base de données — migrations, outils et tests (chantier C1)

Le schéma d'origine (`QuincaillerieFranck_Test/creation_base_donnees.sql`) est
**conservé tel quel** : c'est le point de départ. Tout ce qui suit le **corrige**
par migrations successives, jamais en le remplaçant.

```
db/
├── migrations/   NNN_nom.sql + NNN_nom_inverse.sql, appliquées dans l'ordre
├── outils/       migrer.sh, prevol.sql, definir_mot_de_passe_app.sql,
│                 creer_compte_responsable.ps1, rapprocher_articles.ps1,
│                 demarrer_pg.ps1, arreter_pg.ps1
└── tests/        vérification PAR EXÉCUTION (protections, habilitations, concurrence)
```

---

## Environnement de développement local (`_pgdev/`)

Pour travailler sur ce projet, il n'est **pas nécessaire d'installer PostgreSQL**
au sens habituel (pas de MSI, pas de droits administrateur, pas de service
Windows). Deux scripts PowerShell suffisent :

```powershell
# Démarrer (télécharge et initialise tout seul la toute première fois)
.\db\outils\demarrer_pg.ps1

# Arrêter
.\db\outils\arreter_pg.ps1
```

Ce que fait `demarrer_pg.ps1`, la première fois :

1. télécharge PostgreSQL 17 en **binaires portables** (~330 Mo, une seule fois)
   et les installe dans `_pgdev\pgsql\` ;
2. initialise une base neuve dans `_pgdev\data\`, avec un mot de passe de
   **développement local fixe** : `qf_dev_local` (utilisateur `postgres`) ;
3. démarre le serveur sur `127.0.0.1:5433`.

Les fois suivantes, il se contente de démarrer le serveur (idempotent : le
relancer alors qu'il tourne déjà ne fait rien).

**`_pgdev\` n'est jamais versionné** (voir `.gitignore`) : c'est un dossier de
travail local, environ 1 Go, propre à chaque poste. Il peut être supprimé et
recréé à tout moment en relançant `demarrer_pg.ps1` — c'est d'ailleurs le test
de reproductibilité à faire de temps en temps.

> **Pourquoi pas le dossier temporaire de Windows ?** Le tout premier
> environnement de ce cycle avait été installé dans le dossier temporaire de la
> session (`%TEMP%\...`), que Windows peut purger à tout moment (redémarrage,
> nettoyage de disque). `_pgdev\` vit **dans le dépôt** (mais hors de Git) :
> stable, à côté du code qui l'utilise.

> **Mot de passe `qf_dev_local`.** C'est un mot de passe de développement
> local, jamais transmis nulle part, propre à une base qui ne contient que des
> données de test. Ce n'est pas le mot de passe de `qf_app` (voir plus bas), qui
> lui protège les rôles applicatifs à privilèges restreints et **doit** être
> choisi et gardé secret pour un déploiement réel.

---

## Bases dédiées au travail en parallèle (voir `RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`)

Trois pistes travaillent en même temps sur ce dépôt (une session Claude
Code par piste, chacune dans son propre worktree Git). Une seule instance
PostgreSQL (`127.0.0.1:5433`, celle de `_pgdev\`) héberge **quatre bases
distinctes** : la base de développement/tests habituelle plus une par
piste — deux migrations simultanées sur la **même** base se détruiraient
l'une l'autre.

| Base | Piste | Worktree | Port serveur (uvicorn) |
|---|---|---|---|
| `quincaillerie_test` | (aucune — tests automatisés du dépôt principal, `pytest`/Playwright) | dépôt principal | 8010 (convention des suites) |
| `quincaillerie_ux` | UX (corrections `UX_BASELINE.md`) | `_worktrees/piste-ux` | 8011 |
| `quincaillerie_c6` | C6 (comptabilité et RH) | `_worktrees/piste-c6` | 8012 |
| `quincaillerie_c12` | C12 (sauvegarde et exploitation) | `_worktrees/piste-c12` | 8013 |

Chaque worktree a son propre `server/config.ini` (jamais versionné, comme
d'habitude) pointant vers **sa** base et déclarant son port de
convention ci-dessus. Les trois pistes peuvent partager le même
environnement virtuel Python (`server/.venv/` du dépôt **principal**) :
appeler `python.exe` par son chemin absolu avec `--app-dir` pointé sur le
`server/` du worktree suffit, sans réinstaller les dépendances trois
fois.

**Vérifié par exécution (2026-09-14)** : les trois bases créées (schéma
d'origine + 19 migrations + jeu d'essai chacune), un article marqueur
inséré directement dans `quincaillerie_ux` puis recherché dans les trois
autres bases — **absent partout ailleurs**, preuve d'isolation réelle,
pas seulement nominale. Les trois serveurs démarrés simultanément sur
8011/8012/8013 ont tous répondu `200` sur `/sante`, et un second marqueur
inséré via une requête HTTP réelle sur le port 8011 (piste UX) n'est
apparu que dans `quincaillerie_ux` — la séparation tient de bout en bout,
de la requête réseau à la ligne en base.

### Remettre une base de piste à neuf

Identique à la préparation de `quincaillerie_test`, avec le nom de base
de la piste concernée :

```bash
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=postgres PGPASSWORD=qf_dev_local
BASE=quincaillerie_ux   # ou quincaillerie_c6, quincaillerie_c12

psql -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$BASE' AND pid<>pg_backend_pid();" \
     -c "DROP DATABASE IF EXISTS $BASE;" -c "CREATE DATABASE $BASE;"
psql -d "$BASE" -v ON_ERROR_STOP=1 -f QuincaillerieFranck_Test/creation_base_donnees.sql
PGDATABASE="$BASE" bash db/outils/migrer.sh appliquer
psql -d postgres -c "ALTER ROLE qf_app WITH PASSWORD 'qf_app_dev_local';"   # voir le piège du cycle 20/21
psql -d "$BASE" -v ON_ERROR_STOP=1 -f db/tests/00_jeu_essai.sql
```

Chaque piste ne touche **que** sa propre base — jamais
`quincaillerie_test`, jamais celle d'une autre piste. À la fin du travail
en parallèle (toutes les pistes fusionnées), ces trois bases peuvent être
supprimées ; elles ne contiennent que du jeu d'essai, jamais de donnée
réelle.

---

## Appliquer les migrations

```bash
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=postgres PGDATABASE=quincaillerie_test
export PGPASSWORD=qf_dev_local   # dev local ; jamais un vrai secret dans le dépôt

# 1. Sur une base contenant DÉJÀ des données : vérifier ce qui bloquerait
psql -f db/outils/prevol.sql     # toute ligne avec nb_lignes > 0 est à traiter

# 2. Appliquer
db/outils/migrer.sh appliquer

# 3. Voir l'état
db/outils/migrer.sh etat

# 4. Revenir en arrière si besoin
db/outils/migrer.sh annuler
```

En déploiement réel, `PGPORT` est `5432` (le port par défaut de PostgreSQL) et
`PGPASSWORD` est le vrai mot de passe du serveur — jamais celui ci-dessus.

Chaque fichier est exécuté **dans une transaction unique** avec `ON_ERROR_STOP` :
une migration passe en entier, ou pas du tout. La table `schema_migrations`
enregistre ce qui est appliqué.

### Mot de passe du compte applicatif

Il n'est **jamais** dans le dépôt :

```bash
psql -v mdp="'LeMotDePasseChoisi'" -f db/outils/definir_mot_de_passe_app.sql
```

Puis reporter la valeur dans `config.ini` (fichier local, non versionné), avec
`user = qf_app`. **Ne plus jamais faire tourner l'application sous `postgres`.**

### Premier compte responsable (chantier C0-C, cycle 31)

Sur une installation neuve, aucun compte n'existe : personne ne peut se
connecter. L'outil console ci-dessous crée le **tout premier** compte
`responsable` via la fonction `creer_premier_responsable()` (migration 023,
`SECURITY DEFINER`, réservée à `qf_app`) :

```powershell
powershell -File db\outils\creer_compte_responsable.ps1
# ou avec un config.ini précis :
powershell -File db\outils\creer_compte_responsable.ps1 -ConfigIni "C:\...\config.ini"
```

Il refuse si un responsable existe déjà, si l'identifiant est vide ou déjà
pris, ou si le mot de passe fait moins de 8 caractères. Le mot de passe est
demandé en mode masqué et haché en base (bcrypt `$2a$`, 12 tours). Pour la
vérification automatisée, les variables `QF_PREMIER_COMPTE_NOM`,
`QF_PREMIER_COMPTE_IDENTIFIANT` et `QF_PREMIER_COMPTE_MOT_DE_PASSE`
remplacent les invites.

### Rapprochement des fiches articles homonymes (chantier 13a, cycle 34)

Avant la migration article/stock multi-site (cycle 13b), deux articles de
**même nom sur des sites différents** doivent être rapprochés par un humain,
une par une — jamais de fusion automatique (décision du propriétaire du
2026-09-20). L'outil console ci-dessous liste les paires candidates
(`candidats_rapprochement()`, migration 025, `SECURITY DEFINER`, réservée à
`qf_app`) et enregistre chaque décision `fusionner` ou `distincts`
(`enregistrer_rapprochement()`) :

```powershell
powershell -File db\outils\rapprocher_articles.ps1
# ou avec un config.ini précis :
powershell -File db\outils\rapprocher_articles.ps1 -ConfigIni "C:\...\config.ini"
```

Pour la vérification automatisée, les variables
`QF_RAPPROCHEMENT_ARTICLE_1`, `QF_RAPPROCHEMENT_ARTICLE_2`,
`QF_RAPPROCHEMENT_DECISION` (`fusionner`/`distincts`) et
`QF_RAPPROCHEMENT_DECIDE_PAR` traitent une paire unique sans invite. Les
décisions sont consignées dans `rapprochements_articles` et seront
**consommées** par la migration de données du cycle 13b.

---

## Ce que chaque migration corrige

| # | Migration | Ce qu'elle rend impossible |
|---|-----------|----------------------------|
| 000 | `socle_migrations` | (socle) toute évolution de schéma non tracée |
| 001 | `contraintes_domaine` | stock négatif, prix négatif, quantité vendue ≤ 0, TVA à 500 %, total ≠ sous-total + TVA, ticket numéroté, vente « payée » sans caissier, agent sans site, congé finissant avant de commencer |
| 002 | `coherence_inter_tables` | vendre au Comptoir un article du Magasin ; compter deux fois la recette d'une même vente |
| 003 | `ecart_inventaire_calcule` | **écrire soi-même l'écart d'inventaire**, forger la quantité attendue, modifier un comptage après coup, recompter jusqu'à tomber juste |
| 004 | `audit_non_destructible` | effacer l'historique de prix en supprimant l'article, supprimer une ligne de journal, supprimer une vente |
| 005 | `journaux_audit` | annuler une vente sans laisser de trace, l'annuler deux fois, antidater l'annulation, « dé-encaisser » une vente |
| 006 | `parametres_applicatifs` | écrire un taux de TVA en dur ; **appliquer en silence une règle fiscale non tranchée** |
| 007 | `index_recherche` | (performance) la recherche d'article par balayage complet |
| 008 | `roles_applicatifs` | se connecter en superutilisateur ; qu'un agent stock LISE un prix ; qu'un comptable LISE une quantité en stock ; que quiconque modifie le seuil d'alerte à la main |
| 009 | `authentification` | que quiconque (y compris le serveur applicatif) LISE un hachage de mot de passe ; vérifier un mot de passe ailleurs qu'à un seul endroit audité ; changer le mot de passe d'un tiers via le libre-service |
| 010 | `correction_usage_qf_app` | corrige un oubli de 008 : `qf_app` ne pouvait exécuter AUCUNE fonction, faute d'accès au schéma (`USAGE ON SCHEMA public` manquant) |
| 011 | `ventes_fiscalite_anti_survente` | appliquer une TVA inventée (paramètres fiscaux décidés par le propriétaire, cycle 6) ; bloquer une vente déjà encaissée pour stock insuffisant au lieu de consigner l'écart |
| 012 | `comptage_aveugle_colonnes` | qu'un agent stock LISE `ecart` ou `quantite_attendue` d'un comptage, y compris après coup, y compris en SQL direct |
| 013 | `fuseau_horaire_boutique` | que le « jour » vu par `CURRENT_DATE`/`NOW()` dépende du fuseau du système d'exploitation du poste serveur plutôt que de l'heure réelle de la boutique (Africa/Douala) |
| 014 | `articles_stock_transferts_retours` | confondre un transfert, une casse ou un retour avec une correction de quantité ; qu'un transfert ou un retour recalcule le seuil d'alerte ; qu'un agent stock agisse sur le stock d'un **autre** site via une réception, un transfert ou un retour (trois failles latentes trouvées par exécution en exposant des fonctions du cycle 2 par une route pour la première fois) |
| 015 | `articles_autre_site` | qu'un agent stock lise un prix ou une quantité de l'AUTRE site pour choisir la destination d'un transfert (cycle 11, écran de stock) — une fenêtre volontairement étroite : id, nom, unité, site seulement |
| 016 | `retours_coherence_document_origine` | qu'un retour client porte sur un article jamais vendu dans la vente référencée ; qu'un retour (client ou fournisseur), cumulé sur plusieurs retours contre le MÊME document, dépasse la quantité réellement vendue ou reçue par ce document précis (constat n°2, contrôle de boucle après le cycle 9 — le rattachement à la vente/réception d'origine n'était qu'une traçabilité, jamais une garantie de cohérence) |
| 017 | `annulation_vente_regularisation_ecart` | annuler une vente sans restituer le stock RÉELLEMENT décrémenté (pas la quantité vendue — une vente à découvert, point e, n'avait pas tout décrémenté) ni contre-passer la recette ; annuler une vente déjà annulée ; « régulariser » un écart de vente à découvert dans le mauvais sens ou deux fois ; **faille trouvée par exécution en écrivant ce cycle** — `decrementer_stock_vente()` (cycle 6) ne renseignait jamais `mouvements_stock.vente_id`, rendant tout retour à la vente d'origine impossible (corrigé ici, colonne restée nullable pour ne pas inventer un rattachement rétroactif fiable) |
| 018 | `revocation_jetons` | qu'un jeton signature-valide et non expiré reste utilisable après une déconnexion explicite (`POST /auth/deconnexion`) — jusqu'ici la seule limite documentée de `securite.py` ; résout au passage le partage entre plusieurs processus applicatifs, PostgreSQL servant de registre commun |

---

## Fuseau horaire — Africa/Douala, jamais hérité du système d'exploitation

Trouvé par exécution lors d'un contrôle de boucle après le cycle 7 :
`SHOW TimeZone` renvoyait `Europe/Paris` sur la base de développement, alors
que le poste serveur sera physiquement à Batouri, Cameroun
(`Africa/Douala`, UTC+1, jamais d'heure d'été). `CURRENT_DATE`/`NOW()`
déterminent le « jour » utilisé par :
- l'unicité d'un comptage d'inventaire (« un par article, par moment, par
  jour », migration 003) ;
- les écrans « du jour » : ventes (`GET /ventes/synthese-jour`, C5) et
  écarts (`GET /inventaire/ecarts`, `GET /inventaire/ecarts-ventes`, C7).

Un poste serveur dont le fuseau système est mal réglé ne doit **jamais**
pouvoir décaler silencieusement ces dates. Le fuseau est donc fixé à
**deux niveaux indépendants**, ni l'un ni l'autre hérité du système
d'exploitation :

1. **Au niveau de la base** (migration 013) : `ALTER DATABASE ... SET
   timezone TO 'Africa/Douala'` — persiste dans la base elle-même
   (`pg_db_role_setting`), s'applique à toute nouvelle connexion, quel que
   soit le fuseau de l'instance PostgreSQL ou du système d'exploitation.
2. **À chaque connexion applicative** (`server/app/database.py`,
   `FUSEAU_HORAIRE_BOUTIQUE`) : `set_config('TimeZone', 'Africa/Douala',
   ...)` dans `connexion_anonyme()` et `connexion_pour()`. Vérifié par
   exécution en réglant délibérément la base sur `UTC` : les deux méthodes
   de connexion imposaient quand même `Africa/Douala`.

Un déploiement n'a donc **rien à configurer** pour ce point : ni variable
d'environnement, ni réglage du système d'exploitation du poste serveur, ni
paramètre de `config.ini`. Changer de fuseau (si la boutique déménageait un
jour hors du Cameroun) demanderait une nouvelle migration ET une mise à
jour de `FUSEAU_HORAIRE_BOUTIQUE` — un choix délibéré plutôt qu'une valeur
implicite.

---

## Mouvements de stock : catégorie, et le piège `current_user` en SECURITY DEFINER

Depuis la migration 014 (chantier C4), `mouvements_stock.type` (le **sens** :
`entree`/`sortie`, inchangé depuis le schéma d'origine) est complété par
`categorie` (le **pourquoi** : `reception_fournisseur`, `vente`, `transfert`,
`casse`, `retour_client`, `retour_fournisseur`) — colonne `NOT NULL`, donc
**toute** fonction qui écrit dans cette table doit la renseigner, y compris
celles qui existaient déjà (`enregistrer_entree_stock`,
`decrementer_stock_vente`) et les scripts de test qui y insèrent directement
(`db/tests/01_protections.sql`).

Deux colonnes de traçabilité, nullables selon la catégorie : `vente_id`
(retour client → la vente d'origine) et `mouvement_origine_id`, une
auto-référence réutilisée pour deux cas — un retour fournisseur (→ la
réception qu'il annule partiellement) et la moitié « entrée » d'un
transfert (→ sa moitié « sortie », même transfert).

**Piège rencontré et vérifié par exécution, à ne pas reproduire** :
à l'intérieur d'une fonction `SECURITY DEFINER`, `current_user` (et
`session_user`) valent l'identité du **propriétaire** de la fonction
(typiquement `postgres`), **pas** l'appelant — contrairement à une
politique RLS ordinaire, où `current_user` reflète bien le rôle réellement
actif (`SET ROLE`). Une première version de `transferer_stock()` vérifiait
`current_user = 'qf_agent_stock'` pour restreindre un agent à son propre
site : cette condition ne se déclenchait **jamais**, laissant n'importe quel
agent transférer depuis n'importe quel site. Trouvé en testant directement
en SQL, pas en relisant le code. La seule source fiable ici est
`qf_site_courant()` (une variable de session, `set_config`, indépendante de
l'identité de rôle) : `qf_site_courant() IS NOT NULL AND site <> qf_site_courant()`
identifie correctement « un agent qui n'est pas sur ce site » (le
responsable, dont `qf_site_courant()` vaut toujours `NULL`, n'est jamais
concerné).

Le même contrôle manquait, pour la même raison, dans trois fonctions du
**cycle 2** (`enregistrer_entree_stock`) et de ce cycle
(`enregistrer_retour_client`, `enregistrer_retour_fournisseur`) : des
failles latentes, jamais exploitables tant qu'aucune route ne les exposait,
corrigées en même temps que leur première exposition par une route HTTP.

---

## Droits accordés — qui peut lire et écrire quoi

Quatre rôles PostgreSQL, **aucun superutilisateur**, aucun droit de modifier le
schéma (pas de `CREATE` sur le schéma `public`).

| Rôle | Nature | Usage |
|------|--------|-------|
| `qf_app` | connexion (`LOGIN`), **`NOINHERIT`** | seul rôle qui se connecte. Aucun droit propre : le serveur fait `SET ROLE` vers le rôle de l'utilisateur authentifié, puis `RESET ROLE`. |
| `qf_responsable` | `NOLOGIN` | les deux sites |
| `qf_agent_stock` | `NOLOGIN` | un site, **aucun prix** |
| `qf_agent_comptabilite` | `NOLOGIN` | un site, **aucune quantité en stock** |

### Table `articles`

| Colonne | responsable | agent stock | agent comptabilité |
|---|---|---|---|
| `id`, `nom`, `categorie`, `unite`, `site_id`, `fournisseur_id` | lire / écrire | lire / écrire¹ | **lire** |
| `prix_achat`, `prix_vente` | lire / écrire | — **aucun accès** | `prix_vente` en lecture seule ; `prix_achat` **aucun accès** |
| `quantite_stock` | lire / écrire | lire / écrire | — **aucun accès** |
| `seuil_alerte` | **lecture seule** | **lecture seule** | — **aucun accès** |
| `actif`, `date_desactivation`, `desactive_par_id` | lire / écrire | lire | lire |

¹ l'agent stock écrit `nom`, `categorie`, `unite`, `quantite_stock` ; il crée un
article **sans prix** (`prix_vente` prend son défaut à 0, le responsable le fixe
ensuite).

> **`seuil_alerte` n'est écrit par personne.** Le cahier des charges §4.2 l'exige :
> « le seuil d'alerte ne peut être modifié par personne directement, afin qu'il
> ne puisse pas servir à dissimuler un vol de marchandise ». Il est recalculé par
> `enregistrer_entree_stock()`, à 20 % de la quantité reçue, **uniquement lors
> d'une entrée de stock**.

### Table `utilisateurs`

| Colonne | responsable | agents |
|---|---|---|
| `mot_de_passe_hash` | **écriture seule** (créer un compte, réinitialiser) — jamais en lecture | **aucun accès** |
| `nom_complet`, `identifiant`, `role`, `site_id`, `actif`, `tentatives_echouees`, `doit_changer_mot_de_passe` | lire / écrire | lire |

> Aucun rôle ne peut **lire** un hachage de mot de passe. La vérification à la
> connexion passera par une fonction dédiée exécutée avec les droits de son
> propriétaire — chantier **C2, cycle 3**.

### Autres tables

| Table | responsable | agent stock | agent comptabilité |
|---|---|---|---|
| `sites`, `parametres` | lire (+ écrire `parametres.valeur`) | lire | lire |
| `fournisseurs` | lire / écrire | lire | lire |
| `ventes`, `ventes_lignes` | lire / écrire | — | lire / écrire |
| `transactions` | lire / écrire | — | lire / ajouter |
| `employes` | lire / écrire | — | `id`, `nom_complet`, `poste`, `site_id`, `actif` en lecture (**pas le salaire**) |
| `absences_conges`, `avances_salaire` | lire / écrire | — | — |
| `mouvements_stock` | lire / écrire | lire / ajouter | — |
| `comptages_stock` | lire / ajouter | lire / ajouter | — |
| `historique_prix_articles` | lire / ajouter | — | — |
| `historique_modifications_articles` | lire / ajouter | lire / ajouter | — |
| `journal_connexions`, `journal_comptes` | lire / ajouter | — | — |
| `comptages_stock_ecarts_declares`, `historique_parametres` | lire | — | — |

Aucun rôle n'a `DELETE` sur quoi que ce soit, ni `TRUNCATE`, ni le moindre droit
de DDL.

### Fonctions de pont (exécutées avec les droits de leur propriétaire)

| Fonction | Qui peut l'appeler | Pourquoi elle existe |
|---|---|---|
| `enregistrer_entree_stock(article, quantité, utilisateur, motif)` | responsable, agent stock | seule voie d'entrée de stock ; recalcule le seuil d'alerte, que personne ne peut écrire |
| `decrementer_stock_vente(article, quantité, utilisateur, motif)` | responsable, agent comptabilité | la comptabilité doit faire baisser le stock **sans avoir le droit d'y toucher ni même de le lire** ; décrément atomique et sérialisé |
| `parametre_texte(clé)` / `parametre_numerique(clé)` | les trois rôles | lecture d'un réglage ; **refuse** de livrer une valeur encore `a_definir` |
| `qf_site_courant()` | les trois rôles | site de l'utilisateur, pour le cloisonnement |

### Cloisonnement par site

`Row Level Security` sur `articles`, `ventes`, `transactions`,
`mouvements_stock` et `comptages_stock`. Le serveur positionne, pour la durée de
la requête :

```sql
SET LOCAL qf.site_id = '2';   -- Comptoir
```

Un agent ne voit alors que les lignes de son site ; le responsable voit les deux.
Ce socle sera exploité et testé plus largement au **cycle 3 (chantier C3)**.

---

## Décisions métier volontairement NON prises

La base **refuse d'inventer** ce que le propriétaire n'a pas tranché. Les
réglages concernés valent `a_definir` et `parametre_texte()` lève une erreur
explicite si l'application tente de les utiliser :

```sql
SELECT * FROM parametres_a_decider;   -- doit être vide avant la mise en production
```

| Paramètre | État |
|---|---|
| `regime_fiscal`, `taux_tva`, `prix_saisis_ttc`, `arrondi_montants` | **Décidés cycle 6** (addendum, point d) : régime du réel, 19,25 %, TTC, arithmétique — plus dans `parametres_a_decider` |
| `boutique_numero_contribuable`, `boutique_telephone` | toujours `a_definir` — le reçu de vente imprimable (cycle 19) existe désormais, mais omet ces deux mentions tant qu'elles ne sont pas renseignées, plutôt que de les inventer |
| `seuil_alerte_plancher`, `tentatives_max_connexion` | valeurs proposées, à confirmer |
| `duree_session_minutes` | règle de session inactive à définir |

Décisions **hors table `parametres`**, appliquées directement dans le
schéma et les fonctions : transfert inter-sites et retours/casse
(addendum, **points a et f**, partiellement — retours et casse seulement),
**décidées cycle 9**, voir `014_articles_stock_transferts_retours.sql`.
Restent non tranchés dans le point f : remises, unités/conversions
décimales — et dans le point j : volumétrie/reprise du stock initial (un
article naît donc toujours à `quantite_stock = 0`).

De même, `decrementer_stock_vente()` **signale** un stock insuffisant avec la
quantité réellement disponible, mais ne décide pas de ce que l'application doit
en faire (refuser la saisie, ou l'accepter avec un écart à régulariser) : c'est
l'**addendum, point e**, qui reste ouvert.

Enfin, la suppression d'une recette liée à une vente annulée n'est pas
verrouillée : le traitement comptable d'une annulation (suppression ou
contre-passation) relève de l'**addendum, points b et g**.

---

## Sauvegarde et restauration (chantier C12, cycle 21)

Le CDC (§4.3) exige une sauvegarde, le dossier de recette (§6) exige de
la tester en la restaurant sur une base séparée — **aucun script ni
procédure n'existait avant ce cycle** (constat du diagnostic d'origine,
`PERIMETRE_LIVRE.md` §5, point 7).

```powershell
# Sauvegarder (produit deux fichiers horodatés dans _pgdev\sauvegardes\)
powershell -File db\outils\sauvegarder.ps1

# Restaurer sur une base SÉPARÉE, jamais par-dessus l'existante
powershell -File db\outils\restaurer.ps1 -FichierBase "_pgdev\sauvegardes\quincaillerie_test_XXXXXXXX_XXXXXX.dump" -NomBaseCible quincaillerie_verif
```

- **Deux fichiers par sauvegarde** : `<base>_<horodatage>.dump` (`pg_dump
  -Fc`, contenu de la base — schéma, données, droits par colonne) et
  `<base>_<horodatage>_roles.sql` (`pg_dumpall --roles-only`, les rôles
  applicatifs — **globaux au serveur PostgreSQL**, donc absents de tout
  `pg_dump` d'une seule base ; nécessaires pour restaurer sur un
  **nouveau** serveur qui ne les a pas encore).
- **`restaurer.ps1` ne restaure jamais par-dessus une base existante** :
  il refuse si `-NomBaseCible` existe déjà, sauf `-Forcer` explicite —
  prouver une restauration veut dire la rejouer À CÔTÉ, jamais écraser
  silencieusement.
- **Vérifié par exécution** (2026-09-13) : sauvegarde de `quincaillerie_test`
  (5 utilisateurs, 4 articles, 1 fournisseur), restaurée dans
  `quincaillerie_test_restauration` — comptes de lignes identiques sur les
  trois tables vérifiées, et **les droits par colonne survivent** :
  `qf_agent_stock` peut relire `articles.nom` mais toujours pas
  `articles.prix_vente`, exactement comme sur la base source
  (`has_column_privilege()`, avant et après restauration).
- **Ce que ce cycle NE tranche PAS** (addendum, point i) : la fréquence à
  laquelle lancer `sauvegarder.ps1`, la durée de conservation des
  fichiers produits, et le RPO/RTO cible restent des décisions du
  propriétaire. Ces scripts posent le **mécanisme**, pas la politique —
  aucune valeur n'est inventée pour ces questions.

---

## Tests — vérification par exécution

```powershell
.\db\outils\demarrer_pg.ps1   # si ce n'est pas déjà fait
```

```bash
export PGHOST=127.0.0.1 PGPORT=5433 PGUSER=postgres PGPASSWORD=qf_dev_local
export PSQL="_pgdev/pgsql/bin/psql.exe" PG_DUMP="_pgdev/pgsql/bin/pg_dump.exe"
bash db/tests/executer_tests.sh
```

(sous Git Bash / WSL ; `PSQL` et `PG_DUMP` ne sont utiles que si les binaires ne
sont pas dans le `PATH`, ce qui est le cas par défaut avec `_pgdev\`.)

### Vérifier TOUT le projet en une seule commande (chantier C13, cycle 20)

`db/tests/executer_tests.sh` ne couvre que la couche SQL. Enchaîner en plus
la suite pytest du serveur et les suites Playwright de la maquette se
faisait jusqu'ici à la main, cycle après cycle. `db/outils/verifier_tout.sh`
automatise l'enchaînement complet (mêmes variables d'environnement que
ci-dessus) :

```bash
bash db/outils/verifier_tout.sh
```

Reconstruit la base, rejoue la suite SQL, la suite pytest, puis démarre un
serveur temporaire pour les 7 suites Playwright qui n'exigent qu'un serveur
réel (`cablage`, `vente`, `inventaire`, `stock`, `rapports`, `echappement`,
`rh` — pas `affichage`/`flux`, qui exigent un second serveur **statique**
séparé, `py -m http.server 8080`, jamais automatisé). Laisse la base dans
un état propre (jeu d'essai) à la fin, que le résultat soit bon ou pas.

Le script recrée une base de test à partir du schéma d'origine, applique les
migrations, puis enchaîne :

| Fichier | Ce qu'il prouve |
|---|---|
| `00_jeu_essai.sql` | deux sites, les cinq comptes réels, quatre articles dont un à stock = 1 |
| `01_protections.sql` | **44** contrôles : chaque écriture aberrante est refusée par la base |
| `02_habilitations.sql` | **52** contrôles : les colonnes interdites sont refusées par PostgreSQL, pas seulement masquées par l'interface |
| `03_concurrence.sh` | **4** contrôles, deux sessions simultanées : une seule vente aboutit, le stock tombe à 0 sans jamais devenir négatif, un seul mouvement enregistré |
| (étape 7) | les migrations inverses ramènent le schéma à son état d'origine |

Un test qui « passe » signifie le plus souvent : **la base a bien dit non**.

### Piège à éviter en écrivant un test

- Ne jamais utiliser `1/0` comme sentinelle dans un `CASE` : PostgreSQL replie
  les constantes au moment de la planification et lève une division par zéro
  même dans la branche non prise. Utiliser les fonctions `t_valeur` / `d_valeur`.
- Ne jamais insérer puis supprimer dans la **même** instruction (`WITH x AS
  (INSERT …) DELETE …`) : le `DELETE` ne voit pas la ligne insérée, supprime 0
  ligne, et le déclencheur testé ne se déclenche jamais.

### Migrations inverses — différences attendues après aller-retour

Le script compare le schéma d'origine à celui obtenu après *appliquer* puis
*annuler*. Ces différences subsistent, connues et documentées :

1. **`comptages_stock.ecart` passe en dernière position.** La migration 003
   supprime la colonne pour la recréer en colonne générée ; l'inverse la
   reconstruit en colonne ordinaire, donc en fin de table. Le type, la
   contrainte `NOT NULL` et les valeurs sont identiques.
2. **Les extensions `pg_trgm` et `pgcrypto` restent installées.** Les
   migrations 007 et 009 inverses ne les retirent volontairement pas : elles
   peuvent servir ailleurs et leur présence est sans effet de bord.
3. **Après le cycle 35 (migrations 026-031), l'aller-retour laisse ~10
   différences** au lieu de 4 : les inverses de 030/031 ne recréent pas les
   anciennes fonctions du rapprochement et de l'annulation (elles
   référencent des colonnes d'`articles` qui n'existent plus à ce stade de
   la chaîne) — les versions multi-site restent en place, inoffensives en
   fin de chaîne, et l'écart de schéma est attendu et contrôlé par la suite
   SQL (étape « schéma comparé : OK »).

Un point d'exploitation à connaître : **les rôles PostgreSQL sont globaux au
serveur**, pas propres à une base. Si les rôles `qf_*` servent à une autre base
du même serveur, l'annulation retire tous leurs droits dans la base courante
mais conserve les rôles, en le signalant.
