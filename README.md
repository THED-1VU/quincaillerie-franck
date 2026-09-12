# Quincaillerie Franck — reconstruction

Dépôt de la reconstruction de l'application de gestion des **Ets Quincaillerie Franck**
(Batouri, région de l'Est, Cameroun).

> **État : reconstruction, cycle 3 fusionné.** L'application d'origine a été livrée
> uniquement en exécutables Windows ; le code source est introuvable. Le dépôt a
> commencé par une phase de cadrage (rétro-spécifications, addendum), puis les
> cycles de finalisation.
>
> **Architecture actée :** un seul code applicatif **web**, mais **livré et exécuté
> comme une application Windows (`.exe`)** sur les postes de la boutique —
> l'exécutable embarque le serveur local et ouvre l'interface en plein écran, sans
> installation de Python. Les **téléphones Android / iPhone** ouvrent la **même**
> application dans un navigateur, pour l'**usage** et le **suivi**, via le réseau
> local ou un tunnel. Pas d'interface de bureau PyQt6.

## Documents de cadrage

| Fichier | Contenu |
|---|---|
| [`MODELE_DONNEES.md`](MODELE_DONNEES.md) | Rétro-spécification du schéma PostgreSQL existant + évaluation critique (intégrité, audit, risques). |
| [`PERIMETRE_LIVRE.md`](PERIMETRE_LIVRE.md) | Rétro-spécification fonctionnelle : écrans et fonctions déduits des guides et du dossier de recette. |
| [`ADDENDUM_CAHIER_DES_CHARGES.md`](ADDENDUM_CAHIER_DES_CHARGES.md) | Points ouverts ou contradictoires du cahier des charges : règle proposée, cas limites, question au propriétaire. |
| [`RAPPORT AVANCEMENT/loop-state.md`](RAPPORT%20AVANCEMENT/loop-state.md) | État des 15 chantiers `C0`–`C14` et journal des cycles de finalisation. |
| [`RAPPORT AVANCEMENT/COMPARAISON_ARCHITECTURE.md`](RAPPORT%20AVANCEMENT/COMPARAISON_ARCHITECTURE.md) | Comparaison des deux architectures cibles (bureau+web vs web unique). |
| [`.agents/skills/finalisation-loop/SKILL.md`](.agents/skills/finalisation-loop/SKILL.md) | Le cycle de finalisation en 5 phases utilisé sur ce projet. |

## Cycle 3 — noyau serveur : authentification et habilitations (chantiers C2, C3, C11)

| Élément | Contenu |
|---|---|
| [`server/README.md`](server/README.md) | Serveur FastAPI : authentification, habilitations au niveau des requêtes SQL, sécurité applicative. Aucun écran, aucune règle métier de vente/stock. |
| [`server/app/`](server/app/) | Config (refuse `postgres` et les clés d'exemple), accès base (**seul** point de bascule de rôle PostgreSQL), sécurité (hachage `$2a$`, jetons signés, limiteur de débit), routes (`auth`, `demonstration`). |
| [`server/tests/`](server/tests/) | Suite pytest, exécutée contre la vraie base PostgreSQL (aucun mock). |
| [`server/tests/DERNIER_RESULTAT.md`](server/tests/DERNIER_RESULTAT.md) | Trace de la dernière exécution : **36/36**, plus preuve RLS en SQL direct hors API. |
| [`db/migrations/009_authentification.sql`](db/migrations/009_authentification.sql) | `verifier_connexion()` — seule fonction à lire un hachage de mot de passe, ne le restitue jamais. |
| [`db/migrations/010_correction_usage_qf_app.sql`](db/migrations/010_correction_usage_qf_app.sql) | Corrige un oubli de la migration 008 (`qf_app` sans accès au schéma). |

Preuve la plus forte du cloisonnement par site : en SQL direct, **hors de
toute route**, sous le rôle d'un agent avec son site positionné, une requête
qui demande explicitement les données de l'*autre* site renvoie zéro ligne —
la protection est dans PostgreSQL (RLS), pas dans le code applicatif.

## Cycle 2 — base de données durcie (chantier C1)

| Élément | Contenu |
|---|---|
| [`db/README.md`](db/README.md) | Mode d'emploi des migrations et **tableau complet des droits** : qui peut lire et écrire quoi, colonne par colonne. |
| [`db/migrations/`](db/migrations/) | 9 migrations numérotées + leurs 9 inverses. Le schéma d'origine est corrigé, jamais remplacé. |
| [`db/outils/`](db/outils/) | `migrer.sh` (appliquer / annuler / état), `prevol.sql` (ce qui bloquerait sur une base contenant des données), `definir_mot_de_passe_app.sql`. |
| [`db/tests/`](db/tests/) | Vérification **par exécution** : 44 protections, 52 habilitations, 4 contrôles de concurrence, aller-retour des migrations. |
| [`db/tests/DERNIER_RESULTAT.md`](db/tests/DERNIER_RESULTAT.md) | Trace de la dernière exécution : **100 contrôles, 0 échec**, avec l'avant/après. |

L'écart d'inventaire est désormais **calculé par la base** et la quantité
attendue y est figée par déclencheur : ni l'un ni l'autre ne peut être forgé par
un programme client. L'application ne se connecte plus en superutilisateur.

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
