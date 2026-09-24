# Akuma — reconstruction (Ets Quincaillerie Franck)

Dépôt de la reconstruction d'**Akuma**, l'application de gestion de quincaillerie
déployée aux **Ets Quincaillerie Franck** (Batouri, région de l'Est, Cameroun).
Akuma est le nom de la gamme logicielle (éditeur) ; « Ets Quincaillerie Franck »
reste le nom du client — voir `ADDENDUM_CAHIER_DES_CHARGES.md`.

> **État : cycle 44 fusionné (2026-09-24), moyenne indicative ≈ 71 %**
> sur les 15 chantiers C0–C14 — détail, scores et journal dans
> [`RAPPORT AVANCEMENT/loop-state.md`](RAPPORT%20AVANCEMENT/loop-state.md).
>
> **Architecture actée :** un seul code applicatif **web**, mais **livré et
> exécuté comme une application Windows (`.exe`)** sur les postes de la
> boutique — l'exécutable embarque le serveur local et ouvre l'interface,
> sans installation de Python. Les **téléphones Android / iPhone** ouvrent la
> **même** application dans un navigateur via le réseau local. Pas
> d'interface de bureau PyQt6.

## Livrables du cahier des charges §7 (point l de l'addendum)

| Exigence CDC §7 | Où elle est livrée |
|---|---|
| **Code source complet** (application, API, schéma, scripts, tests) | Ce dépôt Git (`main`), livré en continu ; propriété et accès formalisés dans [`OWNERSHIP.md`](OWNERSHIP.md) |
| **Schéma de base + migrations** | [`QuincaillerieFranck_Test/creation_base_donnees.sql`](QuincaillerieFranck_Test/creation_base_donnees.sql) (schéma d'origine) + [`db/migrations/`](db/migrations/) (000–038 + inverses, appliquées par [`db/outils/migrer.sh`](db/outils/migrer.sh)) |
| **Scripts de fabrication des exécutables** | [`server/fabrication/`](server/fabrication/) : `construire.ps1` (script humain), `quincaillerie_franck.spec` (PyInstaller), `lanceur.py` ; trace de la dernière construction dans [`server/fabrication/DERNIER_RESULTAT.md`](server/fabrication/DERNIER_RESULTAT.md) |
| **Scripts + guide de sauvegarde/restauration** | [`db/outils/sauvegarder.ps1`](db/outils/sauvegarder.ps1), [`restaurer.ps1`](db/outils/restaurer.ps1), [`planifier_sauvegarde.ps1`](db/outils/planifier_sauvegarde.ps1) + [`db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`](db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md) (RPO 1 h, RTO 2 h, chiffrement AES-256) |
| **Jeux de tests** | [`server/tests/`](server/tests/) (pytest, 248 tests, vraie base PostgreSQL), [`db/tests/`](db/tests/) (protections, habilitations, concurrence, réversibilité, volume réaliste), [`maquette/verification/`](maquette/verification/) (suites Playwright) |
| **Intégration continue** | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — service `postgres:17`, migrations + jeu d'essai + pytest sur chaque push/PR vers `main` |
| **Documentation d'installation et d'exploitation** | Ce README, [`db/README.md`](db/README.md), [`db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`](db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md), guides testeur et dossier de recette (références dans [`PERIMETRE_LIVRE.md`](PERIMETRE_LIVRE.md)) |
| **Rétro-spécifications et décisions** | [`MODELE_DONNEES.md`](MODELE_DONNEES.md), [`PERIMETRE_LIVRE.md`](PERIMETRE_LIVRE.md), [`ADDENDUM_CAHIER_DES_CHARGES.md`](ADDENDUM_CAHIER_DES_CHARGES.md), [`VISION_PRODUIT.md`](VISION_PRODUIT.md), [`UX_BASELINE.md`](UX_BASELINE.md) |

**N'est JAMAIS dans le dépôt** : `config.ini` réel, mots de passe, clés
secrètes, sauvegardes de données réelles, exécutables compilés (voir
`.gitignore` et l'audit documenté dans `OWNERSHIP.md`).

## Documents de cadrage et de suivi

| Fichier | Contenu |
|---|---|
| [`ADDENDUM_CAHIER_DES_CHARGES.md`](ADDENDUM_CAHIER_DES_CHARGES.md) | Points ouverts ou contradictoires du cahier des charges : règle proposée, cas limites, décisions du propriétaire (points a–l). |
| [`MODELE_DONNEES.md`](MODELE_DONNEES.md) | Rétro-spécification du schéma PostgreSQL + évaluation critique. |
| [`PERIMETRE_LIVRE.md`](PERIMETRE_LIVRE.md) | Rétro-spécification fonctionnelle : écrans et fonctions déduits des guides et du dossier de recette. |
| [`VISION_PRODUIT.md`](VISION_PRODUIT.md) | Décisions produit datées (cycles et candidats). |
| [`UX_BASELINE.md`](UX_BASELINE.md) | Protocole de mesure d'ergonomie à exécuter par un testeur humain. |
| [`OWNERSHIP.md`](OWNERSHIP.md) | Propriété du code, accès au dépôt, audit des secrets (point l). |
| [`RAPPORT AVANCEMENT/loop-state.md`](RAPPORT%20AVANCEMENT/loop-state.md) | État des 15 chantiers `C0`–`C14` + journal des cycles. |
| [`.agents/skills/finalisation-loop/SKILL.md`](.agents/skills/finalisation-loop/SKILL.md) | La boucle de finalisation utilisée sur ce projet. |

## Architecture du dépôt

```
QuincaillerieFranck_Test/
├── creation_base_donnees.sql   Schéma PostgreSQL d'origine (versionné, sans données)
├── server/                     Serveur FastAPI : app/, tests/, fabrication/ (exe)
│   ├── app/                    Config, accès base (bascule de rôle), sécurité, routes
│   ├── tests/                  Suite pytest (aucun mock, vraie base)
│   └── fabrication/            construire.ps1 + .spec PyInstaller + lanceur.py
├── db/
│   ├── migrations/             000–038 + inverses (appliquées/annulées par migrer.sh)
│   ├── outils/                 migrer.sh, sauvegarde/restauration, générateur de volume,
│   │                           premier compte responsable, rapprochement d'articles, etc.
│   └── tests/                  Vérification PAR EXÉCUTION (protections, habilitations,
│                               concurrence, réversibilité, volume réaliste)
├── maquette/                   Interface web (HTML/CSS/JS) + suites Playwright + captures
├── .github/workflows/ci.yml    CI GitHub Actions (pytest sur postgres:17)
└── RAPPORT AVANCEMENT/         loop-state.md (scores + journal) et documents de suivi
```

## Reconstruire et vérifier (résumé opérationnel)

- **Base de test** : `bash db/tests/executer_tests.sh` (avec `PSQL`/`PG_DUMP`/
  `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD` positionnés) — recrée la base,
  applique 000–038, rejoue protections/habilitations/concurrence, puis les
  inverses et compare le schéma.
- **Serveur** : `server/.venv/Scripts/python.exe -m uvicorn app.main:app
  --app-dir server` (config dans `server/config.ini`, jamais versionnée).
- **Tests applicatifs** : `server/.venv/Scripts/python.exe -m pytest server/tests`.
- **Exécutable** : `.\\server\\fabrication\\construire.ps1` → `Akuma.exe`.
- **Sauvegarde/restauration** : voir
  [`db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`](db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md).

## Contexte métier (résumé)

Deux sites (magasin de stock, comptoir de vente). Trois rôles — **responsable**
(les deux sites, prix, RH, comptes, encaissement, annulation), **agent stock**
(un site, articles et comptage, ne voit aucun montant), **agent comptabilité**
(un site, saisie des ventes d'après le facturier papier, ne voit aucune quantité
de stock) — cumulables sur un même compte depuis le cycle 43. Réseau local,
PostgreSQL sur un poste serveur, jusqu'à 5 postes.

Priorités du propriétaire : **1.** ergonomie / responsivité — **2.** usage
téléphone (suivi **et** saisie) — **3.** fiabilité métier.
