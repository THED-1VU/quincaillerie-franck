# Noyau serveur — authentification, habilitations, sécurité (cycle 3)

Chantiers **C2** (authentification), **C3** (habilitations au niveau des
requêtes SQL) et **C11** (sécurité applicative). Ce cycle **ne construit
aucun écran** (pas de HTML, pas de gabarit) et **n'implémente aucune règle
métier de vente ou de stock** — le décrément de stock, le calcul de TVA, la
composition d'un panier existent déjà côté base (cycle 2) mais ne sont
exposés par aucune route ici, sauf les deux/trois routes de démonstration
prévues pour prouver le cloisonnement.

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
│       └── demonstration.py  articles, synthèse du jour, profil
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

Dernier résultat : **36/36**, trace complète dans
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
