<#
.SYNOPSIS
    Arrete le serveur PostgreSQL de developpement de Quincaillerie Franck.

.DESCRIPTION
    Arret propre ("fast" : ferme les connexions en cours proprement, sans
    attendre une transaction qui ne se terminerait jamais). Ne fait rien --
    sans erreur -- si le serveur est deja arrete.

    NOTE D'ENCODAGE : fichier volontairement en ASCII pur. Voir la note dans
    demarrer_pg.ps1.

.EXAMPLE
    powershell -File db\outils\arreter_pg.ps1
#>

[CmdletBinding()]
param(
    [int]$Port = 5433
)

$ErrorActionPreference = 'Stop'

$Racine  = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$PgDev   = Join-Path $Racine '_pgdev'
$PgBin   = Join-Path $PgDev 'pgsql\bin'
$DataDir = Join-Path $PgDev 'data'

$PgCtlExe   = Join-Path $PgBin 'pg_ctl.exe'
$IsReadyExe = Join-Path $PgBin 'pg_isready.exe'

if (-not (Test-Path $PgCtlExe) -or -not (Test-Path $DataDir)) {
    Write-Host "Aucun serveur de developpement installe dans $PgDev -- rien a arreter."
    exit 0
}

& $IsReadyExe -h 127.0.0.1 -p $Port *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Le serveur n'etait pas demarre (127.0.0.1:$Port ne repondait pas)."
    exit 0
}

Write-Host "Arret du serveur sur 127.0.0.1:$Port ..."
& $PgCtlExe -D $DataDir -m fast stop
if ($LASTEXITCODE -ne 0) {
    Write-Host "L'arret a signale une erreur (code $LASTEXITCODE) -- verifiez le journal :" -ForegroundColor Yellow
    Write-Host (Join-Path $PgDev 'server.log')
    exit 1
}

Write-Host "Serveur arrete." -ForegroundColor Green
