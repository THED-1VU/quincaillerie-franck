<#
.SYNOPSIS
    Double de test du chiffrement des sauvegardes (chantier C12, Lot B).

.DESCRIPTION
    DOUBLE DE TEST SUR, autorise par le proprietaire (ordre de mission
    "Operation 100 % / Lot B", 2026-10-23) : verifier les MECANISMES de
    chiffrement des sauvegardes SANS executer db/outils/sauvegarder.ps1,
    place en quarantaine par Kaspersky (PDM:Trojan.Win32.Generic, faux
    positif documente -- voir REGISTRE_ECARTS_100.md C12 et la procedure
    de controle de securite). Ce fichier n'est PAS ce script et ne l'appelle
    jamais : il re-implemente le FORMAT CONTRACTUEL documente dans les
    en-tetes de sauvegarder.ps1 (Chiffrer-Fichier) et restaurer.ps1
    (Dechiffrer-Fichier) :

        [16 sel][16 IV][... AES-256-CBC ...][32 HMAC-SHA256]

        - PBKDF2-SHA256, 100 000 iterations, 64 octets derives :
          32 pour la cle AES, 32 pour la cle HMAC (cles DISTINCTES).
        - HMAC calcule sur sel+IV+texte chiffre, AJOUTE en fin de fichier.
        - Cote restauration : HMAC verifie AVANT tout dechiffrement, en
          comparaison a temps constant manuelle (le .NET Framework 4.x de
          Windows PowerShell 5.1 n'a pas FixedTimeEquals).

    L'interet d'une implementation INDEPENDANTE : un fichier chiffre par
    ce double doit etre lisible par le VRAI restaurer.ps1 (et
    reciproquement pour le format), ce qui prouve que le contrat de format
    tient entre deux codes separes -- pas seulement qu'un script relit ce
    qu'il vient d'ecrire.

    Deux usages :
      1. AUTOTEST (aucun argument) : suite de controles sur fichiers
         temporaires (cree dans $env:TEMP\qf_double_c12), phrase de test,
         effaces en fin. Aucune base de donnees, aucun fichier reel.
      2. OUTIL pour les tests de restauration :
         -Chiffrer <fichier clair> -Phrase <phrase>  : produit <fichier>.enc
         -Dechiffrer <fichier .enc> -Phrase <phrase> : produit le clair
         (uniquement pour preparer des sauvegardes d'essai sur des bases
         isolees de test -- jamais sur des donnees reelles).

    Les messages sont volontairement SANS accents : ce fichier est ecrit
    en UTF-8 sans BOM comme les autres scripts du depot, que Windows
    PowerShell 5.1 relit en ANSI.
#>
param(
    [string]$Chiffrer = $null,
    [string]$Dechiffrer = $null,
    [string]$Phrase = $null
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Chiffrer-Double : format contractuel [16 sel][16 IV][AES-256-CBC][32 HMAC]
# ---------------------------------------------------------------------------
function Chiffrer-Double([string]$CheminSource, [string]$Phrase) {
    if (-not $Phrase) {
        throw "Phrase de chiffrement obligatoire (refus sans phrase : comportement du script de production, cycle 28)."
    }
    if (-not (Test-Path $CheminSource)) {
        throw "Fichier source introuvable : $CheminSource"
    }
    $CheminCible = "$CheminSource.enc"

    $Sel = New-Object byte[] 16
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Sel)

    $Derivation = New-Object System.Security.Cryptography.Rfc2898DeriveBytes(
        $Phrase, $Sel, 100000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    $Materiel = $Derivation.GetBytes(64)
    $CleAes  = $Materiel[0..31]
    $CleHmac = $Materiel[32..63]

    $Aes = [System.Security.Cryptography.Aes]::Create()
    $Aes.Key = $CleAes
    $Aes.GenerateIV()

    $FluxSortie = [System.IO.File]::Create($CheminCible)
    try {
        $FluxSortie.Write($Sel, 0, $Sel.Length)
        $FluxSortie.Write($Aes.IV, 0, $Aes.IV.Length)
        $Chiffreur = $Aes.CreateEncryptor()
        $FluxCrypto = New-Object System.Security.Cryptography.CryptoStream(
            $FluxSortie, $Chiffreur, [System.Security.Cryptography.CryptoStreamMode]::Write)
        $FluxSource = [System.IO.File]::OpenRead($CheminSource)
        try {
            $FluxSource.CopyTo($FluxCrypto)
        } finally {
            $FluxSource.Close()
        }
        $FluxCrypto.FlushFinalBlock()
        $FluxCrypto.Close()
    } finally {
        $FluxSortie.Close()
        $Aes.Dispose()
    }

    $Hmac = New-Object System.Security.Cryptography.HMACSHA256(, $CleHmac)
    try {
        $FluxLecture = [System.IO.File]::OpenRead($CheminCible)
        $Empreinte = $null
        try {
            $Empreinte = $Hmac.ComputeHash($FluxLecture)
        } finally {
            $FluxLecture.Close()
        }
    } finally {
        $Hmac.Dispose()
    }
    $FluxAjout = [System.IO.File]::Open($CheminCible, [System.IO.FileMode]::Append)
    try {
        $FluxAjout.Write($Empreinte, 0, $Empreinte.Length)
    } finally {
        $FluxAjout.Close()
    }

    # Le clair ne doit jamais rester sur le disque (decision du proprietaire,
    # meme pour le fichier local qui ne part jamais hors-site).
    Remove-Item -Path $CheminSource -Force
    return $CheminCible
}

# ---------------------------------------------------------------------------
# Dechiffrer-Double : HMAC verifie AVANT dechiffrement, temps constant.
# Un fichier SANS extension .enc est rendu tel quel (sauvegarde anterieure
# au cycle 28, deja claire) -- meme comportement que restaurer.ps1.
# ---------------------------------------------------------------------------
function Dechiffrer-Double([string]$CheminChiffre, [string]$Phrase) {
    if (-not $CheminChiffre.EndsWith('.enc')) {
        return $CheminChiffre
    }
    if (-not $Phrase) {
        throw "'$CheminChiffre' est chiffre (.enc) : la phrase est obligatoire."
    }
    $CheminClair = $CheminChiffre.Substring(0, $CheminChiffre.Length - 4)

    $TailleFichier = (Get-Item $CheminChiffre).Length
    $TailleUtile = $TailleFichier - 32
    if ($TailleUtile -lt 32) {
        throw "'$CheminChiffre' est trop court pour etre un fichier chiffre valide (corrompu ou tronque)."
    }

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

    # Empreinte stockee (32 derniers octets) ...
    $HmacStocke = New-Object byte[] 32
    $FluxLu = [System.IO.File]::OpenRead($CheminChiffre)
    try {
        [void]$FluxLu.Seek($TailleUtile, [System.IO.SeekOrigin]::Begin)
        [void]$FluxLu.Read($HmacStocke, 0, 32)
    } finally {
        $FluxLu.Close()
    }
    # ... comparee a l'empreinte calculee sur le fichier ENTIER moins ces
    # 32 octets, en boucle TOUJOURS complete (temps constant manuel, .NET
    # 4.x n'a pas FixedTimeEquals).
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
    $Difference = 0
    for ($i = 0; $i -lt 32; $i++) {
        $Difference = $Difference -bor ($HmacStocke[$i] -bxor $HmacCalcule[$i])
    }
    if ($Difference -ne 0) {
        throw "Dechiffrement de '$CheminChiffre' impossible -- phrase de chiffrement incorrecte, ou fichier corrompu."
    }

    # Authenticite confirmee : dechiffrement reel de la portion utile.
    $Aes = [System.Security.Cryptography.Aes]::Create()
    $Aes.Key = $CleAes
    $Aes.IV = $Iv
    $FluxClair = [System.IO.File]::Create($CheminClair)
    try {
        $Dechiffreur = $Aes.CreateDecryptor()
        $FluxCrypto = New-Object System.Security.Cryptography.CryptoStream(
            $FluxClair, $Dechiffreur, [System.Security.Cryptography.CryptoStreamMode]::Write)
        $FluxSource = [System.IO.File]::OpenRead($CheminChiffre)
        try {
            [void]$FluxSource.Seek(32, [System.IO.SeekOrigin]::Begin)
            $Tampon = New-Object byte[] 65536
            $Restant = $TailleUtile - 32
            while ($Restant -gt 0) {
                $ALire = [Math]::Min($Tampon.Length, $Restant)
                $Lu = $FluxSource.Read($Tampon, 0, $ALire)
                if ($Lu -le 0) { break }
                $FluxCrypto.Write($Tampon, 0, $Lu)
                $Restant -= $Lu
            }
        } finally {
            $FluxSource.Close()
        }
        $FluxCrypto.FlushFinalBlock()
        $FluxCrypto.Close()
    } finally {
        $FluxClair.Close()
        $Aes.Dispose()
    }
    return $CheminClair
}

# ---------------------------------------------------------------------------
# AUTOTEST
# ---------------------------------------------------------------------------
if (-not $Chiffrer -and -not $Dechiffrer) {
    $Dossier = Join-Path $env:TEMP "qf_double_c12"
    if (Test-Path $Dossier) { Remove-Item $Dossier -Recurse -Force }
    New-Item -ItemType Directory -Path $Dossier | Out-Null

    $ControlesOK = 0
    $ControlesTotal = 0
    function Verdict([bool]$Passe, [string]$Nom, [string]$Detail) {
        $script:ControlesTotal++
        if ($Passe) {
            $script:ControlesOK++
            Write-Host ("  OK    {0} : {1}" -f $Nom, $Detail)
        } else {
            Write-Host ("  ECHEC {0} : {1}" -f $Nom, $Detail) -ForegroundColor Red
        }
    }

    Write-Host "== Double de test C12 : mecanismes de chiffrement des sauvegardes =="
    Write-Host ("Dossier de travail : " + $Dossier)
    Write-Host ""

    # --- Preparation d'un contenu d'essai non trivial (512 octets couvrant
    #     les 256 valeurs d'octet x2, texte FCFA en entete) ---
    $Octets = New-Object byte[] 512
    for ($i = 0; $i -lt 512; $i++) { $Octets[$i] = $i % 256 }
    $Entete = [System.Text.Encoding]::UTF8.GetBytes("Vente d'essai C12 : 2 sacs ciment a 6500 FCFA, total 13000 FCFA. ")
    for ($i = 0; $i -lt $Entete.Length; $i++) { $Octets[$i] = $Entete[$i] }
    $Clair = Join-Path $Dossier "essai.dump"
    [System.IO.File]::WriteAllBytes($Clair, $Octets)
    $EmpreinteClair = (Get-FileHash -Algorithm SHA256 $Clair).Hash

    # T1 : chiffrement produit le .enc et supprime le clair
    $PhraseTest = "Phrase de test C12 - jamais utilisee en production"
    $Chiffre = Chiffrer-Double $Clair $PhraseTest
    Verdict ((Test-Path $Chiffre) -and (-not (Test-Path $Clair))) "T1 chiffrement" "produit $([System.IO.Path]::GetFileName($Chiffre)), clair supprime"

    # T2 : format [16 sel][16 IV][chiffre][32 HMAC] -- chiffre = multiple de 16 (AES-CBC), sel et IV non nuls
    $Contenu = [System.IO.File]::ReadAllBytes($Chiffre)
    $SelNul = $true; $IvNul = $true
    for ($i = 0; $i -lt 16; $i++) { if ($Contenu[$i]  -ne 0) { $SelNul = $false } ; if ($Contenu[16 + $i] -ne 0) { $IvNul = $false } }
    $LongueurChiffre = $Contenu.Length - 64
    Verdict (($Contenu.Length -gt 64) -and (($LongueurChiffre % 16) -eq 0) -and (-not $SelNul) -and (-not $IvNul)) "T2 format" ("taille {0} = 16 sel + 16 IV + {1} chiffres (multiple de 16) + 32 HMAC" -f $Contenu.Length, $LongueurChiffre)

    # T3 : aller-retour complet octet a octet
    $Relu = Dechiffrer-Double $Chiffre $PhraseTest
    $EmpreinteRelu = (Get-FileHash -Algorithm SHA256 $Relu).Hash
    Verdict ($EmpreinteClair -eq $EmpreinteRelu) "T3 aller-retour" "SHA-256 du clair regenere identique"

    # T4 : phrase incorrecte -> refus (l'HMAC doit le garantir AVANT tout dechiffrement)
    $Refuse = $false
    try { [void](Dechiffrer-Double $Chiffre "Phrase fausse") } catch { $Refuse = $true }
    Verdict $Refuse "T4 phrase fausse" "refuse par l'HMAC, pas seulement par le padding AES"

    # T5 : corruption d'un octet du texte chiffre -> refus
    # (chaque variante est une copie FRAICHE de l'original, nommee *.enc :
    #  un nom ne finissant pas par .enc serait rendu tel quel par la porte
    #  patrimoine de T10 -- piege trouve au premier passage de ce test.)
    $CorrompuTexte = Join-Path $Dossier "corrompu_texte.dump.enc"
    [System.IO.File]::WriteAllBytes($CorrompuTexte, [System.IO.File]::ReadAllBytes($Chiffre))
    $OctetsCorrompus = [System.IO.File]::ReadAllBytes($CorrompuTexte)
    $OctetsCorrompus[40] = $OctetsCorrompus[40] -bxor 1
    [System.IO.File]::WriteAllBytes($CorrompuTexte, $OctetsCorrompus)
    $Refuse = $false
    try { [void](Dechiffrer-Double $CorrompuTexte $PhraseTest) } catch { $Refuse = $true }
    Verdict $Refuse "T5 texte chiffre corrompu" "octet 40 modifie -> refuse"

    # T6 : corruption de l'empreinte (dernier octet) -> refus
    $CorrompuHmac = Join-Path $Dossier "corrompu_hmac.dump.enc"
    [System.IO.File]::WriteAllBytes($CorrompuHmac, [System.IO.File]::ReadAllBytes($Chiffre))
    $OctetsCorrompus = [System.IO.File]::ReadAllBytes($CorrompuHmac)
    $Dernier = $OctetsCorrompus.Length - 1
    $OctetsCorrompus[$Dernier] = $OctetsCorrompus[$Dernier] -bxor 1
    [System.IO.File]::WriteAllBytes($CorrompuHmac, $OctetsCorrompus)
    $Refuse = $false
    try { [void](Dechiffrer-Double $CorrompuHmac $PhraseTest) } catch { $Refuse = $true }
    Verdict $Refuse "T6 empreinte corrompue" "dernier octet modifie -> refuse"

    # T7 : fichier tronque -> refus explicite
    $Tronque = Join-Path $Dossier "tronque.dump.enc"
    [byte[]]$OctetsTronques = [System.IO.File]::ReadAllBytes($Chiffre)[0..49]
    [System.IO.File]::WriteAllBytes($Tronque, $OctetsTronques)
    $Refuse = $false
    try { [void](Dechiffrer-Double $Tronque $PhraseTest) } catch { $Refuse = $true }
    Verdict $Refuse "T7 troncature" "50 octets -> trop court pour le format"

    # T8 : fichier vide -> aller-retour vers un fichier vide
    $Vide = Join-Path $Dossier "vide.dump"
    [System.IO.File]::WriteAllBytes($Vide, (New-Object byte[] 0))
    $VideEnc = Chiffrer-Double $Vide $PhraseTest
    $VideRelu = Dechiffrer-Double $VideEnc $PhraseTest
    Verdict (((Get-Item $VideRelu).Length -eq 0) -and ((Get-Item $VideEnc).Length -eq 80)) "T8 fichier vide" "chiffre = 80 octets (sel+IV+ bloc de padding seul + HMAC), relu vide"

    # T9 : cles AES et HMAC distinctes dans la derivation PBKDF2
    $Deriv = New-Object System.Security.Cryptography.Rfc2898DeriveBytes(
        $PhraseTest, [System.IO.File]::ReadAllBytes($Chiffre)[0..15], 100000,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    $Mat = $Deriv.GetBytes(64)
    $MemeCle = $true
    for ($i = 0; $i -lt 32; $i++) { if ($Mat[$i] -ne $Mat[32 + $i]) { $MemeCle = $false; break } }
    Verdict (-not $MemeCle) "T9 cles distinctes" "les 2x32 octets derives PBKDF2 different (jamais la meme cle AES et HMAC)"

    # T10 : fichier SANS extension .enc -> rendu tel quel (sauvegarde claire d'avant le cycle 28)
    $Legacy = Join-Path $Dossier "ancienne_sauvegarde.dump"
    [System.IO.File]::WriteAllBytes($Legacy, $Octets)
    $Rendu = Dechiffrer-Double $Legacy $null
    Verdict ($Rendu -eq $Legacy) "T10 heritage clair" "sans .enc : ni phrase exigee ni transformation"

    # T11 : phrase absente sur un .enc -> refus
    $Refuse = $false
    try { [void](Dechiffrer-Double $Chiffre $null) } catch { $Refuse = $true }
    Verdict $Refuse "T11 phrase obligatoire" ".enc sans phrase -> refuse (aucune recuperation sans phrase)"

    Write-Host ""
    Write-Host ("BILAN : {0}/{1} controles passes." -f $ControlesOK, $ControlesTotal)
    Remove-Item $Dossier -Recurse -Force
    if ($ControlesOK -eq $ControlesTotal) { exit 0 } else { exit 1 }
}

# ---------------------------------------------------------------------------
# Mode outil (preparation des tests de restauration sur base isolee)
# ---------------------------------------------------------------------------
if ($Chiffrer) {
    $Produit = Chiffrer-Double $Chiffrer $Phrase
    Write-Host ("Chiffre : " + $Produit)
    exit 0
}
if ($Dechiffrer) {
    $Produit = Dechiffrer-Double $Dechiffrer $Phrase
    Write-Host ("Dechiffre : " + $Produit)
    exit 0
}
