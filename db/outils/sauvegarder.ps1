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

    ETENDU AU CYCLE C12 (2026-09-14), decision du proprietaire du
    2026-09-13 (addendum, point i, question 1) : RPO cible 1 heure. Ce
    script ajoute, par rapport a la version d'origine (cycle 21) :
      - une copie de chaque sauvegarde vers un emplacement HORS du poste
        serveur (-DossierDistant) ;
      - une purge glissante des fichiers de plus de -RetentionJours jours,
        locale ET distante ;
      - un journal horodate (-FichierJournal) qui trace chaque etape,
        succes ou echec ;
      - un code de sortie non nul en cas d'echec de N'IMPORTE QUELLE
        etape (dump, dump des roles, copie distante si demandee, purge),
        pour qu'une tache planifiee (voir planifier_sauvegarde.ps1) ou un
        operateur humain puisse detecter l'echec sans lire la console.
    Ce que ce cycle NE fait PAS : chiffrement de la copie distante ni
    notification (WhatsApp/e-mail) en cas d'echec -- l'addendum (point i)
    les evoque, mais aucun compte reel n'est disponible pour une alerte
    reelle et aucun besoin de chiffrement n'a ete tranche par le
    proprietaire. Documente comme limite dans le rapport de cycle plutot
    que d'inventer un faux envoi ou un faux chiffrement.

.PARAMETER Dossier
    Dossier de destination LOCALE des fichiers de sauvegarde. Cree s'il
    n'existe pas. Par defaut : _pgdev\sauvegardes (developpement local --
    jamais verse au depot, voir .gitignore). En deploiement reel, ce
    dossier reste SUR le poste serveur (a cote de PostgreSQL) : c'est
    -DossierDistant qui assure la copie HORS du poste.

.PARAMETER DossierDistant
    Dossier de destination HORS du poste serveur, ou chaque fichier
    produit est copie apres la sauvegarde locale. Optionnel : si omis,
    aucune copie distante n'est faite (avertissement journalise). En
    deploiement reel, ce serait un partage reseau (ex. \\poste-secours\
    sauvegardes) ou un service de stockage distant -- ce script accepte
    n'importe quel chemin que Copy-Item sait atteindre (dossier local,
    lettre reseau mappee, chemin UNC). Pour la preuve de ce cycle, un
    second dossier local (simulant un second disque/poste) suffit.

.PARAMETER RetentionJours
    Duree de conservation glissante, en jours, des fichiers de sauvegarde
    (locaux ET distants s'il y a -DossierDistant). Tout fichier
    correspondant au motif "<NomBase>_*.dump" ou "<NomBase>_*_roles.sql"
    dont la date de derniere ecriture est plus ancienne que cette duree
    est supprime APRES la sauvegarde du jour. Par defaut 30 jours (CDC
    §4.3 et addendum point i).

.PARAMETER FichierJournal
    Fichier .log dans lequel chaque etape est tracee avec un horodatage.
    Par defaut : <Dossier>\journal_sauvegardes.log (un seul fichier,
    complete a chaque execution -- l'historique des sauvegardes et de
    leurs echecs eventuels reste ainsi consultable sans base de donnees
    supplementaire).

.PARAMETER FichierEtat
    Fichier .json ECRASE (pas complete) a CHAQUE tentative, succes ou
    echec -- "dernier etat connu", lisible par un outil externe (ex. une
    route serveur pour un voyant de tableau de bord) sans avoir a relire
    tout le journal. Par defaut : <Dossier>\dernier_etat_sauvegarde.json.
    Durcissement demande explicitement (2026-09-14) : une sauvegarde qui
    echoue en silence pendant des semaines est pire que l'absence de
    sauvegarde -- ce fichier existe pour qu'un echec soit visible meme
    sans surveiller la console ni le journal .log en continu.

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
    powershell -File db\outils\sauvegarder.ps1 -Dossier "D:\Sauvegardes" -DossierDistant "\\poste-secours\sauvegardes" -NomBase quincaillerie -PgPort 5432 -RetentionJours 30
#>

[CmdletBinding()]
param(
    [string]$Dossier = $null,
    [string]$DossierDistant = $null,
    [int]$RetentionJours = 30,
    [string]$FichierJournal = $null,
    [string]$FichierEtat = $null,
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
if (-not (Test-Path $Dossier)) {
    New-Item -ItemType Directory -Path $Dossier -Force | Out-Null
}
if (-not $FichierJournal) {
    $FichierJournal = Join-Path $Dossier 'journal_sauvegardes.log'
}
if (-not $FichierEtat) {
    $FichierEtat = Join-Path $Dossier 'dernier_etat_sauvegarde.json'
}

$script:MessagesEtat = @()

function Ecrire-Journal([string]$Niveau, [string]$Message) {
    $Ligne = "[{0}] [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Niveau, $Message
    $script:MessagesEtat += $Ligne
    Add-Content -Path $FichierJournal -Value $Ligne -Encoding UTF8
    if ($Niveau -eq 'ERREUR') {
        Write-Host $Ligne -ForegroundColor Red
    } elseif ($Niveau -eq 'AVERTISSEMENT') {
        Write-Host $Ligne -ForegroundColor Yellow
    } else {
        Write-Host $Ligne
    }
}

# Fichier d'etat (voir .PARAMETER FichierEtat) -- toujours ECRASE (jamais
# complete) : c'est le DERNIER etat connu, pas un historique (le journal
# .log ci-dessus joue deja ce role).
function Ecrire-EtatFichier([bool]$EnEchec, [string[]]$MessagesCles) {
    $Etat = [ordered]@{
        horodatage       = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss')
        resultat         = if ($EnEchec) { 'ECHEC' } else { 'SUCCES' }
        base             = $NomBase
        pg_host          = $PgHost
        pg_port          = $PgPort
        fichier_base     = $FichierBase
        fichier_roles    = $FichierRoles
        dossier_distant  = $DossierDistant
        retention_jours  = $RetentionJours
        messages         = $MessagesCles
    }
    try {
        ($Etat | ConvertTo-Json -Depth 4) | Set-Content -Path $FichierEtat -Encoding UTF8
    } catch {
        # Ne doit jamais faire echouer la sauvegarde elle-meme : le fichier
        # d'etat est une aide au diagnostic, pas la sauvegarde en soi. Trace
        # neanmoins dans le journal .log -- deja ecrit a ce point.
        Ecrire-Journal 'AVERTISSEMENT' "Echec d'ecriture du fichier d'etat '$FichierEtat' : $($_.Exception.Message)"
    }
}

# Journal d'evenements Windows (Observateur d'evenements) -- durcissement
# demande explicitement (2026-09-14) : une sauvegarde qui echoue en silence
# pendant des semaines est pire que l'absence de sauvegarde. Tente d'abord
# une source DEDIEE ("QuincaillerieFranck_Sauvegarde"), qu'un installateur
# EXECUTE UNE FOIS EN ADMINISTRATEUR peut enregistrer sur le poste serveur
# reel (New-EventLog -LogName Application -Source
# QuincaillerieFranck_Sauvegarde) -- enregistrer une NOUVELLE source exige
# des droits administrateur (ecriture dans HKLM), que ce script ne suppose
# JAMAIS avoir. A defaut (source dediee absente -- le cas de tout poste de
# developpement non administrateur), replie sur la source "PowerShell" du
# journal "Windows PowerShell", presente de fait sur tout poste Windows ou
# PowerShell est installe, sans droits particuliers requis pour y ECRIRE
# (seule la CREATION d'une source exige l'administration). Verifie par
# execution (voir RAPPORT AVANCEMENT/cycles/piste-c12.md) : le texte
# complet reste present dans les donnees brutes de l'evenement (onglet
# "Details" / XML de l'Observateur d'evenements) meme quand son rendu
# "amical" reste vide faute d'un modele de message pour cet ID chez un
# fournisseur d'evenements emprunte.
function Ecrire-EvenementWindows([string]$Type, [string]$Message) {
    $EventId = if ($Type -eq 'Error') { 9002 } else { 9001 }
    try {
        Write-EventLog -LogName 'Application' -Source 'QuincaillerieFranck_Sauvegarde' `
            -EventId $EventId -EntryType $Type -Message $Message -ErrorAction Stop
        return
    } catch {
        # Source dediee absente (pas d'administrateur pour l'enregistrer ici) --
        # repli sur la source generique toujours disponible.
    }
    try {
        Write-EventLog -LogName 'Windows PowerShell' -Source 'PowerShell' `
            -EventId $EventId -EntryType $Type -Message $Message -ErrorAction Stop
    } catch {
        Ecrire-Journal 'AVERTISSEMENT' "Echec d'ecriture dans le journal d'evenements Windows : $($_.Exception.Message)"
    }
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

Ecrire-Journal 'INFO' "=== Debut sauvegarde de '$NomBase' ($PgHost`:$PgPort) -- dossier local '$Dossier' ==="

# Noms de fichiers calcules AVANT toute operation qui pourrait echouer :
# le fichier d'etat (Ecrire-EtatFichier) doit pouvoir les rapporter meme
# si la sauvegarde echoue des la premiere etape (binaires introuvables).
$Horodatage = Get-Date -Format 'yyyyMMdd_HHmmss'
$FichierBase  = Join-Path $Dossier "${NomBase}_${Horodatage}.dump"
$FichierRoles = Join-Path $Dossier "${NomBase}_${Horodatage}_roles.sql"

try {
    $PgDump    = Resoudre-Binaire 'pg_dump'
    $PgDumpAll = Resoudre-Binaire 'pg_dumpall'
} catch {
    $Msg = "Binaires PostgreSQL introuvables : $($_.Exception.Message)"
    Ecrire-Journal 'ERREUR' $Msg
    Ecrire-EtatFichier $true $script:MessagesEtat
    Ecrire-EvenementWindows 'Error' "Sauvegarde Quincaillerie Franck ($NomBase) EN ECHEC : $Msg"
    exit 1
}

$Echec = $false

Ecrire-Journal 'INFO' "Sauvegarde du contenu de la base (pg_dump -Fc) vers $FichierBase ..."
& $PgDump -h $PgHost -p $PgPort -U $Utilisateur -Fc -f $FichierBase $NomBase
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $FichierBase)) {
    Ecrire-Journal 'ERREUR' "Echec de pg_dump (code $LASTEXITCODE) -- fichier $FichierBase absent ou incomplet."
    $Echec = $true
} else {
    $TailleBase = (Get-Item $FichierBase).Length
    Ecrire-Journal 'INFO' ("Dump de la base OK : {0} ({1} Ko)" -f $FichierBase, [math]::Round($TailleBase / 1KB, 1))
}

if (-not $Echec) {
    Ecrire-Journal 'INFO' "Sauvegarde des roles applicatifs (pg_dumpall --roles-only) vers $FichierRoles ..."
    & $PgDumpAll -h $PgHost -p $PgPort -U $Utilisateur --roles-only -f $FichierRoles
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $FichierRoles)) {
        Ecrire-Journal 'ERREUR' "Echec de pg_dumpall --roles-only (code $LASTEXITCODE) -- fichier $FichierRoles absent."
        $Echec = $true
    } else {
        Ecrire-Journal 'INFO' "Dump des roles OK : $FichierRoles"
    }
}

# Copie hors du poste serveur -- chaque sauvegarde produit une copie a un
# emplacement DIFFERENT du dossier local, condition necessaire (pas
# suffisante seule : voir onduleur/RTO, addendum point i, questions 2-4
# encore ouvertes) pour survivre a une panne materielle du poste serveur
# lui-meme (disque, alimentation, incendie...). En production reelle,
# -DossierDistant serait un partage reseau ou un service de stockage
# distant -- ici, n'importe quel chemin atteignable par Copy-Item convient
# (voir le .PARAMETER ci-dessus).
if (-not $Echec) {
    if ($DossierDistant) {
        try {
            if (-not (Test-Path $DossierDistant)) {
                New-Item -ItemType Directory -Path $DossierDistant -Force | Out-Null
            }
            Copy-Item -Path $FichierBase -Destination $DossierDistant -Force
            Copy-Item -Path $FichierRoles -Destination $DossierDistant -Force

            $CopieBase  = Join-Path $DossierDistant (Split-Path $FichierBase -Leaf)
            $CopieRoles = Join-Path $DossierDistant (Split-Path $FichierRoles -Leaf)
            if ((Test-Path $CopieBase) -and (Test-Path $CopieRoles)) {
                Ecrire-Journal 'INFO' "Copie hors-site OK vers '$DossierDistant' : $(Split-Path $CopieBase -Leaf), $(Split-Path $CopieRoles -Leaf)"
            } else {
                Ecrire-Journal 'ERREUR' "Copie hors-site incomplete vers '$DossierDistant' -- fichier(s) absent(s) apres copie."
                $Echec = $true
            }
        } catch {
            Ecrire-Journal 'ERREUR' "Echec de la copie hors-site vers '$DossierDistant' : $($_.Exception.Message)"
            $Echec = $true
        }
    } else {
        Ecrire-Journal 'AVERTISSEMENT' "Aucun -DossierDistant fourni : cette sauvegarde reste SEULE sur le poste serveur, non protegee d'une panne materielle de ce poste."
    }
}

# Purge glissante -- rétention $RetentionJours jours, locale ET distante.
# Ne supprime QUE les fichiers de sauvegarde de CETTE base (motif
# "<NomBase>_*"), jamais un autre fichier du dossier. Basee sur la date de
# derniere ecriture (LastWriteTime) du fichier, pas sur son nom -- un
# fichier copie conserve sa date d'origine avec Copy-Item, donc la purge
# distante utilise la meme regle que la purge locale.
function Purger-Dossier([string]$Chemin) {
    if (-not (Test-Path $Chemin)) { return }
    $Limite = (Get-Date).AddDays(-$RetentionJours)
    $Candidats = Get-ChildItem -Path $Chemin -File |
        Where-Object { $_.Name -like "${NomBase}_*.dump" -or $_.Name -like "${NomBase}_*_roles.sql" } |
        Where-Object { $_.LastWriteTime -lt $Limite }
    foreach ($Fichier in $Candidats) {
        try {
            Remove-Item -Path $Fichier.FullName -Force
            Ecrire-Journal 'INFO' "Purge (retention $RetentionJours j) : $($Fichier.FullName) supprime (date $($Fichier.LastWriteTime))."
        } catch {
            Ecrire-Journal 'ERREUR' "Echec de la purge de $($Fichier.FullName) : $($_.Exception.Message)"
            $Echec = $true
        }
    }
    if ($Candidats.Count -eq 0) {
        Ecrire-Journal 'INFO' "Purge (retention $RetentionJours j) : rien a supprimer dans '$Chemin'."
    }
}

Purger-Dossier $Dossier
if ($DossierDistant) {
    Purger-Dossier $DossierDistant
}

if ($Echec) {
    Ecrire-Journal 'ERREUR' "=== Sauvegarde de '$NomBase' terminee EN ECHEC -- voir les lignes ERREUR ci-dessus. ==="
    Ecrire-EtatFichier $true $script:MessagesEtat
    Ecrire-EvenementWindows 'Error' "Sauvegarde Quincaillerie Franck ($NomBase) EN ECHEC. Voir $FichierJournal."
    exit 1
}

Ecrire-Journal 'INFO' "=== Sauvegarde de '$NomBase' terminee avec SUCCES. ==="
Ecrire-EtatFichier $false $script:MessagesEtat
Ecrire-EvenementWindows 'Information' "Sauvegarde Quincaillerie Franck ($NomBase) reussie : $FichierBase"
Write-Host ""
Write-Host "Sauvegarde terminee. Pour restaurer :" -ForegroundColor Green
Write-Host "  powershell -File db\outils\restaurer.ps1 -FichierBase `"$FichierBase`" -FichierRoles `"$FichierRoles`" -NomBaseCible <nouvelle_base>"
exit 0
