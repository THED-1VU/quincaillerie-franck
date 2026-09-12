# Noyau serveur — authentification, habilitations, sécurité, ventes, fabrication

Chantiers **C2** (authentification), **C3** (habilitations au niveau des
requêtes SQL), **C11** (sécurité applicative), **C0** (fabrication de
l'exécutable Windows), **C5** (ventes, depuis le cycle 6) et **C7**
(inventaire et écarts, depuis le cycle 7). Les écrans (`maquette/`, servis
sous `/app`) sont câblés depuis le cycle 5 — voir
`RAPPORT AVANCEMENT/loop-state.md`.

```
server/
├── config.example.ini   modèle de configuration (placeholders)
├── requirements.txt     dépendances figées
├── app/
│   ├── config.py         lecture de config.ini, refuse postgres/secret d'exemple
│   ├── database.py       SEULE couche qui parle à PostgreSQL (SET ROLE, RLS)
│   ├── securite.py       hachage bcrypt ($2a$ !), jetons signés, limiteur de débit
│   ├── deps.py            dépendances FastAPI : session, exiger_role(...)
│   ├── roles.py           rôle métier -> rôle PostgreSQL (whitelist fermée)
│   ├── schemas.py         modèles Pydantic
│   ├── main.py            fabrique l'application, gestion d'erreurs
│   └── routes/
│       ├── auth.py         connexion, changer-mot-de-passe, déverrouillage
│       ├── demonstration.py  articles, synthèse du jour, profil
│       ├── ventes.py         POST /ventes (chantier C5, cycle 6) + taux de TVA en vigueur
│       └── inventaire.py     comptage à l'aveugle + écarts (chantier C7, cycle 7)
├── fabrication/           empaquetage en .exe (chantier C0) — voir plus bas
└── tests/                 pytest — exécution réelle contre PostgreSQL
```

---

## Installer

```powershell
py -3.13 -m venv server\.venv
server\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
```

Python 3.13 est utilisé plutôt que 3.14 (celui par défaut sur ce poste) :
toutes les dépendances (`psycopg[binary]`, `bcrypt`) avaient des roues
précompilées disponibles pour 3.13 au moment de ce cycle, vérifié par
exécution — pas d'hypothèse.

## Configurer

```powershell
copy server\config.example.ini server\config.ini
```

Renseigner `config.ini` (jamais versionné — voir `.gitignore`) :
- `database.user` = `qf_app` — **jamais** `postgres` : le démarrage **refuse
  explicitement** ce compte (chantier C11, voir `app/config.py`) ;
- `database.password` = celui défini par
  `db/outils/definir_mot_de_passe_app.sql` ;
- `api.secret_key` = généré avec
  `python -c "import secrets; print(secrets.token_hex(32))"` — le démarrage
  refuse aussi explicitement la valeur d'exemple.

## Lancer

```powershell
.\db\outils\demarrer_pg.ps1          # si PostgreSQL de dev n'est pas déjà démarré
server\.venv\Scripts\uvicorn.exe app.main:app --reload --app-dir server
```

`GET /sante` répond sans authentification, utile pour vérifier que le
serveur et la base sont joignables.

---

## Chantier C2 — authentification

| Route | Rôle requis | Ce qu'elle fait |
|---|---|---|
| `POST /auth/connexion` | aucun | identifiant + mot de passe -> jeton signé, à durée limitée |
| `POST /auth/changer-mot-de-passe` | n'importe quel compte connecté | libre-service, limité à SA PROPRE ligne |
| `POST /admin/comptes/{id}/deverrouiller` | responsable | remet `tentatives_echouees` à 0, trace l'action |

Le mot de passe n'est **jamais** lu par le serveur applicatif : c'est la
fonction PostgreSQL `verifier_connexion()` (migration 009, `SECURITY
DEFINER`) qui seule y accède, et qui ne le restitue jamais dans son résultat.
Verrouillage après 5 échecs consécutifs (`parametres.tentatives_max_connexion`,
valeur **proposée**, à confirmer par le propriétaire — voir
`ADDENDUM_CAHIER_DES_CHARGES.md`), déverrouillage réservé au responsable,
obligation de changer le mot de passe à la première connexion
(`doit_changer_mot_de_passe`).

### Piège rencontré et corrigé — préfixe bcrypt

**pgcrypto ne valide pas un hachage bcrypt au format `$2b$`**, celui que
produit `bcrypt.gensalt()` par défaut. Vérifié par exécution, dans les deux
sens, avant d'écrire une seule ligne de code serveur :

```
$2b$ (défaut Python)  -> crypt() renvoie FAUX même pour le bon mot de passe
$2a$ (gensalt(prefix=b"2a")) -> crypt() valide correctement
```

`securite.hacher_mot_de_passe()` génère donc **toujours** avec
`prefix=b"2a"`. Voir le détail dans
`db/migrations/009_authentification.sql` et le test de non-régression
`server/tests/test_securite.py::test_hachage_genere_par_le_serveur_est_verifiable_par_pgcrypto`.

### Durée de session — décision technique temporaire

`config.api.duree_session_minutes` (défaut **480 min**, 8 h) est un choix
technique de ce cycle, **pas** une décision métier tranchée. Le paramètre
`parametres.duree_session_minutes` reste `a_definir` en base : la vraie
politique (« au bout de combien de temps d'inactivité déconnecter ? ») est
une question ouverte pour le propriétaire — voir `ADDENDUM_CAHIER_DES_CHARGES.md`
et le dossier de recette (« session inactive »). Le jour où cette décision
est prise, il suffit de mettre à jour `config.ini`.

---

## Chantier C3 — habilitations au niveau des requêtes SQL

**Le contrôle qui compte n'est pas dans ce code.** `deps.exiger_role(...)`
et le choix de colonnes dans `routes/demonstration.py` sont un **confort** —
une première haie qui évite un aller-retour inutile à la base. La **vraie**
protection est posée au cycle 2 et vérifiée ici par des tests qui la
contournent délibérément :

- **privilèges par colonne** (migration 008) : `SELECT prix_vente FROM
  articles` échoue avec `permission denied` pour `qf_agent_stock`, quel que
  soit le code qui l'exécute ;
- **RLS par site** (migration 008, `qf_site_courant()`) : un `SELECT * FROM
  articles WHERE site_id = 2` exécuté sous `qf_agent_stock` avec
  `qf.site_id = '1'` renvoie **zéro ligne**, même en demandant explicitement
  l'autre site.

`server/tests/test_cloisonnement_site.py::test_rls_bloque_meme_en_sql_direct_hors_de_lapi`
le prouve en **contournant complètement l'API et le code Python** : preuve la
plus forte possible, indépendante de tout bug applicatif.

### Point de bascule unique

`database.BaseDeDonnees.connexion_pour(role, site_id, utilisateur_id)` est le
**seul** endroit du serveur qui fait `SET LOCAL ROLE`. Aucune route ne
vérifie un droit elle-même « à la main » — impossible d'oublier une
vérification dans une route future, puisqu'il n'y a qu'un seul endroit où
la bascule de rôle a lieu.

### Piège rencontré et corrigé — `qf_app` ne voyait rien

Le tout premier appel réel (`verifier_connexion()` sous `qf_app`) échouait
avec `function verifier_connexion(...) does not exist` — alors que la
fonction existait et que `qf_app` avait reçu `EXECUTE` dessus. Cause :
`qf_app` n'avait jamais reçu `USAGE ON SCHEMA public` (migration 008 ne
l'accordait qu'aux trois rôles métier ; `qf_app` étant `NOINHERIT`, il n'en
hérite pas). Sans `USAGE`, PostgreSQL rend l'objet **invisible** au moment de
résoudre son nom (message « n'existe pas », pas « permission refusée » — il
évite de révéler le contenu d'un schéma inaccessible). Corrigé par la
migration **010** (008 n'a pas été modifiée rétroactivement : elle est déjà
fusionnée). Voir `db/migrations/010_correction_usage_qf_app.sql`.

---

## Chantier C5 — ventes (cycle 6)

`POST /ventes` (réservé `responsable`/`agent_comptabilite`) applique trois
décisions du propriétaire obtenues ce cycle — voir
`ADDENDUM_CAHIER_DES_CHARGES.md`, encarts « Décidé » sur les points b/d/e :

| Route | Rôle requis | Ce qu'elle fait |
|---|---|---|
| `POST /ventes` | responsable, agent comptabilité | enregistre une vente **déjà** encaissée (`statut='payee'` dès la création) : calcule la TVA, décrémente le stock, crée une recette |
| `GET /ventes/parametres` | responsable, agent comptabilité | taux de TVA en vigueur — la maquette le lit ici plutôt que de le coder en dur |

- **Anti-survente (point e)** : la route n'échoue **jamais** pour stock
  insuffisant — le circuit réel de la boutique fait encaisser avant la
  saisie comptable, refuser n'aurait aucun sens. `decrementer_stock_vente()`
  (migration 011) décrémente jusqu'à 0 et consigne l'écart dans
  `ecarts_stock_ventes`, réservé au responsable (jamais l'agent stock, qui
  compte à l'aveugle).
- **Fiscalité (point d)** : régime du réel, TVA 19,25 %, prix négociés TTC.
  Le taux **n'est jamais une constante du code** : il vient de
  `parametres.taux_tva` (`parametre_numerique('taux_tva')`), lu à chaque
  vente. L'arrondi (arithmétique) porte sur le TOTAL de TVA de la vente,
  jamais ligne à ligne.
- **Crédit client (point b)** : `mode_paiement = 'credit_client'` existe
  dans le schéma d'origine mais est explicitement **refusé** par la route
  (422, message clair) — statu quo tant que les 6 questions du point b ne
  sont pas répondues, pas une décision sur le fond.
- **Site du responsable** : un agent a toujours un site en session (jamais
  pris dans le corps de la requête, qu'il pourrait manipuler) ; le
  responsable, qui couvre les deux sites, doit le préciser explicitement
  dans le corps — sinon 422 avant toute écriture.
- **Point c (numéro facturier + vendeur) volontairement NON traité** :
  l'objectif anti-vol (priorité n°3 du propriétaire) reste incomplet tant
  que ce point n'est pas tranché — aucune colonne ajoutée à `ventes`.

### Piège rencontré et corrigé — signature de fonction PL/pgSQL

`decrementer_stock_vente()` (migration 008) devait gagner un paramètre
(`p_vente_id`) et changer de type de retour (`INTEGER` → `TABLE(...)`).
`CREATE OR REPLACE FUNCTION` **n'autorise ni l'un ni l'autre silencieusement** :
plutôt que de risquer deux versions coexistantes avec des signatures
différentes, la migration 011 fait un `DROP FUNCTION` explicite de l'ancienne
signature à 4 arguments, puis `CREATE OR REPLACE` de la nouvelle à 5 — une
seule version peut exister, jamais d'ambiguïté sur celle qui répond.

### Tests — `server/tests/test_ventes.py`, 8/8

TVA vérifiée par un calcul **indépendant** de la route (2000 FCFA TTC → 323
FCFA de TVA, à la main) ; vente à découvert de stock jamais refusée, écart
consigné ; crédit client refusé explicitement ; agent stock sans aucun droit
sur la route ; un comptable ne peut pas vendre pour l'autre site, même en
forçant `site_id` dans le corps ; un responsable doit préciser un site.
Non-régression : suite complète **44/44** (36 héritées + 8 nouvelles), suite
SQL du cycle 2 rejouée à jour (**44/44** protections, **52/52** habilitations,
**6/6** concurrence — réécrite pour le nouveau comportement anti-survente,
voir `db/tests/DERNIER_RESULTAT.md`).

---

## Chantier C7 — inventaire et écarts (cycle 7)

Le socle existait déjà en base depuis le cycle 2 (migration 003) :
`comptages_stock.quantite_attendue` figée par déclencheur à partir du stock
réel, `ecart` généré (`quantite_comptee - quantite_attendue`, non
inscriptible), un seul comptage par article/moment/jour, immuable. Aucune
route ne l'exposait avant ce cycle.

| Route | Rôle requis | Ce qu'elle fait |
|---|---|---|
| `GET /inventaire/articles-a-compter?moment=matin\|soir` | agent stock, responsable | liste `{id, nom, unite}` du site — **aucune** quantité ; exclut les articles déjà comptés aujourd'hui pour ce moment |
| `POST /inventaire/comptages` | agent stock, responsable | enregistre un comptage ; n'accepte que `article_id`/`moment`/`quantite_comptee`, ne renvoie que cela |
| `GET /inventaire/ecarts` | responsable | comptages du jour dont l'écart est non nul |
| `GET /inventaire/ecarts-ventes` | responsable | écarts de stock issus d'une vente à découvert (`ecarts_stock_ventes`, chantier C5) survenus aujourd'hui |

### Défense en profondeur trouvée et corrigée — migration 012

Diagnostic, avant d'écrire une route : `SET ROLE qf_agent_stock; SELECT
ecart, quantite_attendue FROM comptages_stock;` était **accepté** par
PostgreSQL. La migration 008 accordait un `SELECT` sans restriction de
colonne à `qf_agent_stock` sur `comptages_stock` — jamais exploité, aucune
route ne lisant ces colonnes pour ce rôle, mais la protection reposait sur
une absence de code, pas sur la base. Corrigée par
`db/migrations/012_comptage_aveugle_colonnes.sql`, exactement comme pour
`articles.prix_vente` (cycle 2) : `GRANT SELECT (colonnes autorisées)`,
sans `ecart` ni `quantite_attendue`. Revérifié par exécution après coup :
la même requête est désormais refusée (`permission denied`).

### Écran d'inventaire — un comptage est un fait, pas un brouillon

`maquette/inventaire.html` soumet chaque comptage dès que l'agent avance
(« Suivant »), jamais différé jusqu'à la fin de la liste : la base interdit
toute modification d'un comptage déjà enregistré (migration 003), donc un
flux « brouillon modifiable jusqu'au bout » aurait laissé croire à une
correction possible qui n'existe pas. « Précédent » redevient une simple
lecture d'un article déjà soumis (champ désactivé), jamais une réédition.

### Tests — `server/tests/test_inventaire.py`, 9/9

Liste à compter strictement limitée à `{id, nom, unite}` ; réponse d'un
comptage strictement limitée à ce que le client a envoyé ; lecture directe
de `ecart`/`quantite_attendue` refusée à l'agent stock (preuve la plus
forte, hors API, comme `test_cloisonnement_site.py`) ; article déjà compté
absent de la liste et second envoi refusé (409) ; comptage d'un article de
l'autre site refusé (422) ; comptabilité totalement exclue (403) ; écarts
réservés au responsable, avec une valeur d'écart vérifiée à la main
(30 en stock, 22 comptés → **-8**) ; un écart de vente à découvert
(chantier C5) retrouvé tel quel dans `/inventaire/ecarts-ventes`. Suite
complète : **53/53** (44 héritées + 9 nouvelles).

---

## Chantier C11 — sécurité applicative

- **Jamais de connexion superutilisateur** : `config.py` refuse `user =
  postgres` au démarrage (`ErreurConfiguration`), testé par
  `test_config_refuse_le_compte_superutilisateur`.
- **Jamais de clé secrète d'exemple** : refus si `api.secret_key` est absente,
  trop courte, ou encore la valeur `A_GENERER...` du modèle.
- **Requêtes toujours paramétrées** : aucune f-string ni concaténation dans
  du SQL contenant une donnée utilisateur (la seule exception,
  `routes/demonstration.py`, insère une liste de **colonnes** choisie dans une
  whitelist fixe de 3 valeurs indexée par rôle — jamais une valeur venant de
  la requête HTTP). Vérifié par un essai d'injection SQL dans l'identifiant
  (`test_injection_sql_dans_lidentifiant_ne_casse_rien`).
- **Jetons signés (HMAC-SHA256)**, vérifiés à temps constant
  (`hmac.compare_digest`), à durée limitée, jamais de jeton après expiration
  ni avec une signature falsifiée ou une autre clé.
- **Aucun hachage ne quitte jamais la base** : aucune route, aucune réponse
  ne contient de champ ressemblant à un hachage bcrypt (vérifié par
  expression régulière sur le corps JSON complet des réponses).
- **Erreurs SQL jamais renvoyées telles quelles au client** : `main.py`
  intercepte `psycopg.Error` et ne répond que `"Erreur interne."` /
  `"Accès refusé."` — le détail (nom de table, de colonne, de contrainte) est
  journalisé côté serveur, jamais exposé côté client.
- **Limitation de débit sur `/auth/connexion`** : fenêtre glissante en
  mémoire, distincte du verrouillage de compte (qui, lui, est une règle
  métier posée en base). Limite connue et documentée : compteur **par
  processus**, un déploiement à plusieurs travailleurs voudrait un compteur
  partagé — ce n'est pas une décision métier, juste une limite technique de
  ce cycle.
- **Journalisation applicative** : `verifier_connexion()` écrit dans
  `journal_connexions` à **chaque** tentative (succès et échec) ;
  `changer_mon_mot_de_passe()` et le déverrouillage écrivent dans
  `journal_comptes` — ce sont des fonctions PostgreSQL du cycle 2, pas du
  code serveur, pour qu'aucune route ne puisse « oublier » de tracer.

---

## Tests — vérification par exécution réelle

Aucun mock de PostgreSQL : `server/tests/conftest.py` pointe vers la vraie
instance de développement (`_pgdev/`, cycle 2) et recharge le jeu d'essai
(`db/tests/00_jeu_essai.sql`) avant **chaque** test.

```powershell
.\db\outils\demarrer_pg.ps1
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

| Fichier | Ce qu'il prouve |
|---|---|
| `test_authentification.py` | connexion, verrouillage après 5 échecs, déverrouillage, limitation de débit, changement de mot de passe (premier + libre-service), compte désactivé |
| `test_habilitations.py` | contenu des réponses par rôle (colonnes interdites absentes, pas seulement code HTTP), 403 sur route non autorisée, aucune route sans jeton |
| `test_cloisonnement_site.py` | un site fourni en paramètre est ignoré ; **RLS bloquée en SQL direct**, hors API |
| `test_securite.py` | aucun hachage ne fuit, config refuse superutilisateur/clé d'exemple, injection SQL neutralisée, jetons expirés/falsifiés/mal signés refusés |
| `test_ventes.py` | TVA calculée à la main et comparée, vente à découvert jamais refusée (écart consigné), crédit client refusé, cloisonnement par rôle/site sur une route d'ÉCRITURE |
| `test_inventaire.py` | liste à compter sans aucune quantité, réponse d'un comptage limitée à ce qui a été envoyé, **lecture de `ecart` refusée en SQL direct**, article déjà compté exclu, écarts réservés au responsable et exacts |

Dernier résultat : **53/53**, trace complète dans
[`tests/DERNIER_RESULTAT.md`](tests/DERNIER_RESULTAT.md).

### Piège à éviter en écrivant un test (Windows)

`subprocess.run(..., env={...})` **remplace** tout l'environnement du
processus enfant au lieu de le compléter. `psql.exe` a besoin des variables
système (`SystemRoot`...) pour que la résolution réseau fonctionne ; sans
elles, il échoue silencieusement. Toujours partir d'une copie de
`os.environ` :

```python
environnement = {**os.environ, "PGPASSWORD": "..."}
```

### Piège à éviter en écrivant une route (psycopg3)

`BaseDeDonnees.connexion_pour(...)` ouvre déjà `conn.transaction()`, qui
**commit automatiquement** à la sortie normale du bloc `with`. Un
`conn.commit()` manuel à l'intérieur est explicitement **refusé** par
psycopg3 (`ProgrammingError: Explicit commit() forbidden within a
Transaction context`). Seule `connexion_anonyme()` (utilisée avant
authentification) ne gère pas de transaction elle-même : c'est là, et
seulement là, qu'un `conn.commit()` explicite est nécessaire.

---

## Chantier C0 — fabrication de l'exécutable Windows

Architecture actée (`RAPPORT AVANCEMENT/loop-state.md`) : un seul code
applicatif web, **livré comme un `.exe` Windows** qui embarque ce serveur et
ouvre l'interface dans un navigateur — aucune installation de Python sur les
postes de la boutique, double-clic comme l'application d'origine.

```
server/fabrication/
├── lanceur.py                     point d'entrée compilé (démarre le serveur + ouvre le navigateur)
├── quincaillerie_franck.spec      configuration PyInstaller
├── construire.ps1                 script humain : "lance juste ça"
├── DERNIER_RESULTAT.md            trace de la dernière construction + vérifications
├── dist/    (ignoré par Git)      QuincaillerieFranck.exe produit
└── build/   (ignoré par Git)      fichiers intermédiaires de PyInstaller
```

### Construire

```powershell
.\server\fabrication\construire.ps1
```

Installe PyInstaller dans `server\.venv` si besoin, construit l'exécutable,
copie `config.example.ini` à côté. Résultat :
`server\fabrication\dist\QuincaillerieFranck.exe`.

### Distribuer sur un poste

1. Copier tout le contenu de `server\fabrication\dist\` sur le poste cible.
2. Renommer `config.example.ini` en `config.ini`, le remplir (voir
   « Configurer » plus haut) — **jamais** committer ce fichier rempli.
3. Double-cliquer `QuincaillerieFranck.exe`. Une fenêtre console s'ouvre
   (messages de démarrage, erreurs de configuration lisibles), le serveur
   démarre, un navigateur s'ouvre automatiquement.

Aucun Python, aucune dépendance à installer : vérifié en lançant l'exécutable
depuis un dossier **totalement isolé** du dépôt, avec seulement lui-même et
`config.ini` — voir `fabrication/DERNIER_RESULTAT.md`.

### État actuel du lanceur — placeholder documenté

Le navigateur ouvert par `lanceur.py` pointe encore sur `/docs`
(documentation interactive de l'API), pas sur `/app/connexion.html` : la
maquette est câblée sur ce serveur depuis le cycle 5 (`main.py` la sert sous
`/app`), mais l'exécutable, lui, n'a pas été reconstruit ni son
`CHEMIN_A_OUVRIR` mis à jour depuis (fabrication = chantier C0, non rouvert
aux cycles 5/6). Le mécanisme de lancement (port, attente de démarrage,
ouverture du navigateur) ne changera pas quand ce sera fait — seule la
constante `CHEMIN_A_OUVRIR` dans `lanceur.py` sera mise à jour. Le mode
kiosque (plein écran) n'a pas non plus été activé.

### Piège rencontré et corrigé — nommage du dossier

Ce dossier s'appelle `fabrication/`, **pas** `build/` : `.gitignore` exclut
tout dossier nommé `build/` (artefact de compilation générique). Un premier
essai nommé `server/build/` s'est retrouvé **entièrement ignoré par Git, y
compris ses fichiers sources** (`lanceur.py`, le `.spec`, `construire.ps1`) —
`git check-ignore -v` l'a révélé, `git status` seul ne l'aurait jamais
montré. Les **sous-dossiers de sortie** de PyInstaller, eux, s'appellent
volontairement `dist/` et `build/` (noms attendus par les règles génériques
déjà en place) : aucune nouvelle entrée `.gitignore` n'a été nécessaire.

### Piège rencontré — avertissements de construction, confirmés inoffensifs

```
WARNING: Hidden import "_cffi_backend" not found!
WARNING: Hidden import "psycopg_binary._uuid" not found!
```

Le premier vient du hook communautaire de `bcrypt`, écrit pour d'anciennes
versions basées sur `cffi` — `bcrypt` 4.x utilise une extension **Rust**, ce
module n'existe simplement pas. Le second n'a eu **aucune conséquence
observée** dans les tests (aucune colonne de type UUID dans ce projet). Les
deux avertissements sont attendus ; ne pas chercher à les faire disparaître
sans une raison fonctionnelle constatée.
