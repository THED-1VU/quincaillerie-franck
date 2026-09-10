# Rétro-spécification du modèle de données — Ets Quincaillerie Franck

Source unique : `QuincaillerieFranck_Test/creation_base_donnees.sql` (PostgreSQL).
Ce document décrit le schéma **tel qu'il existe**, puis l'évalue de façon critique.
Le schéma n'est pas jeté : il sert de point de départ à la reconstruction, on le corrige.

---

## 1. Vue d'ensemble

| # | Table | Rôle métier | Lignes attendues |
|---|-------|-------------|------------------|
| 1 | `sites` | Les deux emplacements physiques | 2 (figées) |
| 2 | `utilisateurs` | Comptes de connexion + rôle + site | ≤ 5 en usage courant |
| 3 | `fournisseurs` | Carnet fournisseurs | dizaines |
| 4 | `articles` | Catalogue, rattaché à un seul site | dizaines à centaines |
| 5 | `mouvements_stock` | Journal entrées / sorties de stock | milliers / an |
| 6 | `historique_prix_articles` | Audit des changements de prix achat/vente | centaines |
| 7 | `historique_modifications_articles` | Audit des changements nom / unité / seuil | centaines |
| 8 | `ventes` | En-tête de vente (ticket ou facture) | milliers / an |
| 9 | `ventes_lignes` | Détail des articles d'une vente | milliers / an |
| 10 | `transactions` | Recettes et dépenses comptables | milliers / an |
| 11 | `employes` | Fiches RH | dizaines |
| 12 | `absences_conges` | Absences et congés | centaines |
| 13 | `avances_salaire` | Avances sur salaire, remboursées ou non | centaines |
| 14 | `comptages_stock` | Inventaire physique matin / soir, à l'aveugle | milliers / an |

**Séquences** : une séquence implicite par colonne `SERIAL` (`sites_id_seq`, `utilisateurs_id_seq`, … `comptages_stock_id_seq`), soit 14 séquences.
**Déclencheurs (triggers)** : **aucun**.
**Vues** : **aucune**.
**Row-Level Security** : **aucune** politique définie.
**Extensions** : aucune (`pgcrypto`, `citext`, etc. non utilisées).
**Tables d'audit** : `historique_prix_articles`, `historique_modifications_articles` (partiel), et par nature `mouvements_stock` + `comptages_stock`.

---

## 2. Détail des tables

### 2.1 `sites`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `nom` | VARCHAR(100) | NOT NULL, **UNIQUE** |

Données d'amorçage insérées inconditionnellement : `('Magasin de stock'), ('Comptoir')`.
Pas de `ON CONFLICT` → **le script n'est pas ré-exécutable** sans erreur.

### 2.2 `utilisateurs`
| Colonne | Type | Contraintes / défaut |
|---|---|---|
| `id` | SERIAL | **PK** |
| `nom_complet` | VARCHAR(150) | NOT NULL |
| `identifiant` | VARCHAR(50) | NOT NULL, **UNIQUE** |
| `mot_de_passe_hash` | VARCHAR(255) | NOT NULL (bcrypt attendu) |
| `role` | VARCHAR(30) | NOT NULL, **CHECK** `role IN ('responsable','agent_stock','agent_comptabilite')` |
| `site_id` | INTEGER | **FK** → `sites(id)`, **nullable** (responsable = tous sites) |
| `actif` | BOOLEAN | NOT NULL, défaut `TRUE` |
| `tentatives_echouees` | INTEGER | NOT NULL, défaut `0` |
| `doit_changer_mot_de_passe` | BOOLEAN | NOT NULL, défaut `TRUE` |
| `date_creation` | TIMESTAMP | NOT NULL, défaut `NOW()` |

FK `site_id` **sans `ON DELETE`** → défaut `NO ACTION` (supprimer un site est bloqué s'il est référencé).

### 2.3 `fournisseurs`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `nom` | VARCHAR(150) | NOT NULL (**pas** UNIQUE) |
| `contact` | VARCHAR(100) | — |
| `telephone` | VARCHAR(30) | — |

Pas de champ `actif` : impossible de retirer un fournisseur sans le supprimer.

### 2.4 `articles`
| Colonne | Type | Contraintes / défaut |
|---|---|---|
| `id` | SERIAL | **PK** |
| `nom` | VARCHAR(150) | NOT NULL |
| `categorie` | VARCHAR(80) | — |
| `unite` | VARCHAR(30) | NOT NULL (texte libre : sac, barre, unité, m3, litre…) |
| `prix_achat` | NUMERIC(12,2) | NOT NULL, défaut `0` |
| `prix_vente` | NUMERIC(12,2) | NOT NULL |
| `quantite_stock` | INTEGER | NOT NULL, défaut `0` |
| `seuil_alerte` | INTEGER | NOT NULL, défaut `5` |
| `site_id` | INTEGER | NOT NULL, **FK** → `sites(id)` |
| `fournisseur_id` | INTEGER | **FK** → `fournisseurs(id)`, nullable |
| `date_creation` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_articles_site (site_id)`.
Un article appartient à **un seul** site (pas de notion d'article partagé entre magasin et comptoir).

### 2.5 `mouvements_stock`
| Colonne | Type | Contraintes / défaut |
|---|---|---|
| `id` | SERIAL | **PK** |
| `article_id` | INTEGER | NOT NULL, **FK** → `articles(id)` |
| `type` | VARCHAR(20) | NOT NULL, **CHECK** `type IN ('entree','sortie')` |
| `quantite` | INTEGER | NOT NULL (convention de signe non documentée) |
| `motif` | VARCHAR(200) | nullable |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` |
| `date_mouvement` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_mouvements_article (article_id)`, `idx_mouvements_date (date_mouvement)`.
Commentaire du script : **« pas de transfert entre sites »** — seuls `entree` / `sortie` existent.

### 2.6 `historique_prix_articles`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `article_id` | INTEGER | NOT NULL, **FK** → `articles(id)` **`ON DELETE CASCADE`** |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` |
| `ancien_prix_achat` | NUMERIC(12,2) | NOT NULL |
| `nouveau_prix_achat` | NUMERIC(12,2) | NOT NULL |
| `ancien_prix_vente` | NUMERIC(12,2) | NOT NULL |
| `nouveau_prix_vente` | NUMERIC(12,2) | NOT NULL |
| `date_modification` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_historique_prix_article (article_id)`.
Snapshot complet des 4 prix à chaque modification, même si un seul a changé.

### 2.7 `historique_modifications_articles`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `article_id` | INTEGER | NOT NULL, **FK** → `articles(id)` **`ON DELETE CASCADE`** |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` |
| `champ` | VARCHAR(30) | NOT NULL (texte libre, **pas de CHECK** sur les valeurs autorisées) |
| `ancienne_valeur` | VARCHAR(200) | nullable |
| `nouvelle_valeur` | VARCHAR(200) | nullable |
| `date_modification` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_historique_modif_article (article_id)`.
Une ligne par champ modifié. Intention affichée : nom, unité, seuil d'alerte.

### 2.8 `ventes`
| Colonne | Type | Contraintes / défaut |
|---|---|---|
| `id` | SERIAL | **PK** |
| `site_id` | INTEGER | NOT NULL, **FK** → `sites(id)` |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` — *celui qui saisit (comptable)* |
| `type_document` | VARCHAR(20) | NOT NULL, défaut `'ticket'`, **CHECK** `IN ('ticket','facture')` |
| `numero_facture` | VARCHAR(30) | **UNIQUE**, nullable (rempli si `facture`) |
| `statut` | VARCHAR(20) | NOT NULL, défaut `'en_attente'`, **CHECK** `IN ('en_attente','payee','annulee')` |
| `utilisateur_caisse_id` | INTEGER | **FK** → `utilisateurs(id)`, nullable — *qui a encaissé* |
| `mode_paiement` | VARCHAR(30) | **CHECK** `IN ('especes','orange_money','mtn_momo','credit_client','autre')`, nullable |
| `sous_total_ht` | NUMERIC(12,2) | NOT NULL |
| `taux_tva` | NUMERIC(5,2) | NOT NULL, défaut `0` |
| `montant_tva` | NUMERIC(12,2) | NOT NULL |
| `total_ttc` | NUMERIC(12,2) | NOT NULL |
| `date_vente` | TIMESTAMP | NOT NULL, défaut `NOW()` |
| `date_encaissement` | TIMESTAMP | nullable |

Index : `idx_ventes_site`, `idx_ventes_date`, `idx_ventes_statut`.
Circuit prévu (commentaire du script) : `en_attente` (stock retiré) → `payee` (compte en recette) ; `annulee` restitue le stock.

### 2.9 `ventes_lignes`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `vente_id` | INTEGER | NOT NULL, **FK** → `ventes(id)` **`ON DELETE CASCADE`** |
| `article_id` | INTEGER | NOT NULL, **FK** → `articles(id)` |
| `quantite` | INTEGER | NOT NULL |
| `prix_unitaire` | NUMERIC(12,2) | NOT NULL — *prix réellement négocié pour cette vente* |

Index : `idx_ventes_lignes_vente (vente_id)`.
Pas de colonne `sous_total_ligne`. Pas de garantie que `article.site_id = vente.site_id`.

### 2.10 `transactions`
| Colonne | Type | Contraintes / défaut |
|---|---|---|
| `id` | SERIAL | **PK** |
| `site_id` | INTEGER | NOT NULL, **FK** → `sites(id)` |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` |
| `type` | VARCHAR(20) | NOT NULL, **CHECK** `IN ('recette','depense')` |
| `montant` | NUMERIC(12,2) | NOT NULL |
| `description` | VARCHAR(200) | nullable |
| `vente_id` | INTEGER | **FK** → `ventes(id)`, nullable, **pas de UNIQUE** |
| `employe_id` | INTEGER | **FK** → `employes(id)` (ajoutée par `ALTER TABLE` après création d'`employes`), nullable |
| `date_transaction` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_transactions_site`, `idx_transactions_date`.

### 2.11 `employes`
| Colonne | Type | Contraintes / défaut |
|---|---|---|
| `id` | SERIAL | **PK** |
| `nom_complet` | VARCHAR(150) | NOT NULL |
| `poste` | VARCHAR(100) | nullable |
| `telephone` | VARCHAR(30) | nullable |
| `type_contrat` | VARCHAR(20) | NOT NULL, défaut `'permanent'`, **CHECK** `IN ('permanent','temporaire')` |
| `salaire_mensuel` | NUMERIC(12,2) | NOT NULL, défaut `0` |
| `site_id` | INTEGER | **FK** → `sites(id)`, nullable |
| `date_embauche` | DATE | nullable |
| `actif` | BOOLEAN | NOT NULL, défaut `TRUE` |
| `date_creation` | TIMESTAMP | NOT NULL, défaut `NOW()` |

### 2.12 `absences_conges`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `employe_id` | INTEGER | NOT NULL, **FK** → `employes(id)` **`ON DELETE CASCADE`** |
| `type` | VARCHAR(20) | NOT NULL, **CHECK** `IN ('absence','conge')` |
| `date_debut` | DATE | NOT NULL |
| `date_fin` | DATE | NOT NULL (**pas** de CHECK `date_fin >= date_debut`) |
| `motif` | VARCHAR(200) | nullable |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` |
| `date_creation` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_absences_conges_employe (employe_id)`.

### 2.13 `avances_salaire`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `employe_id` | INTEGER | NOT NULL, **FK** → `employes(id)` **`ON DELETE CASCADE`** |
| `montant` | NUMERIC(12,2) | NOT NULL |
| `motif` | VARCHAR(200) | nullable |
| `remboursee` | BOOLEAN | NOT NULL, défaut `FALSE` |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` |
| `date_avance` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_avances_salaire_employe (employe_id)`.

### 2.14 `comptages_stock`
| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | **PK** |
| `article_id` | INTEGER | NOT NULL, **FK** → `articles(id)` **`ON DELETE CASCADE`** |
| `utilisateur_id` | INTEGER | NOT NULL, **FK** → `utilisateurs(id)` |
| `moment` | VARCHAR(10) | NOT NULL, **CHECK** `IN ('matin','soir')` |
| `quantite_attendue` | INTEGER | NOT NULL (copie figée de `articles.quantite_stock` au moment du comptage) |
| `quantite_comptee` | INTEGER | NOT NULL |
| `ecart` | INTEGER | NOT NULL (**stocké**, non calculé par la base) |
| `date_comptage` | TIMESTAMP | NOT NULL, défaut `NOW()` |

Index : `idx_comptages_stock_article (article_id)`, `idx_comptages_stock_date (date_comptage)`.
Pas de contrainte `UNIQUE (article_id, jour, moment)` → comptages multiples possibles pour un même créneau.

---

## 3. Graphe des clés étrangères

```
sites  ←── utilisateurs.site_id (NULL ok)
sites  ←── articles.site_id (NOT NULL)
sites  ←── ventes.site_id / transactions.site_id / employes.site_id
fournisseurs ←── articles.fournisseur_id (NULL ok)
articles ←── mouvements_stock / ventes_lignes / historique_prix_articles(CASCADE) /
             historique_modifications_articles(CASCADE) / comptages_stock(CASCADE)
utilisateurs ←── (presque toutes les tables : auteur de l'action)
                 ventes.utilisateur_id + ventes.utilisateur_caisse_id (double lien)
ventes ←── ventes_lignes(CASCADE) / transactions.vente_id (NULL ok, non unique)
employes ←── absences_conges(CASCADE) / avances_salaire(CASCADE) / transactions.employe_id
```

---

## 4. Évaluation critique

### 4.1 Ce qui est correctement modélisé

1. **Montants en `NUMERIC(12,2)`, pas en `FLOAT`.** Contrairement à l'hypothèse de départ,
   **aucun montant n'est en flottant** : `prix_achat`, `prix_vente`, `sous_total_ht`,
   `montant_tva`, `total_ttc`, `taux_tva`, `montant` (transactions / avances),
   `salaire_mensuel` sont tous en `NUMERIC`. C'est un point fort réel : pas d'erreur
   d'arrondi binaire sur les FCFA. (Réserve mineure : le FCFA/XAF n'a pas de sous-unité ;
   `NUMERIC(12,2)` fonctionne mais `NUMERIC(14,0)` serait plus juste et éviterait des
   demi-francs parasites.)
2. **Séparation des rôles par `CHECK`** sur `utilisateurs.role`, et rattachement à un site
   via `site_id`. Le modèle porte l'intention du cahier des charges.
3. **Traçabilité des prix et des champs descriptifs** : deux tables d'historique dédiées
   (`historique_prix_articles`, `historique_modifications_articles`) avec auteur + date +
   ancienne/nouvelle valeur. C'est exactement l'objectif anti-vol du cahier des charges,
   côté articles.
4. **Comptage à l'aveugle correctement pensé** : `quantite_attendue` est une **copie figée**
   au moment du comptage, pas une valeur recalculée. Permet de reconstituer ce qui était
   attendu ce jour-là. `ecart` conservé ligne à ligne.
5. **Workflow de vente à trois états** (`en_attente` / `payee` / `annulee`) avec
   `utilisateur_caisse_id`, `date_encaissement`, `mode_paiement` remplis à l'encaissement :
   le modèle sépare bien « saisie » et « encaissement ».
6. **Prix négocié capturé par ligne** (`ventes_lignes.prix_unitaire`), distinct du prix
   catalogue (`articles.prix_vente`). Conforme au circuit réel.
7. **RH rattachée proprement** : `transactions.employe_id` relie une dépense de salaire à un
   employé au lieu d'un texte libre.
8. **Index présents sur les colonnes de filtre courantes** : site, date, statut, article_id.
9. **`identifiant` et `numero_facture` en `UNIQUE`** ; `tentatives_echouees` et
   `doit_changer_mot_de_passe` prévus pour le verrouillage et la première connexion.
10. **`ON DELETE CASCADE`** sur les tables filles de RH et d'inventaire : cohérent pour
    `absences_conges`, `avances_salaire`, `ventes_lignes`.

### 4.2 Ce qui manque (lacunes fonctionnelles portées par le schéma)

| # | Lacune | Impact | Chantier |
|---|--------|--------|----------|
| M1 | **Aucun transfert de stock entre sites.** `mouvements_stock.type` = `entree`/`sortie` seulement, et un article n'appartient qu'à un site. | Opération quotidienne du modèle à deux sites impossible à tracer proprement. | C4 / Addendum a |
| M2 | **Pas de créance client.** `mode_paiement='credit_client'` autorisé mais aucune table `clients`, `creances`, `reglements`, aucun solde. Une vente à crédit marquée `payee` génère une recette pour de l'argent non encaissé. | Comptabilité fausse ; suivi des impayés impossible. | C5 / C6 / Addendum b |
| M3 | **Pas de référence au facturier papier** ni d'**identification du vendeur** qui a négocié le prix. `ventes.utilisateur_id` = celui qui saisit (comptable), `utilisateur_caisse_id` = celui qui encaisse. Le vendeur est absent. | Objectif anti-vol inatteignable : la saisie étant a posteriori, on ne peut relier un écart de prix à personne. | C5 / Addendum c |
| M4 | **Pas de table de paramètres.** Taux de TVA courant, coordonnées entreprise pour le ticket, seuil de verrouillage, réglages de sauvegarde : rien. `taux_tva` n'existe que par vente. | Aucune configuration centrale ; TVA non paramétrable comme le demande l'addendum. | C1 / Addendum d |
| M5 | **Aucun audit d'annulation de vente.** `statut='annulee'` sans `annulee_par`, `date_annulation`, `motif_annulation`. | Le cahier des charges impose que l'annulation soit tracée et réservée au responsable : le schéma ne le permet pas. | C1 / C3 / C5 |
| M6 | **Aucun journal de connexion / session.** Pas de `journal_connexions` (succès/échec, horodatage, poste), pas de `date_derniere_connexion`, pas de `date_verrouillage`. Pas de table de sessions/jetons pour l'API mobile. | Détection d'intrusion et exigences de l'API web non couvertes. | C2 / C10 / C11 |
| M7 | **Aucun audit des comptes.** Création, désactivation, réactivation, changement de rôle ou de site : non tracés (seul `date_creation`). | Un responsable peut rétrograder/déplacer un compte sans trace. | C2 / C3 |
| M8 | **Aucun audit des transactions ni des mouvements comptables sensibles** (modification, suppression). `transactions` n'a ni `statut` ni écriture de contre-passation. | La compta peut être « corrigée » sans trace ; annuler une vente supposerait de supprimer des lignes. | C6 |
| M9 | **Pas de table de réception / lot d'entrée.** Le seuil « 20 % de la quantité reçue » suppose de connaître la quantité d'une réception donnée ; elle n'est distinguée que comme un `mouvements_stock` de type `entree`. Pas de bon de livraison, ni prix d'achat par lot. | Règle du seuil fragile ; pas d'historique d'approvisionnement. | C4 |
| M10 | **`champ` de `historique_modifications_articles` non contraint** et ne couvre pas explicitement `categorie`, `fournisseur_id`, `site_id`. | Audit partiel, valeurs incohérentes possibles. | C1 / C4 |
| M11 | **Pas de colonne de version / `updated_at`** sur `articles`, `ventes`, `transactions`. | Pas de verrou optimiste : « deux utilisateurs modifient le même article » (demandé par la recette) non géré. | C1 / C4 |
| M12 | **Horodatages en `TIMESTAMP` sans fuseau.** Toléré sur un LAN mono-fuseau (WAT, UTC+1, sans heure d'été) mais fragile dès que l'API mobile et des appareils à horloges diverses écrivent. | Incohérences d'horodatage possibles avec le mobile. | C1 / C10 |
| M13 | **Pas de clôture de caisse.** Aucune table `cloture_caisse` (date, espèces comptées, total recettes du jour, écart, responsable). | Rapprochement quotidien espèces / recettes impossible. | C6 / Addendum g |
| M14 | **Pas de gestion des retours / casse / avarie / remise.** `mouvements_stock` n'a pas de type dédié ; `ventes` n'a pas de notion d'avoir. | Pertes non tracées, remises noyées dans le prix unitaire. | C4 / C5 / Addendum f |

### 4.3 Ce qui est risqué (intégrité non garantie par la base)

| # | Risque | Détail | Chantier |
|---|--------|--------|----------|
| R1 | **Aucune contrainte de quantité positive.** | `articles.quantite_stock`, `mouvements_stock.quantite`, `ventes_lignes.quantite`, `comptages_stock.quantite_comptee` : pas de `CHECK (… >= 0)` ni `(… > 0)`. Le stock peut devenir négatif ; on peut saisir une ligne de vente de quantité 0 ou négative. | C1 / C4 |
| R2 | **Aucun verrou anti-survente au niveau base.** | Pas de `CHECK (quantite_stock >= 0)` (qui ferait au moins rejeter le second `UPDATE` concurrent), pas de trigger de décrément atomique. La cohérence repose **entièrement** sur le code client. Deux ventes simultanées peuvent lire `stock = 1` et l'écrire toutes les deux. | C1 / C4 / Addendum e |
| R3 | **`quantite_stock` est un total dénormalisé sans garde-fou.** | Aucun trigger ne le maintient à partir de `mouvements_stock` / `ventes_lignes`. Un plantage en cours d'opération fait diverger le compteur et le journal, silencieusement — grave pour un système anti-vol. | C1 / C4 |
| R4 | **`comptages_stock.ecart` est écrit par l'application, pas calculé.** | Rien n'empêche d'enregistrer `ecart = 0` alors que `comptee ≠ attendue`. Devrait être une colonne `GENERATED ALWAYS AS (quantite_comptee - quantite_attendue) STORED` ou imposé par trigger. Faille directe pour l'objectif anti-vol. | C1 / C7 |
| R5 | **Cohérence monétaire de la vente non vérifiée.** | Aucun `CHECK` : `total_ttc = sous_total_ht + montant_tva`, `montant_tva ≈ round(sous_total_ht * taux_tva/100, 2)`, `sous_total_ht = Σ(lignes.quantite * prix_unitaire)`. La base accepte une facture aux montants arbitraires — dans un outil dont le but est anti-fraude. | C1 / C5 |
| R6 | **Suppressions en cascade sur les tables d'audit.** | `historique_prix_articles` et `historique_modifications_articles` sont en `ON DELETE CASCADE` : supprimer un article **efface son historique de prix**. Un journal anti-fraude ne doit jamais être effaçable ; il faut `ON DELETE RESTRICT` (ou interdire la suppression d'article, la remplacer par `actif=FALSE`). | C1 |
| R7 | **L'application se connecte en superutilisateur.** | `config.example.ini` : `user = postgres`. Le cahier des charges exige des droits « appliqués aussi dans les requêtes à la base ». Avec `postgres`, tout client (y compris l'API mobile ou un `psql` direct) contourne toute règle. Il faut un rôle applicatif à privilèges minimaux, et idéalement des politiques **RLS** par site/rôle. | C11 / C1 |
| R8 | **Bornes de valeurs absentes.** | `prix_achat`/`prix_vente` sans `CHECK (>= 0)` ; `taux_tva` sans `CHECK (BETWEEN 0 AND 100)` ; `montant` (transactions, avances) sans `CHECK (> 0)` ; `salaire_mensuel` sans `CHECK (>= 0)`. Valeurs négatives ou absurdes acceptées. | C1 |
| R9 | **`numero_facture` : unicité sans génération.** | Colonne `UNIQUE` mais aucune séquence, aucun `DEFAULT`, aucun format imposé, aucune remise à zéro annuelle. Rien n'impose `type_document='facture' ⇒ numero_facture IS NOT NULL`, ni l'inverse. Numérotation non garantie continue. | C5 / C1 |
| R10 | **`utilisateurs.site_id` incohérent possible.** | Pas de `CHECK` liant le rôle au site : `role='responsable' ⇔ site_id IS NULL` et `role IN ('agent_*') ⇒ site_id IS NOT NULL`. Un agent sans site, ou un responsable épinglé à un site, sont acceptés. | C1 / C3 |
| R11 | **`transactions.vente_id` non unique.** | Une même vente peut engendrer plusieurs lignes `recette` (double comptage). L'annulation « retire la recette » sans mécanisme (pas de `ON DELETE`, pas de contre-passation). | C1 / C6 |
| R12 | **Rien ne garantit `ventes_lignes.article.site_id = ventes.site_id`.** | Une vente au Comptoir peut contenir un article du Magasin. Nécessite un trigger ou une contrainte composite. | C1 / C5 |
| R13 | **`seuil_alerte` : défaut arbitraire `5`, règle des 20 % absente de la base.** | La règle « 20 % de la quantité reçue, recalculé seulement à l'entrée » n'existe que dans le code. Rien n'empêche un `UPDATE articles SET seuil_alerte = …` direct, alors que le cahier des charges veut ce champ **non modifiable par personne**. | C1 / C4 |
| R14 | **`unite` en texte libre.** | Pas de référentiel d'unités ni de règles de conversion (sac↔kg, barre↔mètre). Saisies hétérogènes (« sac », « Sac », « sacs »). | C4 / Addendum f |
| R15 | **Amorçage non idempotent.** | `INSERT INTO sites …` sans `ON CONFLICT DO NOTHING` ; le script complet n'est pas rejouable (utile pour tests, migrations, réinstallation). | C0 / C1 |
| R16 | **Pas de `CHECK (date_fin >= date_debut)`** sur `absences_conges`. | Périodes incohérentes acceptées. | C1 |

### 4.4 Synthèse pour le chantier C1

Le schéma est un **squelette solide** : les entités, les relations et le choix du type
monétaire sont bons, l'intention métier du cahier des charges est lisible dans les tables.
Mais **l'intégrité n'est presque pas défendue par la base** : pas de `CHECK` de domaine,
pas de trigger, pas de colonne calculée, pas de RLS, connexion en superutilisateur,
suppressions en cascade sur l'audit. Pour un outil dont la raison d'être est la traçabilité
anti-vol, c'est le point le plus fragile. La reconstruction doit **ajouter** (contraintes,
triggers, colonnes calculées, table de paramètres, tables d'audit manquantes, rôle applicatif
restreint) sans casser la structure existante.

**Score de départ C1 : 35 %** — structure et types corrects (~½), mais application des
règles d'intégrité quasi absente et plusieurs choix actifs à corriger.
