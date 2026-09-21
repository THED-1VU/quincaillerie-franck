-- Annule la migration 029. Les anciennes politiques et les anciens GRANT de
-- colonnes sont restaurés par l'inverse de la migration 027 (ils référencent
-- des colonnes d'articles qui n'existent qu'après cette restauration).

DROP POLICY IF EXISTS p_stocks_sites_site ON stocks_sites;
ALTER TABLE stocks_sites DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_articles_catalogue ON articles;
DROP POLICY IF EXISTS p_mouvements_site ON mouvements_stock;
DROP POLICY IF EXISTS p_comptages_site ON comptages_stock;
DROP POLICY IF EXISTS p_ecarts_stock_ventes_site ON ecarts_stock_ventes;

DELETE FROM schema_migrations WHERE version = '029';
