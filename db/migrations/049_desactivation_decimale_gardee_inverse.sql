-- ============================================================================
-- 049 (inverse) — retire le garde-fou de désactivation des quantités
-- décimales. Aucune donnée n'est touchée : la colonne
-- articles.quantite_decimale_autorisee et les triggers de la migration 034
-- restent en place.
-- ============================================================================

DROP TRIGGER IF EXISTS trg_refuser_desactivation_decimale ON articles;
DROP FUNCTION IF EXISTS refuser_desactivation_decimale();

DELETE FROM schema_migrations WHERE version = '049';
