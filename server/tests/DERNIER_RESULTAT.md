# Dernier résultat d'exécution — suite pytest du serveur

Trace rejouable :

```powershell
.\db\outils\demarrer_pg.ps1
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

---

## Cycle 7 — chantier C7 (inventaire et écarts), 2026-09-12

Migrations 000 à **012** appliquées (nouvelle :
`012_comptage_aveugle_colonnes.sql`).

### `test_inventaire.py` — nouveau, 9/9

```
test_liste_a_compter_ne_contient_aucune_quantite PASSED
test_comptage_ne_renvoie_jamais_quantite_attendue_ni_ecart PASSED
test_agent_stock_ne_peut_pas_lire_ecart_en_sql_direct[ecart] PASSED
test_agent_stock_ne_peut_pas_lire_ecart_en_sql_direct[quantite_attendue] PASSED
test_article_deja_compte_disparait_de_la_liste_et_refuse_un_second_envoi PASSED
test_agent_stock_ne_peut_pas_compter_un_article_de_lautre_site PASSED
test_agent_comptabilite_interdit_sur_linventaire PASSED
test_ecarts_du_jour_reserves_au_responsable PASSED
test_ecarts_ventes_du_jour_relie_c5_et_c7 PASSED
```

Point le plus important, prouvé par exécution : **avant** la migration 012,
`SET ROLE qf_agent_stock; SELECT ecart, quantite_attendue FROM
comptages_stock;` était accepté par PostgreSQL — jamais exploité par aucune
route, mais une faille de confidentialité réelle. Après la migration :
`ERROR: permission denied for table comptages_stock`.

### Suite complète — 53/53, 0 régression

```
53 passed in ~71s
```

### Non-régression SQL du cycle 2, rejouée à jour (`db/tests/executer_tests.sh`)

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 012) : OK
>>> jeu d'essai chargé : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (6/6)
>>> aller / retour des migrations : OK
```

### Vérification bout-en-bout sur les écrans réels (Playwright, `verifier-inventaire-reel.mjs`)

```
12/12 — liste à compter réelle sans quantité, comptage produisant un écart
réel (-8) sans qu'il n'apparaisse dans la page, le code source ou les
réponses réseau observées après rechargement, article compté absent de la
liste au rechargement, tableau de bord affichant l'écart de comptage exact
(-8) et l'écart de vente à découvert exact (manque 2).
```

Non-régression des cycles 5 et 6 (`verifier-cablage.mjs`,
`verifier-vente-reelle.mjs`, tous deux mis à jour pour refléter les écarts
désormais réels au tableau de bord) : **74/74** et **10/10**.

---

## Cycle 6 — chantier C5 (ventes), 2026-09-12

Exécuté avec **Python 3.13.3**, contre **PostgreSQL 17.11** (`_pgdev/`), base
`quincaillerie_test`, migrations 000 à **011** appliquées (nouvelle :
`011_ventes_fiscalite_anti_survente.sql`).

### `test_ventes.py` — nouveau, 8/8

```
test_parametres_vente_expose_le_taux_tva_en_vigueur PASSED
test_vente_normale_decremente_le_stock_et_calcule_la_tva PASSED
test_vente_a_decouvert_nest_jamais_refusee_et_consigne_lecart PASSED
test_credit_client_reste_desactive PASSED
test_agent_stock_ne_peut_pas_enregistrer_de_vente PASSED
test_agent_comptabilite_ne_peut_pas_vendre_pour_lautre_site PASSED
test_responsable_doit_preciser_le_site PASSED
test_responsable_peut_vendre_pour_un_site_precise PASSED
```

Point le plus important, prouvé par exécution : une vente de 5 unités
d'« Article rare » (stock réel : 1) est **acceptée** (201), le stock tombe à
0 (jamais négatif), et un écart de 4 unités est consigné dans
`ecarts_stock_ventes`, réservé au responsable — jamais un refus.

### Suite complète — 44/44, 0 régression

```
44 passed in ~58s
```

### Non-régression SQL du cycle 2, rejouée à jour (`db/tests/executer_tests.sh`)

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 011) : OK
>>> jeu d'essai chargé : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (6/6 — comportement anti-survente, voir 03_concurrence.sh)
>>> aller / retour des migrations : OK
```

### Vérification bout-en-bout sur l'écran réel (Playwright, `verifier-vente-reelle.mjs`)

```
10/10 — vente normale (numéro de vente serveur, plus aucune mention
SIMULATION, aperçu affiché AVANT validation identique au montant confirmé
par le serveur), vente à découvert acceptée avec écart affiché à l'écran,
crédit client absent des options de paiement, responsable bloqué tant qu'il
n'a pas choisi de site.
```

Bug trouvé en écrivant ce contrôle : l'aperçu du total (`majTotaux()` dans
`vente.html`) ajoutait encore la TVA par-dessus le sous-total au lieu de
l'extraire d'un prix déjà TTC (décision d) — corrigé pour utiliser
exactement la même formule que la route.

Non-régression du cycle 5 (`verifier-cablage.mjs`, mis à jour car la
validation de vente n'est plus une confirmation simulée) : **74/74**.

---

## Cycle 3 — chantiers C2, C3, C11

Exécuté le **2026-09-12** avec **Python 3.13.3**, contre **PostgreSQL 17.11**
(`_pgdev/`, cycle 2 stabilisé), base `quincaillerie_test`, migrations 000 à
010 appliquées.

---

## Phase 1 — Diagnostic par exécution, avant d'écrire une route

Deux pièges trouvés et corrigés **avant** d'écrire le code serveur, en
testant chaque brique en SQL direct d'abord :

1. **pgcrypto ne valide pas un hachage `$2b$`** (défaut de la bibliothèque
   Python `bcrypt`). Testé dans les deux sens :
   ```
   crypt('MotDePasseTest123', '$2b$12$...')  -> f  (FAUX même pour le bon mot de passe)
   crypt('MotDePasseTest123', '$2a$12$...')  -> t  (bon mot de passe)
   crypt('MauvaisMotDePasse', '$2a$12$...')  -> f  (mauvais mot de passe)
   ```
   → `securite.hacher_mot_de_passe()` génère toujours avec `prefix=b"2a"`.

2. **`qf_app` ne pouvait exécuter aucune fonction** :
   ```
   ERROR: function verifier_connexion(...) does not exist   -- sous qf_app
   -- la même requête, identique, réussit sous postgres
   ```
   Cause : `USAGE ON SCHEMA public` jamais accordé à `qf_app` (migration 008).
   → migration **010** (corrective, 008 non modifiée rétroactivement).

## Phase 4 — Vérification par exécution

### Fonctions d'authentification, testées directement en SQL avant tout code Python

```
--- bon mot de passe ---
ok | utilisateur_id | nom_complet | role        | doit_changer_mot_de_passe
t  | 1              | Awa Franck  | responsable | t

--- verrouillage après 5 échecs ---
essai 1 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 2 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 3 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 4 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 5 (mauvais mdp) : f | compte_verrouille
6e essai (BON mdp)    : f | compte_verrouille   <- refusé même avec le bon mot de passe
après déverrouillage  : t |  (bon mot de passe accepté de nouveau)

--- libre-service, limité à sa propre ligne ---
changer_mon_mot_de_passe('AgentTest123', '$2a$...')      -> t (bon mdp actuel)
rejoué avec l'ANCIEN mdp                                  -> f (plus valide)
avec un mauvais mdp actuel dès le départ (autre compte)   -> f
```

### Suite pytest — 36 / 36

```
tests/test_authentification.py::test_connexion_reussie PASSED
tests/test_authentification.py::test_connexion_mot_de_passe_incorrect PASSED
tests/test_authentification.py::test_connexion_identifiant_inconnu PASSED
tests/test_authentification.py::test_verrouillage_apres_echecs_repetes PASSED
tests/test_authentification.py::test_compte_desactive_ne_peut_pas_se_connecter PASSED
tests/test_authentification.py::test_deverrouillage_par_le_responsable PASSED
tests/test_authentification.py::test_deverrouillage_refuse_a_un_agent PASSED
tests/test_authentification.py::test_limitation_de_debit_sur_la_connexion PASSED
tests/test_authentification.py::test_changement_mot_de_passe_a_la_premiere_connexion PASSED
tests/test_authentification.py::test_changement_mot_de_passe_refuse_si_actuel_incorrect PASSED
tests/test_authentification.py::test_un_agent_ne_peut_changer_que_son_propre_mot_de_passe PASSED
tests/test_cloisonnement_site.py::test_agent_ignore_le_site_fourni_en_parametre_de_requete PASSED
tests/test_cloisonnement_site.py::test_rls_bloque_meme_en_sql_direct_hors_de_lapi PASSED
tests/test_cloisonnement_site.py::test_rls_laisse_le_responsable_voir_les_deux_sites_en_sql_direct PASSED
tests/test_cloisonnement_site.py::test_agent_comptoir_ne_voit_pas_les_ventes_du_magasin PASSED
tests/test_habilitations.py::test_agent_stock_ne_voit_aucun_prix PASSED
tests/test_habilitations.py::test_agent_comptabilite_ne_voit_aucune_quantite PASSED
tests/test_habilitations.py::test_responsable_voit_tout PASSED
tests/test_habilitations.py::test_responsable_voit_les_deux_sites PASSED
tests/test_habilitations.py::test_agent_stock_ne_voit_que_son_site PASSED
tests/test_habilitations.py::test_agent_comptabilite_ne_voit_que_son_site PASSED
tests/test_habilitations.py::test_agent_stock_interdit_sur_synthese_ventes PASSED
tests/test_habilitations.py::test_comptabilite_et_responsable_autorises_sur_synthese_ventes PASSED
tests/test_habilitations.py::test_profil_ne_renvoie_jamais_de_hachage PASSED
tests/test_habilitations.py::test_aucune_route_accessible_sans_jeton PASSED
tests/test_habilitations.py::test_jeton_invalide_refuse PASSED
tests/test_habilitations.py::test_jeton_falsifie_refuse PASSED
tests/test_securite.py::test_reponse_de_connexion_ne_contient_jamais_de_hachage PASSED
tests/test_securite.py::test_reponses_articles_et_profil_ne_contiennent_jamais_de_hachage PASSED
tests/test_securite.py::test_config_refuse_le_compte_superutilisateur PASSED
tests/test_securite.py::test_config_refuse_la_cle_secrete_exemple PASSED
tests/test_securite.py::test_mot_de_passe_en_clair_jamais_ecrit_dans_le_code_serveur PASSED
tests/test_securite.py::test_hachage_genere_par_le_serveur_est_verifiable_par_pgcrypto PASSED
tests/test_securite.py::test_jeton_expire_est_refuse PASSED
tests/test_securite.py::test_jeton_signe_avec_une_autre_cle_est_refuse PASSED
tests/test_securite.py::test_injection_sql_dans_lidentifiant_ne_casse_rien PASSED

36 passed in 47.49s
```

### Preuve la plus forte du chantier C3 — RLS en SQL direct, hors API

```sql
BEGIN;
SET LOCAL ROLE qf_agent_stock;
SELECT set_config('qf.site_id', '1', true);
SELECT id, nom, site_id FROM articles WHERE site_id = 2;   -- demande EXPLICITEMENT l'autre site
```
```
 id | nom | site_id
----+-----+---------
(0 ligne)
```
```sql
SELECT id, nom, site_id FROM articles;                      -- sans aucun filtre
```
```
 id |         nom         | site_id
----+---------------------+---------
  1 | Ciment CIM II 50 kg |       1
  2 | Fer à béton 8 mm    |       1
  4 | Article rare        |       1
```

Même en demandant explicitement `WHERE site_id = 2`, PostgreSQL renvoie
**zéro ligne** — la RLS filtre avant même que le `WHERE` du client ne
s'applique. Aucun code applicatif n'est impliqué dans ce test.

### Parcours HTTP bout-en-bout (démarrage réel d'uvicorn, requêtes `curl`)

```
POST /auth/connexion {"identifiant":"resp","mot_de_passe":"ResponsableTest123"}
-> 200 {"jeton":"...","role":"responsable","site_id":null,...}

GET /articles (agent stock, Magasin)
-> 200 {"articles":[{"id":1,"nom":"Ciment CIM II 50 kg","unite":"sac","quantite_stock":30,"seuil_alerte":6,"site_id":1}, ...]}
   (aucun champ prix_achat / prix_vente ; site_id toujours 1)

GET /articles (agent comptabilité, Magasin)
-> 200 {"articles":[{"id":1,"nom":"Ciment CIM II 50 kg","unite":"sac","prix_vente":6500.0,"site_id":1}, ...]}
   (aucun champ quantite_stock / seuil_alerte)

GET /ventes/synthese-jour (agent stock)
-> 403 {"detail":"Rôle non autorisé pour cette route."}

GET /moi (sans jeton)
-> 401 {"detail":"Jeton manquant."}

POST /auth/connexion {"identifiant":"x' OR '1'='1","mot_de_passe":"peu importe"}
-> 401 {"detail":"Identifiant ou mot de passe incorrect."}   (aucune erreur serveur, injection neutralisée)
```

---

## Non-régression du cycle 2

Les migrations 009 et 010 ajoutées ce cycle n'ont rien cassé : la suite
complète du cycle 2 a été rejouée après leur ajout.

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées          : OK
>>> jeu d'essai chargé             : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (4/4)
>>> aller / retour des migrations  : OK
Toutes les étapes sont passées.
```

Différences après aller-retour des migrations (000 à 010) : les 2 déjà
documentées (`db/README.md`) + l'extension `pgcrypto` conservée (comme
`pg_trgm`), sans effet de bord.

---

## Bilan

**136 contrôles au total pour ce cycle** (44 + 52 + 4 hérités du cycle 2,
rejoués sans régression, + 36 nouveaux pour C2/C3/C11), **0 échec**.
