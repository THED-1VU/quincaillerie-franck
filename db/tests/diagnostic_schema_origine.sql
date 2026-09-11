-- ============================================================================
-- DIAGNOSTIC — phase 1 du cycle 2, sur le schéma D'ORIGINE (non migré)
-- ----------------------------------------------------------------------------
-- Ne mesure rien par lecture : chaque bloc TENTE une écriture aberrante. Si
-- elle passe, la protection est absente. C'est ce script qui a établi, par
-- exécution, l'état réel du chantier C1 avant correction.
--
-- À exécuter sur une base créée à partir de creation_base_donnees.sql SEUL,
-- sans aucune migration :
--   psql -d quincaillerie_origine -f db/tests/diagnostic_schema_origine.sql
--
-- Les mêmes tentatives, une fois les migrations appliquées, sont toutes
-- refusées : voir db/tests/01_protections.sql.
-- ============================================================================
\set ON_ERROR_STOP off
\pset pager off

INSERT INTO fournisseurs (nom) VALUES ('Fournisseur test');
INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id)
  VALUES ('Resp Test', 'resp', 'x', 'responsable', NULL);
INSERT INTO articles (nom, unite, prix_achat, prix_vente, quantite_stock, site_id)
  VALUES ('Ciment test', 'sac', 5000, 6500, 10, 1);

\echo '--- Le stock peut-il devenir NÉGATIF ? ---'
UPDATE articles SET quantite_stock = -50 WHERE nom = 'Ciment test';
SELECT nom, quantite_stock FROM articles WHERE nom = 'Ciment test';
UPDATE articles SET quantite_stock = 10 WHERE nom = 'Ciment test';

\echo '--- Un PRIX peut-il être négatif ? ---'
UPDATE articles SET prix_vente = -999 WHERE nom = 'Ciment test';
SELECT nom, prix_vente FROM articles WHERE nom = 'Ciment test';
UPDATE articles SET prix_vente = 6500 WHERE nom = 'Ciment test';

\echo '--- Une ligne de vente de quantité NÉGATIVE passe-t-elle ? ---'
INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc)
  VALUES (1, (SELECT id FROM utilisateurs WHERE identifiant='resp'), 'payee', 0, 0, 0, 0);
INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire)
  VALUES ((SELECT max(id) FROM ventes), (SELECT id FROM articles WHERE nom='Ciment test'), -5, 6500);
SELECT quantite FROM ventes_lignes WHERE vente_id = (SELECT max(id) FROM ventes);

\echo '--- LE POINT CLÉ : un ÉCART D''INVENTAIRE MENSONGER est-il accepté ? ---'
\echo '    (attendu 10, compté 3 — donc 7 sacs manquants — mais écart déclaré 0)'
INSERT INTO comptages_stock (article_id, utilisateur_id, moment, quantite_attendue, quantite_comptee, ecart)
  VALUES ((SELECT id FROM articles WHERE nom='Ciment test'),
          (SELECT id FROM utilisateurs WHERE identifiant='resp'), 'matin', 10, 3, 0);
SELECT quantite_attendue, quantite_comptee, ecart,
       (quantite_comptee - quantite_attendue) AS ecart_reel
  FROM comptages_stock ORDER BY id DESC LIMIT 1;

\echo '--- Des TOTAUX de vente incohérents passent-ils ? (1 + 1 = 999999) ---'
INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc)
  VALUES (1, (SELECT id FROM utilisateurs WHERE identifiant='resp'), 'payee', 1, 0, 1, 999999);
SELECT sous_total_ht, montant_tva, total_ttc FROM ventes ORDER BY id DESC LIMIT 1;

\echo '--- Un taux de TVA de 500 % passe-t-il ? ---'
UPDATE ventes SET taux_tva = 500 WHERE id = (SELECT max(id) FROM ventes);
SELECT taux_tva FROM ventes ORDER BY id DESC LIMIT 1;

\echo '--- Un AGENT SANS SITE passe-t-il ? (tout cloisonnement devient inopérant) ---'
INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id)
  VALUES ('Agent sans site', 'agent.orphelin', 'x', 'agent_stock', NULL);
SELECT identifiant, role, site_id FROM utilisateurs WHERE identifiant='agent.orphelin';

\echo '--- Supprimer un article EFFACE-T-IL son historique de prix ? ---'
INSERT INTO articles (nom, unite, prix_achat, prix_vente, quantite_stock, site_id)
  VALUES ('Article a supprimer', 'pièce', 100, 200, 5, 1);
INSERT INTO historique_prix_articles
  (article_id, utilisateur_id, ancien_prix_achat, nouveau_prix_achat, ancien_prix_vente, nouveau_prix_vente)
  VALUES ((SELECT id FROM articles WHERE nom='Article a supprimer'),
          (SELECT id FROM utilisateurs WHERE identifiant='resp'), 100, 150, 200, 300);
SELECT count(*) AS lignes_historique_avant FROM historique_prix_articles;
DELETE FROM articles WHERE nom = 'Article a supprimer';
SELECT count(*) AS lignes_historique_apres FROM historique_prix_articles;

\echo '--- Une même vente peut-elle produire PLUSIEURS recettes ? ---'
INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
  VALUES (1, (SELECT id FROM utilisateurs WHERE identifiant='resp'), 'recette', 5000, 'recette 1', (SELECT max(id) FROM ventes));
INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
  VALUES (1, (SELECT id FROM utilisateurs WHERE identifiant='resp'), 'recette', 5000, 'recette 2 (doublon)', (SELECT max(id) FROM ventes));
SELECT vente_id, count(*) AS nb_recettes FROM transactions WHERE vente_id IS NOT NULL GROUP BY vente_id;

\echo '--- Peut-on vendre au Magasin un article du Comptoir ? ---'
INSERT INTO articles (nom, unite, prix_achat, prix_vente, quantite_stock, site_id)
  VALUES ('Article comptoir', 'pièce', 100, 200, 5, 2);
INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire)
  VALUES ((SELECT max(id) FROM ventes), (SELECT id FROM articles WHERE nom='Article comptoir'), 1, 200);
SELECT v.site_id AS site_vente, a.site_id AS site_article
  FROM ventes_lignes vl JOIN ventes v ON v.id=vl.vente_id JOIN articles a ON a.id=vl.article_id
  WHERE vl.vente_id = (SELECT max(id) FROM ventes) AND a.nom='Article comptoir';

\echo '--- Le SEUIL D''ALERTE est-il modifiable directement ? (dissimulation de vol) ---'
UPDATE articles SET seuil_alerte = 0 WHERE nom = 'Ciment test';
SELECT nom, seuil_alerte FROM articles WHERE nom = 'Ciment test';

\echo '--- Un congé qui finit AVANT de commencer passe-t-il ? ---'
INSERT INTO employes (nom_complet, site_id) VALUES ('Employe test', 1);
INSERT INTO absences_conges (employe_id, type, date_debut, date_fin, utilisateur_id)
  VALUES ((SELECT id FROM employes WHERE nom_complet='Employe test'), 'conge', '2026-12-31', '2026-01-01',
          (SELECT id FROM utilisateurs WHERE identifiant='resp'));
SELECT date_debut, date_fin FROM absences_conges ORDER BY id DESC LIMIT 1;

\echo '--- L''annulation d''une vente est-elle tracée ? (colonnes de la table ventes) ---'
UPDATE ventes SET statut='annulee' WHERE id=(SELECT max(id) FROM ventes);
SELECT string_agg(column_name, ', ' ORDER BY ordinal_position) AS colonnes_ventes
  FROM information_schema.columns WHERE table_name='ventes';

\echo '--- Existe-t-il des tables de JOURNAL / AUDIT ? ---'
SELECT table_name FROM information_schema.tables
 WHERE table_schema='public' AND (table_name LIKE '%journal%' OR table_name LIKE '%audit%' OR table_name LIKE '%connexion%');

\echo '--- Existe-t-il une table de PARAMÈTRES ? ---'
SELECT table_name FROM information_schema.tables
 WHERE table_schema='public' AND table_name LIKE '%param%';

\echo '--- Existe-t-il un rôle applicatif NON superutilisateur ? ---'
SELECT rolname, rolsuper FROM pg_roles WHERE rolname NOT LIKE 'pg\_%' ORDER BY rolname;

\echo '--- Déclencheurs, colonnes générées, contraintes CHECK métier ---'
SELECT (SELECT count(*) FROM information_schema.triggers WHERE trigger_schema='public') AS nb_declencheurs,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_schema='public' AND is_generated='ALWAYS')                          AS nb_colonnes_generees,
       (SELECT count(*) FROM information_schema.table_constraints
         WHERE table_schema='public' AND constraint_type='CHECK'
           AND constraint_name NOT LIKE '%not_null%')                                    AS nb_check_metier;
