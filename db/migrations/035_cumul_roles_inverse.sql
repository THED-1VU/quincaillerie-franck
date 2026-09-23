-- Annule la migration 035.

DROP FUNCTION IF EXISTS roles_utilisateur(INTEGER);
DROP TABLE IF EXISTS utilisateurs_roles;

DELETE FROM schema_migrations WHERE version = '035';
