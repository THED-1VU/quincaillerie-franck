-- ============================================================================
-- 005 INVERSE — retire les journaux d'audit et le contrôle de statut
-- ============================================================================

DROP TRIGGER  IF EXISTS trg_statut_vente ON ventes;
DROP FUNCTION IF EXISTS controler_changement_statut_vente();

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_annulation_tracee;
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS fk_ventes_annulee_par;
ALTER TABLE ventes DROP COLUMN IF EXISTS motif_annulation;
ALTER TABLE ventes DROP COLUMN IF EXISTS date_annulation;
ALTER TABLE ventes DROP COLUMN IF EXISTS annulee_par_id;

DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON journal_comptes;
DROP TRIGGER IF EXISTS trg_journal_non_supprimable ON journal_connexions;

DROP TABLE IF EXISTS journal_comptes;
DROP TABLE IF EXISTS journal_connexions;

DELETE FROM schema_migrations WHERE version = '005';
