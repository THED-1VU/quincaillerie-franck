-- ============================================================================
-- 010 INVERSE — retire l'accès au schéma pour qf_app (retour au bug d'origine)
-- ============================================================================

REVOKE USAGE ON SCHEMA public FROM qf_app;

DELETE FROM schema_migrations WHERE version = '010';
