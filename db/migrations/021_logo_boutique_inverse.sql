-- Annule la migration 021.

DELETE FROM parametres WHERE cle = 'logo_boutique_extension';

DELETE FROM schema_migrations WHERE version = '021';
