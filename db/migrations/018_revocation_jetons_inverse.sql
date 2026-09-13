-- Annule la migration 018.

DROP FUNCTION IF EXISTS jeton_est_revoque(VARCHAR);
DROP FUNCTION IF EXISTS revoquer_jeton(VARCHAR, INTEGER, BIGINT);
DROP TABLE IF EXISTS jetons_revoques;

DELETE FROM schema_migrations WHERE version = '018';
