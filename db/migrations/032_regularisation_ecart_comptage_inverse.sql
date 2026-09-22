-- Annule la migration 032.

DROP TABLE IF EXISTS regularisations_ecarts_comptage;

DROP FUNCTION IF EXISTS regulariser_ecart_comptage(INTEGER, VARCHAR, INTEGER, VARCHAR);

DELETE FROM parametres WHERE cle = 'plafond_vraisemblance_comptage';

DELETE FROM schema_migrations WHERE version = '032';
