# Dossier d'installation — Akuma / Quincaillerie Franck

Ce dossier décrit l'installation complète d'Akuma sur le poste serveur de la
boutique, **de zéro**, avec uniquement des fichiers copiés et PowerShell —
aucun Git, aucun Python, aucun Git Bash requis sur le poste cible.

> **Cadre.** Ce document a été préparé et **prouvé par simulation réelle**
> (voir `PREUVE_SIMULATION.md` dans ce dossier) : chaque commande ci-dessous
> a été exécutée dans un dossier temporaire isolé reproduisant l'arborescence
> cible. Aucune installation réelle sur le poste de la boutique n'a été faite :
> elle reste soumise à l'autorisation explicite du propriétaire.

---

## 1. Ce qu'on installe

| Composant | Nature | Taille approx. |
|---|---|---|
| `Akuma.exe` | Application (serveur FastAPI + maquette web, PyInstaller one-file) | ~29 Mo |
| `_pgdev\pgsql\` | PostgreSQL 17 portable (binaires seuls, sans installeur MSI) | ~1 Go |
| `_pgdev\data\` | Données PostgreSQL (créées sur place par `initdb`) | croissant |
| Base `quincaillerie` | Schéma d'origine + migrations 000→049 | — |
| `db\` | Migrations et outils PowerShell (sauvegarde, restauration, premiers comptes) | ~2 Mo |
| Sauvegardes | Dumps chiffrés AES-256, locales + copie hors poste | roulant 30 j |

Points d'architecture déjà actés (ne pas réinterpréter) :

- **Un seul poste serveur** : l'exe y tourne, PostgreSQL y tourne, les autres
  postes et téléphones de la boutique y accèdent par le réseau local.
- **PostgreSQL portable enregistré comme service Windows** (pas d'installeur
  MSI, pas de PostgreSQL préexistant) — port **5432** en production
  (le 5433 est réservé au développement).
- **L'exe ne démarre pas PostgreSQL et ne migre pas la base** : il suppose la
  base créée, migrée et joignable via `config.ini`. C'est ce dossier qui fait
  ces étapes, une seule fois.
- Le rôle applicatif de connexion est **`qf_app`** — jamais `postgres`
  (refusé au démarrage, chantier C11).

## 2. Prérequis du poste serveur

- Windows 10 ou 11, 64 bits ; 8 Go de RAM recommandés ; **3 Go d'espace disque
  libre** au départ.
- **Droits administrateur** disponibles (une seule fois : étapes 3, 6 et 7).
- **Edge ou Chrome** installé (l'exe ouvre la caisse en mode kiosque plein
  écran ; à défaut, repli sur le navigateur par défaut).
- Un **second emplacement** pour les sauvegardes (partage réseau, disque
  externe ou second poste) — jamais le même disque que les données.
- Antivirus : prévoir l'**exclusion** de `postgres.exe` et du dossier
  `_pgdev\` (collision d'adressage mémoire documentée, cycle 28) et de
  `db\outils\sauvegarder.ps1` — au cycle 63, Kaspersky a mis en quarantaine
  ce script (faux positif `PDM:Trojan.Win32.Generic`, preuves au journal).
  Sans exclusion, la sauvegarde planifiée peut disparaître silencieusement.
- Réseau : le poste doit avoir une **IP stable** (fixe ou réservation DHCP)
  pour que les téléphones le retrouvent.

## 3. Arborescence cible

Tout vit dans un dossier unique, ici `C:\QuincaillerieFranck\` (chemin sans
espace ni accent recommandé — les scripts PowerShell y sont sensibles) :

```
C:\QuincaillerieFranck\
├── Akuma.exe                     ← depuis server\fabrication\dist\
├── config.example.ini            ← depuis server\fabrication\dist\
├── config.ini                    ← à créer (étape 5)
├── _pgdev\
│   ├── pgsql\                    ← binaires PostgreSQL 17 portables (~1 Go)
│   ├── data\                     ← créé par initdb (étape 3)
│   └── sauvegardes\              ← sauvegardes locales chiffrées
├── db\
│   ├── migrations\               ← 000…049 + inverses
│   └── outils\                   ← sauvegarder, restaurer, planifier,
│                                 ← enregistrer_service_pg, migrer.ps1,
│                                 ← creer_compte_responsable, …
├── QuincaillerieFranck_Test\
│   └── creation_base_donnees.sql ← schéma d'origine
└── phrase_chiffrement.txt        ← créé à l'étape 6 (jamais sur Git)
```

> **Voyant de sauvegarde sans variable d'environnement.** L'application lit
> l'état de sauvegarde dans `_pgdev\sauvegardes\dernier_etat_sauvegarde.json`
> **à côté de l'exe** (résolution par défaut, correctif du cycle 64 — avec un
> exe construit avant ce cycle, le défaut pointait ailleurs et la variable
> `QF_FICHIER_ETAT_SAUVEGARDE` était indispensable : le cycle 63 documentait
> ce contournement). Tant que la planification écrit son fichier d'état au
> même endroit (c'est son défaut), **aucune variable n'est nécessaire** ; elle
> ne sert que si le fichier d'état est déplacé ailleurs. Preuve : simulation
> F de `PREUVE_SIMULATION.md`.

## 4. Procédure

Les étapes 1 à 5 peuvent se faire sans administrateur. Les étapes 3 (service),
6 et 7 (planification) l'exigent. Remplacer `C:\QuincaillerieFranck` par le
chemin réellement choisi partout où il apparaît.

### Étape 1 — Copier les fichiers

Depuis le poste de préparation (développement), copier dans le dossier cible :

1. `server\fabrication\dist\Akuma.exe` et `server\fabrication\dist\config.example.ini`
2. le dossier `db\migrations\` **complet** (50 fichiers : 000–049 + inverses)
3. le dossier `db\outils\` **complet** (scripts `.ps1`)
4. `QuincaillerieFranck_Test\creation_base_donnees.sql`
5. `_pgdev\pgsql\` **complet** (~1 Go — binaires PostgreSQL 17 portables)

Vérification : `dir C:\QuincaillerieFranck\db\migrations\*.sql | measure` doit
afficher **100** fichiers (50 migrations + 50 inverses).

### Étape 2 — Initialiser PostgreSQL (données)

Dans une console PowerShell **du dossier cible** :

```powershell
cd C:\QuincaillerieFranck
# Premier lancement : initdb dans _pgdev\data (mot de passe du compte
# « postgres » créé sur place, à noter hors ligne), puis démarrage sur le
# port production 5432.
powershell -File db\outils\demarrer_pg.ps1 -Port 5432
```

Le script télécharge PostgreSQL 17 si `_pgdev\pgsql` est absent et l'initialise
si `_pgdev\data` est absent ; il est **idempotent** (relancer ne casse rien).
Note : `demarrer_pg.ps1` pose le mot de passe superutilisateur de
développement — sur le poste réel, **changer le mot de passe `postgres`**
après l'installation (étape 8) et ne le noter nulle part en ligne.

### Étape 3 — PostgreSQL en service Windows  (administrateur)

```powershell
powershell -File db\outils\enregistrer_service_pg.ps1 -PgPort 5432
```

Effet : démarrage automatique au boot + relance automatique après plantage
(5 s / 10 s / 30 s). Désinstallation : ajouter `-Supprimer`.

### Étape 4 — Créer la base, le schéma, appliquer les migrations

```powershell
cd C:\QuincaillerieFranck
$env:PGPASSWORD = '<mot de passe postgres choisi à l''etape 2>'
$env:PSQL       = 'C:\QuincaillerieFranck\_pgdev\pgsql\bin\psql.exe'
$env:PGHOST     = '127.0.0.1'
$env:PGPORT     = '5432'
$env:PGUSER     = 'postgres'
$env:PGDATABASE = 'quincaillerie'

# 4a. Créer la base
& $env:PSQL -d postgres -c "CREATE DATABASE quincaillerie;"

# 4b. Schéma d'origine, puis migrations 000 -> 049 (migrer.ps1 affiche la
#     liste appliquée ; "Termine" + 49 lignes = réussite)
& $env:PSQL -d quincaillerie -v ON_ERROR_STOP=1 -f QuincaillerieFranck_Test\creation_base_donnees.sql
powershell -File db\outils\migrer.ps1 appliquer
```

`migrer.ps1` est l'équivalent PowerShell de `migrer.sh` (même fichiers, même
ordre, une transaction par fichier) — inutile d'installer Git Bash sur le
poste serveur. Preuves d'exécution des deux sens : `PREUVE_SIMULATION.md`.

> **Mise à jour ultérieure de l'application** (nouvelles migrations livrées) :
> `migrer.ps1 appliquer` rejouerait tout depuis 000 et échouerait sur une base
> déjà migrée. Sur une base existante, appliquer **uniquement les fichiers
> nouveaux**, un par un dans l'ordre :
> `& $env:PSQL -d quincaillerie -v ON_ERROR_STOP=1 --single-transaction -f db\migrations\05X_....sql`

### Étape 5 — config.ini et mot de passe applicatif

1. Copier `config.example.ini` en `config.ini` (même dossier que `Akuma.exe`).
2. Renseigner `[database]` : `host = 127.0.0.1`, `port = 5432`,
   `dbname = quincaillerie`, `user = qf_app`, `password = <choisi>`.
3. Renseigner `[api] secret_key` — 64 caractères hexadécimaux au hasard,
   sans Python sur le poste :

   ```powershell
   -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
   ```

4. Poser le mot de passe du rôle `qf_app` (créé par la migration 008) :

   ```powershell
   & $env:PSQL -d quincaillerie -v mdp="'<le même password que config.ini>'" `
       -f db\outils\definir_mot_de_passe_app.sql
   ```

### Étape 6 — Premier compte responsable

Sur une base neuve, personne ne peut se connecter : ce script crée le premier
compte responsable (mot de passe masqué à la saisie, haché bcrypt en base,
changement imposé à la première connexion) :

```powershell
powershell -File db\outils\creer_compte_responsable.ps1 -ConfigIni C:\QuincaillerieFranck\config.ini
```

### Étape 7 — Lancement et réseau

1. Double-clic sur `Akuma.exe`. Une console s'ouvre (ne pas la fermer tant
   que la boutique tourne — la fermer arrête l'application), puis un
   navigateur en plein écran sur l'écran de connexion.
2. Vérifications immédiates :
   - `http://127.0.0.1:8000/sante` répond `{"etat":"ok","base":"joignable"}` ;
   - connexion avec le compte responsable créé à l'étape 6 ;
   - carte « Dernière sauvegarde » du tableau de bord affiche un état
     (même « aucune sauvegarde » — le voyant fonctionne).
3. **Téléphones / autres postes** : autoriser le port 8000 entrant dans le
   pare-feu Windows (assistant : « Autoriser une application » →
   `Akuma.exe` → réseau privé), puis ouvrir sur le téléphone
   `http://<IP du serveur>:8000/app/connexion.html` (l'IP est affichée dans
   la console de l'exe).
4. Si le port 8000 est déjà pris, l'exe bascule seul sur un port libre et
   l'affiche en console — mettre à jour les favoris des téléphones en
   conséquence.

### Étape 8 — Sauvegarde planifiée  (administrateur)

Suivre `db\outils\GUIDE_SAUVEGARDE_RESTAURATION.md` §2 à la lettre — quatre
commandes : phrase de chiffrement (fichier local protégé par `icacls`),
sauvegarde de test, planification horaire RPO 1 h sous `NT AUTHORITY\SYSTEM`,
puis `Start-ScheduledTask` pour un essai immédiat. Points spécifiques au
poste de production :

- `-PgPort 5432`, `-NomBase quincaillerie` ;
- le fichier d'état par défaut de la planification
  (`_pgdev\sauvegardes\dernier_etat_sauvegarde.json`) **coïncide avec le
  défaut lu par l'application** — ne pas déplacer l'un sans l'autre
  (sinon, se reporter à la note `QF_FICHIER_ETAT_SAUVEGARDE`, §3) ;
- mot de passe de la connexion de sauvegarde : fichier `.pgpass` de
  l'utilisateur qui exécute la tâche — **jamais** `-PgPasswordDev`
  (réservé au dépôt de développement) ;
- **exclusions antivirus** (§2) à faire AVANT de juger la planification
  défaillante : une quarantaine silencieuse de `sauvegarder.ps1` se
  présente exactement comme « les sauvegardes ont cessé sans message ».

### Étape 9 — Fin d'installation

- Changer le mot de passe du superutilisateur `postgres` posé par défaut :
  `ALTER USER postgres WITH PASSWORD '<fort>';` (à noter hors ligne, coffre).
- Renseigner `CHECKLIST_INSTALLATION.md` de ce dossier, imprimée et cochée
  sur place : c'est la preuve d'installation à conserver.
- Supprimer de l'ordinateur tout fichier temporaire contenant des mots de
  passe (l'historique de la console peut en garder : fermer la console).

## 5. Désinstallation

1. `powershell -File db\outils\enregistrer_service_pg.ps1 -Supprimer`
   (administrateur) ; supprimer la tâche planifiée :
   `Unregister-ScheduledTask -TaskName 'QuincaillerieFranck_Sauvegarde' -Confirm:$false`.
2. Arrêter l'exe (fermer sa console).
3. Sauvegarder puis supprimer le dossier `C:\QuincaillerieFranck\` entier —
   `_pgdev\data` contient toutes les données ; sa suppression est
   **irrémédiable** (les dumps chiffrés restent la seule copie).
4. `phrase_chiffrement.txt` : à conserver aussi longtemps que des
   sauvegardes chiffrées avec elle existent (voir le guide C12, §6).

## 6. Dépannage rapide

| Symptôme | Cause probable | Action |
|---|---|---|
| La console de l'exe dit que la config manque | `config.ini` absent ou mal nommé | Étape 5 (copier depuis `config.example.ini`) |
| Refus de démarrer : compte `postgres` | `[database] user` vaut `postgres` | Mettre `user = qf_app` (C11) |
| Refus de démarrer : `secret_key` | Valeur d'exemple ou trop courte | Étape 5.3 |
| `FATAL: password authentication failed` | Mot de passe `qf_app` incohérent entre `config.ini` et la base | Étape 5.4 |
| `relation « utilisateurs » does not exist` | Migrations appliquées sans le schéma d'origine | Étape 4b **dans l'ordre** (schéma puis migrations) |
| Les téléphones ne joignent pas le serveur | Pare-feu / IP changeante | Étape 7.3, IP stable |
| Le navigateur ne s'ouvre pas tout seul | Ni Edge ni Chrome | Installer l'un des deux, ou ouvrir l'URL manuellement |
| Sauvegardes arrêtées sans message d'erreur | Script mis en quarantaine par l'antivirus | Restaurer `db\outils\sauvegarder.ps1`, ajouter l'exclusion (§2), relancer la tâche |
| `could not reserve shared memory region` au démarrage de PostgreSQL | Collision mémoire connue de PostgreSQL/Windows, souvent aggravée par l'antivirus | Exclusions antivirus §2 ; le service Windows relance automatiquement (étape 3) |
| Port 5432 déjà occupé | Autre PostgreSQL/MSI installé sur le poste | Le retirer ou choisir un autre port (cohérent partout : service, config.ini, planification) |

## 7. Références

- `db\outils\GUIDE_SAUVEGARDE_RESTAURATION.md` — exploitation, restauration,
  phrase de chiffrement, coupure de courant (chantier C12, à jour cycle 39).
- `db\README.md` — recette de remise à neuf d'une base (§ « Remettre une base
  de piste à neuf »), environnement de développement `_pgdev`.
- `server\README.md` § « Chantier C0 » — fabrication de l'exécutable.
- `server\fabrication\DERNIER_RESULTAT.md` — trace de la construction de
  l'exe candidat (cycle 63) et de ses vérifications (12 suites Playwright,
  431/431, contre l'exe réel).
- `INSTALLATION\CHECKLIST_INSTALLATION.md` — recette vierge à cocher le jour J.
- `INSTALLATION\PREUVE_SIMULATION.md` — preuves d'exécution de cette
  procédure en environnement isolé (cycle 64).
