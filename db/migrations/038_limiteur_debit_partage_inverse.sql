-- Annule la migration 038.

DROP FUNCTION IF EXISTS tentative_autorisee(VARCHAR, INTEGER, INTEGER);
DROP FUNCTION IF EXISTS reinitialiser_limitation(VARCHAR);
DROP TABLE IF EXISTS limitations_debit;

DELETE FROM schema_migrations WHERE version = '038';
