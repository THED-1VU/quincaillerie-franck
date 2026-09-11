-- ============================================================================
-- 006 INVERSE — retire les paramètres applicatifs
-- ============================================================================

DROP VIEW     IF EXISTS parametres_a_decider;
DROP FUNCTION IF EXISTS parametre_numerique(VARCHAR);
DROP FUNCTION IF EXISTS parametre_texte(VARCHAR);

DROP TRIGGER  IF EXISTS trg_tracer_parametre ON parametres;
DROP FUNCTION IF EXISTS tracer_modification_parametre();

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON historique_parametres;

DROP TABLE IF EXISTS historique_parametres;
DROP TABLE IF EXISTS parametres;

DELETE FROM schema_migrations WHERE version = '006';
