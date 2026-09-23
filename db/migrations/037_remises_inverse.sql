-- ============================================================================
-- 037 (inverse) — retire les remises (par ligne et globale), restaure la
--                  contrainte de prix d'origine (>= 0).
-- ----------------------------------------------------------------------------
-- ATTENTION : si des remises réelles ont déjà été accordées, cette
-- migration inverse REFUSE de continuer plutôt que de les effacer
-- silencieusement — même principe que les migrations 034 et 036.
-- ============================================================================

DO $$
DECLARE
    v_message TEXT := '';
BEGIN
    IF EXISTS (SELECT 1 FROM ventes_lignes WHERE remise_montant <> 0) THEN
        v_message := v_message || 'ventes_lignes.remise_montant ';
    END IF;
    IF EXISTS (SELECT 1 FROM ventes WHERE remise_globale_montant <> 0) THEN
        v_message := v_message || 'ventes.remise_globale_montant ';
    END IF;
    IF v_message <> '' THEN
        RAISE EXCEPTION
          'Migration inverse 037 refusée : des remises réelles existent dans : %. '
          'Les annuler manuellement d''abord si c''est vraiment voulu.', v_message
          USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

DELETE FROM parametres WHERE cle = 'seuil_remise_validation_pct';

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_remise_globale_positive;
ALTER TABLE ventes DROP COLUMN IF EXISTS remise_globale_montant;

ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS chk_ventes_lignes_remise_coherente;
ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS chk_ventes_lignes_remise_positive;

ALTER TABLE ventes_lignes DROP CONSTRAINT chk_ventes_lignes_prix_positif;
ALTER TABLE ventes_lignes ADD CONSTRAINT chk_ventes_lignes_prix_positif
  CHECK (prix_unitaire >= 0);

ALTER TABLE ventes_lignes DROP COLUMN IF EXISTS remise_montant;
ALTER TABLE ventes_lignes DROP COLUMN IF EXISTS prix_catalogue;

DELETE FROM schema_migrations WHERE version = '037';
