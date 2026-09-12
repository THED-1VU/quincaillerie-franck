-- ============================================================================
-- 013 INVERSE — retire le fuseau horaire explicite de la base (retour à
-- l'héritage du système d'exploitation / de l'instance PostgreSQL)
-- ============================================================================

DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I RESET timezone', current_database());
END
$$;

DELETE FROM schema_migrations WHERE version = '013';
