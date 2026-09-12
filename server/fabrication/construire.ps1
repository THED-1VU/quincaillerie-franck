<#
.SYNOPSIS
    Fabrique QuincaillerieFranck.exe (chantier C0).

.DESCRIPTION
    Ce script ne suppose AUCUNE connaissance de PyInstaller. Il :
      1. verifie que l'environnement Python de server\.venv existe et
         contient PyInstaller (l'installe sinon) ;
      2. construit l'executable a partir de quincaillerie_franck.spec ;
      3. copie config.example.ini a cote de l'executable produit, pour
         qu'un installateur puisse le renommer en config.ini et le remplir.

    Le resultat se trouve dans server\fabrication\dist\QuincaillerieFranck.exe.

    NOTE DE NOMMAGE : ce dossier s'appelle "fabrication", pas "build" : le
    .gitignore exclut tout dossier nomme "build/" (artefacts de compilation
    generiques) ou "dist/" -- s'il s'etait appele "build", Git aurait aussi
    ignore ces scripts sources. Les SOUS-dossiers de sortie de PyInstaller,
    eux, s'appellent bien "dist" et "build" ci-dessous : ce sont exactement
    les artefacts que ces regles generiques doivent exclure.

    NOTE D'ENCODAGE : ce fichier est volontairement en ASCII pur. Voir la
    note dans db/outils/demarrer_pg.ps1 pour la raison (Windows PowerShell
    5.1 peut mal decoder un script UTF-8 sans BOM contenant des accents).

.EXAMPLE
    powershell -File server\fabrication\construire.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$RacineServeur = Resolve-Path (Join-Path $PSScriptRoot '..')
$Venv          = Join-Path $RacineServeur '.venv'
$PythonExe     = Join-Path $Venv 'Scripts\python.exe'
$PyInstaller   = Join-Path $Venv 'Scripts\pyinstaller.exe'
$SpecFile      = Join-Path $PSScriptRoot 'quincaillerie_franck.spec'
$DistPath      = Join-Path $PSScriptRoot 'dist'
$WorkPath      = Join-Path $PSScriptRoot 'build'

function EcrireEtape($msg) { Write-Host ''; Write-Host "== $msg ==" -ForegroundColor Cyan }

if (-not (Test-Path $PythonExe)) {
    Write-Host "ERREUR : environnement Python introuvable dans $Venv" -ForegroundColor Red
    Write-Host "Creez-le d'abord :"
    Write-Host "  py -3.13 -m venv server\.venv"
    Write-Host "  server\.venv\Scripts\python.exe -m pip install -r server\requirements.txt"
    exit 1
}

if (-not (Test-Path $PyInstaller)) {
    EcrireEtape "Installation de PyInstaller (premiere utilisation)"
    & $PythonExe -m pip install -q "pyinstaller==6.11.1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ECHEC de l'installation de PyInstaller." -ForegroundColor Red
        exit 1
    }
}

EcrireEtape "Construction de QuincaillerieFranck.exe"
& $PyInstaller $SpecFile --distpath $DistPath --workpath $WorkPath --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "ECHEC de la construction. Voir le journal ci-dessus." -ForegroundColor Red
    exit 1
}

$ExeCree = Join-Path $DistPath 'QuincaillerieFranck.exe'
if (-not (Test-Path $ExeCree)) {
    Write-Host "ECHEC : $ExeCree n'a pas ete produit." -ForegroundColor Red
    exit 1
}

$ConfigExemple = Join-Path $RacineServeur 'config.example.ini'
Copy-Item $ConfigExemple -Destination $DistPath -Force

Write-Host ''
Write-Host "Construction terminee." -ForegroundColor Green
Write-Host "  Executable : $ExeCree"
Write-Host "  Taille     : $([math]::Round((Get-Item $ExeCree).Length / 1MB, 1)) Mo"
Write-Host ''
Write-Host "Avant de distribuer ce dossier ($DistPath) a un poste :"
Write-Host "  1. copier config.example.ini en config.ini a cote de l'exe ;"
Write-Host "  2. le remplir (voir server\README.md) ;"
Write-Host "  3. NE JAMAIS committer ce config.ini rempli."
