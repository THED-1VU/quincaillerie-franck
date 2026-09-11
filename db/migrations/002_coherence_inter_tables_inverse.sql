-- ============================================================================
-- 002 INVERSE — retire les cohérences inter-tables
-- ============================================================================

ALTER TABLE transactions  DROP CONSTRAINT IF EXISTS fk_transactions_vente_site;
DROP INDEX IF EXISTS uq_transactions_recette_par_vente;

ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS fk_ventes_lignes_article_site;
ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS fk_ventes_lignes_vente_site;
ALTER TABLE ventes_lignes DROP COLUMN IF EXISTS site_id;

ALTER TABLE ventes   DROP CONSTRAINT IF EXISTS uq_ventes_id_site;
ALTER TABLE articles DROP CONSTRAINT IF EXISTS uq_articles_id_site;

DELETE FROM schema_migrations WHERE version = '002';
