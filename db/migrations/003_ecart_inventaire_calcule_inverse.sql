-- ============================================================================
-- 003 INVERSE — l'écart d'inventaire redevient une colonne ordinaire
-- ----------------------------------------------------------------------------
-- Restaure le comportement d'origine (écart écrit par le client). La valeur
-- recalculée est conservée telle quelle ; la table d'archive des écarts
-- déclarés est supprimée avec le reste.
-- ============================================================================

DROP INDEX IF EXISTS uq_comptage_article_moment_jour;

DROP TRIGGER  IF EXISTS trg_interdire_modification_comptage ON comptages_stock;
DROP FUNCTION IF EXISTS interdire_modification_comptage();

DROP TRIGGER  IF EXISTS trg_figer_quantite_attendue ON comptages_stock;
DROP FUNCTION IF EXISTS figer_quantite_attendue();

-- Repasse « ecart » en colonne ordinaire, en conservant les valeurs calculées.
ALTER TABLE comptages_stock ADD COLUMN IF NOT EXISTS ecart_tmp INTEGER;
UPDATE comptages_stock SET ecart_tmp = ecart;
ALTER TABLE comptages_stock DROP COLUMN IF EXISTS ecart;
ALTER TABLE comptages_stock RENAME COLUMN ecart_tmp TO ecart;
UPDATE comptages_stock SET ecart = 0 WHERE ecart IS NULL;
ALTER TABLE comptages_stock ALTER COLUMN ecart SET NOT NULL;

DROP TABLE IF EXISTS comptages_stock_ecarts_declares;

DELETE FROM schema_migrations WHERE version = '003';
