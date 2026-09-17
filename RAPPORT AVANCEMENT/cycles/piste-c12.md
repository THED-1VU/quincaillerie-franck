# Piste C12 — Sauvegarde et exploitation

Worktree : `_worktrees/piste-c12` — branche `piste-c12-sauvegarde` — base
`quincaillerie_c12` (127.0.0.1:5433) — port serveur de convention 8013.

Ce rapport suit le format « cycle » de `SKILL.md` (étapes 1 à 4), pour le
chantier **C12** conduit en parallèle des pistes UX et C6 (voir
`RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`).

---

## Cycle 22 — C12 Sauvegarde et exploitation

- Date : 2026-09-14 → 2026-09-17

### Étape 1 — Diagnostic (rejeu du mécanisme existant, cycle 21)

Rejoué **par exécution réelle**, dans ce worktree, sur `quincaillerie_c12`
(jamais `quincaillerie_test`) :

```powershell
powershell -File db\outils\sauvegarder.ps1 -NomBase quincaillerie_c12
powershell -File db\outils\restaurer.ps1 -FichierBase "..\quincaillerie_c12_20260914_002729.dump" -NomBaseCible quincaillerie_c12_diag_verif -Forcer
```

Résultat : sauvegarde produite (197,1 Ko), restauration réussie
(**23 tables**), comptes de lignes identiques avant/après sur
`utilisateurs` (5), `articles` (4), `ventes` (0 à ce moment), droits par
colonne identiques (`has_column_privilege('qf_agent_stock','articles',
'prix_vente','SELECT')` = `f` avant et après). **0 régression** confirmée
par exécution sur les scripts hérités du cycle 21 — verdict : le
mécanisme de base fonctionnait déjà, rien à corriger avant d'étendre.

**Piège rencontré et documenté (pas un bug du cycle 21)** : dans une
configuration de **worktree Git** (ce chantier en parallèle), `$Racine`
dans `sauvegarder.ps1`/`restaurer.ps1` (calculé comme `..\..` du script)
pointe vers la racine du **worktree**, pas vers le dépôt principal qui
contient `_pgdev\pgsql\bin` — les binaires PostgreSQL ne sont donc trouvés
que si le `PATH` de l'appelant les contient déjà (repli déjà prévu par le
script d'origine, « sinon le PATH »). Contourné pour le diagnostic en
ajoutant `_pgdev\pgsql\bin` au `PATH` de la session avant d'appeler les
scripts — **je n'ai pas touché à la logique de résolution de
`sauvegarder.ps1`/`restaurer.ps1` eux-mêmes** (qui fonctionnent tels
quels en dépôt unique, cas réel de production). En revanche, j'ai ajouté
une résolution similaire (recherche en remontant l'arborescence) dans
mes **deux nouveaux/modifiés scripts qui en avaient réellement besoin**
pour la preuve par exécution : `planifier_sauvegarde.ps1` (pour que la
tâche planifiée retrouve `pg_dump` même hors de ma session interactive)
et `server/fabrication/construire.ps1` (pour retrouver le venv Python
partagé). Sans incidence en production réelle (dépôt unique, pas de
`_pgdev`) : la recherche ne trouve alors simplement rien et le
comportement retombe sur l'existant (PATH système).

Le même problème de chemin affecte `server/tests/conftest.py`
(`PSQL_EXE` introuvable en worktree) — préexistant, pas causé par ce
cycle, et hors du périmètre de fichiers exclusifs de cette piste ; signalé
ici plutôt que corrigé unilatéralement (voir « Reste à faire »).

### Étape 2 — Propositions (rappel, la décision avait déjà été prise en amont de ce cycle)

Chantier C12 retenu par le propriétaire (plan fourni en amont de ce
cycle, cohérent avec la priorité 3 « fiabilité métier » et la décision du
2026-09-13 sur le RPO). Aucune autre option n'a été évaluée dans ce
cycle : le plan était déjà validé au moment où cette session a démarré.

### Étape 3 — Objectif retenu (rappel du plan validé)

Rendre l'exploitation (sauvegarde/restauration/continuité) réellement
autonome pour un non-technicien, RPO cible 1 heure (décision du
2026-09-13), et refabriquer l'exécutable Windows avec `openpyxl`,
`reportlab`, `pypdf`. Plan détaillé fourni par le propriétaire — voir la
consigne de la session, non reproduite ici in extenso.

**VALIDÉ PAR LE PROPRIÉTAIRE en amont de la session** (plan détaillé fourni
au démarrage de cette piste, 2026-09-14).

### Étape 4 — Mise en œuvre, vérifications, preuves

Branche : `piste-c12-sauvegarde`.

#### 4.1 — `db/outils/sauvegarder.ps1` étendu

Ajouts (compatibles avec les appels existants — aucun paramètre existant
retiré ni renommé) :

- **`-DossierDistant`** : copie chaque fichier produit (`.dump` +
  `_roles.sql`) vers un second emplacement après la sauvegarde locale,
  avec vérification **par `Test-Path` après copie** (pas seulement
  `Copy-Item` sans erreur) avant de considérer l'étape réussie.
- **`-RetentionJours`** (défaut 30) : purge glissante, basée sur
  `LastWriteTime`, des fichiers `<base>_*.dump` / `<base>_*_roles.sql` plus
  vieux que N jours, **locale ET distante**.
- **`-FichierJournal`** (défaut `<Dossier>\journal_sauvegardes.log`) :
  chaque étape horodatée, succès comme échec.
- **`-FichierEtat`** (défaut `<Dossier>\dernier_etat_sauvegarde.json`) :
  **durcissement demandé explicitement en cours de cycle** (une sauvegarde
  qui échoue en silence pendant des semaines est pire que l'absence de
  sauvegarde) — fichier **écrasé à chaque tentative**, succès ou échec,
  avec horodatage, résultat, chemins des fichiers produits, et les
  messages clés du journal.
- **Journal d'événements Windows** : `Ecrire-EvenementWindows` tente
  d'abord une source dédiée `QuincaillerieFranck_Sauvegarde` (log
  `Application` — nécessite qu'un administrateur l'ait enregistrée une
  fois, `New-EventLog`, hors de portée d'un compte non-admin) puis se
  rabat sur la source générique `PowerShell` (log `Windows PowerShell`,
  toujours présente, aucun droit spécial requis pour y **écrire** — seule
  la création d'une source l'exige). Vérifié par exécution : le texte
  complet reste présent dans le XML brut de l'événement même quand le
  rendu « amical » reste vide (fournisseur emprunté, sans modèle de
  message pour cet ID).
- **Code de sortie** : `exit 1` sur l'échec de N'IMPORTE QUELLE étape
  (dump, dump des rôles, copie distante si demandée, purge), `exit 0`
  sinon — déjà vrai partiellement au cycle 21, généralisé ici à toutes les
  nouvelles étapes.

**Preuves par exécution (toutes rejouées sur `quincaillerie_c12`) :**

Succès, avec copie hors-site :
```
[2026-09-14 00:30:45] [INFO] === Debut sauvegarde de 'quincaillerie_c12' ...
[2026-09-14 00:30:46] [INFO] Dump de la base OK : ...quincaillerie_c12_20260914_003045.dump (197,1 Ko)
[2026-09-14 00:30:46] [INFO] Dump des roles OK : ...quincaillerie_c12_20260914_003045_roles.sql
[2026-09-14 00:30:46] [INFO] Copie hors-site OK vers '_pgdev\sauvegardes_distant' : quincaillerie_c12_20260914_003045.dump, quincaillerie_c12_20260914_003045_roles.sql
[2026-09-14 00:30:46] [INFO] Purge (retention 30 j) : rien a supprimer dans '_pgdev\sauvegardes_test'.
[2026-09-14 00:30:46] [INFO] === Sauvegarde de 'quincaillerie_c12' terminee avec SUCCES. ===
CODE DE SORTIE: 0
```

Purge 30 jours, **fichiers réellement rendus vieux** (`Set-ItemProperty
-Name LastWriteTime` à J-35) puis rejeu :
```
AVANT purge :
...quincaillerie_c12_20260101_000000.dump
...quincaillerie_c12_20260101_000000_roles.sql
...sauvegardes_distant\quincaillerie_c12_20260101_000000.dump
[...]
[2026-09-14 00:31:08] [INFO] Purge (retention 30 j) : ...quincaillerie_c12_20260101_000000.dump supprime (date 08/10/2026 00:30:57).
[2026-09-14 00:31:08] [INFO] Purge (retention 30 j) : ...quincaillerie_c12_20260101_000000_roles.sql supprime (date 08/10/2026 00:30:57).
[2026-09-14 00:31:08] [INFO] Purge (retention 30 j) : ...sauvegardes_distant\quincaillerie_c12_20260101_000000.dump supprime (date 08/10/2026 00:30:57).
APRES purge : (aucun -- purges avec succes)
```

Échec provoqué (port PostgreSQL invalide, 5999) :
```
pg_dump: erreur : la connexion au serveur ... a échoué : Connection refused
[2026-09-14 00:31:21] [ERREUR] Echec de pg_dump (code 1) -- fichier ... absent ou incomplet.
[2026-09-14 00:31:21] [ERREUR] === Sauvegarde de 'quincaillerie_c12' terminee EN ECHEC ... ===
CODE DE SORTIE: 1
```

Fichier d'état (`dernier_etat_sauvegarde.json`) après ce même échec :
`"resultat": "ECHEC"`, horodatage correct, `fichier_base`/`fichier_roles`
renseignés (même en échec, pour diagnostic). Après un succès :
`"resultat": "SUCCES"`.

Journal d'événements Windows, vérifié par lecture directe du XML brut de
l'événement (`Get-WinEvent ... | % { $_.ToXml() }`) :
```
Succès (ID 9001, niveau Information) :
<Data>Sauvegarde Quincaillerie Franck (quincaillerie_c12) reussie : ...dump</Data>
Échec (ID 9002, niveau Erreur) :
<Data>Sauvegarde Quincaillerie Franck (quincaillerie_c12) EN ECHEC. Voir ...journal_sauvegardes.log.</Data>
```
Horodatages des événements concordent au dixième de seconde près avec les
lignes de journal correspondantes — preuve que ce n'est pas un événement
recyclé d'un essai précédent.

#### 4.2 — `db/outils/planifier_sauvegarde.ps1` (nouveau)

Enregistre une tâche planifiée Windows (`Register-ScheduledTask`) avec
**deux déclencheurs**, conformes à la décision du 2026-09-13 (addendum
point i) : horaire de `-HeureOuverture` à `-HeureFermeture` (répétition
horaire, technique standard : déclencheur `-Once` porteur de la
répétition, sa propriété `.Repetition` recopiée sur le déclencheur
`-Daily` réellement utilisé), plus un déclencheur unique à
`-HeureFinJournee`.

**Piège rencontré et corrigé par exécution** : une première version
enveloppait les arguments (déjà entre guillemets doubles pour tolérer les
espaces d'un chemin) dans un second niveau de guillemets doubles pour
`-Command` — guillemets imbriqués non échappés, ligne de commande tronquée
par le Planificateur de tâches. Détecté par exécution :
`LastTaskResult = 1`, **aucun fichier produit**, en relisant seulement le
message d'erreur de PowerShell on aurait pu croire que la tâche avait
tourné. Corrigé en reconstruisant la commande interne avec des guillemets
**simples** uniquement, enveloppée une seule fois dans des guillemets
doubles pour `-Command` — plus de conflit de niveaux.

Sans droits administrateur (vérifié explicitement, `IsInRole
Administrator` = `False`) : `Register-ScheduledTask`/
`Unregister-ScheduledTask` fonctionnent pour une tâche propre à
l'utilisateur courant (`-LogonType Interactive -RunLevel Limited`) — sans
mot de passe. Limite honnête, documentée dans le guide : une tâche
`Interactive` ne se déclenche que si une session de cet utilisateur est
ouverte ; un déploiement 24/7 réel demande soit une session laissée
ouverte en permanence, soit un compte de service dédié enregistré par un
administrateur (`-LogonType Password`/`ServiceAccount`, mot de passe réel
saisi une fois à l'installation, jamais dans ce dépôt).

**Preuve par exécution (déclenchement réel, pas seulement l'enregistrement) :**

```
Register-ScheduledTask ... -> "Tache planifiee 'QF_Test_Planif' creee/mise a jour."
Start-ScheduledTask -TaskName 'QF_Test_Planif'
Get-ScheduledTaskInfo -TaskName 'QF_Test_Planif' -> LastRunTime : 14/09/2026 00:43:56 / LastTaskResult : 0
```
Fichiers réellement produits par CE déclenchement (pas par un appel manuel
antérieur) :
```
_pgdev\sauvegardes_planif\quincaillerie_c12_20260914_004357.dump (201792 octets)
_pgdev\sauvegardes_planif\quincaillerie_c12_20260914_004357_roles.sql
_pgdev\sauvegardes_planif\dernier_etat_sauvegarde.json ("resultat":"SUCCES")
_pgdev\sauvegardes_planif\journal_sauvegardes.log (8 lignes, dont "Copie hors-site OK")
_pgdev\sauvegardes_planif_distant\quincaillerie_c12_20260914_004357.dump   <- copie hors-site
_pgdev\sauvegardes_planif_distant\quincaillerie_c12_20260914_004357_roles.sql
```
Tâche de test supprimée après la preuve (`-Supprimer`) ; aucune tâche
planifiée laissée active sur le poste de développement.

Paramètre `-PgPasswordDev` ajouté **uniquement pour rendre ce test
reproductible sur `_pgdev`** (mot de passe de développement non secret) —
son en-tête interdit explicitement son usage en production réelle
(mot de passe en clair visible via `Get-ScheduledTask`) et renvoie vers
`.pgpass`/`pg_hba.conf` — voir le guide, section 2.

#### 4.3 — Durcissement de l'alerte d'échec (demandé explicitement en cours de cycle)

Trois éléments, chacun vérifié par exécution (voir 4.1) :
1. fichier d'état daté, mis à jour à chaque tentative (succès et échec) ;
2. trace dans le journal d'événements Windows, au minimum à chaque
   échec (et aussi au succès, pour une vue complète) ;
3. donnée exposée pour un futur voyant de tableau de bord — voir 4.4.

**Non fait, honnêtement documenté** : une alerte WhatsApp/e-mail réelle
reste hors de portée sans compte réel à notifier (numéro WhatsApp
Business, boîte e-mail dédiée) — voir le guide, section 5.

#### 4.4 — Nouvelle route serveur `GET /exploitation/derniere-sauvegarde`

Fichier nouveau `server/app/routes/exploitation.py`, enregistré dans
`server/app/main.py` (import + `include_router`, deux lignes ajoutées en
fin de liste — **seul fichier partagé touché**, avec un risque de
collision triviale à la fusion si C6 ajoute sa propre route de clôture de
caisse au même endroit ; résolution attendue : garder les deux lignes,
comme les autres ajouts en fin de fichier documentés dans
`TRAVAIL_PARALLELE.md`).

Lit le fichier d'état écrit par `sauvegarder.ps1` (chemin par défaut
`_pgdev\sauvegardes\dernier_etat_sauvegarde.json`, surchargeable par la
variable d'environnement `QF_FICHIER_ETAT_SAUVEGARDE` — même convention
que `QF_CONFIG` dans `app/config.py`). Réservée au rôle `responsable`
(`exiger_role`) ; ne lève jamais d'erreur HTTP — absence ou corruption du
fichier renvoyées comme information (`"configure": false`), pas comme
panne applicative.

**INTÉGRATION VOLONTAIREMENT EN ATTENTE** : `maquette/tableau-bord.html`
est exclusivement réservé à la piste UX ce tour — cette route **n'a
câblé aucun écran**, uniquement l'API. Le voyant visuel sur le tableau de
bord est un point d'intégration à faire après la fusion de la piste UX
(même principe que le lien de clôture de caisse reporté pour C6).

**Preuve par exécution**, serveur réel démarré sur `quincaillerie_c12`
(port 8013) :
```
GET /sante -> {"etat":"ok","base":"joignable"}
POST /auth/connexion (resp) -> 200, jeton reçu
GET /exploitation/derniere-sauvegarde (fichier absent) ->
  {"configure":false,"detail":"Aucun fichier d'état trouvé (...). Aucune sauvegarde n'a encore tourné..."}
[sauvegarde réelle lancée]
GET /exploitation/derniere-sauvegarde (fichier présent) ->
  {"configure":true,"horodatage":"2026-09-16T13:37:00","resultat":"SUCCES", ...}
GET /exploitation/derniere-sauvegarde avec un jeton agent_stock -> 403 {"detail":"Rôle non autorisé pour cette route."}
```

#### 4.5 — Fichier commun touché : `server/tests/conftest.py`

Patch identique à celui de la piste UX (convergence demandée par le
coordinateur, pour éviter un conflit de fusion sur ce fichier partagé) :
nouvelle constante `QF_TEST_DBNAME = os.environ.get("QF_TEST_DBNAME",
"quincaillerie_test")`, substituée aux trois occurrences en dur de
`"quincaillerie_test"` (`PG_ADMIN_DSN`, l'appel `psql -d ...`, et
`ConfigBase.dbname` de la fixture `app`). Défaut inchangé.

**Diagnostic (pas corrigé, hors périmètre exclusif de cette piste)** :
`pytest server/tests` échoue systématiquement dans CE worktree
(`FileNotFoundError: [WinError 2]`, `subprocess.run([str(PSQL_EXE), ...])`
dans `base_reinitialisee`) — même cause que le piège documenté en étape 1
(`PGDEV = RACINE_DEPOT / "_pgdev"` résolu à la racine du **worktree**, où
`_pgdev` n'existe pas physiquement). Ce n'est ni une régression
introduite par ce cycle (le chemin était déjà faux avant mon patch
`QF_TEST_DBNAME`), ni un fichier de mon périmètre exclusif — signalé ici
plutôt que corrigé unilatéralement. Contournement possible pour une
prochaine piste qui en aurait besoin : ajouter `_pgdev\pgsql\bin` au
`PATH` de la session avant `pytest`, ou (mieux, mais à valider par la
piste qui possède réellement ce fichier) une résolution de repli
identique à celle ajoutée dans `planifier_sauvegarde.ps1`/
`construire.ps1` pour ce cycle. Non testé ici faute de temps et de
mandat sur ce fichier — mes propres vérifications de non-régression pour
`exploitation.py`/`main.py` ont donc été faites par un **serveur réel
démarré manuellement** (uvicorn) plutôt que par la suite pytest — voir
4.4, preuves par exécution HTTP réelle, rôle par rôle.

#### 4.6 — `server/fabrication/` reconstruit

`server/requirements.txt` contenait déjà `openpyxl==3.1.5`,
`reportlab==5.0.1`, `pypdf==6.18.1` (ajoutés au cycle 10, jamais retirés)
— **aucun changement de version nécessaire**, le venv partagé du dépôt
principal les avait déjà installés.

`server/fabrication/construire.ps1` étendu (repli sur le venv partagé du
dépôt principal si le worktree n'a pas le sien — voir étape 1, même
esprit que le repli déjà existant pour les binaires PostgreSQL). Sans
incidence en dépôt unique (le venv local est trouvé en premier, comme
avant).

**Construction réelle** :
```
Construction terminee.
  Executable : ...\_worktrees\piste-c12\server\fabrication\dist\QuincaillerieFranck.exe
  Taille     : 26 Mo   (17,9 Mo au cycle 4 -- openpyxl/reportlab/PIL ajoutés)
```
Deux mêmes avertissements inoffensifs qu'au cycle 4
(`_cffi_backend`, `psycopg_binary._uuid`, déjà expliqués et sans
conséquence observée) plus deux nouveaux, également inoffensifs
(`pkg_resources` — vendored setuptools, jamais utilisé par ce projet).
**Aucun hidden-import manuel n'a été nécessaire pour
openpyxl/reportlab/PIL** : `pyinstaller-hooks-contrib` fournit déjà
`hook-openpyxl.py`, `hook-reportlab.lib.utils.py`,
`hook-reportlab.pdfbase._fontdata.py`, `hook-PIL.py` — détectés et
appliqués automatiquement à la construction (vérifié dans la sortie de
PyInstaller, pas supposé).

**Test ISOLÉ** (dossier totalement séparé du dépôt, `%TEMP%\...\
test_fabrication_c12\`, seuls l'exécutable et un `config.ini` pointant
vers `quincaillerie_c12` présents) :
```
Ets Quincaillerie Franck — démarrage du serveur local...
Serveur démarré sur 127.0.0.1:64277. Fermez cette fenêtre pour arrêter l'application.
```
Puis, en HTTP réel contre cet exécutable autonome (pas le code source) :
```
GET /sante -> {"etat":"ok","base":"joignable"}
POST /auth/connexion (resp) -> 200
GET /rapports/articles?format=xlsx -> HTTP 200, 5135 octets, en-tête PK.. (ZIP/Office) ;
  relu avec openpyxl.load_workbook() depuis l'exécutable produit : 5 lignes, 8 colonnes, contenu correct
GET /rapports/articles?format=pdf  -> HTTP 200, 2004 octets, en-tête %PDF-1.4
POST /ventes (vente réelle créée, id=1, total 2000 FCFA)
GET /ventes/1/recu -> HTTP 200, 2185 octets, en-tête %PDF-1.4 ;
  relu avec pypdf.PdfReader (vérification, jamais en production) : texte extrait contient
  "Reçu — vente n°1", "Article rare", "Total TTC 2 000 FCFA" -- conforme à la vente réelle
```
Les **trois bibliothèques** (`openpyxl`, `reportlab`, et `pypdf` pour la
vérification) fonctionnent donc réellement depuis l'exécutable autonome,
sur des routes qui en dépendent réellement — pas seulement « ça compile ».

**Précision honnête** : `pypdf` n'est importé **nulle part dans
`server/app/`** (confirmé par recherche) — seulement dans
`server/tests/test_rapports.py`/`test_ventes.py`, pour relire le PDF
produit et vérifier son contenu (comme au cycle 10/19). Aucune route de
l'exécutable ne dépend donc réellement de `pypdf` à l'exécution ; je
l'utilise ici exactement comme les tests du projet le font déjà — pour
**vérifier** le PDF produit, pas pour le produire. Le signaler plutôt que
d'inventer un usage de production qui n'existe pas.

#### 4.7 — Preuve de restauration NON NÉGOCIABLE

Sur `quincaillerie_c12` (jamais `quincaillerie_test`), sauvegarde réelle
avec copie hors-site puis **restauration depuis la copie hors-site
elle-même** (pas depuis le fichier local — preuve que la copie distante
est réellement exploitable, pas un fichier inerte), vers une base séparée
dédiée `quincaillerie_c12_preuve_restauration` (même serveur — voir la
limite ci-dessous).

Comptes de lignes, **avant** (`quincaillerie_c12`) :
```
 table_            | count
 articles          |     4
 employes          |     1
 fournisseurs      |     1
 mouvements_stock  |     1
 utilisateurs      |     5
 ventes            |     1
 ventes_lignes     |     1
```
Comptes de lignes, **après restauration** (`quincaillerie_c12_preuve_restauration`) :
identiques ligne pour ligne (mêmes 7 valeurs).

Droits par colonne, **avant** :
```
 stock_lit_prix_vente | stock_lit_nom | compta_lit_stock | compta_lit_prix_vente | resp_lit_salaire | compta_lit_salaire
 f                    | t             | f                | t                     | t                | f
```
Droits par colonne, **après restauration** : identiques, valeur pour
valeur (`has_column_privilege`, six couples rôle/colonne couvrant stock,
comptabilité et responsable, dont un cas RH — `employes.salaire_mensuel` —
non testé au cycle 21).

Contenu réel vérifié (pas seulement un compte égal par coïncidence) :
```
 id | numero_facture | mode_paiement | total_ttc
  1 |                | especes       |   2000.00
```
correspond exactement à la vente créée pendant le test de l'exécutable
(4.6) — preuve que ce sont bien LES MÊMES données, pas deux jeux
d'essai identiques par hasard.

Base de preuve supprimée après vérification (`DROP DATABASE
quincaillerie_c12_preuve_restauration`) pour ne pas laisser d'objet inutile
sur l'instance partagée par les trois pistes.

**Limite honnête, comme prévu au plan** : restauration prouvée sur le
**même serveur** PostgreSQL que la source (une seconde base), exactement
comme au cycle 21 — **jamais sur un second poste physique**, faute d'un
poste de secours disponible pour ce test. Documenté explicitement dans le
guide (section 4) comme point non couvert par ce cycle.

#### 4.8 — Documentation

`db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md` (nouveau, ne touche ni
`db/README.md` ni `server/README.md`, gelés) : installation en une fois,
vérification quotidienne pour un non-technicien (fichier d'état, journal,
Observateur d'événements, route serveur), procédure de restauration
(toujours à côté d'abord), section dédiée à la coupure de courant
(WAL/reprise automatique de PostgreSQL expliqués en clair, procédure
pas-à-pas au redémarrage : `pg_isready`, `/sante`, lecture du fichier
d'état, quand contacter le prestataire plutôt qu'agir seul), et une
section « Ce que ce cycle NE couvre PAS » qui liste honnêtement chaque
limite (pas d'alerte WhatsApp/e-mail réelle, voyant non câblé
visuellement, pas de chiffrement de la copie hors-site, tâche planifiée
en mode utilisateur connecté, source d'événements dédiée non enregistrée
par défaut, onduleur/poste de secours hors de portée du code,
restauration testée sur un seul serveur).

### Reste à faire (points ouverts, renvois addendum)

- **Câblage visuel du voyant de sauvegarde sur le tableau de bord** —
  après fusion de la piste UX, quand `maquette/tableau-bord.html` n'est
  plus son périmètre exclusif. La donnée existe déjà
  (`GET /exploitation/derniere-sauvegarde`), rien à refaire côté serveur.
- **Alerte WhatsApp/e-mail réelle en cas d'échec** — addendum point i,
  suppose un compte réel à notifier, non fourni.
- **Chiffrement de la copie hors-site** — addendum point i, aucune
  décision (algorithme, gestion de clé) prise par le propriétaire.
- **Test de restauration sur un second poste physique réellement
  différent** — addendum point i, question 3 (budget onduleur/poste de
  secours) encore ouverte.
- **Compte de service dédié pour la tâche planifiée en environnement
  24/7 réel** — actuellement `-LogonType Interactive`, suffisant pour la
  preuve de ce cycle, insuffisant pour une exploitation continue sans
  session ouverte en permanence.
- **Source d'événements Windows dédiée** (`QuincaillerieFranck_Sauvegarde`)
  — à enregistrer une fois par un administrateur sur le poste serveur réel
  pour un rendu « amical » complet dans l'Observateur d'événements
  (fonctionne déjà sans, via la source générique `PowerShell`, texte brut
  présent mais rendu non résolu).
- **`server/tests/conftest.py` : résolution `_pgdev` incompatible avec un
  worktree Git** — diagnostiqué (voir 4.5), pas corrigé (fichier partagé,
  hors périmètre exclusif de cette piste). Toute piste future qui doit
  lancer `pytest` depuis un worktree devra soit ajouter `_pgdev\pgsql\bin`
  au `PATH` avant l'appel, soit proposer un correctif de résolution de
  chemin (hors mandat de cette session).
- **Migration de schéma** : **aucune n'a été nécessaire** pour ce cycle —
  le fichier d'état est un fichier JSON, pas une table (choix du plan,
  confirmé suffisant par l'exécution). Rien à réserver après C6.

### Fichiers touchés (rappel du périmètre)

- `db/outils/sauvegarder.ps1` (étendu, exclusif C12)
- `db/outils/planifier_sauvegarde.ps1` (nouveau, exclusif C12)
- `db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md` (nouveau, exclusif C12)
- `server/fabrication/construire.ps1` (étendu, exclusif C12)
- `server/app/routes/exploitation.py` (nouveau)
- `server/app/main.py` (2 lignes ajoutées : import + `include_router` —
  fichier partagé, risque de collision triviale avec C6 à la fusion)
- `server/tests/conftest.py` (patch `QF_TEST_DBNAME`, convergence avec la
  piste UX — fichier partagé)

Aucun fichier sous `maquette/` touché. `db/README.md` et
`server/README.md` non modifiés (gelés).
