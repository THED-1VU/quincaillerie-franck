-- Annule la migration 024.

DROP FUNCTION IF EXISTS compte_est_actif(INTEGER);

DELETE FROM schema_migrations WHERE version = '024';
