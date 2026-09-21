-- Annule la migration 026.

DROP TABLE IF EXISTS stocks_sites;

DELETE FROM schema_migrations WHERE version = '026';
