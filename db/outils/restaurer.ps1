<#
.SYNOPSIS
    Restaure une sauvegarde Quincaillerie Franck sur une base SEPAREE
    (chantier C12).

.DESCRIPTION
    Restaure TOUJOURS vers une base NOUVELLE (NomBaseCible) : ce script ne
    touche jamais une base existante, encore moins la base de production.
    Prouver qu'une restauration fonctionne veut dire la rejouer a cote,
    jamais ecraser ce qui existe deja (voir le dossier de recette, "Test :
    Sauvegarde / restauration sur base separee").

    Etapes :
      1. Refuse si NomBaseCible existe deja (protection -- pas d'ecrasement
         silencieux ; -Forcer la supprime d'abord si explicitement demande).
      2. Cree NomBaseCible.
      3. Restaure le contenu (pg_restore, depuis FichierBase).
      4. Si -FichierRoles est fourni : rejoue les CREATE ROLE (psql). Sur
         le MEME serveur que celui sauvegarde, les roles existent deja --
         les erreurs "already exists" qui en resultent sont attendues et
         sans consequence (le but de ce fichier est de recreer les roles
         sur un NOUVEAU serveur qui ne les a pas encore).

.PARAMETER FichierBase
    Chemin du fichier .dump produit par sauvegarder.ps1.

.PARAMETER FichierRoles
    Chemin du fichier _roles.sql produit par sauvegarder.ps1. Optionnel :
    a fournir seulement pour restaurer sur un serveur qui n'a pas encore
    les roles applicatifs.

.PARAMETER NomBaseCible
    Nom de la NOUVELLE base a creer et restaurer. Doit etre different de
    la base source.

.PARAMETER PgHost
    Hote PostgreSQL. Par defaut 127.0.0.1.

.PARAMETER PgPort
    Port PostgreSQL. Par defaut 5433 (developpement local).

.PARAMETER Utilisateur
    Role de connexion superutilisateur. Par defaut "postgres".

.PARAMETER Forcer
    Si NomBaseCible existe deja, la supprime avant de restaurer. Sans ce
    drapeau, le script refuse plutot que d'ecraser silencieusement.

.EXAMPLE
    powershell -File db\outils\restaurer.ps1 -FichierBase "_pgdev\sauvegardes\quincaillerie_test_20260913_180000.dump" -NomBaseCible quincaillerie_restauree
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FichierBase,
    [string]$FichierRoles = $null,
    [Parameter(Mandatory = $true)]
    [string]$NomBaseCible,
    [string]$PgHost = '127.0.0.1',
    [int]$PgPort = 5433,
    [string]$Utilisateur = 'postgres',
    [switch]$Forcer
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $FichierBase)) {
    throw "Fichier de sauvegarde introuvable : $FichierBase"
}

$Racine = Resolve-Path (Join-Path $PSScriptRoot '..\..')

function Resoudre-Binaire([string]$Nom) {
    $Candidat = Join-Path $Racine "_pgdev\pgsql\bin\$Nom.exe"
    if (Test-Path $Candidat) { return $Candidat }
    $Commande = Get-Command $Nom -ErrorAction SilentlyContinue
    if ($Commande) { return $Commande.Source }
    throw "Introuvable : $Nom (ni dans _pgdev\pgsql\bin, ni dans le PATH)."
}

$Psql      = Resoudre-Binaire 'psql'
$PgRestore = Resoudre-Binaire 'pg_restore'

$env:PGPASSWORD = $env:PGPASSWORD  # transmis tel quel si deja positionne par l'appelant

$BaseExisteBrut = & $Psql -h $PgHost -p $PgPort -U $Utilisateur -d postgres -tAc `
    "SELECT 1 FROM pg_database WHERE datname = '$NomBaseCible'"
# psql -tAc ne renvoie AUCUNE ligne quand la base n'existe pas. PowerShell
# capture alors $BaseExisteBrut comme la valeur interne "AutomationNull" --
# distincte d'un $null ordinaire, sur laquelle MEME [string]$x ne redevient
# pas une chaine vide (elle reste "null" pour .GetType()/.Trim()). Seule
# une comparaison EXPLICITE ($null -eq ...) la detecte de facon fiable.
if ($null -eq $BaseExisteBrut) {
    $BaseExisteTexte = ''
} else {
    $BaseExisteTexte = ([string]$BaseExisteBrut).Trim()
}
if ($BaseExisteTexte -eq '1') {
    if (-not $Forcer) {
        throw "La base '$NomBaseCible' existe deja. Relancez avec -Forcer pour la remplacer, ou choisissez un autre nom -- ce script ne restaure JAMAIS par-dessus une base existante sans confirmation explicite."
    }
    Write-Host "La base '$NomBaseCible' existe deja -- suppression (Forcer demande) ..." -ForegroundColor Yellow
    & $Psql -h $PgHost -p $PgPort -U $Utilisateur -d postgres -q -c `
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$NomBaseCible' AND pid <> pg_backend_pid();" | Out-Null
    & $Psql -h $PgHost -p $PgPort -U $Utilisateur -d postgres -q -c "DROP DATABASE $NomBaseCible;" | Out-Null
}

if ($FichierRoles) {
    if (-not (Test-Path $FichierRoles)) {
        throw "Fichier de roles introuvable : $FichierRoles"
    }
    Write-Host "Rejeu des roles applicatifs (les erreurs 'already exists' sont attendues sur le serveur d'origine) ..."
    & $Psql -h $PgHost -p $PgPort -U $Utilisateur -d postgres -f $FichierRoles
}

Write-Host "Creation de la base '$NomBaseCible' ..."
& $Psql -h $PgHost -p $PgPort -U $Utilisateur -d postgres -q -c "CREATE DATABASE $NomBaseCible;"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de la creation de la base (code $LASTEXITCODE)." -ForegroundColor Red
    exit 1
}

Write-Host "Restauration du contenu depuis $FichierBase ..."
& $PgRestore -h $PgHost -p $PgPort -U $Utilisateur -d $NomBaseCible --no-owner --role=$Utilisateur $FichierBase
$CodeRestore = $LASTEXITCODE
# pg_restore renvoie parfois un code non nul pour des avertissements sans
# consequence (ordre de creation d'extensions, etc.) -- on verifie le
# resultat REEL juste apres (compte de tables), pas seulement le code.
$NbTablesBrut = & $Psql -h $PgHost -p $PgPort -U $Utilisateur -d $NomBaseCible -tAc `
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
if ($null -eq $NbTablesBrut) {
    $NbTables = '0'
} else {
    $NbTables = ([string]$NbTablesBrut).Trim()
}
$NbTablesEntier = 0
[void][int]::TryParse($NbTables, [ref]$NbTablesEntier)

Write-Host ""
if ($NbTablesEntier -gt 0) {
    Write-Host "Restauration terminee : $NbTables table(s) restauree(s) dans '$NomBaseCible'." -ForegroundColor Green
    if ($CodeRestore -ne 0) {
        Write-Host "(pg_restore a renvoye le code $CodeRestore -- voir les messages ci-dessus ; les tables sont neanmoins presentes.)" -ForegroundColor Yellow
    }
    exit 0
} else {
    Write-Host "Echec : aucune table trouvee dans '$NomBaseCible' apres restauration." -ForegroundColor Red
    exit 1
}
