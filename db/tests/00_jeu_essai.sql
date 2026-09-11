-- ============================================================================
-- Jeu d'essai des tests du cycle 2 (chantier C1).
-- ----------------------------------------------------------------------------
-- Données minimales, conformes au scénario du guide testeur : deux sites,
-- les cinq rôles réels, quelques articles dont un à stock = 1 pour le test de
-- concurrence.
--
-- À exécuter sur une base de TEST uniquement.
-- ============================================================================

-- CE FICHIER SUPPOSE UNE BASE NEUVE : créée à partir de
-- creation_base_donnees.sql puis migrée. Il n'efface rien lui-même, et c'est
-- volontaire :
--   * les journaux (ventes, mouvements, comptages, historiques) refusent toute
--     suppression de ligne depuis la migration 004 — un DELETE échouerait ;
--   * un TRUNCATE ... CASCADE, lui, emporterait au passage la table
--     « parametres » (elle référence « utilisateurs »), donc les réglages
--     amorcés par la migration 006.
-- db/tests/executer_tests.sh recrée donc la base avant chaque fichier de test.

INSERT INTO fournisseurs (id, nom, contact, telephone) VALUES
  (1, 'Cimenterie du Cameroun', 'M. Ateba', '+237 6 99 00 11 22');
SELECT setval('fournisseurs_id_seq', 1, TRUE);

-- Responsable : aucun site (couvre les deux). Agents : un site chacun.
INSERT INTO utilisateurs (id, nom_complet, identifiant, mot_de_passe_hash, role, site_id) VALUES
  (1, 'Awa Franck',       'resp',            'hash_factice', 'responsable',        NULL),
  (2, 'Ali Magasin',      'magasin.stock',   'hash_factice', 'agent_stock',        1),
  (3, 'Bea Comptoir',     'comptoir.stock',  'hash_factice', 'agent_stock',        2),
  (4, 'Cyr Magasin',      'magasin.compta',  'hash_factice', 'agent_comptabilite', 1),
  (5, 'Dina Comptoir',    'comptoir.compta', 'hash_factice', 'agent_comptabilite', 2);
SELECT setval('utilisateurs_id_seq', 5, TRUE);

INSERT INTO articles (id, nom, categorie, unite, prix_achat, prix_vente, quantite_stock, seuil_alerte, site_id, fournisseur_id) VALUES
  (1, 'Ciment CIM II 50 kg', 'Gros oeuvre', 'sac',   5000, 6500,  30, 6, 1, 1),
  (2, 'Fer à béton 8 mm',    'Gros oeuvre', 'barre', 2800, 3500,  40, 8, 1, 1),
  (3, 'Clou 5 cm',           'Quincaillerie', 'kg',   600,  800, 100, 20, 2, 1),
  (4, 'Article rare',        'Divers',      'pièce', 1000, 2000,   1, 1, 1, 1);
SELECT setval('articles_id_seq', 4, TRUE);

INSERT INTO employes (id, nom_complet, poste, type_contrat, salaire_mensuel, site_id, date_embauche) VALUES
  (1, 'Employé Essai', 'Manutentionnaire', 'permanent', 60000, 1, '2026-01-15');
SELECT setval('employes_id_seq', 1, TRUE);
