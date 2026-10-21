# Rapport des tests — Matrice des rôles (cycle 65, 2026-10-21)

Base : `quincaillerie_c65` (schéma + migrations 000→050 + jeu d'essai),
serveur réel sur `http://127.0.0.1:8010` (config dédiée `$TEMP/akuma_c65_config.ini`,
base et serveur jetables, arrêtés/supprimés en fin de cycle). Aucun mock :
bcrypt réel, jetons réels, RLS réelle, navigateur Chrome réel.

## 1. Récapitulatif des exécutions

| Suite | Résultat | Preuve |
|---|---|---|
| `test_matrice_roles.py` (nouveau, 56 routes × 3 rôles + anonyme) | **1/1, zéro divergence** (≈ 390 requêtes) | sortie pytest |
| `test_privileges_sql_roles.py` (nouveau, 10 sondes SQL sous rôle) | **10/10** | sortie pytest |
| `test_changement_mdp_force.py` (nouveau, correctif cycle 65) | **3/3** | sortie pytest |
| `verifier-roles.mjs` (nouveau, Playwright : UI par rôle + force + cumul) | **30/30, 22 captures** | `maquette/captures/roles/`, sortie console |
| Régression complète `pytest tests` (après correctif des 3 tests préexistants) | **voir §4** | sortie pytest |

## 2. Défaut trouvé par la matrice et corrigé dans le cycle

**Défaut** : `utilisateurs.doit_changer_mot_de_passe` était émis dans le
jeton et dans la réponse de connexion (cycle 38) mais **contrôlé nulle part** —
vérifié par grep exhaustif sur `server/` et `maquette/` avant correction.
Un compte créé par le responsable (ou réinitialisé) pouvait donc travailler
indéfiniment avec son mot de passe provisoire, alors que
`server/README.md` (C2) documente une obligation de changement à la première
connexion. La maquette documentait pareillement cet écran comme « à faire ».

**Correctif** (minimal, dans les conventions du dépôt) :
- `db/migrations/050_changement_mdp_requis.sql` (+ inverse) : fonction
  `changement_mdp_requis(INTEGER) BOOLEAN` en `SECURITY DEFINER`, `STABLE`,
  `REVOKE PUBLIC` + `GRANT EXECUTE TO qf_app` uniquement — `qf_app` n'a
  aucun `SELECT` direct sur `utilisateurs` (008), c'est la fenêtre étroite
  qui manquait, exactement le motif de `compte_est_actif` (024).
- `server/app/deps.py` : `obtenir_session` la relit **en base à chaque
  requête** (pas la valeur figée du jeton) ; drapeau vrai ⇒ 403 sur toute
  route sauf `/auth/changer-mot-de-passe` et `/auth/deconnexion`. Deux
  conséquences voulues, prouvées par les tests : après un changement réussi,
  la même session redevient utilisable immédiatement ; une réinitialisation
  par le responsable coupe un jeton encore valide dès la requête suivante.
- `maquette/changer-mot-de-passe.html` (nouvel écran) : garde volontairement
  différente (ne passe PAS par `exigerSession`, qui bouclerait sur le 403 de
  `/moi`) ; ré-enregistre la session si `appelApiBrut` l'a effacée sur un 401
  « mot de passe actuel incorrect » (le jeton reste valide serveur).
- `maquette/connexion.html` + `maquette/api.js` : renvoi vers l'écran de
  changement quand le drapeau est vrai (garde anti-boucle sur l'écran lui-même).
- `db/tests/00_jeu_essai.sql` : les comptes de travail du jeu d'essai passent
  `doit_changer_mot_de_passe = FALSE` (employés en poste). Sans cela, avec
  l'obligation appliquée, toute la suite métier derrière ces comptes serait
  403. L'obligation elle-même reste prouvée par `test_premier_compte`
  (création ⇒ TRUE) et `test_changement_mdp_force`.

## 3. Adaptation de tests préexistants (conséquence directe du correctif)

Première régression : **3 échecs**, une seule cause racine — des tests
créent un compte par l'API (le drapeau est alors TRUE par construction, ce
qui est le comportement voulu) puis appellent des routes métier avec ce
compte, désormais bloqué par l'obligation. L'obligation a raison ; ce sont
les tests qui dataient d'avant elle.

| Test | Correction |
|---|---|
| `test_authentification.py::test_changement_mot_de_passe_a_la_premiere_connexion` | le jeu d'essai représente désormais des comptes en poste : la prémisse « première connexion » est posée explicitement (`fixer_drapeau_changement_mdp("resp", True)`) — le test garde exactement son sens |
| `test_comptes.py::test_desactiver_reactiver_et_coupure_session` | retrait du drapeau sur le compte créé (le test porte sur la désactivation) |
| `test_cumul_roles.py::_creer_agent_cumule` (2 tests) | retrait du drapeau sur le compte créé — sinon le second test passerait « pour la mauvaise raison » (403 du drapeau au lieu du 403 de rôle qu'il doit prouver) |

Helper commun ajouté à `conftest.py` :
`fixer_drapeau_changement_mdp(identifiant, valeur)` — raccourci
d'administration de test (DSN postgres), car l'application ne peut retirer
ce drapeau que par le changement réel du mot de passe. Le helper local de
`test_changement_mdp_force.py` réutilise désormais celui-ci (doublon retiré).

Après correction : **40/40** sur les 6 fichiers touchés (3 anciens + 3 nouveaux).

## 4. Régression complète finale

`QF_TEST_DBNAME=quincaillerie_c65 python -m pytest tests -q --basetemp=$TEMP/pytest-c65-final`

**Résultat : 320 passed, 0 failed, exit 0** en 11 min 39 s. Dont ce cycle :
14 tests nouveaux (3 force + 1 matrice API + 10 sondes SQL) et les 3 tests
préexistants adaptés au §3, tous verts.

Note environnement : le répertoire de base par défaut de pytest
(`%TEMP%\pytest-of-USER\pytest-current`) contient un jonction résiduel
inaccessible sans élévation (connu depuis le cycle 56, tableau de pilotage) :
le premier run s'est écrasé en nettoyage de fin de session. Contournement
sans élévation : `--basetemp` dédié, sans toucher au lien. L'élévation
reste une action propriétaire (décision déjà consignée).

## 5. Divergences et anomalies relevées (non corrigées, consignées)

| # | Gravité | Description | Où |
|---|---|---|---|
| D1 | P3 | `inventaire.html` refuse le responsable ; l'API l'autorise à compter | `MATRICE_ROLES_AKUMA.md` §2, `DECISIONS_PROPRIETAIRE.md` D8 |
| D2 | P3 | UI cumul de rôles = rôle principal seul ; API = tous les rôles (403/200 mesurés) | `MATRICE_ROLES_AKUMA.md` §8, `DECISIONS_PROPRIETAIRE.md` D7 |
| D3 | P2 | Attribution `utilisateur_caisse_id` à auditer (`server/app/routes/ventes.py:210-227`) — relevée en exploration | audit planifié cycle 66 (`REGISTRE_ECARTS_100.md`) |
| D4 | P2 | Visibilité des prix du caissier : vérifiée en inspection (aucun `prix_achat` ni à l'écran ni dans les rapports), confirmation formelle requise | `DECISIONS_PROPRIETAIRE.md` D1 |
| D5 | P3 | Journal `loop-state.md` : sections des cycles 61-64 absentes (branches et PR #78-#81 existent) | à reconstituer au cycle 66 si le propriétaire le demande |

**Statuées au cycle 69 (écart C8-01 clôturé, preuves d'exécution : pytest
6/6 sur `test_cumul_roles.py` + `test_matrice_roles.py`, Playwright
`verifier-cablage.mjs` 94/94, inspection `ventes.py:220-227`)** : D1 et D2
**acceptées en l'état** (gates UI volontaires, recommandations D8/D7 option 1 —
confirmation réservée au propriétaire) ; D3 tracée vers l'écart C5-01
(BLOQUE_PROPRIETAIRE, décision D9) ; D4 tracée vers C3-01 (BLOQUE_PROPRIETAIRE,
décision D1) ; D5 tracée vers C0-04 (OUVERT, développement — journal des
cycles 61-64). Détail : `MATRICE_ROLES_AKUMA.md` §9 ; `REGISTRE_ECARTS_100.md`
C8-01.

## 6. Captures (22) — `maquette/captures/roles/`

- `00-connexion.png` — écran de connexion.
- `responsable-01-accueil-tableau-bord` + 4 pages autorisées + `responsable-refuse-inventaire` (preuve de redirection vers le tableau de bord).
- `agent-comptabilite-01-accueil-vente` + 2 pages autorisées + 2 refus redirigés vers vente.
- `agent-stock-01-accueil-inventaire` + 2 pages autorisées + 2 refus redirigés vers inventaire.
- `force-01` à `force-04` : écran de changement imposé, deep-link bloqué, mauvais mot de passe actuel refusé (message serveur), session libérée vers l'accueil comptabilité.
- `cumul-01-ui-refuse-perimetre-secondaire` : la vente refusée à l'écran malgré l'acceptation API.

Rejeu : `cd maquette/verification && PGDATABASE_PISTE=quincaillerie_c65 npm run roles`
(prérequis : serveur sur SERVEUR_URL servant /app ; la suite réinitialise
elle-même la base et supprime ses comptes temporaires via le rejeu d'essai —
TRUNCATE, seul mécanisme qui respecte les déclencheurs anti-suppression
des journaux, migration 004).
