-- ============================================================================
-- Jeu de volume realiste pour la preuve de reprise C1 (cycle 39).
-- ----------------------------------------------------------------------------
-- A executer sur une base VIERGE, migree 000-033, par le generateur
-- db/outils/generer_volume_realiste.ps1.
--
-- Volume cible (decision proprietaire 2026-09-22) : ~1 000 references,
-- 2 sites, historique de ventes / mouvements / comptages sur 30 jours.
-- Donnees SYNTHETIQUES, volontairement ASCII pures pour psql sous Windows.
-- ============================================================================

-- 1. Comptes (mot de passe bcrypt reel, jamais relu ensuite)
INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id, actif, doit_changer_mot_de_passe)
VALUES
  ('Responsable Volume', 'resp.volume', crypt('RespVolume123', gen_salt('bf', 12)), 'responsable', NULL, TRUE, FALSE),
  ('Agent Stock Volume', 'stock.volume', crypt('StockVolume123', gen_salt('bf', 12)), 'agent_stock', 1, TRUE, FALSE),
  ('Agent Compta Volume', 'compta.volume', crypt('ComptaVolume123', gen_salt('bf', 12)), 'agent_comptabilite', 2, TRUE, FALSE);

-- 1 bis. Employes (vendeur_id, chantier B, migration 040) - un par site,
-- distinct des comptes utilisateurs ci-dessus (un vendeur peut n'avoir
-- jamais eu de compte).
INSERT INTO employes (nom_complet, poste, type_contrat, salaire_mensuel, site_id, date_embauche, actif)
VALUES
  ('Vendeur Volume Magasin', 'Vendeur', 'permanent', 55000, 1, '2026-01-01', TRUE),
  ('Vendeuse Volume Comptoir', 'Vendeuse', 'permanent', 55000, 2, '2026-01-01', TRUE);

-- 2. Fournisseurs
INSERT INTO fournisseurs (nom, contact, telephone)
VALUES
  ('Fournisseur Alpha', 'Contact Alpha', '0600000001'),
  ('Fournisseur Beta',  'Contact Beta',  '0600000002'),
  ('Fournisseur Gamma', 'Contact Gamma', '0600000003'),
  ('Fournisseur Delta', 'Contact Delta', '0600000004');

-- 3. 1 000 articles (fiche commune, prix realistes)
INSERT INTO articles (nom, categorie, unite, prix_achat, prix_vente, fournisseur_id)
SELECT 'Article ' || lpad(g::text, 4, '0'),
       'categorie_' || ((g % 10) + 1)::text,
       'unite',
       ((g % 50) + 1) * 100,        -- prix d'achat 100..5000 FCFA
       ((g % 50) + 1) * 150,        -- prix de vente 150..7500 FCFA
       ((g % 4) + 1)
FROM generate_series(1, 1000) AS g;

-- 4. Un stock par site pour chaque article
INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
SELECT a.id, s.site_id, (a.id * 7 + s.site_id * 13) % 500, 10
FROM articles a
CROSS JOIN (VALUES (1), (2)) AS s(site_id);

-- 5. Une entree initiale tracee pour chaque stock non nul
INSERT INTO mouvements_stock (article_id, type, quantite, motif, utilisateur_id, date_mouvement, categorie, site_id)
SELECT st.article_id, 'entree', st.quantite_stock, 'entree initiale',
       (SELECT id FROM utilisateurs WHERE identifiant = 'stock.volume'),
       NOW() - interval '40 days', 'reception_fournisseur', st.site_id
FROM stocks_sites st
WHERE st.quantite_stock > 0;

-- 6. 600 ventes payees reparties sur 30 jours et 2 sites
INSERT INTO ventes (site_id, utilisateur_id, type_document, numero_facture, statut,
                    utilisateur_caisse_id, mode_paiement, sous_total_ht, taux_tva,
                    montant_tva, total_ttc, date_vente, date_encaissement,
                    numero_facturier, vendeur_id)
SELECT s.site_id,
       u.id,
       'facture',
       'VOL-' || CASE WHEN s.site_id = 1 THEN 'MAG-' ELSE 'CPT-' END || lpad(g::text, 6, '0'),
       'payee',
       (SELECT id FROM utilisateurs WHERE identifiant = 'resp.volume'),
       'especes',
       0, 0, 0, 0,
       NOW() - interval '1 day' * ((g - 1) % 30),
       NOW() - interval '1 day' * ((g - 1) % 30),
       CASE WHEN s.site_id = 1 THEN 'MAG-' || lpad(g::text, 6, '0')
            ELSE 'CPT-' || lpad(g::text, 6, '0') END,
       e.id
FROM generate_series(1, 600) AS g
CROSS JOIN (VALUES (1), (2)) AS s(site_id)
JOIN LATERAL (
    SELECT id FROM utilisateurs
     WHERE site_id = s.site_id AND role IN ('agent_stock', 'agent_comptabilite')
     LIMIT 1
) AS u ON TRUE
-- vendeur_id = une fiche employe, pas un compte utilisateur (chantier B,
-- migration 040) - l'employe cree a l'etape 1 bis, du meme site.
JOIN LATERAL (
    SELECT id FROM employes WHERE site_id = s.site_id LIMIT 1
) AS e ON TRUE;

-- 7. 3 lignes par vente (1 800 lignes), article et prix reels
INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id)
SELECT v.id,
       ((v.id * 13 + l.ligne) % 1000) + 1,
       ((v.id + l.ligne) % 4) + 1,
       a.prix_vente,
       v.site_id
FROM ventes v
CROSS JOIN generate_series(1, 3) AS l(ligne)
JOIN articles a ON a.id = ((v.id * 13 + l.ligne) % 1000) + 1;

-- 8. 120 comptages d'inventaire (article/moment/jour uniques)
INSERT INTO comptages_stock (article_id, utilisateur_id, moment, quantite_comptee, site_id, date_comptage)
SELECT ((g * 11) % 1000) + 1,
       (SELECT id FROM utilisateurs
         WHERE identifiant = CASE WHEN (g % 2) + 1 = 1 THEN 'stock.volume' ELSE 'compta.volume' END),
       CASE WHEN g % 2 = 0 THEN 'matin' ELSE 'soir' END,
       ((g * 17) % 500),
       (g % 2) + 1,
       NOW() - interval '1 day' * ((g - 1) % 30)
FROM generate_series(1, 120) AS g;

-- 9. Bilan attendu (a comparer apres restauration)
SELECT 'articles'      AS table_concernee, count(*) AS total FROM articles
UNION ALL SELECT 'stocks_sites', count(*) FROM stocks_sites
UNION ALL SELECT 'mouvements_stock', count(*) FROM mouvements_stock
UNION ALL SELECT 'ventes', count(*) FROM ventes
UNION ALL SELECT 'ventes_lignes', count(*) FROM ventes_lignes
UNION ALL SELECT 'comptages_stock', count(*) FROM comptages_stock
ORDER BY table_concernee;
