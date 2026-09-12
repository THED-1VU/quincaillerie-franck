-- ============================================================================
-- 012 INVERSE — retour au SELECT sans restriction de colonne (état de la
-- migration 008)
-- ============================================================================

REVOKE SELECT ON comptages_stock FROM qf_agent_stock;
GRANT SELECT ON comptages_stock TO qf_agent_stock;

DELETE FROM schema_migrations WHERE version = '012';
