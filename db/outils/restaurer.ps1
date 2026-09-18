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

.PARAMETER FichierLogo
    Chemin du fichier _logo.* produit par sauvegarder.ps1 (cycle 28),
    optionnel -- absent si la sauvegarde n'incluait aucun logo de boutique.
    Restaure dans -DossierLogoCible (par defaut
    server\donnees\logo_boutique\).

.PARAMETER DossierLogoCible
    Dossier de destination du logo restaure. Par defaut
    server\donnees\logo_boutique\ (voir server/app/routes/configuration.py).

.PARAMETER PhraseChiffrement
    Phrase de chiffrement utilisee a la sauvegarde (voir sauvegarder.ps1).
    OBLIGATOIRE si les fichiers fournis se terminent par ".enc" (toute
    sauvegarde produite depuis le cycle 28). SANS cette phrase, la
    restauration est IMPOSSIBLE -- aucun mecanisme de recuperation
    n'existe en son absence (voir GUIDE_SAUVEGARDE_RESTAURATION.md,
    section 6). Un fichier .dump/.sql SANS ".enc" (sauvegarde anterieure
    au cycle 28) est restaure directement, sans phrase.

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
    [string]$FichierLogo = $null,
    [string]$DossierLogoCible = $null,
    [string]$PhraseChiffrement = $null,
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
if (-not $DossierLogoCible) {
    $DossierLogoCible = Join-Path $Racine 'server\donnees\logo_boutique'
}

# ----------------------------------------------------------------------------
# Dechiffrement AES-256 -- contrepartie exacte de Chiffrer-Fichier
# (sauvegarder.ps1) : sel (16 octets) + IV (16 octets) en tete du fichier,
# cle re-derivee de la MEME phrase par PBKDF2. Une phrase incorrecte produit
# un flux illisible -- CryptographicException, jamais une restauration
# partielle ou silencieusement corrompue.
# ----------------------------------------------------------------------------
function Dechiffrer-Fichier([string]$CheminChiffre, [string]$Phrase) {
    if (-not $CheminChiffre.EndsWith('.enc')) {
        return $CheminChiffre  # sauvegarde d'avant le cycle 28 : deja en clair
    }
    if (-not $Phrase) {
        throw "'$CheminChiffre' est chiffre (.enc) : -PhraseChiffrement est obligatoire pour le restaurer."
    }
    $CheminClair = $CheminChiffre.Substring(0, $CheminChiffre.Length - 4)

    # Format (voir Chiffrer-Fichier, sauvegarder.ps1) :
    #   [16 sel][16 IV][... AES-256-CBC ...][32 HMAC-SHA256]
    # Meme derivation (64 octets PBKDF2 : 32 AES, 32 HMAC) que la production.
    $Sel = New-Object byte[] 16
    $Iv  = New-Object byte[] 16
    $FluxLu = [System.IO.File]::OpenRead($CheminChiffre)
    try {
        [void]$FluxLu.Read($Sel, 0, 16)
        [void]$FluxLu.Read($Iv, 0, 16)
    } finally {
        $FluxLu.Close()
    }

    $Derivation = New-Object System.Security.Cryptography.Rfc2898DeriveBytes(
        $Phrase, $Sel, 100000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    $Materiel = $Derivation.GetBytes(64)
    $CleAes  = $Materiel[0..31]
    $CleHmac = $Materiel[32..63]

    # Verification de l'authenticite AVANT tout dechiffrement -- une phrase
    # incorrecte est ainsi TOUJOURS rejetee ici, jamais seulement "en
    # general" (le padding AES-CBC seul ne le garantissait pas -- voir
    # sauvegarder.ps1, Chiffrer-Fichier). Calcul sur le fichier ENTIER moins
    # les 32 derniers octets (l'empreinte elle-meme).
    $TailleFichier = (Get-Item $CheminChiffre).Length
    $TailleUtile = $TailleFichier - 32
    if ($TailleUtile -lt 32) {
        throw "'$CheminChiffre' est trop court pour etre un fichier chiffre valide (corrompu ou tronque)."
    }
    $HmacStocke = New-Object byte[] 32
    $FluxLu = [System.IO.File]::OpenRead($CheminChiffre)
    try {
        [void]$FluxLu.Seek($TailleUtile, [System.IO.SeekOrigin]::Begin)
        [void]$FluxLu.Read($HmacStocke, 0, 32)
    } finally {
        $FluxLu.Close()
    }
    $Hmac = New-Object System.Security.Cryptography.HMACSHA256(, $CleHmac)
    $HmacCalcule = $null
    try {
        $FluxUtile = [System.IO.File]::OpenRead($CheminChiffre)
        try {
            $FluxLimite = New-Object System.IO.MemoryStream
            $Tampon = New-Object byte[] 65536
            $Restant = $TailleUtile
            while ($Restant -gt 0) {
                $ALire = [Math]::Min($Tampon.Length, $Restant)
                $Lu = $FluxUtile.Read($Tampon, 0, $ALire)
                if ($Lu -le 0) { break }
                $FluxLimite.Write($Tampon, 0, $Lu)
                $Restant -= $Lu
            }
            $FluxLimite.Position = 0
            $HmacCalcule = $Hmac.ComputeHash($FluxLimite)
        } finally {
            $FluxUtile.Close()
        }
    } finally {
        $Hmac.Dispose()
    }
    if (-not [System.Security.Cryptography.CryptographicOperations]::FixedTimeEquals($HmacStocke, $HmacCalcule)) {
        throw "Dechiffrement de '$CheminChiffre' impossible -- phrase de chiffrement incorrecte, ou fichier corrompu."
    }

    # Authenticite confirmee : dechiffrement reel, en lisant uniquement la
    # portion utile (sans les 32 octets d'empreinte finaux).
    $FluxSource = [System.IO.File]::OpenRead($CheminChiffre)
    try {
        [void]$FluxSource.Seek(32, [System.IO.SeekOrigin]::Begin)  # apres sel+IV
        $FluxLimiteSource = New-Object System.IO.MemoryStream
        $Tampon = New-Object byte[] 65536
        $Restant = $TailleUtile - 32
        while ($Restant -gt 0) {
            $ALire = [Math]::Min($Tampon.Length, $Restant)
            $Lu = $FluxSource.Read($Tampon, 0, $ALire)
            if ($Lu -le 0) { break }
            $FluxLimiteSource.Write($Tampon, 0, $Lu)
            $Restant -= $Lu
        }
        $FluxLimiteSource.Position = 0

        $Aes = [System.Security.Cryptography.Aes]::Create()
        $Aes.Key = $CleAes
        $Aes.IV  = $Iv
        $FluxSortie = [System.IO.File]::Create($CheminClair)
        try {
            $Dechiffreur = $Aes.CreateDecryptor()
            $FluxCrypto = New-Object System.Security.Cryptography.CryptoStream(
                $FluxLimiteSource, $Dechiffreur, [System.Security.Cryptography.CryptoStreamMode]::Read)
            $FluxCrypto.CopyTo($FluxSortie)
            $FluxCrypto.Close()
        } finally {
            $FluxSortie.Close()
            $Aes.Dispose()
        }
    } finally {
        $FluxSource.Close()
    }
    return $CheminClair
}

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

# Dechiffrement AVANT tout usage -- les variables sont reaffectees au
# chemin CLAIR (ou inchangees si le fichier n'etait pas chiffre, voir
# Dechiffrer-Fichier). Fichiers clairs temporaires supprimes en fin de
# script (voir la fin du fichier) : jamais laisses sur le disque au-dela
# de cette restauration.
$FichiersClairsTemporaires = @()

$AvantBase = $FichierBase
$FichierBase = Dechiffrer-Fichier $FichierBase $PhraseChiffrement
if ($FichierBase -ne $AvantBase) { $FichiersClairsTemporaires += $FichierBase }

if ($FichierRoles) {
    $AvantRoles = $FichierRoles
    $FichierRoles = Dechiffrer-Fichier $FichierRoles $PhraseChiffrement
    if ($FichierRoles -ne $AvantRoles) { $FichiersClairsTemporaires += $FichierRoles }
}
if ($FichierLogo) {
    $AvantLogo = $FichierLogo
    $FichierLogo = Dechiffrer-Fichier $FichierLogo $PhraseChiffrement
    if ($FichierLogo -ne $AvantLogo) { $FichiersClairsTemporaires += $FichierLogo }
}

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

# Fichiers clairs temporaires (issus du dechiffrement) : jamais laisses sur
# le disque au-dela de cette restauration, quelle que soit l'issue.
function Nettoyer-FichiersClairs {
    foreach ($f in $FichiersClairsTemporaires) {
        Remove-Item -Path $f -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Creation de la base '$NomBaseCible' ..."
& $Psql -h $PgHost -p $PgPort -U $Utilisateur -d postgres -q -c "CREATE DATABASE $NomBaseCible;"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de la creation de la base (code $LASTEXITCODE)." -ForegroundColor Red
    Nettoyer-FichiersClairs
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

# Logo de la boutique (cycle 28) : restaure APRES la base, independamment
# de son resultat -- un logo perdu a la restauration serait une regression,
# meme si par ailleurs quelque chose d'autre echoue.
if ($FichierLogo -and (Test-Path $FichierLogo)) {
    if (-not (Test-Path $DossierLogoCible)) {
        New-Item -ItemType Directory -Path $DossierLogoCible -Force | Out-Null
    }
    Get-ChildItem -Path $DossierLogoCible -Filter 'logo.*' -File -ErrorAction SilentlyContinue |
        Remove-Item -Force
    $Extension = [System.IO.Path]::GetExtension($FichierLogo)
    $CibleLogo = Join-Path $DossierLogoCible "logo$Extension"
    Copy-Item -Path $FichierLogo -Destination $CibleLogo -Force
    Write-Host "Logo de la boutique restaure : $CibleLogo" -ForegroundColor Green
}

Write-Host ""
Nettoyer-FichiersClairs
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
