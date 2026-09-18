-- Annule la migration 022.

DELETE FROM parametres WHERE cle = 'contact_support_technique';

DELETE FROM schema_migrations WHERE version = '022';
