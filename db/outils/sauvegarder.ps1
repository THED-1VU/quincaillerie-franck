<#
.SYNOPSIS
    Sauvegarde complete de la base Quincaillerie Franck (chantier C12).

.DESCRIPTION
    Produit DEUX fichiers horodates dans le dossier de destination :
      - <base>_<horodatage>.dump       : contenu de la base (pg_dump,
        format "custom" -Fc -- compresse, restaurable par table, format
        recommande par PostgreSQL pour une restauration fiable).
      - <base>_<horodatage>_roles.sql  : les roles applicatifs (qf_app,
        qf_responsable, qf_agent_stock, qf_agent_comptabilite), GLOBAUX au
        serveur PostgreSQL -- jamais inclus dans un pg_dump d'une seule
        base (pg_dumpall --roles-only). Necessaire pour restaurer sur un
        NOUVEAU serveur, qui n'aurait pas encore ces roles.

    Ne modifie JAMAIS la base source : une sauvegarde est une lecture pure.

    NOTE D'ENCODAGE : fichier volontairement en ASCII pur. Voir la note
    dans demarrer_pg.ps1 -- un script .ps1 avec des caracteres accentues,
    une fois relu par Windows PowerShell 5.1, peut voir son parseur
    desynchronise (guillemets courbes mal decodes, etc.).

    Ce script pose le MECANISME (chantier C12). La FREQUENCE a laquelle le
    lancer, la duree de conservation des fichiers produits, et le RPO/RTO
    cible restent des decisions du proprietaire non tranchees (addendum,
    point i) -- voir db/README.md, section "Sauvegarde et restauration".
    Aucune valeur n'est inventee ici : ce script sauvegarde quand on
    l'appelle, un point c'est tout.

.PARAMETER Dossier
    Dossier de destination des fichiers de sauvegarde. Cree s'il n'existe
    pas. Par defaut : _pgdev\sauvegardes (developpement local -- jamais
    verse au depot, voir .gitignore). En deploiement reel, choisir un
    dossier HORS du poste (disque externe, reseau) : une sauvegarde sur le
    meme disque que la base ne protege de rien en cas de panne materielle.

.PARAMETER NomBase
    Nom de la base a sauvegarder. Par defaut "quincaillerie_test" (nom
    utilise partout en developpement -- voir config.ini). A adapter au nom
    reel de la base en production.

.PARAMETER PgHost
    Hote PostgreSQL. Par defaut 127.0.0.1.

.PARAMETER PgPort
    Port PostgreSQL. Par defaut 5433 (port du serveur de developpement
    local -- voir demarrer_pg.ps1). En deploiement reel, le port standard
    est 5432.

.PARAMETER Utilisateur
    Role de connexion utilise pour la sauvegarde -- superutilisateur ou
    proprietaire des objets, PAS le role applicatif qf_app (qui n'a pas les
    privileges necessaires pour lire toutes les tables sans restriction).
    Par defaut "postgres".

.EXAMPLE
    powershell -File db\outils\sauvegarder.ps1

.EXAMPLE
    powershell -File db\outils\sauvegarder.ps1 -Dossier "D:\Sauvegardes" -NomBase quincaillerie -PgPort 5432
#>

[CmdletBinding()]
param(
    [string]$Dossier = $null,
    [string]$NomBase = 'quincaillerie_test',
    [string]$PgHost = '127.0.0.1',
    [int]$PgPort = 5433,
    [string]$Utilisateur = 'postgres'
)

$ErrorActionPreference = 'Stop'

$Racine = Resolve-Path (Join-Path $PSScriptRoot '..\..')
if (-not $Dossier) {
    $Dossier = Join-Path $Racine '_pgdev\sauvegardes'
}

# Resolution des binaires : le dossier de developpement local en priorite
# (_pgdev\pgsql\bin, jamais verse au depot), sinon le PATH -- meme logique
# que demarrer_pg.ps1 / verifier_tout.sh.
function Resoudre-Binaire([string]$Nom) {
    $Candidat = Join-Path $Racine "_pgdev\pgsql\bin\$Nom.exe"
    if (Test-Path $Candidat) { return $Candidat }
    $Commande = Get-Command $Nom -ErrorAction SilentlyContinue
    if ($Commande) { return $Commande.Source }
    throw "Introuvable : $Nom (ni dans _pgdev\pgsql\bin, ni dans le PATH)."
}

$PgDump    = Resoudre-Binaire 'pg_dump'
$PgDumpAll = Resoudre-Binaire 'pg_dumpall'

if (-not (Test-Path $Dossier)) {
    New-Item -ItemType Directory -Path $Dossier -Force | Out-Null
}

$Horodatage = Get-Date -Format 'yyyyMMdd_HHmmss'
$FichierBase  = Join-Path $Dossier "${NomBase}_${Horodatage}.dump"
$FichierRoles = Join-Path $Dossier "${NomBase}_${Horodatage}_roles.sql"

Write-Host "Sauvegarde de la base '$NomBase' ($PgHost`:$PgPort) ..."
& $PgDump -h $PgHost -p $PgPort -U $Utilisateur -Fc -f $FichierBase $NomBase
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de pg_dump (code $LASTEXITCODE)." -ForegroundColor Red
    exit 1
}
$TailleBase = (Get-Item $FichierBase).Length
Write-Host ("  -> {0} ({1} Ko)" -f $FichierBase, [math]::Round($TailleBase / 1KB, 1)) -ForegroundColor Green

Write-Host "Sauvegarde des roles applicatifs (globaux au serveur) ..."
& $PgDumpAll -h $PgHost -p $PgPort -U $Utilisateur --roles-only -f $FichierRoles
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de pg_dumpall --roles-only (code $LASTEXITCODE)." -ForegroundColor Red
    exit 1
}
Write-Host "  -> $FichierRoles" -ForegroundColor Green

Write-Host ""
Write-Host "Sauvegarde terminee. Pour restaurer :" -ForegroundColor Green
Write-Host "  powershell -File db\outils\restaurer.ps1 -FichierBase `"$FichierBase`" -FichierRoles `"$FichierRoles`" -NomBaseCible <nouvelle_base>"
