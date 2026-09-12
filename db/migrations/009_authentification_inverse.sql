-- ============================================================================
-- 009 INVERSE — retire les fonctions d'authentification
-- ----------------------------------------------------------------------------
-- pgcrypto n'est PAS retirée : comme pg_trgm (migration 007), elle peut
-- servir ailleurs et sa présence est sans effet de bord.
-- ============================================================================

DROP FUNCTION IF EXISTS changer_mon_mot_de_passe(TEXT, TEXT);
DROP FUNCTION IF EXISTS verifier_connexion(VARCHAR, TEXT, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS qf_utilisateur_courant();

DELETE FROM schema_migrations WHERE version = '009';
