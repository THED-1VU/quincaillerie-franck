# Note de transfert (escrow) — Akuma / Ets Quincaillerie Franck

**Cycle 72 (2026-10-21) — écart C14-03.** Ce document permet à un **tiers
qualifié de reprendre l'application** (maintenance, hébergement, évolution)
sans dépendre de la connaissance tacite du projet. Il ne remplace pas les
guides détaillés : il les **recense et en donne la hiérarchie**. Chaque
affirmation citée est vérifiable dans le dépôt (chemins entre backticks).

> La propriété du code, l'accès administrateur au dépôt et la clause de
> réversibilité sont actés dans [`OWNERSHIP.md`](OWNERSHIP.md) — point l de
> l'addendum, décision du 2026-09-13. La présente note couvre le « comment »
> opérationnel ; le « qui et pourquoi » y est.

## 1. Ce que le dépôt contient — et ne contient jamais

Le dépôt (`THED-1VU/quincaillerie-franck`) est **autonome** : code API,
maquette, schéma, migrations, scripts de fabrication/sauvegarde/restauration,
jeux de tests et documentation. Tableau complet des livrables exigés par le
CDC §7 : [`README.md`](README.md) (section « Livrables du cahier des charges
§7 »).

**Jamais commités** (vérifié par audit d'historique, voir `OWNERSHIP.md`) :
`server/config.ini` réel, mots de passe, clés secrètes, sauvegardes de
données réelles, exécutables compilés. Une installation réelle se reconstruit
depuis le dépôt + les secrets fournis par le propriétaire (§4 et §5).

## 2. Architecture en cinq lignes

1. **API** : FastAPI (Python, `server/app/`), servie par uvicorn ; la
   maquette statique (`maquette/`) est servie sous `/app` par le même
   processus (`server/README.md`).
2. **Base** : PostgreSQL 17 (`_pgdev/pgsql` portable sur le poste de
   développement ; service Windows en production). Schéma d'origine
   `QuincaillerieFranck_Test/creation_base_donnees.sql` + migrations
   numérotées `db/migrations/` (000→050, chacune avec son inverse),
   appliquées par `db/outils/migrer.sh` (`appliquer` / `annuler`).
3. **Sécurité des accès** : l'application ne se connecte que comme le rôle
   PostgreSQL `qf_app`, qui n'a **aucun droit direct** ; chaque transaction
   fait `SET LOCAL ROLE` vers un rôle métier (`qf_responsable`,
   `qf_agent_stock`, `qf_agent_comptabilite`) — habilitations entièrement en
   base, testées par `db/tests/02_habilitations.sql` et
   `server/tests/test_matrice_roles.py` (matrice complète :
   `MATRICE_ROLES_AKUMA.md`).
4. **Livraison** : un seul code web, empaqueté en `.exe` Windows par
   PyInstaller (`server/fabrication/construire.ps1`, spéc
   `quincaillerie_franck.spec`, lanceur `lanceur.py`) ; les téléphones
   ouvrent la même application en navigateur via le réseau local.
5. **Qualité** : trois couches de tests rejouées par **une seule commande**
   `bash db/outils/verifier_tout.sh` (suite SQL → pytest 334 tests → 13
   suites Playwright, 477 contrôles) ; correspondance suites↔chantiers dans
   `maquette/verification/SUITES_CHANTIERS.md` ; CI GitHub Actions sur
   `.github/workflows/ci.yml`.

## 3. Comptes : modèle et provisioning

- **Rôles métier** : `responsable` (administrateur de la boutique),
  `agent_stock`, `agent_comptabilite` (encaisse et saisit — addendum
  point h, cycle 27). Un compte peut porter plusieurs rôles
  (`utilisateurs_roles` ; divergence UI/API documentée D2,
  `DECISIONS_PROPRIETAIRE.md` D7).
- **Provisioning** : les comptes sont **créés par le responsable** depuis
  l'écran Comptes ; il n'existe pas de création libre ni de MFA en v1
  (décision du 2026-10-20, `DECISIONS_PROPRIETAIRE.md`).
- **Premier compte** (base neuve) : fonction `creer_premier_responsable()`
  (migration 023, `SECURITY DEFINER`, refuse un second compte) via
  `db/outils/creer_compte_responsable.ps1` ou l'assistant
  `QuincaillerieFranck_Test/CreerCompteResponsable.exe` du dossier
  d'installation.
- **Mot de passe applicatif** : `db/outils/definir_mot_de_passe_app.sql`
  (jamais exécuté par les migrations, par conception) ; valeur réelle dans
  `server/config.ini`, reconstruite depuis `QuincaillerieFranck_Test/
  config.example.ini`.
- **Durcissement** : mot de passe provisoire imposé à changer à la
  prochaine requête (migration 050) ; anti force brute
  (`tentatives_max_par_minute`, config.ini) ; journalisation
  `journal_comptes`.

## 4. Reconstruire un poste à neuf (procédure de reprise)

1. Prérequis : Windows 10/11, PostgreSQL 17 (portable ou installé), Python
   3.13 + dépendances (`server/requirements.txt`), Node 24 (tests
   Playwright uniquement).
2. Cloner le dépôt ; démarrer PostgreSQL (`db/outils/demarrer_pg.ps1` ou
   service enregistré par `db/outils/enregistrer_service_pg.ps1`).
3. Créer la base et charger le schéma d'origine, puis
   `bash db/outils/migrer.sh appliquer` (000→050), puis le jeu d'essai
   `psql -f db/tests/00_jeu_essai.sql` (base de test seulement).
4. Définir le mot de passe de `qf_app` (`definir_mot_de_passe_app.sql`),
   écrire `server/config.ini` depuis `config.example.ini`.
5. Démarrer l'API : `python -m uvicorn app.main:app --app-dir server
   --port 8010` ; l'interface vit sous `/app/connexion.html`.
6. Pour une livraison bout en bout : `server/fabrication/construire.ps1`
   (produit l'exe + dossier ; trace du dernier build dans
   `server/fabrication/DERNIER_RESULTAT.md`).
7. **Vérifier la reprise** : `bash db/outils/verifier_tout.sh` — le bilan
   consolidé doit être entièrement vert (SQL + pytest + 13 suites) ;
   variante CI : `.github/workflows/ci.yml`.

## 5. Sauvegarde et restauration (résumé opérationnel)

Détail complet, rédigé pour un exploitant non technicien :
[`db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`](db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md).

- `sauvegarder.ps1` : sauvegarde complète (contenu + rôles + logo),
  **chiffrée AES-256**, copie hors poste, purge 30 jours, journalisée.
- `planifier_sauvegarde.ps1` : tâche planifiée Windows, **RPO 1 heure**
  (décision addendum point i), sans session ouverte.
- `restaurer.ps1` : déchiffre et restaure vers une base **séparée** —
  jamais par-dessus une base existante.
- Mot de passe de chiffrement : fourni par le propriétaire (jamais dans le
  dépôt) — voir §7.

## 6. État des travaux, décisions ouvertes, risques résiduels

- **Registre des écarts vivant** : [`REGISTRE_ECARTS_100.md`](REGISTRE_ECARTS_100.md)
  (cycle 66, tenu à jour chaque cycle) — synthèse par gravité, chemins de
  preuve, statuts et responsables.
- **Décisions métier réservées au propriétaire** :
  [`DECISIONS_PROPRIETAIRE.md`](DECISIONS_PROPRIETAIRE.md) (D1–D13 — dont
  visibilité des prix du caissier D1, cumul de rôles D7, attribution
  caisse D9).
- **Journal complet des cycles** : [`RAPPORT AVANCEMENT/loop-state.md`](RAPPORT%20AVANCEMENT/loop-state.md)
  — scores par chantier C0–C14, preuves d'exécution, blocages.
- À la date de ce document : aucun écart d'intégrité/comptabilité/sécurité
  ouvert (P0 = 0) ; le chemin vers 99–100 % se joue sur des décisions
  propriétaire, des validations humaines (campagnes, 2ᵉ poste) et des
  fusions Git.

## 7. Contacts et secrets (à compléter par le propriétaire)

Le dépôt ne contient volontairement aucune donnée nominative ni secret.
Le propriétaire complète et conserve ce tableau **hors dépôt** :

| Rôle | Nom / structure | Coordonnées |
|---|---|---|
| Propriétaire des Ets Quincaillerie Franck (administrateur dépôt GitHub) | *à compléter* | *à compléter* |
| Reprise technique (mainteneur tiers) | *à compléter* | *à compléter* |
| Mot de passe applicatif `qf_app` (production) | *secret — `server/config.ini` du poste serveur* | — |
| Mot de passe de chiffrement des sauvegardes | *secret, détenu par le propriétaire* | — |
| Compte de la tâche planifiée de sauvegarde | *à compléter* | — |

## 8. Documents de référence (ordre de lecture conseillé)

1. [`README.md`](README.md) — vue d'ensemble et livrables CDC §7.
2. [`OWNERSHIP.md`](OWNERSHIP.md) — propriété, accès, réversibilité.
3. [`db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`](db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md) — exploitation réelle.
4. [`RAPPORT AVANCEMENT/loop-state.md`](RAPPORT%20AVANCEMENT/loop-state.md) + [`REGISTRE_ECARTS_100.md`](REGISTRE_ECARTS_100.md) — état et preuves.
5. [`ADDENDUM_CAHIER_DES_CHARGES.md`](ADDENDUM_CAHIER_DES_CHARGES.md) + [`DECISIONS_PROPRIETAIRE.md`](DECISIONS_PROPRIETAIRE.md) — exigences et arbitrages.
6. [`QuincaillerieFranck_Test/GUIDE_TESTEUR_INSTALLATION.txt`](QuincaillerieFranck_Test/GUIDE_TESTEUR_INSTALLATION.txt) — guide de mise en place du poste.
