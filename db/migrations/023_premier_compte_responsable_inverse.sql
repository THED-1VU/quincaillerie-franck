-- Annule la migration 023.

DROP FUNCTION IF EXISTS creer_premier_responsable(VARCHAR, VARCHAR, TEXT);

DELETE FROM schema_migrations WHERE version = '023';
