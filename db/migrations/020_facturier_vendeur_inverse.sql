-- Annule la migration 020.

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_numero_facturier_prefixe_site;
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS uq_ventes_numero_facturier;
DROP INDEX IF EXISTS idx_ventes_vendeur_id;
ALTER TABLE ventes DROP COLUMN IF EXISTS vendeur_id;
ALTER TABLE ventes DROP COLUMN IF EXISTS numero_facturier;

DELETE FROM schema_migrations WHERE version = '020';
