-- ============================================================================
-- 008 INVERSE — retire les rôles applicatifs, les privilèges et la RLS
-- ============================================================================

DROP POLICY IF EXISTS p_comptages_site   ON comptages_stock;
DROP POLICY IF EXISTS p_mouvements_site  ON mouvements_stock;
DROP POLICY IF EXISTS p_transactions_site ON transactions;
DROP POLICY IF EXISTS p_ventes_site      ON ventes;
DROP POLICY IF EXISTS p_articles_site    ON articles;

ALTER TABLE comptages_stock  DISABLE ROW LEVEL SECURITY;
ALTER TABLE mouvements_stock DISABLE ROW LEVEL SECURITY;
ALTER TABLE transactions     DISABLE ROW LEVEL SECURITY;
ALTER TABLE ventes           DISABLE ROW LEVEL SECURITY;
ALTER TABLE articles         DISABLE ROW LEVEL SECURITY;

DROP FUNCTION IF EXISTS qf_site_courant();
DROP FUNCTION IF EXISTS enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS decrementer_stock_vente(INTEGER, INTEGER, INTEGER, VARCHAR);

-- Retrait des privilèges DANS CETTE BASE, puis suppression des rôles.
--
-- ATTENTION : un rôle PostgreSQL est global au SERVEUR, pas propre à une base.
-- Si les mêmes rôles servent à une autre base du même serveur (une base de
-- test à côté de la base réelle, par exemple), leur suppression est refusée.
-- L'annulation ne doit pas échouer pour autant : elle retire tous les droits
-- dans la base courante et signale que le rôle subsiste ailleurs.
DO $$
DECLARE
    r TEXT;
BEGIN
    FOREACH r IN ARRAY ARRAY['qf_responsable', 'qf_agent_stock', 'qf_agent_comptabilite', 'qf_app'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM %I', r);
            EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', r);
            EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I', r);
            EXECUTE format('REVOKE ALL ON SCHEMA public FROM %I', r);
            EXECUTE format('DROP OWNED BY %I', r);
            BEGIN
                EXECUTE format('DROP ROLE %I', r);
            EXCEPTION WHEN dependent_objects_still_exist OR insufficient_privilege THEN
                RAISE NOTICE
                  'Rôle « % » conservé : il est encore utilisé par une autre base '
                  'de ce serveur. Tous ses droits ont été retirés de la base courante.', r;
            END;
        END IF;
    END LOOP;
END
$$;

-- Rétablit l'ouverture par défaut du schéma public (état d'origine).
GRANT USAGE ON SCHEMA public TO PUBLIC;

ALTER TABLE articles ALTER COLUMN prix_vente DROP DEFAULT;

DELETE FROM schema_migrations WHERE version = '008';
