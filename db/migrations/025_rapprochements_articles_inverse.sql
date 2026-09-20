-- Annule la migration 025.

DROP VIEW IF EXISTS candidats_rapprochement;
DROP FUNCTION IF EXISTS enregistrer_rapprochement(INTEGER, INTEGER, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS candidats_rapprochement();
DROP TABLE IF EXISTS rapprochements_articles;

DELETE FROM schema_migrations WHERE version = '025';
