# Base de données — migrations, outils et tests (chantier C1)

Le schéma d'origine (`QuincaillerieFranck_Test/creation_base_donnees.sql`) est
**conservé tel quel** : c'est le point de départ. Tout ce qui suit le **corrige**
par migrations successives, jamais en le remplaçant.

```
db/
├── migrations/   NNN_nom.sql + NNN_nom_inverse.sql, appliquées dans l'ordre
├── outils/       migrer.sh, prevol.sql, definir_mot_de_passe_app.sql
└── tests/        vérification PAR EXÉCUTION (protections, habilitations, concurrence)
```

---

## Appliquer les migrations

```bash
export PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGDATABASE=quincaillerie
export PGPASSWORD=...            # jamais dans le dépôt

# 1. Sur une base contenant DÉJÀ des données : vérifier ce qui bloquerait
psql -f db/outils/prevol.sql     # toute ligne avec nb_lignes > 0 est à traiter

# 2. Appliquer
db/outils/migrer.sh appliquer

# 3. Voir l'état
db/outils/migrer.sh etat

# 4. Revenir en arrière si besoin
db/outils/migrer.sh annuler
```

Chaque fichier est exécuté **dans une transaction unique** avec `ON_ERROR_STOP` :
une migration passe en entier, ou pas du tout. La table `schema_migrations`
enregistre ce qui est appliqué.

### Mot de passe du compte applicatif

Il n'est **jamais** dans le dépôt :

```bash
psql -v mdp="'LeMotDePasseChoisi'" -f db/outils/definir_mot_de_passe_app.sql
```

Puis reporter la valeur dans `config.ini` (fichier local, non versionné), avec
`user = qf_app`. **Ne plus jamais faire tourner l'application sous `postgres`.**

---

## Ce que chaque migration corrige

| # | Migration | Ce qu'elle rend impossible |
|---|-----------|----------------------------|
| 000 | `socle_migrations` | (socle) toute évolution de schéma non tracée |
| 001 | `contraintes_domaine` | stock négatif, prix négatif, quantité vendue ≤ 0, TVA à 500 %, total ≠ sous-total + TVA, ticket numéroté, vente « payée » sans caissier, agent sans site, congé finissant avant de commencer |
| 002 | `coherence_inter_tables` | vendre au Comptoir un article du Magasin ; compter deux fois la recette d'une même vente |
| 003 | `ecart_inventaire_calcule` | **écrire soi-même l'écart d'inventaire**, forger la quantité attendue, modifier un comptage après coup, recompter jusqu'à tomber juste |
| 004 | `audit_non_destructible` | effacer l'historique de prix en supprimant l'article, supprimer une ligne de journal, supprimer une vente |
| 005 | `journaux_audit` | annuler une vente sans laisser de trace, l'annuler deux fois, antidater l'annulation, « dé-encaisser » une vente |
| 006 | `parametres_applicatifs` | écrire un taux de TVA en dur ; **appliquer en silence une règle fiscale non tranchée** |
| 007 | `index_recherche` | (performance) la recherche d'article par balayage complet |
| 008 | `roles_applicatifs` | se connecter en superutilisateur ; qu'un agent stock LISE un prix ; qu'un comptable LISE une quantité en stock ; que quiconque modifie le seuil d'alerte à la main |

---

## Droits accordés — qui peut lire et écrire quoi

Quatre rôles PostgreSQL, **aucun superutilisateur**, aucun droit de modifier le
schéma (pas de `CREATE` sur le schéma `public`).

| Rôle | Nature | Usage |
|------|--------|-------|
| `qf_app` | connexion (`LOGIN`), **`NOINHERIT`** | seul rôle qui se connecte. Aucun droit propre : le serveur fait `SET ROLE` vers le rôle de l'utilisateur authentifié, puis `RESET ROLE`. |
| `qf_responsable` | `NOLOGIN` | les deux sites |
| `qf_agent_stock` | `NOLOGIN` | un site, **aucun prix** |
| `qf_agent_comptabilite` | `NOLOGIN` | un site, **aucune quantité en stock** |

### Table `articles`

| Colonne | responsable | agent stock | agent comptabilité |
|---|---|---|---|
| `id`, `nom`, `categorie`, `unite`, `site_id`, `fournisseur_id` | lire / écrire | lire / écrire¹ | **lire** |
| `prix_achat`, `prix_vente` | lire / écrire | — **aucun accès** | `prix_vente` en lecture seule ; `prix_achat` **aucun accès** |
| `quantite_stock` | lire / écrire | lire / écrire | — **aucun accès** |
| `seuil_alerte` | **lecture seule** | **lecture seule** | — **aucun accès** |
| `actif`, `date_desactivation`, `desactive_par_id` | lire / écrire | lire | lire |

¹ l'agent stock écrit `nom`, `categorie`, `unite`, `quantite_stock` ; il crée un
article **sans prix** (`prix_vente` prend son défaut à 0, le responsable le fixe
ensuite).

> **`seuil_alerte` n'est écrit par personne.** Le cahier des charges §4.2 l'exige :
> « le seuil d'alerte ne peut être modifié par personne directement, afin qu'il
> ne puisse pas servir à dissimuler un vol de marchandise ». Il est recalculé par
> `enregistrer_entree_stock()`, à 20 % de la quantité reçue, **uniquement lors
> d'une entrée de stock**.

### Table `utilisateurs`

| Colonne | responsable | agents |
|---|---|---|
| `mot_de_passe_hash` | **écriture seule** (créer un compte, réinitialiser) — jamais en lecture | **aucun accès** |
| `nom_complet`, `identifiant`, `role`, `site_id`, `actif`, `tentatives_echouees`, `doit_changer_mot_de_passe` | lire / écrire | lire |

> Aucun rôle ne peut **lire** un hachage de mot de passe. La vérification à la
> connexion passera par une fonction dédiée exécutée avec les droits de son
> propriétaire — chantier **C2, cycle 3**.

### Autres tables

| Table | responsable | agent stock | agent comptabilité |
|---|---|---|---|
| `sites`, `parametres` | lire (+ écrire `parametres.valeur`) | lire | lire |
| `fournisseurs` | lire / écrire | lire | lire |
| `ventes`, `ventes_lignes` | lire / écrire | — | lire / écrire |
| `transactions` | lire / écrire | — | lire / ajouter |
| `employes` | lire / écrire | — | `id`, `nom_complet`, `poste`, `site_id`, `actif` en lecture (**pas le salaire**) |
| `absences_conges`, `avances_salaire` | lire / écrire | — | — |
| `mouvements_stock` | lire / écrire | lire / ajouter | — |
| `comptages_stock` | lire / ajouter | lire / ajouter | — |
| `historique_prix_articles` | lire / ajouter | — | — |
| `historique_modifications_articles` | lire / ajouter | lire / ajouter | — |
| `journal_connexions`, `journal_comptes` | lire / ajouter | — | — |
| `comptages_stock_ecarts_declares`, `historique_parametres` | lire | — | — |

Aucun rôle n'a `DELETE` sur quoi que ce soit, ni `TRUNCATE`, ni le moindre droit
de DDL.

### Fonctions de pont (exécutées avec les droits de leur propriétaire)

| Fonction | Qui peut l'appeler | Pourquoi elle existe |
|---|---|---|
| `enregistrer_entree_stock(article, quantité, utilisateur, motif)` | responsable, agent stock | seule voie d'entrée de stock ; recalcule le seuil d'alerte, que personne ne peut écrire |
| `decrementer_stock_vente(article, quantité, utilisateur, motif)` | responsable, agent comptabilité | la comptabilité doit faire baisser le stock **sans avoir le droit d'y toucher ni même de le lire** ; décrément atomique et sérialisé |
| `parametre_texte(clé)` / `parametre_numerique(clé)` | les trois rôles | lecture d'un réglage ; **refuse** de livrer une valeur encore `a_definir` |
| `qf_site_courant()` | les trois rôles | site de l'utilisateur, pour le cloisonnement |

### Cloisonnement par site

`Row Level Security` sur `articles`, `ventes`, `transactions`,
`mouvements_stock` et `comptages_stock`. Le serveur positionne, pour la durée de
la requête :

```sql
SET LOCAL qf.site_id = '2';   -- Comptoir
```

Un agent ne voit alors que les lignes de son site ; le responsable voit les deux.
Ce socle sera exploité et testé plus largement au **cycle 3 (chantier C3)**.

---

## Décisions métier volontairement NON prises

La base **refuse d'inventer** ce que le propriétaire n'a pas tranché. Les
réglages concernés valent `a_definir` et `parametre_texte()` lève une erreur
explicite si l'application tente de les utiliser :

```sql
SELECT * FROM parametres_a_decider;   -- doit être vide avant la mise en production
```

| Paramètre | Décision attendue |
|---|---|
| `regime_fiscal`, `prix_saisis_ttc`, `arrondi_montants`, `boutique_numero_contribuable` | addendum, **point d** (fiscalité) |
| `taux_tva` | vaut **0** : l'application fonctionne sans aucune TVA, ce qui est un choix valide et non une valeur devinée |
| `seuil_alerte_plancher`, `tentatives_max_connexion` | valeurs proposées, à confirmer |
| `duree_session_minutes` | règle de session inactive à définir |

De même, `decrementer_stock_vente()` **signale** un stock insuffisant avec la
quantité réellement disponible, mais ne décide pas de ce que l'application doit
en faire (refuser la saisie, ou l'accepter avec un écart à régulariser) : c'est
l'**addendum, point e**, qui reste ouvert.

Enfin, la suppression d'une recette liée à une vente annulée n'est pas
verrouillée : le traitement comptable d'une annulation (suppression ou
contre-passation) relève de l'**addendum, points b et g**.

---

## Tests — vérification par exécution

```bash
export PGHOST=... PGPORT=... PGUSER=postgres PGPASSWORD=...
bash db/tests/executer_tests.sh
```

Le script recrée une base de test à partir du schéma d'origine, applique les
migrations, puis enchaîne :

| Fichier | Ce qu'il prouve |
|---|---|
| `00_jeu_essai.sql` | deux sites, les cinq comptes réels, quatre articles dont un à stock = 1 |
| `01_protections.sql` | **44** contrôles : chaque écriture aberrante est refusée par la base |
| `02_habilitations.sql` | **52** contrôles : les colonnes interdites sont refusées par PostgreSQL, pas seulement masquées par l'interface |
| `03_concurrence.sh` | **4** contrôles, deux sessions simultanées : une seule vente aboutit, le stock tombe à 0 sans jamais devenir négatif, un seul mouvement enregistré |
| (étape 7) | les migrations inverses ramènent le schéma à son état d'origine |

Un test qui « passe » signifie le plus souvent : **la base a bien dit non**.

### Piège à éviter en écrivant un test

- Ne jamais utiliser `1/0` comme sentinelle dans un `CASE` : PostgreSQL replie
  les constantes au moment de la planification et lève une division par zéro
  même dans la branche non prise. Utiliser les fonctions `t_valeur` / `d_valeur`.
- Ne jamais insérer puis supprimer dans la **même** instruction (`WITH x AS
  (INSERT …) DELETE …`) : le `DELETE` ne voit pas la ligne insérée, supprime 0
  ligne, et le déclencheur testé ne se déclenche jamais.

### Migrations inverses — différences attendues après aller-retour

Le script compare le schéma d'origine à celui obtenu après *appliquer* puis
*annuler*. Deux différences subsistent, connues et documentées :

1. **`comptages_stock.ecart` passe en dernière position.** La migration 003
   supprime la colonne pour la recréer en colonne générée ; l'inverse la
   reconstruit en colonne ordinaire, donc en fin de table. Le type, la
   contrainte `NOT NULL` et les valeurs sont identiques.
2. **L'extension `pg_trgm` reste installée.** La migration 007 inverse ne la
   retire volontairement pas : elle peut servir ailleurs et sa présence est sans
   effet de bord.

Un point d'exploitation à connaître : **les rôles PostgreSQL sont globaux au
serveur**, pas propres à une base. Si les rôles `qf_*` servent à une autre base
du même serveur, l'annulation retire tous leurs droits dans la base courante
mais conserve les rôles, en le signalant.
