<#
.SYNOPSIS
    Enregistre PostgreSQL comme SERVICE WINDOWS, avec reprise automatique
    apres un arret anormal (chantier C12, cycle 28).

.DESCRIPTION
    Constat central de ce cycle : PostgreSQL, sur le poste de developpement
    actuel, tourne comme un simple PROCESSUS lance par demarrer_pg.ps1 --
    RIEN ne le relance apres un arret anormal (plantage, coupure de
    courant). Trouve par execution, plus grave que les plantages
    eux-memes : apres un arret qui se declare pourtant reussi, des
    processus postgres.exe residuels peuvent meme EMPECHER un nouveau
    demarrage tant qu'un humain ne les a pas termines a la main -- sur le
    poste reel de la boutique, cela veut dire aucune vente possible jusqu'a
    ce que quelqu'un sache ouvrir un terminal.

    Ce script resout cela en DEUX temps :
      1. `pg_ctl register` : enregistre PostgreSQL comme service Windows
         (demarrage automatique au demarrage du systeme -- POSTGRESQL SE
         RELANCE MEME APRES UN REDEMARRAGE COMPLET DU POSTE, pas seulement
         apres son propre plantage).
      2. `sc.exe failure` : configure la RECUPERATION APRES ECHEC du
         service lui-meme -- si le PROCESSUS s'arrete de facon anormale
         (plantage), Windows le relance automatiquement (5 s, puis 10 s,
         puis 30 s pour les echecs suivants), SANS intervention humaine.

    Ce que ce script NE resout PAS : la cause des plantages (ex. l'erreur
    Windows "could not reserve shared memory region", bug connu de
    PostgreSQL sous Windows lie a une collision d'adressage memoire,
    parfois aggravee par un antivirus qui injecte du code dans chaque
    processus). Voir GUIDE_SAUVEGARDE_RESTAURATION.md pour la mitigation
    documentee (exclusion antivirus de postgres.exe).

    EXIGE DES DROITS ADMINISTRATEUR (verifie explicitement) -- ni
    demarrer_pg.ps1 ni sauvegarder.ps1 ne les exigent, c'est le SEUL script
    de ce projet qui le fait, parce que c'est la SEULE operation qui
    l'exige reellement (enregistrer un service Windows).

    NOTE D'ENCODAGE : fichier volontairement en ASCII pur (voir
    demarrer_pg.ps1).

.PARAMETER NomService
    Nom du service Windows. Par defaut "QuincaillerieFranck_PostgreSQL".

.PARAMETER PgPort
    Port d'ecoute de PostgreSQL. Par defaut 5433 (developpement local --
    5432 en production reelle).

.PARAMETER Supprimer
    Si present, arrete et desenregistre le service au lieu de l'enregistrer.

.EXAMPLE
    powershell -File db\outils\enregistrer_service_pg.ps1
    (a executer UNE FOIS, en tant qu'administrateur, sur le poste serveur reel)

.EXAMPLE
    powershell -File db\outils\enregistrer_service_pg.ps1 -Supprimer
#>

[CmdletBinding()]
param(
    [string]$NomService = 'QuincaillerieFranck_PostgreSQL',
    [int]$PgPort = 5433,
    [switch]$Supprimer
)

$ErrorActionPreference = 'Stop'

$EstAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $EstAdmin) {
    Write-Host "ERREUR : ce script doit etre execute en tant qu'administrateur (une seule fois, a l'installation du poste serveur reel)." -ForegroundColor Red
    exit 1
}

$Racine = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$DataDir = Join-Path $Racine '_pgdev\data'
$PgCtl   = Join-Path $Racine '_pgdev\pgsql\bin\pg_ctl.exe'

if (-not (Test-Path $PgCtl)) {
    Write-Host "ERREUR : introuvable : $PgCtl" -ForegroundColor Red
    Write-Host "Sur un poste de production reel, adapter -DataDir/pg_ctl a l'installation PostgreSQL du systeme (pas la copie portable de developpement)."
    exit 1
}

if ($Supprimer) {
    Write-Host "Arret et desenregistrement du service '$NomService' ..."
    & sc.exe stop $NomService | Out-Null
    Start-Sleep -Seconds 2
    & $PgCtl unregister -N $NomService
    Write-Host "Service '$NomService' desenregistre." -ForegroundColor Green
    exit 0
}

if (-not (Test-Path $DataDir)) {
    Write-Host "ERREUR : repertoire de donnees introuvable : $DataDir" -ForegroundColor Red
    exit 1
}

# Si PostgreSQL tourne deja comme simple processus (demarrer_pg.ps1),
# l'arreter proprement avant d'enregistrer le service -- eviter que les
# deux essaient d'ecouter sur le meme port en meme temps.
$IsReady = Join-Path $Racine '_pgdev\pgsql\bin\pg_isready.exe'
& $IsReady -h 127.0.0.1 -p $PgPort *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "PostgreSQL repond deja sur le port $PgPort (processus autonome) -- arret avant enregistrement du service ..."
    & $PgCtl stop -D $DataDir -m fast
    Start-Sleep -Seconds 2
}

Write-Host "Enregistrement du service '$NomService' (demarrage automatique) ..."
& $PgCtl register -D $DataDir -N $NomService -S auto -o "-p $PgPort -c listen_addresses=127.0.0.1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de l'enregistrement (code $LASTEXITCODE)." -ForegroundColor Red
    exit 1
}

# Reprise automatique APRES UN PLANTAGE du service lui-meme (pas seulement
# le demarrage automatique au demarrage du systeme, deja couvert par
# -S auto ci-dessus) : trois tentatives espacees (5 s, 10 s, 30 s), le
# compteur d'echecs revenant a zero apres 24 h sans nouvel echec.
Write-Host "Configuration de la reprise automatique apres plantage ..."
& sc.exe failure $NomService reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

Start-Sleep -Seconds 2
& sc.exe start $NomService | Out-Null
Start-Sleep -Seconds 2
& $IsReady -h 127.0.0.1 -p $PgPort
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Service '$NomService' enregistre, demarre et repond sur le port $PgPort." -ForegroundColor Green
    Write-Host "Se relance desormais automatiquement : au demarrage du poste (service Windows)"
    Write-Host "ET apres un plantage du processus (recuperation configuree ci-dessus)."
    Write-Host ""
    Write-Host "Verifier :  Get-Service '$NomService'"
    Write-Host "Supprimer : powershell -File db\outils\enregistrer_service_pg.ps1 -Supprimer"
    exit 0
} else {
    Write-Host "ATTENTION : le service est enregistre mais ne repond pas encore sur le port $PgPort -- verifier _pgdev\server.log." -ForegroundColor Yellow
    exit 1
}
