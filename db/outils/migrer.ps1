# ============================================================================
# Applique (ou annule) les migrations de schema, dans l'ordre.
# Equivalent PowerShell de migrer.sh, pour un poste sans Git/Git Bash.
# NOTE ENCODAGE : ASCII volontairement (PowerShell 5.1 decode mal l'UTF-8
# sans BOM contenant des accents -- voir la note de creer_compte_responsable.ps1).
# ----------------------------------------------------------------------------
# Usage :
#   db\outils\migrer.ps1 appliquer            # 000 -> la plus recente
#   db\outils\migrer.ps1 annuler              # la plus recente -> 000
#   db\outils\migrer.ps1 etat                 # ce qui est applique
#
# Connexion : variables d'environnement PostgreSQL habituelles.
#   PGHOST (defaut 127.0.0.1), PGPORT (5432), PGUSER (postgres),
#   PGDATABASE (quincaillerie_test), PGPASSWORD.
#   PSQL permet de pointer un binaire psql qui n'est pas dans le PATH.
#
# Chaque fichier est execute dans UNE transaction, avec ON_ERROR_STOP :
# une migration passe en entier, ou pas du tout.
# ============================================================================
$ErrorActionPreference = 'Stop'

$Ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$Migrations = Join-Path (Split-Path -Parent $Ici) 'migrations'

if (-not $env:PSQL) { $Psql = 'psql' } else { $Psql = $env:PSQL }
if (-not $env:PGHOST) { $env:PGHOST = '127.0.0.1' }
if (-not $env:PGPORT) { $env:PGPORT = '5432' }
if (-not $env:PGUSER) { $env:PGUSER = 'postgres' }
if (-not $env:PGDATABASE) { $env:PGDATABASE = 'quincaillerie_test' }
if (-not $env:PGCLIENTENCODING) { $env:PGCLIENTENCODING = 'UTF8' }

function Executer-Migration {
    param([string]$Fichier)
    & $Psql -v ON_ERROR_STOP=1 --single-transaction -q -f $Fichier
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de $Fichier (code $LASTEXITCODE)"
    }
}

switch ($args[0]) {
    'appliquer' {
        Write-Host "== Application des migrations sur $env:PGDATABASE ($env:PGHOST`:$env:PGPORT) =="
        $plancher = -1
        $versionsAppliquees = @()
        $existe = & $Psql -v ON_ERROR_STOP=1 -Atqc "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
        if ($LASTEXITCODE -ne 0) { throw 'Lecture du suivi des migrations impossible' }
        if ($existe -eq 't') {
            $valeur = & $Psql -v ON_ERROR_STOP=1 -Atqc 'SELECT COALESCE(MAX(version::integer),-1) FROM schema_migrations'
            if ($LASTEXITCODE -ne 0) { throw 'Lecture de la version courante impossible' }
            $plancher = [int]$valeur
            $versionsAppliquees = @(& $Psql -v ON_ERROR_STOP=1 -Atqc 'SELECT version FROM schema_migrations')
            if ($LASTEXITCODE -ne 0) { throw 'Lecture des versions appliquees impossible' }
        }
        # -Filter Win32 ne supporte pas les classes de caracteres repetes
        # ([0-9][0-9][0-9] retourne 0 fichier) : filtrage par regex ici.
        $fichiers = Get-ChildItem -Path $Migrations -Filter '*.sql' |
            Where-Object { $_.Name -match '^[0-9]{3}_.*\.sql$' -and $_.Name -notlike '*_inverse.sql' } |
            Sort-Object Name
        foreach ($f in $fichiers) {
            if ([int]$f.Name.Substring(0,3) -le $plancher) {
                if ($versionsAppliquees -notcontains $f.Name.Substring(0,3)) {
                    throw "Historique incomplet : version $($f.Name.Substring(0,3)) absente avant $plancher. Diagnostic requis."
                }
                continue
            }
            Write-Host "-- $($f.Name)"
            Executer-Migration -Fichier $f.FullName
        }
        Write-Host "== Termine =="
        & $Psql -q -c "SELECT version, nom, applique_le FROM schema_migrations ORDER BY version;"
        if ($LASTEXITCODE -ne 0) { throw "Lecture de schema_migrations impossible (code $LASTEXITCODE)" }
    }
    'annuler' {
        Write-Host "== Annulation des migrations sur $env:PGDATABASE ($env:PGHOST`:$env:PGPORT) =="
        $fichiers = Get-ChildItem -Path $Migrations -Filter '*.sql' |
            Where-Object { $_.Name -match '^[0-9]{3}_.*_inverse\.sql$' } |
            Sort-Object Name -Descending
        foreach ($f in $fichiers) {
            Write-Host "-- $($f.Name)"
            Executer-Migration -Fichier $f.FullName
        }
        Write-Host "== Termine (schema revenu a son etat d'origine) =="
    }
    'etat' {
        & $Psql -q -c "SELECT version, nom, applique_le, applique_par FROM schema_migrations ORDER BY version;"
        if ($LASTEXITCODE -ne 0) { throw "Lecture de schema_migrations impossible (code $LASTEXITCODE)" }
    }
    default {
        Write-Host "Usage : migrer.ps1 {appliquer|annuler|etat}" -ForegroundColor Red
        exit 2
    }
}
