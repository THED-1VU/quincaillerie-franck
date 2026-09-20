<#
.SYNOPSIS
    Rapproche les fiches articles homonymes, une par une (chantier 13a).

.DESCRIPTION
    Avant la migration article/stock multi-site (cycle 13b), deux articles
    portant le MEME nom sur des sites DIFFERENTS doivent etre rapproches par
    un HUMAIN : le proprietaire decide pour chaque paire "fusionner" (une
    seule fiche) ou "distincts" (deux articles differents qui se ressemblent
    par coincidence). Jamais de fusion automatique aveugle.

    Ce script liste les paires candidates (meme nom apres suppression des
    espaces de bord, sites differents, sans decision deja enregistree) via la
    fonction SQL candidats_rapprochement() (migration 025, SECURITY DEFINER),
    puis enregistre chaque decision via enregistrer_rapprochement().

    MODE DE VERIFICATION AUTOMATISEE : si les quatre variables
    d'environnement QF_RAPPROCHEMENT_ARTICLE_1, QF_RAPPROCHEMENT_ARTICLE_2,
    QF_RAPPROCHEMENT_DECISION et QF_RAPPROCHEMENT_DECIDE_PAR sont toutes
    renseignees, le script traite cette paire unique sans invite interactive
    (usage : tests automatises, deploiement scripte).

    NOTE D'ENCODAGE : ce fichier est volontairement en ASCII pur (voir la
    note dans db/outils/demarrer_pg.ps1).

.PARAMETER ConfigIni
    Chemin du config.ini de l'application (section [database]) : host, port,
    dbname, user (qf_app) et son mot de passe. Defaut : server\config.ini a
    la racine du depot (developpement), sinon config.ini a cote de ce
    script.

.PARAMETER CheminPsql
    Binaire psql a utiliser. Defaut : _pgdev\pgsql\bin\psql.exe s'il existe,
    sinon "psql" trouve sur le PATH.

.EXAMPLE
    powershell -File db\outils\rapprocher_articles.ps1
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

function Executer-Sql([string]$Sql) {
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
        throw "Echec SQL. Reponse du serveur : $Sortie"
    }
    return @($Sortie | Where-Object { $_ -ne '' })
}

function Lire-Candidats {
    $Lignes = Executer-Sql "SELECT article_id_1, article_id_2, nom, site_id_1, site_id_2, quantite_stock_1, quantite_stock_2 FROM candidats_rapprochement() ORDER BY nom, article_id_1, article_id_2;"
    $Candidats = @()
    foreach ($Ligne in $Lignes) {
        $Champs = $Ligne -split '\|'
        if ($Champs.Count -ne 7) { continue }
        $Candidats += [pscustomobject]@{
            Article1 = [int]$Champs[0]; Article2 = [int]$Champs[1]
            Nom      = $Champs[2]
            Site1    = [int]$Champs[3]; Site2    = [int]$Champs[4]
            Quantite1 = [int]$Champs[5]; Quantite2 = [int]$Champs[6]
        }
    }
    return $Candidats
}

function Enregistrer-Decision([int]$Article1, [int]$Article2, [string]$Decision, [string]$DecidePar) {
    $Sql = "SELECT enregistrer_rapprochement($Article1, $Article2, " `
         + (Litteral-Sql $Decision) + ", " + (Litteral-Sql $DecidePar) + ");"
    $Resultat = Executer-Sql $Sql
    return ($Resultat | Select-Object -Last 1).Trim()
}

function Litteral-Sql([string]$Texte) {
    return "'" + ($Texte -replace "'", "''") + "'"
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

# --- Candidats ----------------------------------------------------------------
EcrireEtape "Rapprochement des fiches articles homonymes"
Write-Host "Base : $($Base['dbname']) sur $($Base['host']):$($Base['port']) (utilisateur $($Base['user']))"

$Candidats = Lire-Candidats
if ($Candidats.Count -eq 0) {
    Write-Host "Aucune paire homonyme a traiter." -ForegroundColor Green
    exit 0
}

$Article1Auto = $env:QF_RAPPROCHEMENT_ARTICLE_1
$Article2Auto = $env:QF_RAPPROCHEMENT_ARTICLE_2
$DecisionAuto = $env:QF_RAPPROCHEMENT_DECISION
$DecideParAuto = $env:QF_RAPPROCHEMENT_DECIDE_PAR

if ($Article1Auto -and $Article2Auto -and $DecisionAuto -and $DecideParAuto) {
    # Verification automatisee : une seule paire, pas d'invite interactive.
    $A1 = [int]$Article1Auto
    $A2 = [int]$Article2Auto
    if ($DecisionAuto -notin @('fusionner', 'distincts')) {
        throw "QF_RAPPROCHEMENT_DECISION invalide : attendu fusionner ou distincts."
    }
    $Id = Enregistrer-Decision $A1 $A2 $DecisionAuto $DecideParAuto
    Write-Host "Decision enregistree (id $Id) : articles $A1 et $A2 -> $DecisionAuto." -ForegroundColor Green
    $Restants = Lire-Candidats
    Write-Host "Paires restantes a traiter : $($Restants.Count)."
    exit 0
}

# Mode interactif : une par une, jamais de fusion aveugle.
Write-Host "$($Candidats.Count) paire(s) homonyme(s) a traiter." -ForegroundColor Yellow
$DecidePar = Read-Host "Votre nom (enregistre avec chaque decision)"
if ([string]::IsNullOrWhiteSpace($DecidePar)) { throw "Le nom est obligatoire." }

$Traitees = 0
foreach ($Candidat in $Candidats) {
    Write-Host ''
    Write-Host "Article $($Candidat.Article1) : $($Candidat.Nom) — site $($Candidat.Site1), stock $($Candidat.Quantite1)" -ForegroundColor White
    Write-Host "Article $($Candidat.Article2) : $($Candidat.Nom) — site $($Candidat.Site2), stock $($Candidat.Quantite2)" -ForegroundColor White
    $Reponse = Read-Host "Fusionner en une seule fiche ? (o = fusionner / n = distincts / q = quitter)"
    $Reponse = $Reponse.Trim().ToLowerInvariant()
    if ($Reponse -eq 'q') {
        Write-Host "Arret demande. Paires restantes : $($Candidats.Count - $Traitees)."
        exit 0
    }
    if ($Reponse -eq 'o') {
        $Id = Enregistrer-Decision $Candidat.Article1 $Candidat.Article2 'fusionner' $DecidePar
        Write-Host "Fusion validee (decision id $Id)." -ForegroundColor Green
        $Traitees++
    } elseif ($Reponse -eq 'n') {
        $Id = Enregistrer-Decision $Candidat.Article1 $Candidat.Article2 'distincts' $DecidePar
        Write-Host "Distincts valide (decision id $Id)." -ForegroundColor Green
        $Traitees++
    } else {
        Write-Host "Reponse non reconnue : paire laissee en attente." -ForegroundColor Yellow
    }
}

$Restants = Lire-Candidats
Write-Host ''
Write-Host "Termine : $Traitees decision(s) enregistree(s), $($Restants.Count) paire(s) restante(s)." -ForegroundColor Green
