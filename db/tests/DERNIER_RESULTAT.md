# Dernier résultat d'exécution — chantier C1 (cycle 2)

Exécuté le **2026-09-11** sur **PostgreSQL 17.11**, base `quincaillerie_test`
recréée à partir de `QuincaillerieFranck_Test/creation_base_donnees.sql`.

Trace rejouable : `bash db/tests/executer_tests.sh`.

---

## Stabilisation de l'environnement (2026-09-12)

Le serveur de développement tournait initialement dans le dossier temporaire
de la session Windows (`%TEMP%\...`), purgeable à tout moment. Il a été
**déplacé** vers `_pgdev\` (à la racine du dépôt, hors Git — voir
`.gitignore`), avec deux scripts PowerShell pour le piloter sans connaître
PostgreSQL : `db/outils/demarrer_pg.ps1` et `db/outils/arreter_pg.ps1`.

Vérifications faites par exécution réelle :

1. **Arrêt propre** de l'ancien serveur (`pg_ctl -m fast stop`), puis copie des
   binaires et du répertoire de données vers `_pgdev\`.
2. **`demarrer_pg.ps1`** exécuté depuis le nouvel emplacement : détecte les
   binaires et les données déjà présents (pas de re-téléchargement, pas de
   re-`initdb`), démarre le serveur, `pg_isready` confirme `127.0.0.1:5433`
   opérationnel.
3. **Idempotence testée** : `arreter_pg.ps1` sur un serveur déjà arrêté →
   « rien à arrêter » (code 0) ; `demarrer_pg.ps1` sur un serveur déjà démarré →
   « rien à faire » (code 0). Cycle arrêt → démarrage → re-démarrage rejoué en
   direct, sans erreur.
4. **Les 100 contrôles du cycle 2 ont été rejoués depuis `_pgdev\`** via
   `bash db/tests/executer_tests.sh` :

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

   **100 contrôles, 0 échec — identique au résultat du cycle 2, depuis le
   nouvel emplacement durable.**
5. L'ancien dossier temporaire (**1,3 Go**) a été supprimé après vérification
   que tout fonctionnait depuis `_pgdev\`.

**Piège rencontré et corrigé** : les deux scripts, écrits une première fois
avec des caractères accentués et un tiret cadratin en UTF-8 sans BOM, ont fait
échouer le parseur de Windows PowerShell 5.1 (guillemets courbes fabriqués par
un mauvais décodage, parenthèse qui semblait manquante). Réécrits en **ASCII
pur** : plus aucun risque d'encodage, quel que soit le poste. Voir la note en
tête de `demarrer_pg.ps1`.

---

## Phase 1 — Diagnostic sur le schéma d'ORIGINE (avant migrations)

`db/tests/diagnostic_schema_origine.sql` — chaque ligne est une écriture
aberrante qui a été **ACCEPTÉE** par la base d'origine :

| Tentative | Résultat obtenu |
|---|---|
| `quantite_stock = -50` | accepté → **stock négatif** |
| `prix_vente = -999` | accepté → **prix négatif** |
| ligne de vente `quantite = -5` | accepté |
| comptage « attendu 10, compté 3, **écart déclaré 0** » | accepté → **7 sacs disparus, écart invisible** |
| vente `1 + 1 = 999999` | accepté → **facture aux montants arbitraires** |
| `taux_tva = 500` | accepté |
| `agent_stock` avec `site_id = NULL` | accepté → cloisonnement inopérant |
| suppression d'un article | historique de prix : **1 ligne → 0** (effacé par `ON DELETE CASCADE`) |
| 2 recettes pour 1 vente | accepté → **double comptage du chiffre d'affaires** |
| vente site 1 avec article site 2 | accepté |
| `seuil_alerte = 0` en direct | accepté → **dissimulation de vol possible** |
| congé `2026-12-31 → 2026-01-01` | accepté |

Et par ailleurs :

| Recherche | Résultat |
|---|---|
| tables de journal / audit | **0** |
| table de paramètres | **0** |
| déclencheurs | **0** |
| colonnes générées | **0** |
| rôles non superutilisateurs | **aucun** — seul `postgres`, superutilisateur |
| contraintes `CHECK` métier | 9 (uniquement les listes de valeurs : rôle, statut, type…) |

---

## Phase 4 — Vérification après migrations

### Migrations appliquées — 9/9

```
 version |           nom
---------+--------------------------
 000     | socle_migrations
 001     | contraintes_domaine
 002     | coherence_inter_tables
 003     | ecart_inventaire_calcule
 004     | audit_non_destructible
 005     | journaux_audit
 006     | parametres_applicatifs
 007     | index_recherche
 008     | roles_applicatifs
```

### `01_protections.sql` — 44 / 44

Extraits significatifs (la base **refuse** désormais) :

```
17 | [ok] | 003 · écriture directe de l'écart d'inventaire         | refusé : cannot insert a non-DEFAULT value into column "ecart"
18 | [ok] | 003 · quantité attendue forgée par le client → ignorée | 30
19 | [ok] | 003 · écart réellement calculé par la base             | -5
20 | [ok] | 003 · modification d'un comptage déjà enregistré       | refusé : Un comptage d'inventaire ne se modifie pas.
21 | [ok] | 003 · deuxième comptage même article / moment / jour   | refusé : duplicate key value violates unique constraint
23 | [ok] | 004 · suppression d'un article ayant un historique     | refusé : violates foreign key constraint "fk_historique_prix_article"
24 | [ok] | 004 · suppression d'une ligne d'historique de prix     | refusé : La table « historique_prix_articles » est un journal
29 | [ok] | 002 · vente du Magasin contenant un article du Comptoir| refusé : violates foreign key constraint "fk_ventes_lignes_article_site"
31 | [ok] | 002 · deuxième recette pour la même vente              | refusé : duplicate key value violates unique constraint
34 | [ok] | 005 · retour en arrière d'une vente payée              | refusé : Passage de statut « payee » vers « en_attente » interdit
36 | [ok] | 005 · seconde annulation de la même vente              | refusé : Vente 900 déjà annulée le …
39 | [ok] | 005 · date d'annulation non antidatable                | true
40 | [ok] | 006 · lecture d'un paramètre non tranché (régime fiscal)| refusé : Paramètre « regime_fiscal » non tranché par le propriétaire
41 | [ok] | 006 · taux de TVA lisible et nul (appli sans TVA)      | 0
```

Le test n° 18 est le plus important du cycle : le client a envoyé une quantité
attendue de **999** alors que le stock réel était de **30**. La base a **ignoré**
la valeur envoyée, retenu 30, et calculé l'écart réel **−5**.

```
 reussis | echecs | total
      44 |      0 |    44
```

### `02_habilitations.sql` — 52 / 52

```
 1 | [ok] | qf_agent_stock        | lire le prix de vente d'un article       | refusé : permission denied for table articles
 3 | [ok] | qf_agent_stock        | lire toutes les colonnes (SELECT *)      | refusé : permission denied for table articles
16 | [ok] | qf_agent_stock        | seuil d'alerte recalculé (20 % de 50)    | 10 (attendu 10)
17 | [ok] | qf_agent_stock        | aucun article d'un autre site visible    | 0 (attendu 0)
19 | [ok] | qf_agent_comptabilite | lire la quantité en stock                | refusé : permission denied for table articles
25 | [ok] | qf_agent_comptabilite | écrire directement dans le stock         | refusé : permission denied for table articles
31 | [ok] | qf_agent_comptabilite | décrémenter le stock via la fonction     | accepté
34 | [ok] | qf_responsable        | voir les DEUX sites (vue consolidée)     | 2 (attendu 2)
38 | [ok] | qf_responsable        | lire un hachage de mot de passe          | refusé : permission denied for table utilisateurs
39 | [ok] | qf_responsable        | modifier le seuil d'alerte à la main     | refusé : permission denied for table articles
41 | [ok] | qf_responsable        | créer une table (DDL)                    | refusé : permission denied for schema public
44 | [ok] | qf_responsable        | n'est pas superutilisateur               | non superutilisateur
52 | [ok] | qf_app                | NOINHERIT (doit basculer par SET ROLE)   | n'hérite pas
```

```
 reussis | echecs | total
      52 |      0 |    52
```

> Deux vraies failles ont été **trouvées par ces tests** et corrigées pendant le
> cycle : le responsable pouvait lire un hachage de mot de passe et modifier le
> seuil d'alerte à la main (un `GRANT` au niveau table écrasait les restrictions
> de colonne). Les droits du responsable sont désormais accordés colonne par
> colonne.

### `03_concurrence.sh` — 4 / 4

Article à stock = 1, deux sessions PostgreSQL simultanées :

```
----- Poste A (code de sortie 0) -----
 stock_apres_a
             0
COMMIT
----- Poste B (code de sortie 3) -----
ERROR:  Stock insuffisant pour l'article 4 : 1 demandé(s), 0 disponible(s).
ASTUCE : Traitement à trancher — addendum, point e.

stock final                  : 0
mouvements de sortie ajoutés : 1

[ok] une seule des deux ventes aboutit (= oui)
[ok] le stock n'est jamais négatif, il tombe à 0 (= 0)
[ok] un seul mouvement de sortie enregistré (= 1)
[ok] la session perdante reçoit « stock insuffisant » (= oui)
```

Le poste B a **attendu** le verrou du poste A (3 secondes), puis constaté un
stock à 0. Aucune survente n'est possible.

### Migrations inverses — schéma restauré

```
>>> aller  (migrations appliquées) : OK
>>> retour (migrations annulées)   : OK
```

Différences après aller-retour : **2 écarts, connus et documentés**
(`db/README.md`, section « migrations inverses ») —

1. `comptages_stock.ecart` se retrouve en dernière position (la colonne est
   supprimée puis recréée) ; type, `NOT NULL` et valeurs identiques ;
2. l'extension `pg_trgm` reste installée (volontaire).

Aucune autre différence : toutes les contraintes, clés étrangères,
déclencheurs, index, tables et rôles ajoutés ont bien été retirés.

---

## Bilan (cycle 2)

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées          : OK
>>> jeu d'essai chargé             : OK
>>> protections                    : OK   (44/44)
>>> habilitations                  : OK   (52/52)
>>> concurrence                    : OK   (4/4)
>>> aller / retour des migrations  : OK
Toutes les étapes sont passées.
```

---

## Cycle 6 — chantier C5 (ventes), 2026-09-12

Migrations 000 à **011** (`011_ventes_fiscalite_anti_survente.sql`, décisions
du propriétaire — addendum points b/d/e). Deux fichiers mis à jour pour
rester exacts :

- `01_protections.sql` utilisait `regime_fiscal`/`taux_tva` comme exemples
  d'un paramètre « non tranché » — désormais faux (point d décidé). Basculé
  sur `duree_session_minutes`, toujours réellement indécis.
- `03_concurrence.sh` attendait qu'une des deux ventes concurrentes soit
  **refusée** — comportement abandonné (point e décidé : jamais de blocage).
  Réécrit pour vérifier le NOUVEAU contrat : les deux ventes réussissent,
  une seule marchandise réelle sort, un seul écart d'1 unité est consigné.

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 011) : OK
>>> jeu d'essai chargé             : OK
>>> protections                    : OK   (44/44)
>>> habilitations                  : OK   (52/52)
>>> concurrence                    : OK   (6/6 — anti-survente, plus de « perdante »)
>>> aller / retour des migrations  : OK
Toutes les étapes sont passées.
```

**100 contrôles exécutés, 0 échec.**

---

## Cycle 7 — chantier C7 (inventaire et écarts), 2026-09-12

Migrations 000 à **012** (`012_comptage_aveugle_colonnes.sql`) : retire le
`SELECT` sans restriction de colonne accordé à `qf_agent_stock` sur
`comptages_stock` (migration 008) — `ecart` et `quantite_attendue`
désormais illisibles pour ce rôle, comme les prix d'`articles`. Aucun
fichier de test SQL à modifier : ni `01_protections.sql` (exécuté comme
superutilisateur, jamais affecté par un `GRANT`), ni `02_habilitations.sql`
(le seul comptage y est un `INSERT`, jamais un `SELECT` de ces colonnes).

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 012) : OK
>>> jeu d'essai chargé             : OK
>>> protections                    : OK   (44/44)
>>> habilitations                  : OK   (52/52)
>>> concurrence                    : OK   (6/6)
>>> aller / retour des migrations  : OK
Toutes les étapes sont passées.
```

**100 contrôles exécutés, 0 échec** — inchangé, migration 012 vérifiée
séparément par `server/tests/test_inventaire.py` (voir
`server/tests/DERNIER_RESULTAT.md`).

---

## Cycle de correction après le cycle 7, 2026-09-12

Migration 000 à **013** (`013_fuseau_horaire_boutique.sql`) : fixe le
fuseau au niveau de la base (`ALTER DATABASE ... SET timezone`), trouvé
faux (`Europe/Paris`) lors d'un contrôle de boucle — voir
`RAPPORT AVANCEMENT/loop-state.md` et `db/README.md`, section
« Fuseau horaire ». Aucun fichier de test SQL à modifier : ni
`01_protections.sql` ni `02_habilitations.sql` ne dépendent du fuseau.

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 013) : OK
>>> jeu d'essai chargé             : OK
>>> protections                    : OK   (44/44)
>>> habilitations                  : OK   (52/52)
>>> concurrence                    : OK   (6/6)
>>> aller / retour des migrations  : OK
Toutes les étapes sont passées.
```

**100 contrôles exécutés, 0 échec** — inchangé. Vérification directe du
fuseau (fraîche connexion) : `SHOW TimeZone` renvoie `Africa/Douala`.

---

## Cycle 9 — chantier C4 (articles et stock), 2026-09-13

Migration 000 à **014** (`014_articles_stock_transferts_retours.sql`) :
transfert inter-sites, casse, retours client/fournisseur (addendum,
points a et f). `01_protections.sql` corrigé : deux `INSERT INTO
mouvements_stock` directs sans `categorie` (désormais `NOT NULL`)
faisaient échouer le script en entier avant correction.

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 014) : OK
>>> jeu d'essai chargé             : OK
>>> protections                    : OK   (44/44)
>>> habilitations                  : OK   (52/52)
>>> concurrence                    : OK   (6/6)
>>> aller / retour des migrations  : OK
Toutes les étapes sont passées.
```

**100 contrôles exécutés, 0 échec** — inchangé (aucun nouveau contrôle
ajouté à ces fichiers ; les 18 nouveaux contrôles de C4 vivent dans
`server/tests/test_articles.py`/`test_stock.py`, voir
`server/tests/DERNIER_RESULTAT.md`).

Trois failles trouvées par exécution en écrivant les fonctions de ce cycle
(détail complet dans `server/tests/DERNIER_RESULTAT.md` et
`db/README.md`) : `enregistrer_entree_stock()` (cycle 2),
`enregistrer_retour_client()` et `enregistrer_retour_fournisseur()` (ce
cycle) ne vérifiaient aucun site avant d'agir sur le stock — jamais
exploitable tant qu'aucune route ne les appelait, corrigé en les exposant.
