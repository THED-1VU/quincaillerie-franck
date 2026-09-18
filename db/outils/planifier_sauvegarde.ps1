<#
.SYNOPSIS
    Cree (ou remplace) une tache planifiee Windows qui declenche
    sauvegarder.ps1 automatiquement (chantier C12).

.DESCRIPTION
    Decision du proprietaire (2026-09-13, addendum point i, question 1) :
    RPO cible 1 heure -- sauvegarde automatique HORAIRE pendant les heures
    d'ouverture, plus une sauvegarde de fin de journee. Ce script pose deux
    declencheurs (Register-ScheduledTask) sur UNE tache Windows qui
    execute sauvegarder.ps1 avec les parametres fournis :
      1. un declencheur quotidien a -HeureOuverture, repete toutes les
         heures jusqu'a -HeureFermeture (couvre les heures d'ouverture) ;
      2. un declencheur quotidien unique a -HeureFinJournee (le dump de
         fin de journee explicitement demande par l'addendum, en plus de
         la derniere sauvegarde horaire des heures d'ouverture -- utile si
         la boutique reste active apres la derniere heure pleine, ou pour
         inclure les toutes dernieres operations de fermeture de caisse).

    NE MODIFIE JAMAIS sauvegarder.ps1 ni restaurer.ps1 : ce script se
    contente d'enregistrer QUAND ils sont lances, jamais COMMENT.

    SESSION WINDOWS (decision du proprietaire, 2026-09-18) : par defaut, ce
    script enregistre la tache pour l'utilisateur Windows courant
    (-LogonType Interactive), sans mot de passe -- c'est la seule maniere
    de creer une tache planifiee sans droits administrateur. Une tache
    Interactive ne se declenche QUE si cet utilisateur est ouvert sur une
    session Windows -- inacceptable sur le poste serveur reel de la
    boutique (« sans cela, il n'y aura simplement pas de sauvegarde »).

    -CompteSysteme resout cette limite : enregistre la tache sous
    NT AUTHORITY\SYSTEM (compte integre Windows, AUCUN mot de passe requis,
    s'execute SANS session utilisateur ouverte). Contrepartie : cette
    COMMANDE D'ENREGISTREMENT (pas les executions ulterieures de la tache
    elle-meme) doit etre lancee UNE FOIS par un administrateur du poste --
    verifie explicitement, refuse proprement sinon plutot qu'un message
    Windows cryptique.
    Ce choix revient a l'installateur du poste serveur reel ; voir
    db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md.

    NOTE D'ENCODAGE : fichier volontairement en ASCII pur (voir
    demarrer_pg.ps1).

.PARAMETER NomTache
    Nom de la tache planifiee Windows. Par defaut
    "QuincaillerieFranck_Sauvegarde".

.PARAMETER HeureOuverture
    Heure (HH:mm) de la premiere sauvegarde horaire de la journee. Par
    defaut "08:00".

.PARAMETER HeureFermeture
    Heure (HH:mm) de la DERNIERE sauvegarde horaire de la journee (la
    repetition horaire s'arrete a cette heure -- une sauvegarde a lieu
    A cette heure meme). Par defaut "18:00".

.PARAMETER HeureFinJournee
    Heure (HH:mm) de la sauvegarde de fin de journee, en plus des
    sauvegardes horaires ci-dessus. Par defaut "20:00".

.PARAMETER Dossier
    Transmis tel quel a sauvegarder.ps1 (-Dossier). Voir sauvegarder.ps1.

.PARAMETER DossierDistant
    Transmis tel quel a sauvegarder.ps1 (-DossierDistant). Voir
    sauvegarder.ps1 -- fortement recommande de le fournir : une tache
    planifiee sans copie hors-site sauvegarde automatiquement mais reste
    vulnerable a une panne materielle du poste serveur.

.PARAMETER RetentionJours
    Transmis tel quel a sauvegarder.ps1 (-RetentionJours). Par defaut 30.

.PARAMETER NomBase
    Transmis tel quel a sauvegarder.ps1 (-NomBase). Par defaut
    "quincaillerie_test".

.PARAMETER PgHost
    Transmis tel quel a sauvegarder.ps1 (-PgHost). Par defaut 127.0.0.1.

.PARAMETER PgPort
    Transmis tel quel a sauvegarder.ps1 (-PgPort). Par defaut 5433
    (developpement local -- 5432 en production reelle).

.PARAMETER Utilisateur
    Transmis tel quel a sauvegarder.ps1 (-Utilisateur). Par defaut
    "postgres".

.PARAMETER PgPasswordDev
    UNIQUEMENT pour ce poste de DEVELOPPEMENT (_pgdev, mot de passe fixe
    non secret "qf_dev_local" -- voir db/README.md). Si fourni, la tache
    planifiee positionne $env:PGPASSWORD AVANT d'appeler sauvegarder.ps1,
    parce qu'une tache planifiee ne herite pas forcement des variables
    d'environnement de la session interactive qui l'a enregistree.

    NE JAMAIS FAIRE CECI EN PRODUCTION REELLE : le mot de passe apparaitrait
    en clair dans la definition de la tache (visible via Get-ScheduledTask
    par quiconque peut lister les taches planifiees du poste). Sur le
    poste serveur reel, utiliser un fichier .pgpass (mecanisme standard
    PostgreSQL, permissions NTFS restreintes a l'utilisateur qui execute
    la tache) ou une regle pg_hba.conf "trust"/"peer" pour les connexions
    LOCALES de sauvegarde -- jamais un mot de passe sur la ligne de
    commande d'une tache planifiee.

.PARAMETER FichierPhrase
    Transmis tel quel a sauvegarder.ps1 (-FichierPhrase) : chemin d'un
    fichier local (jamais versionne, permissions NTFS restreintes) qui
    contient la phrase de chiffrement des sauvegardes (cycle 28). Un
    CHEMIN n'est pas un secret -- c'est la seule maniere sure de la
    fournir a une tache planifiee, jamais la phrase elle-meme en ligne de
    commande.

.PARAMETER CompteSysteme
    Enregistre la tache sous NT AUTHORITY\SYSTEM au lieu de l'utilisateur
    courant -- voir la section SESSION WINDOWS ci-dessus. Exige d'executer
    CETTE commande en tant qu'administrateur (verifie explicitement).

.PARAMETER Supprimer
    Si present, supprime la tache planifiee -NomTache au lieu d'en creer
    une (nettoyage, ou avant de la recreer avec d'autres parametres).

.EXAMPLE
    powershell -File db\outils\planifier_sauvegarde.ps1 -DossierDistant "D:\Sauvegardes_hors_site" -NomBase quincaillerie -PgPort 5432

.EXAMPLE
    powershell -File db\outils\planifier_sauvegarde.ps1 -Supprimer
#>

[CmdletBinding()]
param(
    [string]$NomTache = 'QuincaillerieFranck_Sauvegarde',
    [string]$HeureOuverture = '08:00',
    [string]$HeureFermeture = '18:00',
    [string]$HeureFinJournee = '20:00',
    [string]$Dossier = $null,
    [string]$DossierDistant = $null,
    [int]$RetentionJours = 30,
    [string]$NomBase = 'quincaillerie_test',
    [string]$PgHost = '127.0.0.1',
    [int]$PgPort = 5433,
    [string]$Utilisateur = 'postgres',
    [string]$PgPasswordDev = $null,
    [string]$FichierPhrase = $null,
    [switch]$CompteSysteme,
    [switch]$Supprimer
)

$ErrorActionPreference = 'Stop'

Import-Module ScheduledTasks -ErrorAction Stop

if ($Supprimer) {
    $Existe = Get-ScheduledTask -TaskName $NomTache -ErrorAction SilentlyContinue
    if ($Existe) {
        Unregister-ScheduledTask -TaskName $NomTache -Confirm:$false
        Write-Host "Tache '$NomTache' supprimee." -ForegroundColor Green
    } else {
        Write-Host "Tache '$NomTache' introuvable -- rien a supprimer." -ForegroundColor Yellow
    }
    exit 0
}

$Racine = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$ScriptSauvegarde = Join-Path $PSScriptRoot 'sauvegarder.ps1'
if (-not (Test-Path $ScriptSauvegarde)) {
    throw "Introuvable : $ScriptSauvegarde"
}

# Recherche du dossier _pgdev\pgsql\bin (binaires PostgreSQL portables de
# developpement local -- voir db/README.md) en remontant depuis ce script,
# jusqu'a 5 niveaux : necessaire pour un WORKTREE Git (ce script peut vivre
# dans _worktrees\<piste>\db\outils, deux niveaux plus profond que le
# depot principal qui contient _pgdev). Sans resultat (poste de production
# reel, qui n'a jamais de dossier _pgdev), la tache planifiee compte
# simplement sur pg_dump/pg_dumpall deja presents dans le PATH systeme --
# comportement normal d'une installation PostgreSQL standard.
function Chercher-DossierPgsqlBin([string]$Depart) {
    $Courant = Resolve-Path $Depart
    for ($i = 0; $i -lt 6; $i++) {
        $Candidat = Join-Path $Courant '_pgdev\pgsql\bin\pg_dump.exe'
        if (Test-Path $Candidat) {
            return (Join-Path $Courant '_pgdev\pgsql\bin')
        }
        $Parent = Split-Path $Courant -Parent
        if (-not $Parent -or $Parent -eq $Courant) { break }
        $Courant = $Parent
    }
    return $null
}

$DossierPgsqlBin = Chercher-DossierPgsqlBin $PSScriptRoot

try {
    $DebutOuverture = [datetime]::ParseExact($HeureOuverture, 'HH:mm', $null)
    $FinOuverture   = [datetime]::ParseExact($HeureFermeture, 'HH:mm', $null)
    $FinJournee     = [datetime]::ParseExact($HeureFinJournee, 'HH:mm', $null)
} catch {
    throw "Heures invalides -- format attendu HH:mm (ex. 08:00). $($_.Exception.Message)"
}
if ($FinOuverture -le $DebutOuverture) {
    throw "-HeureFermeture ($HeureFermeture) doit etre APRES -HeureOuverture ($HeureOuverture)."
}

# Construction de la commande interne (celle qui appelle reellement
# sauvegarder.ps1), TOUJOURS avec des guillemets SIMPLES pour chaque valeur
# -- elle sera elle-meme enveloppee dans des guillemets DOUBLES pour
# -Command ci-dessous ; des guillemets doubles imbriques a cet endroit
# tronqueraient la ligne de commande transmise par le Planificateur de
# taches (piege rencontre et corrige par execution : LastTaskResult=1,
# aucun fichier produit, avec la version precedente qui utilisait "`"...`""
# a l'interieur d'un -Command deja entre guillemets doubles).
function Echapper-Simple([string]$Valeur) {
    # Un chemin Windows ne contient pratiquement jamais d'apostrophe ; on la
    # double neanmoins par principe (convention PowerShell : ' -> '').
    return $Valeur.Replace("'", "''")
}

$PrefixeChemin = ''
if ($PgPasswordDev) {
    # Voir .PARAMETER PgPasswordDev -- developpement uniquement.
    $PrefixeChemin += "`$env:PGPASSWORD = '$(Echapper-Simple $PgPasswordDev)'; "
}
if ($DossierPgsqlBin) {
    # Poste de developpement / worktree : la tache doit pouvoir retrouver
    # pg_dump/pg_dumpall meme si le PATH herite au declenchement (session
    # utilisateur) ne les contient pas. Prepend fait dans le PROCESSUS de
    # la tache uniquement -- jamais une modification persistante du PATH
    # de l'utilisateur ou du systeme. Sur un poste de production reel (pas
    # de dossier _pgdev), $DossierPgsqlBin est $null et cette ligne est
    # simplement absente : pg_dump est alors cherche dans le PATH systeme,
    # comme le pose deja sauvegarder.ps1 lui-meme.
    $PrefixeChemin += "`$env:Path = '$(Echapper-Simple $DossierPgsqlBin);' + `$env:Path; "
}

$CommandeInterneListe = @("& '$(Echapper-Simple $ScriptSauvegarde)'")
$CommandeInterneListe += "-NomBase '$(Echapper-Simple $NomBase)'"
$CommandeInterneListe += "-PgHost '$(Echapper-Simple $PgHost)'"
$CommandeInterneListe += "-PgPort $PgPort"
$CommandeInterneListe += "-Utilisateur '$(Echapper-Simple $Utilisateur)'"
$CommandeInterneListe += "-RetentionJours $RetentionJours"
if ($Dossier) {
    $CommandeInterneListe += "-Dossier '$(Echapper-Simple $Dossier)'"
}
if ($DossierDistant) {
    $CommandeInterneListe += "-DossierDistant '$(Echapper-Simple $DossierDistant)'"
}
if ($FichierPhrase) {
    # Un CHEMIN, jamais la phrase elle-meme : voir sauvegarder.ps1,
    # .PARAMETER FichierPhrase -- seule valeur sans risque a poser ici,
    # visible via Get-ScheduledTask comme le reste de cette commande.
    $CommandeInterneListe += "-FichierPhrase '$(Echapper-Simple $FichierPhrase)'"
}
$CommandeInterne = $PrefixeChemin + ($CommandeInterneListe -join ' ')

# Un seul niveau de guillemets doubles ici (autour de $CommandeInterne, qui
# ne contient plus lui-meme QUE des guillemets simples) : plus de conflit
# de quoting a l'execution par le Planificateur de taches.
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$CommandeInterne`"" `
    -WorkingDirectory "$Racine"

# Declencheur 1 : horaire, de -HeureOuverture a -HeureFermeture inclus.
# New-ScheduledTaskTrigger ne propose -RepetitionInterval/-RepetitionDuration
# qu'avec -Once ; le contournement standard (documente par Microsoft) est
# de creer un declencheur -Once porteur de la repetition souhaitee, puis de
# recopier sa propriete .Repetition sur le declencheur quotidien reellement
# utilise.
$DureeRepetition = New-TimeSpan -Start $DebutOuverture -End $FinOuverture
$TriggerModele = New-ScheduledTaskTrigger -Once -At $DebutOuverture `
    -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration $DureeRepetition
$TriggerHoraire = New-ScheduledTaskTrigger -Daily -At $DebutOuverture
$TriggerHoraire.Repetition = $TriggerModele.Repetition

# Declencheur 2 : un dump supplementaire de fin de journee (addendum point i).
$TriggerFinJournee = New-ScheduledTaskTrigger -Daily -At $FinJournee

if ($CompteSysteme) {
    # NT AUTHORITY\SYSTEM (cycle 28, decision du proprietaire 2026-09-18) :
    # AUCUN mot de passe requis (compte integre Windows), s'execute SANS
    # qu'une session utilisateur soit ouverte -- resout la limite documentee
    # ci-dessus pour -LogonType Interactive. Contrepartie : l'ENREGISTREMENT
    # de la tache (cette commande, pas les executions ulterieures) exige des
    # droits administrateur -- verifie explicitement ci-dessous plutot que
    # de laisser Register-ScheduledTask echouer avec un message cryptique.
    $EstAdmin = ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $EstAdmin) {
        Write-Host "ERREUR : -CompteSysteme exige d'executer CE script en tant qu'administrateur (une seule fois, a l'installation)." -ForegroundColor Red
        Write-Host "Sans droits administrateur, utilisez le mode par defaut (session ouverte requise) ou faites executer cette commande par un administrateur du poste."
        exit 1
    }
    $Principal = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\SYSTEM' -LogonType ServiceAccount -RunLevel Highest
} else {
    # Compte courant, sans mot de passe : voir la limite documentee ci-dessus
    # (.DESCRIPTION) et dans GUIDE_SAUVEGARDE_RESTAURATION.md -- exige une
    # session ouverte en permanence sur le poste serveur reel.
    $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
}

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $NomTache -Action $Action -Trigger @($TriggerHoraire, $TriggerFinJournee) `
    -Principal $Principal -Settings $Settings -Force `
    -Description "Sauvegarde automatique de la base Quincaillerie Franck (RPO 1h, addendum point i). Genere par db/outils/planifier_sauvegarde.ps1, ne pas modifier a la main -- relancer ce script pour changer les parametres." `
    | Out-Null

Write-Host "Tache planifiee '$NomTache' creee/mise a jour." -ForegroundColor Green
Write-Host ""
Write-Host "Declencheurs :"
Write-Host "  - horaire de $HeureOuverture a $HeureFermeture (chaque heure)"
Write-Host "  - fin de journee a $HeureFinJournee"
Write-Host ""
Write-Host "Commande executee a chaque declenchement :"
Write-Host "  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command `"$CommandeInterne`""
Write-Host ""
Write-Host "Verifier :"
Write-Host "  Get-ScheduledTask -TaskName '$NomTache' | Get-ScheduledTaskInfo"
Write-Host "Declencher immediatement (test) :"
Write-Host "  Start-ScheduledTask -TaskName '$NomTache'"
Write-Host "Supprimer :"
Write-Host "  powershell -File db\outils\planifier_sauvegarde.ps1 -Supprimer -NomTache '$NomTache'"
