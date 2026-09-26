-- Annule la migration 046 : retire la fonction de normalisation.

DROP FUNCTION IF EXISTS normaliser_nom_article(VARCHAR);

DELETE FROM schema_migrations WHERE version = '046';
