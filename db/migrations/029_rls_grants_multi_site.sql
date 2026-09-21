-- ============================================================================
-- 029 — Chantier 13b (cycle 35) : RLS et GRANT du modèle multi-site.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (2026-09-20, confirmée) : le CATALOGUE (nom,
-- catégorie, unité, prix) est visible aux deux sites ; seule la QUANTITÉ
-- reste cloisonnée par site. Traduction dans la base :
--   * `articles` n'est plus filtré par site (politique permissive) — les
--     colonnes de prix restent protégées par les GRANT de colonnes
--     (l'agent stock ne lit toujours pas prix_achat/prix_vente) ;
--   * `stocks_sites` porte le cloisonnement : un agent ne lit que la ligne
--     de son site ; aucun rôle métier n'a d'écriture directe (tout passe
--     par les fonctions SECURITY DEFINER de la migration 028) ;
--   * `mouvements_stock`, `comptages_stock` et `ecarts_stock_ventes`
--     filtrent désormais directement sur leur propre colonne `site_id`
--     (fini les sous-requêtes vers `articles`).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. articles : catalogue commun aux deux sites
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS p_articles_site ON articles;
CREATE POLICY p_articles_catalogue ON articles
  USING (TRUE) WITH CHECK (TRUE);

-- Les colonnes site_id, quantite_stock et seuil_alerte ont disparu d'articles :
-- on repart propre, avec les mêmes protections de colonnes qu'avant.
REVOKE ALL ON articles FROM qf_responsable, qf_agent_stock, qf_agent_comptabilite;

GRANT SELECT ON articles TO qf_responsable;
GRANT INSERT (nom, categorie, unite, prix_achat, prix_vente, fournisseur_id)
  ON articles TO qf_responsable;
GRANT UPDATE (nom, categorie, unite, prix_achat, prix_vente,
              fournisseur_id, actif, date_desactivation, desactive_par_id)
  ON articles TO qf_responsable;

GRANT SELECT (id, nom, categorie, unite, fournisseur_id, date_creation,
              actif, date_desactivation, desactive_par_id)
  ON articles TO qf_agent_stock;
GRANT INSERT (nom, categorie, unite, fournisseur_id)
  ON articles TO qf_agent_stock;
GRANT UPDATE (nom, categorie, unite)
  ON articles TO qf_agent_stock;

GRANT SELECT (id, nom, categorie, unite, prix_vente, fournisseur_id,
              date_creation, actif)
  ON articles TO qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- 2. stocks_sites : le cloisonnement de la quantité vit ici
-- ----------------------------------------------------------------------------
ALTER TABLE stocks_sites ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_stocks_sites_site ON stocks_sites;
CREATE POLICY p_stocks_sites_site ON stocks_sites
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

-- Lecture seule, par colonne : quantité visible du responsable et de l'agent
-- stock, JAMAIS de la comptabilité. Aucune écriture directe pour personne.
GRANT SELECT (article_id, site_id, quantite_stock, seuil_alerte)
  ON stocks_sites TO qf_responsable, qf_agent_stock;

-- ----------------------------------------------------------------------------
-- 3. Mouvements, comptages et écarts : filtrage direct sur leur site_id
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS p_mouvements_site ON mouvements_stock;
CREATE POLICY p_mouvements_site ON mouvements_stock
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

DROP POLICY IF EXISTS p_comptages_site ON comptages_stock;
CREATE POLICY p_comptages_site ON comptages_stock
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

DROP POLICY IF EXISTS p_ecarts_stock_ventes_site ON ecarts_stock_ventes;
CREATE POLICY p_ecarts_stock_ventes_site ON ecarts_stock_ventes
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

-- Comptage à l'aveugle : l'agent stock gagne site_id dans sa lecture,
-- toujours sans quantite_attendue ni ecart.
REVOKE SELECT ON comptages_stock FROM qf_agent_stock;
GRANT SELECT (id, article_id, site_id, utilisateur_id, moment,
              quantite_comptee, date_comptage)
  ON comptages_stock TO qf_agent_stock;

INSERT INTO schema_migrations (version, nom)
VALUES ('029', 'rls_grants_multi_site')
ON CONFLICT (version) DO NOTHING;
