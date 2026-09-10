[CmdletBinding()]
param(
    [string]$ProjectPath = 'H:\2026\PROFESSIONNEL\THED CONNECT\QuincaillerieFranck_Test\QuincaillerieFranck_Test',
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Continue'
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path (Get-Location) ('diagnostic_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
}

if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {
    Write-Error ('Dossier introuvable : ' + $ProjectPath)
    exit 2
}

New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
$resolved = (Resolve-Path -LiteralPath $ProjectPath).Path
$findings = @()

function Add-Finding {
    param([string]$Area,[string]$Item,[string]$Status,[int]$Points,[string]$Evidence)
    $script:findings += [pscustomobject]@{
        Domaine = $Area
        Controle = $Item
        Statut = $Status
        Points = $Points
        Preuve = $Evidence
    }
}

function Search-ProjectText {
    param([string]$Pattern)
    $files = Get-ChildItem -LiteralPath $resolved -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -lt 20MB -and $_.Extension -in '.py','.sql','.ini','.env','.toml','.yaml','.yml','.json','.txt','.md','.ps1','.bat' }
    $hits = @()
    foreach ($file in $files) {
        $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($text -match $Pattern) {
            $hits += $file.FullName.Substring($resolved.Length).TrimStart('\')
        }
    }
    return ($hits | Select-Object -Unique)
}

$manifest = @(Get-ChildItem -LiteralPath $resolved -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{
        Chemin = $_.FullName.Substring($resolved.Length).TrimStart('\')
        Extension = $_.Extension
        TailleOctets = $_.Length
        DerniereModification = $_.LastWriteTime
    }
})
$manifest | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputPath 'inventaire_fichiers.csv')

$hasExe = @($manifest | Where-Object { $_.Extension -eq '.exe' }).Count -gt 0
$hasSql = @($manifest | Where-Object { $_.Extension -eq '.sql' }).Count -gt 0
$hasDocs = @($manifest | Where-Object { $_.Extension -in '.docx','.pdf','.md','.txt' }).Count -gt 0
$hasConfig = @($manifest | Where-Object { $_.Chemin -match 'config|\.env|settings' }).Count -gt 0
$hasTests = @($manifest | Where-Object { $_.Chemin -match 'test|spec' }).Count -gt 0
$hasBackup = @($manifest | Where-Object { $_.Chemin -match 'backup|restore|sauvegarde|restauration' }).Count -gt 0
$hasBuild = @($manifest | Where-Object { $_.Chemin -match 'build|installer|pyinstaller|\.spec$|setup' }).Count -gt 0
$hasWeb = @($manifest | Where-Object { $_.Chemin -match 'fastapi|flask|frontend|web|api' }).Count -gt 0

Add-Finding 'Deployment' 'Executable Windows present' $(if ($hasExe) { 'Present' } else { 'Absent' }) $(if ($hasExe) { 10 } else { 0 }) 'Recherche des fichiers exe.'
Add-Finding 'Data' 'SQL creation script present' $(if ($hasSql) { 'Present' } else { 'Absent' }) $(if ($hasSql) { 10 } else { 0 }) 'Recherche des fichiers sql.'
Add-Finding 'Documentation' 'Guides present' $(if ($hasDocs) { 'Present' } else { 'Absent' }) $(if ($hasDocs) { 8 } else { 0 }) 'Recherche des fichiers docx, pdf, md et txt.'
Add-Finding 'Configuration' 'Configuration separable' $(if ($hasConfig) { 'Found' } else { 'Not found' }) $(if ($hasConfig) { 5 } else { 0 }) 'Recherche de config, env et settings.'
Add-Finding 'Tests' 'Tests identifiable' $(if ($hasTests) { 'Found' } else { 'Not found' }) $(if ($hasTests) { 10 } else { 0 }) 'Recherche de noms test et spec.'
Add-Finding 'Backup' 'Backup and restore procedure' $(if ($hasBackup) { 'Found' } else { 'Not found' }) $(if ($hasBackup) { 10 } else { 0 }) 'Recherche de backup, restore et sauvegarde.'
Add-Finding 'Deployment' 'Build or installer script' $(if ($hasBuild) { 'Found' } else { 'Not found' }) $(if ($hasBuild) { 7 } else { 0 }) 'Recherche de build, installer et pyinstaller.'
Add-Finding 'Mobile' 'Web API or mobile interface' $(if ($hasWeb) { 'Found' } else { 'Not found' }) $(if ($hasWeb) { 10 } else { 0 }) 'Recherche de fastapi, flask, web, api et frontend.'

$checks = @(
    @('Security','Password hashing','(?i)bcrypt|argon2|pbkdf2',10),
    @('Security','Roles and permissions','(?i)role|permission|authorization|responsable|agent',10),
    @('Traceability','Audit or history','(?i)audit|journal|historique|trace|created_by|updated_by',8),
    @('Stock','Transaction or locking','(?i)transaction|atomic|for update|select_for_update|verrou',8),
    @('Stock','Automatic stock threshold','(?i)seuil|alerte|quantite.*re[cce]ue|20\s*%',6),
    @('Sales','VAT totals and payment','(?i)tva|tax|total|orange|mtn|mobile money|credit',6),
    @('Inventory','Inventory blind count and gap','(?i)inventaire|comptage|ecart|attendu|aveugle',6),
    @('Continuity','Backup restore test','(?i)restore|restauration|pg_dump|pg_restore|backup',6)
)
foreach ($check in $checks) {
    $hits = @(Search-ProjectText -Pattern $check[2])
    Add-Finding $check[0] $check[1] $(if ($hits.Count -gt 0) { 'Evidence found' } else { 'Not found' }) $(if ($hits.Count -gt 0) { [int]$check[3] } else { 0 }) ($hits -join '; ')
}

$scores = [ordered]@{}
$stockPoints = ($findings | Where-Object { $_.Domaine -eq 'Stock' } | Measure-Object Points -Sum).Sum
$securityPoints = ($findings | Where-Object { $_.Domaine -eq 'Security' } | Measure-Object Points -Sum).Sum
$tracePoints = ($findings | Where-Object { $_.Domaine -eq 'Traceability' } | Measure-Object Points -Sum).Sum
$salesPoints = ($findings | Where-Object { $_.Domaine -eq 'Sales' } | Measure-Object Points -Sum).Sum
$deploymentPoints = ($findings | Where-Object { $_.Domaine -in 'Deployment','Continuity','Backup' } | Measure-Object Points -Sum).Sum

$scores['Fonctionnalites metier'] = [math]::Min(100, [int](($stockPoints + $salesPoints) * 3))
$scores['Ergonomie PC'] = 0
$scores['Mobile responsive'] = $(if ($hasWeb) { 40 } else { 10 })
$scores['Securite'] = [math]::Min(100, [int]($securityPoints * 5))
$scores['Donnees et concurrence'] = [math]::Min(100, [int]($stockPoints * 5))
$scores['Comptabilite et tracabilite'] = [math]::Min(100, [int](($tracePoints + $salesPoints) * 4))
$scores['Deploiement et exploitation'] = [math]::Min(100, [int]($deploymentPoints * 3))
$scores['Tests et documentation'] = [math]::Min(100, [int](($hasTests.ToString().Length + $hasDocs.ToString().Length) * 10))

$findings | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutputPath 'constats.csv')

$summary = [pscustomobject]@{
    Projet = $resolved
    DateAudit = (Get-Date)
    NombreFichiers = $manifest.Count
    NombreExecutables = @($manifest | Where-Object { $_.Extension -eq '.exe' }).Count
    NombreScriptsSQL = @($manifest | Where-Object { $_.Extension -eq '.sql' }).Count
    Scores = $scores
    Limite = 'Audit statique. Ergonomie, responsive et execution runtime exigent un test manuel.'
}
$summary | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path (Join-Path $OutputPath 'synthese.json')

$report = @()
$report += '# Diagnostic automatise - Quincaillerie Franck'
$report += ''
$report += ('Projet : ' + $resolved)
$report += ('Date : ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$report += ''
$report += '## Scores statiques par compartiment'
$report += ''
$report += '| Compartiment | Score indicatif |'
$report += '|---|---:|'
foreach ($key in $scores.Keys) {
    $report += ('| ' + $key + ' | ' + $scores[$key] + ' % |')
}
$report += ''
$report += '## Constats'
$report += ''
foreach ($item in $findings) {
    $report += ('- ' + $item.Domaine + ' - ' + $item.Controle + ' : ' + $item.Statut + '. ' + $item.Preuve)
}
$report += ''
$report += '> Les scores ne remplacent pas les tests UI, fonctionnels et reseau avec des utilisateurs reels.'
$report -join "`r`n" | Set-Content -Encoding UTF8 -Path (Join-Path $OutputPath 'diagnostic.md')

$checklist = @(
    'CHECKLIST MANUELLE UI UX',
    '[ ] Connexion compréhensible en moins de 30 secondes.',
    '[ ] Vente standard réalisable en moins de 60 secondes.',
    '[ ] Quantité et prix accessibles sur le même écran.',
    '[ ] Erreurs affichées en français près du champ.',
    '[ ] Aucun débordement sur 360, 390, 768 et 1366 pixels.',
    '[ ] Zones tactiles utilisables sur téléphone.',
    '[ ] Tableau de bord lisible sans zoom.',
    '[ ] Impression ticket testée.',
    '[ ] Test de deux ventes concurrentes.',
    '[ ] Test de coupure réseau et reprise.'
)
$checklist -join "`r`n" | Set-Content -Encoding UTF8 -Path (Join-Path $OutputPath 'checklist_ui_ux.txt')

Write-Host ('Diagnostic termine. Resultats : ' + $OutputPath) -ForegroundColor Green
Write-Host 'Fichiers : inventaire_fichiers.csv, constats.csv, synthese.json, diagnostic.md, checklist_ui_ux.txt'
