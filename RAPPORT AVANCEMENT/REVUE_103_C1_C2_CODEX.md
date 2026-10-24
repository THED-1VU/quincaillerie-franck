# Revue #103 — données et authentification

Date : 23/10/2026. Destinataires : Qoder et propriétaire.
Périmètre autorisé : revue et préparation des décisions ; aucune correction de la branche Qoder.

## Socle et verdict

- `main` synchronisé par fetch/prune, switch et pull ff-only : `d745ead5377da65336c2498b56fb25cbd7dd4992`.
- Branche de revue créée depuis `origin/main` : `codex/revue-103-decisions-c1-c3`.
- #103 examinée à `54ffea5010c8a14948a86465cb384c3e5ac49565`, branche `operation-100-lot-b`.
- Ancêtre commun avec main : `2dae40616d2b906f8f6c3939832f6fc573a1c8b7` (#100).
- GitHub annonce MERGEABLE/CLEAN ; cela ne constitue ni une validation d'intégration ni une autorisation de fusion. La CI existante de #103 porte sur l'ancien socle. Sa description mentionne encore des dépendances #92→#100 à actualiser.
- **Avis : réserves avant fusion.** Faire traiter les points ci-dessous par Qoder et revalider la PR sur main intégrant 053/054. Aucun merge effectué.

## Remarques à traiter

### R1 — P1 : code de sortie faussement vert de la campagne EXE

`db/outils/campagne_exe_lotb.sh:58-71,130-137` : les échecs de préparation augmentent `ETAPES_KO`, mais le script poursuit et termine uniquement par `exit "$CODE_PW"`. Si les suites passent, le code final reste 0 malgré une préparation en échec.

Preuve exécutée sur le script #103 inchangé, dans un répertoire factice : psql, Akuma, réseau et suites remplacés par des doubles. CREATE DATABASE échoue ; les 13 suites simulées réussissent ; bilan « 1 étape(s) en échec », **code final 0**. Aucun vrai EXE ni PostgreSQL sollicité par cette sonde.

Attendu : arrêter la préparation à son premier échec et retourner un code non nul pour toute étape en échec. Installer le nettoyage avant les sorties anticipées. Ne pas modifier la branche Qoder depuis cette revue.

### R2 — P1 pour le travail parallèle : port pytest non transmis

`db/outils/verifier_tout.sh:191` transmet QF_TEST_DBNAME et QF_CONFIG, mais pas QF_TEST_PGPORT. Depuis #102, `server/tests/conftest.py` lit QF_TEST_PGPORT, défaut 5433, indépendamment de PGPORT.

Preuve de configuration exécutée avec PGPORT=5558 et QF_TEST_PGPORT absent : PGPORT=5558, port administratif effectif de conftest=5433. Le serveur applicatif viserait 5558 via QF_CONFIG et les réinitialisations pytest 5433. Aucun appel à 5433 effectué pour cette preuve.

Attendu : transmettre explicitement QF_TEST_PGPORT="$PGPORT" à pytest et vérifier l'identité de la base avant la campagne. Préserver une **instance PostgreSQL isolée**, pas seulement un nom de base : la suite SQL inverse supprime/recrée des rôles globaux. La campagne EXE impose encore 5433 et change le mot de passe global qf_app ; ne pas l'exécuter en concurrence sur le serveur partagé.

### R3 — P1 avant remise en service : sessions après restauration

`db/outils/restaurer.ps1:315-369` restaure le contenu sans invalidation des sessions. Avec 053, sessions_serveur et jetons_revoques sont restaurées à l'instant du dump.

Preuve synthétique : session A révoquée avant dump, session B révoquée après dump. Après restauration : A et B présentes dans sessions_serveur ; seule A présente dans jetons_revoques. La révocation de B a été perdue. Avec la même clé de signature et un jeton encore valide, cette révocation n'est donc plus opposable. Ce risque de retour à un état ancien est une propriété de restauration, pas une régression imputée à la seule modification de nettoyage de #103.

Attendu : avant toute exposition d'une base restaurée, imposer une reconnexion générale par une procédure vérifiée (invalidations des sessions restaurées ou rotation maîtrisée de la clé). Ajouter une preuve de refus HTTP d'un ancien jeton sur la procédure retenue. Le nombre de tables seul, critère de succès actuel, ne prouve pas les invariants de sécurité et de paiement. Aucun changement de politique métier proposé.

## Vérifications positives exécutées

Cluster PostgreSQL 17 privé, port **5558**, base `quincaillerie_revue103`, données du jeu d'essai uniquement. Python de l'environnement existant ; aucune installation ni donnée réelle. Les fichiers #103 sont extraits par SHA, sans modification de leur contenu.

1. Reconstruction du schéma initial, migrations main jusqu'à 054, seed synthétique : OK.
2. Commande ciblée :

   `python -m pytest server/tests/test_campagne_fcfa_c5.py server/tests/test_integrite_paiements_sql.py server/tests/test_sessions_serveur.py -q --tb=short -p no:cacheprovider --basetemp <répertoire unique>`

   **27 passed, 5 warnings, 62.23 s.** Le premier fichier est celui de #103 ; les deux autres sont ceux de main. Les 27 incluent les paramétrages. Cela comprend les 2 scénarios FCFA, la concurrence des paiements, les refus SQL directs, la RLS intersites, l'attaque par table temporaire, les sessions et les rôles vivants.
3. `bash -n` sur les deux scripts Bash #103 : OK.
4. Dump créé directement par pg_dump sur les seules données synthétiques, puis **restaurer.ps1 de #103 exécuté sans modification**, vers `quincaillerie_revue103_restauree` : code 0, 40 tables. `sauvegarder.ps1` n'a été ni exécuté ni restauré.
5. Sur la base restaurée : 053 et 054 présentes ; les cinq fonctions contrôlées conservent `search_path=public, pg_temp` ; pour qf_agent_comptabilite, UPDATE(ventes.id)=true et UPDATE(ventes.total_ttc)=false ; les déclencheurs de somme, parent et verrou restent activés (`O`). Voir la transcription jointe.
6. Cluster privé arrêté après les tests. Fichiers temporaires copiés dans le worktree supprimés ; branche Qoder non modifiée. Le worktree `verif-integration` est conservé.

Une erreur dans mon SQL de préparation initial (INSERT sans liste de colonnes dans jetons_revoques) a interrompu la première tentative de restauration ; corrigée dans le harnais, puis restauration exécutée avec succès. Les 27 tests ont été exécutés une fois ; leur succès n'a pas été obtenu en les modifiant.

**Limites :** pas de rejeu complet de pytest ni des 13 suites Playwright dans cette revue ciblée, pas de reconstruction/exécution du binaire Lot B. Les 394 pytest et 13/13 Playwright de la simulation antérieure restent une preuve historique de #100+#101+#102, et ne valident pas #103. La sonde de code retour EXE utilise des suites simulées, pas Playwright réel.

## Décisions, scores et référentiel

Les huit fiches séparées sont dans `DECISIONS_LOT_A/`. Aucun paramètre changé, aucune décision prise. Aucune migration ajoutée ou utilisée : 055 demeure le prochain numéro, à réserver dans loop-state.md **avant usage**.

Scores de référence du registre : **C1 96 %, C2 90 %, C3 88 %**. Aucun relèvement par cette revue. Les preuves ciblées ne permettent pas d'affirmer « 100 % technique » de l'ensemble ni « 100 % global ». C1 reste notamment dépendant de Q1–Q6 et des validations de données réelles hors périmètre ; C2 de C2-01 ; C3 de D1.

Divergences signalées, sans correction silencieuse :

- Le tableau d'en-tête de loop-state.md affiche encore C1 92 %, C2 82 %, C3 77 %, contre 96/90/88 dans REGISTRE_ECARTS_100.md et l'état communiqué par le propriétaire.
- Le skill finalisation-loop appelle C8 « Tableaux de bord et rapports », tandis que le registre officiel appelle C8 « Interfaces et parcours ». Pour cette revue, **le registre fait autorité**, comme demandé ; le libellé C8 de Lot B ne constitue donc pas à lui seul une erreur.
- La fiche Q3 historique questionne encore la saisie TTC : la décision applicative TTC est acquise ; seule sa confirmation fiscale par le comptable reste ouverte.

Journaux complets conservés localement sous `_preuves_simulation_integration/revue103_20261023T213722Z/`. Aucun cluster, dump, capture, binaire ou artefact volumineux publié.
