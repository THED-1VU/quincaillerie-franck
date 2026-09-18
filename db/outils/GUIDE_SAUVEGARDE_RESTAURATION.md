# Guide de sauvegarde, restauration et continuité — Quincaillerie Franck

Chantier C12 (« Sauvegarde et exploitation »), cycle 22. Ce guide s'adresse
à l'exploitant du magasin, **pas nécessairement technicien** : chaque
commande est donnée telle qu'à copier-coller, sans supposer de
connaissance de PostgreSQL ou de PowerShell.

Ce document est **nouveau** et propre à la piste C12 : `db/README.md` et
`server/README.md` restent gelés pendant le travail en parallèle (voir
`RAPPORT AVANCEMENT/TRAVAIL_PARALLELE.md`) — c'est ici, et dans
`RAPPORT AVANCEMENT/cycles/piste-c12.md`, que tout ce qui concerne
l'exploitation réelle est consigné pour l'instant. Une fois la fusion
faite, son contenu a vocation à être repris (en tout ou partie) dans
`db/README.md`, section « Sauvegarde et restauration ».

---

## 1. Ce qui existe, et depuis quand

| Élément | Depuis | Rôle |
|---|---|---|
| `db/outils/sauvegarder.ps1` | Cycle 21, étendu cycles 22 et 28 | Produit une sauvegarde complète (contenu + rôles + logo de la boutique), **chiffrée (AES-256)**, la copie hors du poste serveur, purge les sauvegardes de plus de 30 jours, journalise chaque étape |
| `db/outils/restaurer.ps1` | Cycle 21, étendu cycle 28 | Déchiffre puis restaure une sauvegarde vers une base **séparée**, jamais par-dessus une base existante ; restaure aussi le logo |
| `db/outils/planifier_sauvegarde.ps1` | Cycle 22, étendu cycle 28 | Enregistre une tâche planifiée Windows qui déclenche `sauvegarder.ps1` automatiquement (RPO 1 heure), **sans exiger de session ouverte** (`-CompteSysteme`) |
| `db/outils/enregistrer_service_pg.ps1` | Cycle 28 (nouveau) | Enregistre PostgreSQL comme **service Windows**, avec reprise automatique après un plantage |

Décision du propriétaire (2026-09-13, `ADDENDUM_CAHIER_DES_CHARGES.md`,
point i, question 1) : **RPO cible 1 heure** — une sauvegarde automatique
**toutes les heures pendant les heures d'ouverture, plus une en fin de
journée**. C'est exactement ce que `planifier_sauvegarde.ps1` met en
place.

**Mise à jour cycle 28 (2026-09-18)** : trois failles opérationnelles
identifiées par le propriétaire ont été traitées ici — la sauvegarde
exigeait une session Windows ouverte (résolu, voir section 2) ; la copie
hors-site n'était pas chiffrée alors qu'elle contient les salaires et les
prix d'achat (résolu, voir section 6) ; et PostgreSQL, sur un plantage,
ne redémarrait jamais tout seul (résolu, voir section 2 également).

---

## 2. Installation en une fois (à faire par le prestataire, une seule fois)

Sur le poste serveur réel (PostgreSQL déjà installé, pas `_pgdev`), **en
tant qu'administrateur** (deux des quatre étapes l'exigent) :

```powershell
# 1. PostgreSQL en service Windows, avec reprise automatique après un
#    plantage (cycle 28) -- point le plus critique de cette liste : sans
#    lui, un arrêt anormal peut immobiliser la boutique jusqu'à ce qu'un
#    humain sache intervenir. Exige l'administrateur.
powershell -File db\outils\enregistrer_service_pg.ps1 -PgPort 5432

# 2. La phrase de chiffrement des sauvegardes (voir section 6 -- À LIRE
#    avant cette étape) -- un fichier local, jamais versionné.
"Une phrase longue et unique, choisie par le responsable" | Out-File -Encoding utf8 "C:\QuincaillerieFranck\phrase_chiffrement.txt"
icacls "C:\QuincaillerieFranck\phrase_chiffrement.txt" /inheritance:r /grant:r "SYSTEM:(R)"

# 3. Vérifier que le mécanisme de base fonctionne (facultatif mais recommandé)
powershell -File db\outils\sauvegarder.ps1 -Dossier "D:\Sauvegardes" -DossierDistant "\\poste-secours\sauvegardes" -NomBase quincaillerie -PgPort 5432 -FichierPhrase "C:\QuincaillerieFranck\phrase_chiffrement.txt"

# 4. Planifier l'automatisation (RPO 1 heure, addendum point i), SANS exiger
#    de session Windows ouverte (cycle 28) -- exige l'administrateur.
powershell -File db\outils\planifier_sauvegarde.ps1 -CompteSysteme -Dossier "D:\Sauvegardes" -DossierDistant "\\poste-secours\sauvegardes" -NomBase quincaillerie -PgPort 5432 -HeureOuverture "08:00" -HeureFermeture "18:00" -HeureFinJournee "20:00" -FichierPhrase "C:\QuincaillerieFranck\phrase_chiffrement.txt"
```

> **Protection anti-rançongiciel de Windows (« Accès contrôlé aux
> dossiers »).** Si elle est active sur le poste, elle peut bloquer
> `sauvegarder.ps1` : le script lit un fichier, produit une version chiffrée,
> puis supprime l'original — un comportement qui ressemble, de l'extérieur,
> à un rançongiciel. Si les sauvegardes s'arrêtent de fonctionner sans
> message d'erreur clair après cette installation, ouvrir *Sécurité
> Windows → Protection contre les virus et menaces → Gérer la protection
> contre les rançongiciels → Autoriser une application via l'accès contrôlé
> aux dossiers*, et y ajouter `powershell.exe` (ou l'exécutable
> `Akuma.exe` si la sauvegarde est un jour déclenchée depuis l'application
> elle-même).

Adapter `-HeureOuverture`/`-HeureFermeture` aux horaires réels de la
boutique. `-DossierDistant` doit être un emplacement **physiquement
différent** du poste serveur (partage réseau, second poste, disque
externe) — voir section 5 (limites) pour ce qui reste à trancher ici.

**Mot de passe PostgreSQL du compte de sauvegarde.** Ni `sauvegarder.ps1`
ni `planifier_sauvegarde.ps1` n'écrivent de mot de passe en clair dans un
fichier du dépôt. Sur le poste serveur réel, deux options :
- un fichier `.pgpass` (mécanisme standard PostgreSQL, permissions
  restreintes à l'utilisateur qui exécute la tâche) — **recommandé** ;
- une règle `pg_hba.conf` en `trust` ou `peer` pour les connexions
  **locales** de sauvegarde uniquement.

Ne jamais utiliser `-PgPasswordDev` de `planifier_sauvegarde.ps1` en
production réelle : ce paramètre existe uniquement pour ce dépôt de
développement (mot de passe fixe non secret `qf_dev_local`, voir
`db/README.md`) et écrirait un vrai mot de passe en clair, lisible par
quiconque peut lister les tâches planifiées du poste
(`Get-ScheduledTask`).

**Vérifier que la tâche est bien enregistrée :**

```powershell
Get-ScheduledTask -TaskName 'QuincaillerieFranck_Sauvegarde' | Get-ScheduledTaskInfo
```

**Déclencher un essai immédiat** (sans attendre la prochaine heure pleine) :

```powershell
Start-ScheduledTask -TaskName 'QuincaillerieFranck_Sauvegarde'
```

---

## 3. Vérifier au quotidien que les sauvegardes fonctionnent (non-technicien)

Trois façons, de la plus simple à la plus complète :

1. **Fichier d'état** — ouvrir avec le Bloc-notes
   `D:\Sauvegardes\dernier_etat_sauvegarde.json` (ou l'emplacement choisi
   à l'installation). Le champ `"resultat"` vaut `"SUCCES"` ou `"ECHEC"`,
   et `"horodatage"` donne la date/heure de la DERNIÈRE tentative — ce
   fichier est réécrit à **chaque** tentative, réussie ou non, jamais
   silencieux.
2. **Journal complet** — `D:\Sauvegardes\journal_sauvegardes.log`
   (Bloc-notes) : une ligne horodatée par étape, tout l'historique
   depuis l'installation.
3. **Observateur d'événements Windows** — touche Windows, taper
   « Observateur d'événements », ouvrir « Journaux Windows » →
   « Windows PowerShell » (ou « Application » si un administrateur a
   enregistré la source dédiée `QuincaillerieFranck_Sauvegarde` à
   l'installation, voir section 5). Chercher les événements de niveau
   « Erreur » — un déclic de « niveau erreur » ici veut dire qu'une
   sauvegarde a échoué.

Un développeur peut aussi interroger la route serveur dédiée (voir
`server/app/routes/exploitation.py`) :

```
GET /exploitation/derniere-sauvegarde
```

(réservée au compte responsable) — même information que le fichier
d'état, en JSON, pensée pour être affichée un jour comme un voyant sur le
tableau de bord (voir section 5, « Reste à faire »).

**Ce qu'il faut faire si `"resultat"` vaut `"ECHEC"` :** lire les dernières
lignes du journal (`journal_sauvegardes.log`) — chaque ligne `[ERREUR]`
explique concrètement ce qui a échoué (base injoignable, disque plein,
partage réseau inaccessible...). Contacter le prestataire avec ce
message exact plutôt que de réessayer au hasard.

---

## 4. Restaurer une sauvegarde (à faire UNIQUEMENT sur une base séparée d'abord)

**Règle absolue, jamais contournée** : on ne restaure JAMAIS directement
sur la base de production. `restaurer.ps1` applique cette règle
lui-même (il refuse si la base cible existe déjà, sauf `-Forcer`
explicite) — mais même avec `-Forcer`, restaurer d'abord à côté pour
vérifier reste la procédure à suivre :

```powershell
# 1. Restaurer À CÔTÉ (jamais sur la base réelle) -- -PhraseChiffrement
#    obligatoire depuis le cycle 28 pour un fichier .dump.enc (SANS elle,
#    aucune restauration n'est possible, voir section 6).
powershell -File db\outils\restaurer.ps1 -FichierBase "D:\Sauvegardes\quincaillerie_20260913_180000.dump.enc" -FichierRoles "D:\Sauvegardes\quincaillerie_20260913_180000_roles.sql.enc" -FichierLogo "D:\Sauvegardes\quincaillerie_20260913_180000_logo.png.enc" -PhraseChiffrement (Get-Content "C:\QuincaillerieFranck\phrase_chiffrement.txt" -Raw).Trim() -NomBaseCible quincaillerie_verification -PgPort 5432

# 2. Vérifier (avec psql, ou en pointant temporairement un config.ini de test dessus) :
#    - les 10 dernières ventes sont bien là et cohérentes
#    - le nombre d'articles, d'employés, d'utilisateurs correspond à ce qui est attendu
#    - un agent stock ne voit toujours pas les prix (has_column_privilege), etc.

# 3. Seulement si tout est bon, et seulement sur décision du responsable :
#    bascule réelle -- HORS DE PORTÉE d'un script automatique, décision humaine
#    (renommer/reconfigurer, jamais un simple "restaurer par-dessus")
```

**Limite honnête de ce cycle** : la preuve de restauration de ce document
(section 6 du rapport de cycle) a été faite sur le **même serveur
PostgreSQL** que la base source (une seconde base, `quincaillerie_..._
preuve_restauration`), comme au cycle 21 — **jamais sur un second poste
physique**, faute d'un second poste disponible pour ce test. Un test de
restauration sur un poste de secours RÉELLEMENT différent reste à faire
une fois un tel poste identifié (addendum, point i, question 3, encore
ouverte).

---

## 5. Ce que ce cycle NE couvre PAS (honnête, pas caché)

- **Pas de notification WhatsApp/e-mail réelle en cas d'échec.** L'addendum
  (point i) l'évoque, mais aucun compte réel (numéro WhatsApp Business,
  boîte e-mail dédiée) n'est disponible pour envoyer une vraie alerte.
  Plutôt que d'inventer un faux envoi, ce cycle pose trois garde-fous
  vérifiables par exécution (fichier d'état daté, journal .log, entrée dans
  l'Observateur d'événements Windows) — voir section 3. Câbler une vraie
  alerte (WhatsApp Business API, ou un simple envoi SMTP) est un chantier
  distinct, qui suppose que le propriétaire fournisse un compte réel.
- ~~Voyant de tableau de bord non câblé visuellement.~~ **Fait au cycle
  27** : `maquette/tableau-bord.html` affiche désormais une carte
  « Dernière sauvegarde » lisant `GET /exploitation/derniere-sauvegarde`.
- ~~Chiffrement de la copie hors-site non fait.~~ **Fait au cycle 28** :
  AES-256 (voir section 6), appliqué au fichier local ET à la copie
  hors-site — pas seulement celle qui voyage.
- ~~Tâche planifiée en mode « utilisateur connecté ».~~ **Résolu au cycle
  28** : `planifier_sauvegarde.ps1 -CompteSysteme` enregistre la tâche
  sous `NT AUTHORITY\SYSTEM`, sans session ni mot de passe requis (voir
  section 2). L'ancien mode `-LogonType Interactive` reste disponible par
  défaut pour un poste où l'installateur ne dispose pas de droits
  administrateur.
- **Source d'événements Windows dédiée non enregistrée par défaut.**
  Créer une NOUVELLE source d'événements (`QuincaillerieFranck_Sauvegarde`)
  exige des droits administrateur (écriture dans le Registre, `HKLM`).
  `sauvegarder.ps1` essaie d'abord cette source dédiée puis, si elle
  n'existe pas, se rabat automatiquement sur la source générique
  `PowerShell` (journal « Windows PowerShell »), déjà présente sur tout
  poste Windows — aucune installation supplémentaire requise, mais le
  rendu « amical » de l'événement dans l'Observateur peut rester vide
  (le texte complet reste néanmoins présent dans l'onglet « Détails »,
  vue XML). Un administrateur qui veut la source dédiée, avec un rendu
  propre, l'enregistre une fois : `New-EventLog -LogName Application
  -Source QuincaillerieFranck_Sauvegarde`.
- **Onduleur et poste de secours : hors de portée du code.** L'addendum
  (point i) les recommande ; aucun budget ni matériel n'a été identifié
  par le propriétaire (questions 2 et 3, encore ouvertes). Ce cycle ne
  fait qu'appliquer le mécanisme logiciel qui protégera les données une
  fois ce matériel en place.
- **Restauration testée sur le MÊME serveur uniquement** (voir section 4).
- **La CAUSE des plantages PostgreSQL n'est pas éliminée, seulement la
  reprise après coup.** `enregistrer_service_pg.ps1` (cycle 28) fait
  redémarrer PostgreSQL automatiquement après un plantage, mais le
  plantage lui-même (« could not reserve shared memory region », bug
  connu de PostgreSQL sous Windows, 15 occurrences observées en 6 jours
  sur le poste de développement) reste possible. Mitigation documentée,
  pas garantie : exclure `postgres.exe` (et le dossier `_pgdev`/
  l'installation PostgreSQL réelle) de l'antivirus du poste — une
  collision d'adressage mémoire est parfois aggravée par un antivirus qui
  injecte du code dans chaque processus.
- **`sauvegarder.ps1` peut être bloqué par la protection anti-rançongiciel
  de Windows** (« Accès contrôlé aux dossiers ») — voir l'encart en
  section 2. Observé sur le poste de développement : le script continue de
  fonctionner à l'exécution directe, mais le fichier de script lui-même a
  disparu du disque à plusieurs reprises, quelques secondes après une
  exécution réussie qui chiffre puis supprime l'original — un
  comportement qui ressemble, de l'extérieur, à un rançongiciel. Si les
  sauvegardes planifiées s'arrêtent de fonctionner sans qu'aucune erreur
  n'apparaisse, vérifier D'ABORD que `db\outils\sauvegarder.ps1` existe
  toujours sur le disque avant de chercher plus loin.

---

## 6. La phrase de chiffrement des sauvegardes — À LIRE avant toute installation

Depuis le cycle 28, chaque fichier de sauvegarde (contenu de la base,
rôles, logo de la boutique) est **chiffré** avant d'être écrit sur le
disque — y compris la copie qui reste sur le poste serveur, pas seulement
celle qui part sur une clé USB. C'est nécessaire : ces fichiers contiennent
les salaires du personnel et les prix d'achat des articles.

**Ce que cela veut dire concrètement, en français simple :**

- La sauvegarde est protégée par une **phrase de chiffrement**, choisie
  par le responsable au moment de l'installation (voir section 2).
- **Sans cette phrase, personne — ni l'éditeur du logiciel, ni un
  prestataire, ni qui que ce soit d'autre — ne peut lire le contenu
  d'une sauvegarde ni la restaurer.** Ce n'est pas une limite du
  logiciel : c'est le principe même du chiffrement, et c'est ce qui rend
  la sauvegarde utile sur une clé USB qui pourrait être perdue ou volée.
- **Il n'existe aucun moyen de récupérer une sauvegarde si cette phrase
  est perdue.** Une sauvegarde sans sa phrase n'est plus qu'un fichier
  illisible. Autant dire qu'elle n'existe plus.
- Cette phrase **ne doit jamais être notée dans ce dépôt, ni envoyée par
  e-mail ou WhatsApp, ni collée sur l'écran du poste serveur.** Elle vit
  dans un fichier local sur le poste serveur (voir section 2), lu
  automatiquement par les scripts — le responsable n'a pas besoin de la
  ressaisir à chaque sauvegarde.

**Où conserver cette phrase, HORS de la boutique :**

- Un endroit physique différent du magasin (domicile du responsable,
  coffre, ou tout lieu où un incendie ou un vol dans la boutique ne
  l'atteindrait pas en même temps que les postes).
- Idéalement, **écrite sur papier** plutôt que dans un fichier numérique
  facilement copiable ou perdu avec un téléphone.
- Si plusieurs personnes doivent pouvoir restaurer une sauvegarde en
  l'absence du responsable, prévoir une copie chez une seconde personne de
  confiance, au même titre qu'un double des clés du magasin.

**Que faire si la phrase a été changée ou si un doute existe** : garder
l'ANCIENNE phrase tant que d'anciennes sauvegardes chiffrées avec elle
existent encore — une sauvegarde reste liée à la phrase utilisée AU
MOMENT où elle a été produite, jamais à la phrase actuelle.

---

## 7. En cas de coupure de courant en pleine écriture

### Ce que PostgreSQL fait nativement (rien à configurer)

PostgreSQL écrit d'abord chaque changement dans un journal séquentiel
avant de le confirmer (*Write-Ahead Log*, WAL — mécanisme standard, actif
par défaut, sans réglage à faire pour ce projet) :

- une transaction qui n'a **jamais été confirmée** (`COMMIT`) au moment de
  la coupure est automatiquement annulée au redémarrage — comme si elle
  n'avait jamais eu lieu (ex. une vente en cours de saisie) ;
- une transaction **confirmée** juste avant la coupure, mais dont
  l'écriture définitive sur disque n'était pas encore terminée, est
  **rejouée** automatiquement depuis le WAL au redémarrage — aucune donnée
  confirmée n'est perdue ;
- ce mécanisme s'appelle la *reprise après incident* (*crash recovery*) :
  PostgreSQL le déclenche **tout seul**, silencieusement, dès qu'il
  redémarre et détecte que son arrêt précédent n'était pas propre. Aucune
  commande à taper pour ça.
- une sauvegarde (`pg_dump`) interrompue en cours d'écriture, elle, ne
  bénéficie PAS de ce mécanisme : le fichier `.dump` produit est
  **incomplet et inutilisable**. C'est pour cela que `sauvegarder.ps1`
  vérifie la présence ET compare le code de sortie de `pg_dump` avant de
  considérer une sauvegarde comme réussie (voir le fichier d'état,
  section 3) — un dump partiel ne doit jamais être confondu avec un bon.

### Procédure pas-à-pas pour l'exploitant (non technicien), au redémarrage

1. **Rallumer le poste serveur normalement.** Ne rien forcer, ne rien
   réinstaller.
2. **Attendre que PostgreSQL démarre** (démarrage automatique au boot,
   voir addendum point i) — compter une à deux minutes après l'écran de
   connexion Windows.
3. **Vérifier que PostgreSQL répond**, avec `pg_isready` (ouvrir une
   invite de commandes, PowerShell) :
   ```powershell
   & "C:\Program Files\PostgreSQL\<version>\bin\pg_isready.exe" -h 127.0.0.1 -p 5432
   ```
   Réponse attendue : `... accepting connections`. Si la réponse est
   différente, ou si la commande échoue, **ne pas continuer** — contacter
   le prestataire, ne pas tenter de « réparer » la base soi-même.
4. **Vérifier que l'application répond** : ouvrir
   `http://127.0.0.1:<port>/sante` dans un navigateur sur le poste
   serveur. Réponse attendue : `{"etat":"ok","base":"joignable"}`.
5. **Vérifier que le dernier dump automatique est valide**, en ouvrant
   `dernier_etat_sauvegarde.json` (section 3) : si son horodatage est
   antérieur à la coupure de plus d'une heure (RPO cible), la dernière
   sauvegarde utilisable date d'avant la coupure — c'est **attendu** (le
   RPO d'une heure signifie qu'on accepte de reperdre au pire la dernière
   heure de saisie, rattrapable via le facturier papier, addendum point
   i) : ce n'est **pas** un signe d'anomalie en soi.
6. **Reprendre l'activité normalement.** PostgreSQL a déjà fait le travail
   de reprise (étape « ce que PostgreSQL fait nativement » ci-dessus) —
   il n'y a rien de plus à faire côté base de données.
7. **Si `pg_isready` ou `/sante` échouent après plusieurs minutes** :
   c'est le seul cas où une intervention manuelle est nécessaire, et elle
   revient au prestataire (vérifier les journaux PostgreSQL dans son
   dossier `data\log\`) — **ne jamais** supprimer ou réinitialiser le
   dossier de données pour « repartir à zéro » : cela détruirait des
   données peut-être encore récupérables.

---

## 8. Référence rapide des scripts

| Script | Ce qu'il fait | Ne fait jamais |
|---|---|---|
| `sauvegarder.ps1` | dump + rôles + logo + **chiffrement AES-256** + copie hors-site + purge 30 j + journal + fichier d'état + événement Windows | ne modifie jamais la base source (lecture pure) ; ne produit jamais de fichier en clair sans `-PhraseChiffrement`/`-FichierPhrase` |
| `restaurer.ps1` | déchiffre puis restaure vers une base **nouvelle** ; restaure le logo | ne restaure jamais par-dessus une base existante sans `-Forcer` explicite ; ne déchiffre jamais sans la bonne phrase (rejet garanti par HMAC, pas seulement probable) |
| `planifier_sauvegarde.ps1` | enregistre/supprime une tâche planifiée Windows qui appelle `sauvegarder.ps1`, avec ou sans session ouverte (`-CompteSysteme`) | ne modifie jamais `sauvegarder.ps1` ni `restaurer.ps1` — seulement QUAND ils sont lancés |
| `enregistrer_service_pg.ps1` | enregistre PostgreSQL comme service Windows, avec reprise automatique après un plantage | n'élimine jamais la CAUSE d'un plantage (voir section 5) — seulement la reprise après coup |

Voir l'en-tête (`Get-Help -Full`) de chaque script pour la liste complète
des paramètres :

```powershell
Get-Help .\db\outils\sauvegarder.ps1 -Full
Get-Help .\db\outils\restaurer.ps1 -Full
Get-Help .\db\outils\planifier_sauvegarde.ps1 -Full
Get-Help .\db\outils\enregistrer_service_pg.ps1 -Full
```
