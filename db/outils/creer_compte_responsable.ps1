<#
.SYNOPSIS
    Cree le tout premier compte responsable (chantier C0-C, cycle 31).

.DESCRIPTION
    Sur une installation neuve, aucun compte n'existe encore : personne ne
    peut se connecter. Ce script cree le premier compte "responsable"
    (site NULL, actif, changement de mot de passe impose a la premiere
    connexion) en appelant la fonction SQL creer_premier_responsable()
    (migration 023, SECURITY DEFINER) avec le role applicatif qf_app.

    Il refuse si un responsable existe deja, si l'identifiant est vide ou
    deja pris, ou si le mot de passe fait moins de 8 caracteres.

    Le mot de passe est demande en mode masque (jamais affiche, jamais ecrit
    dans un fichier). La fonction SQL le hache immediatement (bcrypt $2a$,
    12 tours) : ce script ne manipule jamais le hachage.

    MODE DE VERIFICATION AUTOMATISEE : si les trois variables
    d'environnement QF_PREMIER_COMPTE_NOM, QF_PREMIER_COMPTE_IDENTIFIANT et
    QF_PREMIER_COMPTE_MOT_DE_PASSE sont toutes renseignees, le script les
    utilise au lieu des invites interactives (usage : tests automatises,
    deploiement scripte). Le mot de passe transite alors par l'environnement
    du processus, jamais par la ligne de commande ni par un fichier.

    NOTE D'ENCODAGE : ce fichier est volontairement en ASCII pur. Voir la
    note dans db/outils/demarrer_pg.ps1 (Windows PowerShell 5.1 peut mal
    decoder un script UTF-8 sans BOM contenant des accents).

.PARAMETER ConfigIni
    Chemin du config.ini de l'application (section [database]) : host, port,
    dbname, user (qf_app) et son mot de passe. Defaut : server\config.ini a
    la racine du depot (developpement), sinon config.ini a cote de ce
    script.

.PARAMETER CheminPsql
    Binaire psql a utiliser. Defaut : _pgdev\pgsql\bin\psql.exe s'il existe,
    sinon "psql" trouve sur le PATH.

.EXAMPLE
    powershell -File db\outils\creer_compte_responsable.ps1
#>

[CmdletBinding()]
param(
    [string]$ConfigIni = "",
    [string]$CheminPsql = ""
)

$ErrorActionPreference = 'Stop'

# db/outils/ -> racine du depot = deux niveaux au-dessus.
$Racine = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function EcrireEtape($msg) { Write-Host ''; Write-Host "== $msg ==" -ForegroundColor Cyan }

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

function Lire-ConfigIni([string]$Chemin, [string]$Section) {
    if (-not (Test-Path $Chemin)) { throw "ConfigIni introuvable : $Chemin" }
    $DansSection = $false
    $Valeurs = @{}
    foreach ($Ligne in Get-Content $Chemin) {
        $Ligne = $Ligne.Trim()
        if ($Ligne -match '^\s*\[') {
            $DansSection = ($Ligne -eq "[$Section]")
            continue
        }
        if (-not $DansSection) { continue }
        if ($Ligne -match '^\s*([^#;][^=]*?)\s*=\s*(.*)$') {
            $Cle = $Matches[1].Trim()
            $Val = $Matches[2].Trim()
            $Valeurs[$Cle] = $Val
        }
    }
    return $Valeurs
}

function Demander-MotDePasse {
    $Premier = Read-Host "Mot de passe du responsable" -AsSecureString
    $Second  = Read-Host "Confirmez le mot de passe" -AsSecureString
    $Clair1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Premier))
    $Clair2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Second))
    if ($Clair1 -cne $Clair2) { throw "Les deux saisies du mot de passe ne correspondent pas." }
    if ($Clair1.Length -lt 8) { throw "Le mot de passe doit comporter au moins 8 caracteres." }
    return $Clair1
}

# --- Configuration -----------------------------------------------------------
if ($ConfigIni -eq '') {
    $CandidatConfig = Join-Path $Racine 'server\config.ini'
    if (Test-Path $CandidatConfig) { $ConfigIni = $CandidatConfig }
    else { $ConfigIni = Join-Path $PSScriptRoot 'config.ini' }
}
$Base = Lire-ConfigIni $ConfigIni 'database'
foreach ($Cle in @('host', 'port', 'dbname', 'user', 'password')) {
    if (-not $Base.ContainsKey($Cle) -or [string]::IsNullOrWhiteSpace($Base[$Cle])) {
        throw "Cle [$Cle] absente de la section [database] de $ConfigIni"
    }
}
if ($Base['user'] -eq 'postgres') {
    throw "Ce script doit se connecter avec qf_app, jamais avec le compte superutilisateur postgres."
}

$Psql = Resoudre-Psql

# --- Saisie ------------------------------------------------------------------
EcrireEtape "Creation du premier compte responsable"
Write-Host "Base : $($Base['dbname']) sur $($Base['host']):$($Base['port']) (utilisateur $($Base['user']))"

$NomAuto   = $env:QF_PREMIER_COMPTE_NOM
$IdentAuto = $env:QF_PREMIER_COMPTE_IDENTIFIANT
$MdpAuto   = $env:QF_PREMIER_COMPTE_MOT_DE_PASSE

if ($NomAuto -and $IdentAuto -and $MdpAuto) {
    # Verification automatisee (ou deploiement scripte) : les trois valeurs
    # viennent de l'environnement, aucune invite interactive.
    $NomComplet  = $NomAuto.Trim()
    $Identifiant = $IdentAuto.Trim()
    $MotDePasse  = $MdpAuto
    if ($MotDePasse.Length -lt 8) { throw "Le mot de passe doit comporter au moins 8 caracteres." }
} else {
    $NomComplet = Read-Host "Nom complet du responsable"
    if ([string]::IsNullOrWhiteSpace($NomComplet)) { throw "Le nom complet est obligatoire." }
    $Identifiant = Read-Host "Identifiant de connexion"
    if ([string]::IsNullOrWhiteSpace($Identifiant)) { throw "L'identifiant est obligatoire." }
    $MotDePasse = Demander-MotDePasse
}

# --- Appel de la fonction SQL ------------------------------------------------
# Le mot de passe de connexion (qf_app) passe par la variable d'environnement
# PGPASSWORD, jamais par la ligne de commande. Les valeurs saisies sont
# insérées comme littéraux SQL correctement echappes (apostrophe doublee),
# jamais par concatenation naive : un identifiant ou un nom contenant une
# apostrophe ne peut pas casser ni detourner la requete.
function Litteral-Sql([string]$Texte) {
    return "'" + ($Texte -replace "'", "''") + "'"
}
$Sql = "SELECT creer_premier_responsable(" `
     + (Litteral-Sql $NomComplet) + ", " `
     + (Litteral-Sql $Identifiant) + ", " `
     + (Litteral-Sql $MotDePasse) + ");"
$env:PGPASSWORD = $Base['password']
try {
    $Sortie = & $Psql -h $Base['host'] -p $Base['port'] -U $Base['user'] -d $Base['dbname'] `
        -v ON_ERROR_STOP=1 -t -A -q `
        -c $Sql 2>&1
    $Code = $LASTEXITCODE
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
if ($Code -ne 0) {
    throw "Echec de la creation. Reponse du serveur : $Sortie"
}

$Id = ($Sortie | Select-Object -Last 1).Trim()
Write-Host ''
Write-Host "Compte responsable cree (id $Id, identifiant : $($Identifiant.Trim()))." -ForegroundColor Green
Write-Host "A la premiere connexion, le mot de passe devra etre change."
