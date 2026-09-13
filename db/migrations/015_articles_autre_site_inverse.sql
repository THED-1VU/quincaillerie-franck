-- Annule la migration 015 : supprime articles_autre_site().

DROP FUNCTION IF EXISTS articles_autre_site();

DELETE FROM schema_migrations WHERE version = '015';
