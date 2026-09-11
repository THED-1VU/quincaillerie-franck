# Quincaillerie Franck — reconstruction

Dépôt de la reconstruction de l'application de gestion des **Ets Quincaillerie Franck**
(Batouri, région de l'Est, Cameroun).

> **État : reconstruction, cycle 1 fusionné.** L'application d'origine a été livrée
> uniquement en exécutables Windows ; le code source est introuvable. Le dépôt a
> commencé par une phase de cadrage (rétro-spécifications, addendum), puis les
> cycles de finalisation. **Architecture actée : application web unique servie sur
> le réseau local** (PC de caisse + téléphones).

## Documents de cadrage

| Fichier | Contenu |
|---|---|
| [`MODELE_DONNEES.md`](MODELE_DONNEES.md) | Rétro-spécification du schéma PostgreSQL existant + évaluation critique (intégrité, audit, risques). |
| [`PERIMETRE_LIVRE.md`](PERIMETRE_LIVRE.md) | Rétro-spécification fonctionnelle : écrans et fonctions déduits des guides et du dossier de recette. |
| [`ADDENDUM_CAHIER_DES_CHARGES.md`](ADDENDUM_CAHIER_DES_CHARGES.md) | Points ouverts ou contradictoires du cahier des charges : règle proposée, cas limites, question au propriétaire. |
| [`RAPPORT AVANCEMENT/loop-state.md`](RAPPORT%20AVANCEMENT/loop-state.md) | État des 15 chantiers `C0`–`C14` et journal des cycles de finalisation. |
| [`RAPPORT AVANCEMENT/COMPARAISON_ARCHITECTURE.md`](RAPPORT%20AVANCEMENT/COMPARAISON_ARCHITECTURE.md) | Comparaison des deux architectures cibles (bureau+web vs web unique). |
| [`.agents/skills/finalisation-loop/SKILL.md`](.agents/skills/finalisation-loop/SKILL.md) | Le cycle de finalisation en 5 phases utilisé sur ce projet. |

## Cycle 1 — maquette d'ergonomie (chantier C9)

| Élément | Contenu |
|---|---|
| [`maquette/`](maquette/) | Maquette **non câblée** des 4 écrans clés (connexion, vente PC de caisse, tableau de bord mobile, comptage à l'aveugle). HTML/CSS/JS, sans build. Lancer : `cd maquette && py -m http.server 8080`. |
| [`maquette/verification/`](maquette/verification/) | Scripts qui exécutent la maquette et vérifient débordement, erreurs console, cibles tactiles et parcours clés. |
| [`maquette/captures/`](maquette/captures/) | 20 captures (4 écrans × 360/390/768/1366/1920 px). |
| [`UX_BASELINE.md`](UX_BASELINE.md) | Protocole de mesure d'ergonomie à exécuter par un testeur humain. Tant que son tableau §4 n'est pas rempli, **C9 ≤ 60 %**. |

## Source de référence (hors dépôt)

Restent sur le disque, **non versionnés** (voir `.gitignore`) — ils servent de référence :

- `QuincaillerieFranck.exe`, `CreerCompteResponsable.exe` — application livrée ;
- `config.ini` réel — jamais commité.

`QuincaillerieFranck_Test/creation_base_donnees.sql` (le **schéma**, sans données) est
versionné. Les sauvegardes `.sql` **contenant des données** sont exclues.

## Contexte métier (résumé)

Deux sites (magasin de stock, comptoir de vente). Trois rôles : **responsable**
(les deux sites, prix, RH, comptes, encaissement, annulation), **agent stock**
(un site, articles et comptage, ne voit aucun montant), **agent comptabilité**
(un site, saisie a posteriori des ventes payées d'après le facturier papier, ne voit
aucune quantité de stock). Réseau local, PostgreSQL sur un poste serveur, jusqu'à 5 postes.

Priorités du propriétaire : **1.** ergonomie / responsivité — **2.** usage téléphone
(suivi **et** saisie) — **3.** fiabilité métier.
