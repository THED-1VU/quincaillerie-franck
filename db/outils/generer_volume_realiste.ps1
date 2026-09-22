<#
.SYNOPSIS
    Genere une base a volume realiste pour la preuve de reprise C1 (cycle 39).

.DESCRIPTION
    Reconstruit la base -NomBase (par defaut quincaillerie_volume) de zero :
      1. schema d'origine (creation_base_donnees.sql) ;
      2. migrations 000-033 (les memes que la production, jamais a la main) ;
      3. jeu de volume realiste db/tests/volume_realiste.sql :
         ~1 000 articles, 2 sites, 600 ventes (30 jours), 1 800 lignes de
         vente, ~2 000 mouvements d'entree, 120 comptages, 3 comptes.

    Decision proprietaire (2026-09-22) : la preuve de reprise C1 se fait sur
    un volume genere (~1 000 references), pas sur le petit jeu d'essai.

    NOTE D'ENCODAGE : fichier volontairement en ASCII pur (meme regle que
    demarrer_pg.ps1 -- parseur PowerShell 5.1).

.PARAMETER NomBase
    Base a reconstruire. Defaut : quincaillerie_volume.

.PARAMETER PgHost / PgPort / Utilisateur
    Connexion PostgreSQL. Defaut : 127.0.0.1:5433, utilisateur postgres.

.PARAMETER PgPasswordDev
    UNIQUEMENT pour ce poste de DEVELOPPEMENT (_pgdev, mot de passe fixe
    non secret "qf_dev_local" -- voir db/README.md). Positionne PGPASSWORD
    avant chaque appel psql (une tache planifiee n'herite pas forcement des
    variables d'environnement de la session interactive).

.PARAMETER CheminPsql
    Chemin explicite de psql.exe. Defaut : _pgdev\pgsql\bin\psql.exe puis
    le PATH.
#>
param(
    [string]$NomBase = 'quincaillerie_volume',
    [string]$PgHost = '127.0.0.1',
    [int]$PgPort = 5433,
    [string]$Utilisateur = 'postgres',
    [string]$PgPasswordDev = 'qf_dev_local',
    [string]$CheminPsql = ''
)

$Racine = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
if ($PgPasswordDev) { $env:PGPASSWORD = $PgPasswordDev }

function Resoudre-Psql {
    if ($CheminPsql -ne '') {
        if (-not (Test-Path $CheminPsql)) { throw "CheminPsql introuvable : $CheminPsql" }
        return (Resolve-Path $CheminPsql).Path
    }
    $CandidatDev = Join-Path $Racine '_pgdev\pgsql\bin\psql.exe'
    if (Test-Path $CandidatDev) { return $CandidatDev }
    $Commande = Get-Command psql -ErrorAction SilentlyContinue
    if ($Commande) { return $Commande.Source }
    throw "psql introuvable : renseignez -CheminPsql ou installez PostgreSQL."
}

$Psql = Resoudre-Psql
$Creation = Join-Path $Racine 'QuincaillerieFranck_Test\creation_base_donnees.sql'
$Migrations = Join-Path $Racine 'db\migrations'
$Volume = Join-Path $Racine 'db\tests\volume_realiste.sql'

function Executer-Sql([string]$Fichier, [string]$Base, [string]$ArgumentsSupp = '') {
    & $Psql -h $PgHost -p $PgPort -U $Utilisateur -d $Base -v ON_ERROR_STOP=1 $ArgumentsSupp -q -f $Fichier
    if ($LASTEXITCODE -ne 0) { throw "Echec psql sur $Fichier (code $LASTEXITCODE)." }
}

Write-Host "== Reconstruction de $NomBase ($PgHost`:$PgPort) =="
& $Psql -h $PgHost -p $PgPort -U $Utilisateur -d postgres -q `
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$NomBase' AND pid <> pg_backend_pid();" `
    -c "DROP DATABASE IF EXISTS $NomBase;" `
    -c "CREATE DATABASE $NomBase;" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Echec de la recreation de $NomBase (code $LASTEXITCODE)." }

Executer-Sql $Creation $NomBase
Write-Host "== Application des migrations 000-033 =="
$Fichiers = Get-ChildItem -Path $Migrations -Filter '*.sql' |
    Where-Object { $_.Name -match '^[0-9]{3}_' -and $_.Name -notlike '*_inverse.sql' } |
    Sort-Object Name
foreach ($Fichier in $Fichiers) {
    Write-Host "-- $($Fichier.Name)"
    Executer-Sql $Fichier.FullName $NomBase '--single-transaction'
}

Write-Host "== Generation du volume realiste =="
Executer-Sql $Volume $NomBase

Write-Host "== Bilan =="
& $Psql -h $PgHost -p $PgPort -U $Utilisateur -d $NomBase -t -A -c "SELECT 'articles=' || count(*) FROM articles UNION ALL SELECT 'stocks_sites=' || count(*) FROM stocks_sites UNION ALL SELECT 'mouvements_stock=' || count(*) FROM mouvements_stock UNION ALL SELECT 'ventes=' || count(*) FROM ventes UNION ALL SELECT 'ventes_lignes=' || count(*) FROM ventes_lignes UNION ALL SELECT 'comptages_stock=' || count(*) FROM comptages_stock;"
Write-Host "== Termine : $NomBase prete pour la preuve de reprise. =="
