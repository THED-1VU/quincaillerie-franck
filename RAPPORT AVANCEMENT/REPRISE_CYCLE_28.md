# Reprise du cycle 28 — à lire en premier, session neuve

Ce fichier existe pour qu'une session Claude Code qui n'a **aucun accès à
la conversation précédente** puisse reprendre exactement où celle-ci s'est
arrêtée, sans reposer les questions déjà tranchées. Écrit le 2026-09-19,
avant un redémarrage de session demandé par le propriétaire.

**Ne pas fusionner ni redémarrer le cycle de finalisation sans avoir lu ce
fichier en entier**, ni sans instruction explicite du propriétaire.

## 1. Où en est le code : PR #30, PAS fusionnée

Branche `cycle-28-identite-logo-exploitation`, PR **#30** :
https://github.com/THED-1VU/quincaillerie-franck/pull/30

État au moment de l'écriture : **`OPEN`, `MERGEABLE`, non fusionnée.** Ne
pas la fusionner sans instruction explicite du propriétaire (règle
constante de ce projet — voir `.agents/skills/finalisation-loop/SKILL.md`).

Contenu de la PR (chantier C12 exploitation, choisi par le propriétaire
lui-même, plus deux tâches transverses) :

- **Chiffrement du fichier de sauvegarde** : AES-256-CBC + HMAC-SHA256, pur
  PowerShell/.NET, phrase de passe saisie par le responsable et jamais
  versionnée (`db/outils/sauvegarder.ps1` / `restaurer.ps1`).
- **Sauvegarde sans session Windows ouverte** :
  `db/outils/planifier_sauvegarde.ps1 -CompteSysteme` (tâche sous
  `NT AUTHORITY\SYSTEM`).
- **PostgreSQL comme service Windows**, redémarrage automatique après un
  arrêt brutal : `db/outils/enregistrer_service_pg.ps1` — **script écrit et
  vérifié syntaxiquement uniquement**, jamais exécuté en conditions
  réelles avant ce redémarrage de session (voir section 3).
- **Message clair en français** quand la base est injoignable
  (`server/app/main.py`, gestionnaire `psycopg.OperationalError`),
  `connect_timeout=5` (`server/app/database.py`) — corrige un blocage
  mesuré de 2 min 10 s avant cette correction.
- **Logo du client** (nouvelle fonction) : `POST/DELETE/GET
  /configuration/logo`, réservé au responsable, PNG/JPEG vérifiés par
  signature réelle du fichier, stocké hors base, inclus dans la sauvegarde
  chiffrée.
- **Identité visuelle Akuma** : Akuma = nom de la gamme logicielle
  (éditeur) ; **« Ets Quincaillerie Franck » reste le nom du client**,
  inchangé sur les reçus (`boutique_nom`). Logo décliné en 3 formats,
  thème aligné sur les deux couleurs du logo sans refonte d'écran,
  renommage de surface (titres, bandeau, exécutable `Akuma.exe`,
  documentation listée par le propriétaire).

Vérifié par exécution avant l'ouverture de la PR (`db/outils/
verifier_tout.sh`, base reconstruite depuis zéro) : suite SQL complète
0 échec, **183/183 pytest**, **9 suites Playwright, 210 contrôles, 0
échec**. Détail complet dans la description de la PR #30 et dans
`RAPPORT AVANCEMENT/loop-state.md`, entrée "Cycle 28".

## 2. Les 9 commandes administrateur données au propriétaire

Le propriétaire a ouvert un terminal PowerShell **administrateur** sur son
poste de développement pour exécuter, lui-même, ce qui exige des droits
que la session assistant n'a pas. Voici les 9 commandes transmises,
**une par une**, avec la sortie qui confirmerait chacune :

```powershell
# 1
cd "H:\2026\PROFESSIONNEL\THED CONNECT\QuincaillerieFranck_Test"
# confirme : le prompt affiche ce chemin

# 2
.\db\outils\enregistrer_service_pg.ps1
# confirme : dernière ligne verte "Service 'QuincaillerieFranck_PostgreSQL'
# enregistré, démarré et repond sur le port 5433."

# 3
Get-Service 'QuincaillerieFranck_PostgreSQL' | Format-List Status, StartType
# confirme : Status = Running, StartType = Automatic

# 4
sc.exe qfailure QuincaillerieFranck_PostgreSQL
# confirme : trois RESTART à 5000/10000/30000 ms, RESET_PERIOD 86400

# 5
Set-Content -Path "$env:TEMP\phrase_sauvegarde_test.txt" -Value 'PhraseDeTestCycle28VerificationReelle' -NoNewline
# confirme : aucune sortie (normal), ou relire avec Get-Content

# 6
.\db\outils\planifier_sauvegarde.ps1 -CompteSysteme -FichierPhrase "$env:TEMP\phrase_sauvegarde_test.txt" -PgPasswordDev qf_dev_local
# confirme : ligne verte "Tache planifiee 'QuincaillerieFranck_Sauvegarde' creee/mise a jour."

# 7
(Get-ScheduledTask -TaskName 'QuincaillerieFranck_Sauvegarde').Principal
# confirme : UserId = NT AUTHORITY\SYSTEM, LogonType = ServiceAccount

# 8
Start-ScheduledTask -TaskName 'QuincaillerieFranck_Sauvegarde'
Start-Sleep -Seconds 8
Get-ScheduledTaskInfo -TaskName 'QuincaillerieFranck_Sauvegarde'
# confirme : LastTaskResult = 0, LastRunTime à l'instant présent

# 9
Get-ChildItem "_pgdev\sauvegardes" | Sort-Object LastWriteTime -Descending | Select-Object -First 3 Name, LastWriteTime, Length
# confirme : au moins un fichier .enc daté de maintenant
```

**État d'exécution au moment de l'écriture de ce fichier : AUCUNE des 9
commandes n'a encore été confirmée exécutée.** Le propriétaire a demandé
ce fichier de reprise **avant** de les lancer, en prévision d'un
redémarrage de session. La session suivante doit **demander au
propriétaire où il en est** (a-t-il lancé tout ou partie des 9 commandes
pendant que cette session était fermée ?) avant de supposer quoi que ce
soit — ne jamais relancer une commande déjà exécutée sans vérifier
l'état réel d'abord (`Get-Service`, `Get-ScheduledTask`), conformément à
la règle du projet : jamais de confiance sur un rapport, toujours une
vérification par exécution réelle.

## 3. Ce qu'il reste à faire, dans l'ordre

1. **Si pas déjà fait** : obtenir du propriétaire la confirmation des 9
   sorties ci-dessus (ou les faire relancer), et **vérifier soi-même**
   l'état réel du service et de la tâche plutôt que de se fier au récit
   (`Get-Service 'QuincaillerieFranck_PostgreSQL'`, `Get-ScheduledTask
   -TaskName 'QuincaillerieFranck_Sauvegarde'`).
2. **Test du scénario complet, demandé explicitement par le
   propriétaire** (« je veux voir la trace réelle, pas la théorie ») :
   arrêt **brutal** de PostgreSQL (pas un arrêt propre — il faut simuler
   un plantage réel pour déclencher la récupération `sc.exe failure`,
   pas un `Stop-Service` normal qui n'active jamais ces actions), constat
   du redémarrage automatique du service, et vérification que
   l'application affiche le message clair en français pendant la coupure
   (pas un écran figé) puis repart seule. Points d'attention identifiés
   avant l'interruption :
   - Tuer le **postmaster** du service, pas un processus au hasard :
     `(Get-CimInstance Win32_Service -Filter "Name='QuincaillerieFranck_PostgreSQL'").ProcessId`
     puis `Stop-Process -Id <ce PID> -Force`. Ce geste exige des droits
     administrateur — la session assistant ne les a pas (vérifié plus tôt
     dans ce cycle : `Stop-Process`/`taskkill /F` sur un `postgres.exe`
     échouent avec Accès refusé depuis une session non élevée), donc
     **c'est au propriétaire de lancer cette commande précise**, au
     moment choisi avec la session qui reprend.
   - La route `GET /sante` **ne montre PAS** le nouveau message clair
     (elle capte `psycopg.Error` localement et renvoie son propre JSON
     dégradé, avant que le gestionnaire d'exception `OperationalError` de
     `main.py` n'entre en jeu) — utiliser une route métier réelle pour
     l'observer, par exemple `POST /auth/connexion` avec un couple
     identifiant/mot de passe valide (déjà utilisé pour vérifier le
     message pendant ce cycle).
   - Prévoir de démarrer le serveur applicatif (`server\.venv\Scripts\
     uvicorn.exe app.main:app --app-dir server --host 127.0.0.1 --port
     8010`, ou un autre port libre) et de suivre en direct
     (`curl`/`Invoke-WebRequest` en boucle courte) avant de demander au
     propriétaire de tuer le processus, pour capturer la vraie
     chronologie (dernier appel sain, premier message clair affiché,
     durée réelle de la coupure, premier appel de nouveau sain après le
     redémarrage automatique du service).
   - **Remettre PostgreSQL dans un état normal après le test** et
     prévenir le propriétaire, comme convenu pour toute manipulation de
     PostgreSQL sur ce poste ce cycle.
3. Une fois la preuve obtenue : consigner le résultat réel (trace, pas
   théorie) dans `RAPPORT AVANCEMENT/loop-state.md` (entrée du cycle 28)
   et dans la description de la PR #30, puis attendre l'instruction
   explicite du propriétaire avant de fusionner.

## 4. Constat signalé pour mémoire : `sauvegarder.ps1` mis en quarantaine trois fois

Pendant les essais de chiffrement de ce cycle, `db/outils/sauvegarder.ps1`
a **disparu du disque à trois reprises**, à chaque fois environ 10 à 15
secondes après une exécution **réussie** du script (`git status` montrait
le fichier en `D`, supprimé — jamais modifié). Reproduit une fois de
façon isolée (invocation `-File` puis `sleep 15`) pour confirmer que ce
n'est pas une coïncidence.

**Diagnostic (probable, pas certain à 100 %)** : le **Contrôle d'accès aux
dossiers** de Windows (protection anti-rançongiciel, distincte de la
protection en temps réel de Defender — celle-ci **confirmée désactivée**
via `Get-MpComputerStatus`, ce qui écarte un balayage antivirus ordinaire
comme cause) réagit au comportement du script (lire un fichier, écrire sa
version chiffrée, **supprimer l'original**) — un motif qui ressemble
exactement à un rançongiciel. `Get-MpPreference` a échoué avec une erreur
de fournisseur WMI, empêchant une confirmation directe de l'état du
Contrôle d'accès aux dossiers depuis cette session.

**Non éliminable depuis l'intérieur du script.** Contourné pendant ce
cycle en committant après chaque petit changement vérifié (restauration
via `git checkout --` à chaque disparition). Documenté comme **risque
opérationnel réel** dans `db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`
(section dédiée), avec la remédiation standard : ajouter
`powershell.exe` et/ou `Akuma.exe` à la liste des applications autorisées
du Contrôle d'accès aux dossiers (Windows Security → Protection contre
les rançongiciels).

**À surveiller sur le poste réel de la boutique** : si ce phénomène s'y
reproduit, la sauvegarde planifiée échouerait en silence côté fichier de
script lui-même (pas seulement côté résultat de sauvegarde) — vérifier en
premier lieu si ce risque se manifeste avant de chercher une autre cause.

## 5. Repères utiles pour une session neuve

- Dépôt : `THED-1VU/quincaillerie-franck`. Branche de travail de ce
  cycle : `cycle-28-identite-logo-exploitation`. `main` ne contient pas
  encore ces changements.
- PostgreSQL de développement : `127.0.0.1:5433`, utilisateur `postgres`,
  mot de passe `qf_dev_local` (dev local uniquement, voir `db/README.md`).
  Démarrage habituel : `db/outils/demarrer_pg.ps1` — **devient inutile
  une fois le service Windows enregistré** (étape 1 de ce fichier) : PostgreSQL
  démarre alors tout seul.
- Base de test : `quincaillerie_test`. Reconstruction complète + suite
  de non-régression : `db/outils/verifier_tout.sh` (nécessite `PSQL` et
  `PG_DUMP` pointés vers `_pgdev/pgsql/bin/` sur ce poste — voir l'en-tête
  du script).
- Serveur applicatif de dev : `server/.venv/Scripts/uvicorn.exe
  app.main:app --app-dir server --host 127.0.0.1 --port 8010` (le port
  8000 est parfois occupé par un processus sans rapport avec ce projet
  sur ce poste — vérifier avant de l'utiliser).
- Autorisation permanente pour ce cycle (donnée par le propriétaire) :
  arrêter/redémarrer PostgreSQL pour tester en conditions réelles, à
  condition de prévenir avant, de le remettre en marche après, et de ne
  jamais le faire sans un rappel explicite que c'est bien ce poste de
  développement (aucune donnée de production).
- Règle constante du projet : jamais de décision métier inventée, jamais
  de fusion sans instruction explicite, toujours vérifier par exécution
  réelle — voir `.agents/skills/finalisation-loop/SKILL.md`.
