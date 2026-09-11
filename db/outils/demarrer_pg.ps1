<#
.SYNOPSIS
    Demarre le serveur PostgreSQL de developpement de Quincaillerie Franck.

.DESCRIPTION
    Ce script ne suppose AUCUNE connaissance de PostgreSQL. Il :
      1. verifie que les binaires PostgreSQL sont presents dans _pgdev\pgsql
         (les telecharge et les installe tout seul si c'est la premiere fois) ;
      2. verifie que le repertoire de donnees _pgdev\data existe (l'initialise
         tout seul si c'est la premiere fois, avec un mot de passe de
         DEVELOPPEMENT LOCAL fixe - voir db/README.md) ;
      3. demarre le serveur sur 127.0.0.1:5433 s'il n'est pas deja demarre.

    _pgdev\ n'est JAMAIS versionne (voir .gitignore) : c'est un dossier de
    travail local, ~1 Go, propre a chaque poste.

    NOTE D'ENCODAGE : ce fichier est volontairement ecrit en ASCII pur (sans
    accent, sans tiret cadratin, sans guillemet francais). Un script .ps1 en
    UTF-8 SANS BOM, une fois relu par Windows PowerShell 5.1, peut voir ses
    caracteres accentues mal decodes au point de desynchroniser le parseur
    (guillemets courbes fabriques par erreur, parenthese qui semble manquante).
    Rester en ASCII evite ce probleme quel que soit le poste et sa page de code.

.EXAMPLE
    powershell -File db\outils\demarrer_pg.ps1

.EXAMPLE
    # Depuis n'importe quel dossier :
    & "H:\2026\PROFESSIONNEL\THED CONNECT\QuincaillerieFranck_Test\db\outils\demarrer_pg.ps1"
#>

[CmdletBinding()]
param(
    [int]$Port = 5433
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Emplacements. $PSScriptRoot = db\outils ; la racine du depot est deux
# niveaux au-dessus. Fonctionne quel que soit le lecteur ou le chemin exact.
# ---------------------------------------------------------------------------
$Racine   = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$PgDev    = Join-Path $Racine '_pgdev'
$PgBin    = Join-Path $PgDev 'pgsql\bin'
$DataDir  = Join-Path $PgDev 'data'
$LogFile  = Join-Path $PgDev 'server.log'

$PsqlExe    = Join-Path $PgBin 'psql.exe'
$InitdbExe  = Join-Path $PgBin 'initdb.exe'
$PgCtlExe   = Join-Path $PgBin 'pg_ctl.exe'
$IsReadyExe = Join-Path $PgBin 'pg_isready.exe'

# Mot de passe de DEVELOPPEMENT LOCAL uniquement. Ce dossier n'est jamais
# versionne (_pgdev\ est dans .gitignore) : ce n'est donc pas un secret qui
# fuit, seulement une valeur commode pour une base qui ne contient que des
# donnees de test. Voir db/README.md, section "Environnement de dev local".
$MotDePasseDev = 'qf_dev_local'

function EcrireEtape($msg) { Write-Host ''; Write-Host "== $msg ==" -ForegroundColor Cyan }

# ---------------------------------------------------------------------------
# 1. Binaires PostgreSQL - telecharges une seule fois, ~330 Mo
# ---------------------------------------------------------------------------
if (-not (Test-Path $PsqlExe)) {
    EcrireEtape "Telechargement de PostgreSQL 17 (premiere utilisation, ~330 Mo)"
    New-Item -ItemType Directory -Force -Path $PgDev | Out-Null

    $UrlZip = 'https://get.enterprisedb.com/postgresql/postgresql-17.11-3-windows-x64-binaries.zip'
    $ZipTmp = Join-Path $PgDev 'postgresql-binaires.zip'

    try {
        Write-Host "Telechargement depuis $UrlZip ..."
        Invoke-WebRequest -Uri $UrlZip -OutFile $ZipTmp -UseBasicParsing
    } catch {
        Write-Host ''
        Write-Host "ECHEC du telechargement : $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Verifiez la connexion Internet, puis relancez ce script." -ForegroundColor Red
        exit 1
    }

    Write-Host "Extraction..."
    Expand-Archive -Path $ZipTmp -DestinationPath $PgDev -Force
    Remove-Item $ZipTmp -Force

    if (-not (Test-Path $PsqlExe)) {
        Write-Host "ECHEC : psql.exe introuvable apres extraction dans $PgBin" -ForegroundColor Red
        exit 1
    }
    Write-Host "Binaires PostgreSQL installes dans $PgBin"
}

# ---------------------------------------------------------------------------
# 2. Repertoire de donnees - initialise une seule fois
# ---------------------------------------------------------------------------
if (-not (Test-Path (Join-Path $DataDir 'PG_VERSION'))) {
    EcrireEtape "Initialisation de la base de donnees (premiere utilisation)"

    if (Test-Path $DataDir) { Remove-Item $DataDir -Recurse -Force }

    $PwFile = Join-Path $PgDev 'mdp_initial.tmp'
    Set-Content -Path $PwFile -Value $MotDePasseDev -NoNewline -Encoding ascii

    try {
        & $InitdbExe -D $DataDir -U postgres --pwfile="$PwFile" -E UTF8 --locale=C `
            --auth-local=trust --auth-host=scram-sha-256
        if ($LASTEXITCODE -ne 0) { throw "initdb a echoue (code $LASTEXITCODE)" }
    } finally {
        Remove-Item $PwFile -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Base de donnees initialisee dans $DataDir"
    Write-Host "Utilisateur : postgres  /  Mot de passe (dev local) : $MotDePasseDev"
}

# ---------------------------------------------------------------------------
# 3. Demarrage du serveur (idempotent : ne fait rien s'il tourne deja)
# ---------------------------------------------------------------------------
EcrireEtape "Demarrage du serveur sur 127.0.0.1:$Port"

$env:PGPASSWORD = $MotDePasseDev
& $IsReadyExe -h 127.0.0.1 -p $Port *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Le serveur repond deja sur 127.0.0.1:$Port -- rien a faire."
} else {
    & $PgCtlExe -D $DataDir -l $LogFile -o "-p $Port -c listen_addresses=127.0.0.1" start
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ECHEC du demarrage. Consultez le journal : $LogFile" -ForegroundColor Red
        exit 1
    }

    $pret = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        & $IsReadyExe -h 127.0.0.1 -p $Port *> $null
        if ($LASTEXITCODE -eq 0) { $pret = $true; break }
    }
    if (-not $pret) {
        Write-Host "Le serveur ne repond pas apres 30 secondes. Journal : $LogFile" -ForegroundColor Red
        exit 1
    }
}

Write-Host ''
Write-Host "PostgreSQL de developpement est demarre." -ForegroundColor Green
Write-Host "  Hote / port  : 127.0.0.1 / $Port"
Write-Host "  Utilisateur  : postgres"
Write-Host "  Mot de passe : $MotDePasseDev   (dev local uniquement -- voir db/README.md)"
Write-Host "  Journal      : $LogFile"
Write-Host ''
Write-Host "Pour arreter : db\outils\arreter_pg.ps1"
