-- ============================================================================
-- Jeu d'essai des tests du cycle 2 (chantier C1).
-- ----------------------------------------------------------------------------
-- Données minimales, conformes au scénario du guide testeur : deux sites,
-- les cinq rôles réels, quelques articles dont un à stock = 1 pour le test de
-- concurrence.
--
-- À exécuter sur une base de TEST uniquement.
-- ============================================================================

-- CE FICHIER SUPPOSE UNE BASE DÉJÀ MIGRÉE (000 à la plus récente). Il peut
-- être rejoué PLUSIEURS FOIS de suite sur la même base (idempotent) : c'est
-- ce que fait server/tests/conftest.py entre deux tests du cycle 3.
--
-- TRUNCATE, et non DELETE : les journaux (ventes, mouvements, comptages,
-- historiques) refusent toute suppression ligne à ligne depuis la migration
-- 004 (déclencheurs BEFORE DELETE) — mais TRUNCATE ne déclenche PAS ces
-- déclencheurs (ce n'est pas un DELETE), et postgres, propriétaire des
-- tables, l'exécute sans passer par les droits des rôles applicatifs.
--
-- « parametres » et « historique_parametres » sont INCLUSES dans le même
-- TRUNCATE : elles référencent utilisateurs(id), PostgreSQL exigerait sinon
-- un CASCADE qui les viderait de toute façon. On les re-amorce donc juste
-- après, à l'identique de la migration 006 — SOURCE DE VÉRITÉ : si le jeu de
-- paramètres change là-bas, le reporter ici. Les 4 paramètres de fiscalité
-- (point d) reprennent en plus la décision du propriétaire appliquée par la
-- migration 011 (cycle 6) : un jeu d'essai doit refléter une base migrée
-- jusqu'au bout, pas seulement jusqu'à 006.
TRUNCATE TABLE
    journal_comptes, journal_connexions,
    comptages_stock_ecarts_declares, comptages_stock, mouvements_stock,
    historique_modifications_articles, historique_prix_articles,
    ventes_lignes, transactions, ventes,
    avances_salaire, absences_conges, employes,
    stocks_sites, articles, fournisseurs,
    historique_parametres, parametres,
    utilisateurs
RESTART IDENTITY CASCADE;

-- Réamorçage de parametres — copie de la migration 006, voir ce commentaire.
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision) VALUES
('boutique_nom', 'Ets Quincaillerie Franck', 'texte',
 'Raison sociale, imprimée sur les tickets et factures.', TRUE, FALSE, NULL),
('boutique_ville', 'Batouri', 'texte',
 'Ville, imprimée sur les documents.', TRUE, FALSE, NULL),
('boutique_telephone', 'a_definir', 'texte',
 'Téléphone imprimé sur les tickets et factures.', TRUE, TRUE, 'à fournir par le propriétaire'),
('boutique_numero_contribuable', 'a_definir', 'texte',
 'Numéro de contribuable, si les mentions légales l''exigent.', TRUE, TRUE, 'addendum point d'),
('regime_fiscal', 'reel', 'texte',
 'Régime fiscal réel : impot_liberatoire, simplifie ou reel (assujetti TVA). '
 'Tant que ce point n''est pas tranché, aucune TVA n''est appliquée.', TRUE, FALSE, 'addendum point d, décidé cycle 6'),
('taux_tva', '19.25', 'decimal',
 'Taux de TVA en pourcentage. 0 = aucune TVA appliquée, ce qui est le '
 'fonctionnement par défaut et parfaitement valide.', TRUE, FALSE, 'addendum point d, décidé cycle 6'),
('prix_saisis_ttc', 'oui', 'texte',
 'Les prix négociés avec le client sont-ils compris TTC (oui) ou HT (non) ?', TRUE, FALSE, 'addendum point d, décidé cycle 6'),
('arrondi_montants', 'arithmetique', 'texte',
 'Méthode d''arrondi au franc CFA (le FCFA n''a pas de sous-unité).', TRUE, FALSE, 'addendum point d, décidé cycle 6'),
('devise', 'FCFA', 'texte',
 'Devise affichée.', FALSE, FALSE, NULL),
('seuil_alerte_pourcentage', '20', 'entier',
 'Pourcentage de la quantité reçue servant de seuil d''alerte, recalculé '
 'UNIQUEMENT lors d''une entrée de stock (cahier des charges §3.2).', TRUE, FALSE, NULL),
('seuil_alerte_plancher', '1', 'entier',
 'Seuil d''alerte minimal, quand 20 %% de la quantité reçue donnerait 0. '
 'Valeur proposée, à confirmer.', TRUE, TRUE, 'à confirmer par le propriétaire'),
('plafond_vraisemblance_comptage', 'a_definir', 'entier',
 'Quantité comptée maximale acceptée sur une ligne de comptage. Tant que '
 'cette valeur n''est pas fixée, aucun comptage n''est refusé pour '
 'vraisemblance (décision 2026-09-22).', TRUE, TRUE, 'à fixer par le propriétaire'),
('tentatives_max_connexion', '5', 'entier',
 'Nombre d''échecs consécutifs avant verrouillage du compte. Valeur proposée, '
 'à confirmer.', TRUE, TRUE, 'à confirmer par le propriétaire'),
('duree_session_minutes', 'a_definir', 'entier',
 'Durée d''inactivité au bout de laquelle la session se ferme.', TRUE, TRUE, 'dossier de recette §6, session inactive'),
('seuil_ecart_caisse_tolere', 'a_definir', 'decimal',
 'Écart de caisse toléré (FCFA, par mode de paiement) au-delà duquel un '
 'commentaire devient obligatoire à la clôture. Tant que ce n''est pas '
 'tranché, cloturer_caisse() applique une tolérance NULLE (tout écart non '
 'nul exige un commentaire) — jamais un chiffre inventé.',
 TRUE, TRUE, 'addendum point g, question 5');

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

-- Une fiche article, un stock par site (décision 2026-09-19, migration 026).
INSERT INTO articles (id, nom, categorie, unite, prix_achat, prix_vente, fournisseur_id) VALUES
  (1, 'Ciment CIM II 50 kg', 'Gros oeuvre', 'sac',   5000, 6500, 1),
  (2, 'Fer à béton 8 mm',    'Gros oeuvre', 'barre', 2800, 3500, 1),
  (3, 'Clou 5 cm',           'Quincaillerie', 'kg',   600,  800, 1),
  (4, 'Article rare',        'Divers',      'pièce', 1000, 2000, 1);
SELECT setval('articles_id_seq', 4, TRUE);

INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte) VALUES
  (1, 1,  30, 6),
  (2, 1,  40, 8),
  (3, 2, 100, 20),
  (4, 1,   1, 1);

INSERT INTO employes (id, nom_complet, poste, type_contrat, salaire_mensuel, site_id, date_embauche) VALUES
  (1, 'Employé Essai', 'Manutentionnaire', 'permanent', 60000, 1, '2026-01-15');
SELECT setval('employes_id_seq', 1, TRUE);
