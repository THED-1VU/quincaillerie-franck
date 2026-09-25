-- ============================================================================
-- 040 (inverse) — restaure vendeur_id -> utilisateurs(id) (état de la
--                  migration 020).
-- ----------------------------------------------------------------------------
-- ATTENTION : si des ventes réelles portent déjà un vendeur_id (référençant
-- un employé), cette migration inverse REFUSE de continuer plutôt que de
-- les effacer silencieusement — même principe que les migrations
-- 034/036/039.
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM ventes WHERE vendeur_id IS NOT NULL) THEN
        RAISE EXCEPTION
          'Migration inverse 040 refusée : des ventes portent déjà un '
          'vendeur_id (référençant employes). Les traiter manuellement '
          'd''abord si c''est vraiment voulu.'
          USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

ALTER TABLE ventes DROP CONSTRAINT ventes_vendeur_id_fkey;
ALTER TABLE ventes ADD CONSTRAINT ventes_vendeur_id_fkey
  FOREIGN KEY (vendeur_id) REFERENCES utilisateurs(id);

COMMENT ON COLUMN ventes.vendeur_id IS
    'Personne ayant négocié le prix et rempli la ligne du facturier papier '
    '(addendum point c) — distincte de utilisateur_id (qui saisit) et de '
    'utilisateur_caisse_id (qui encaisse), même si les trois coïncident '
    'souvent en pratique. Référence toujours un compte existant '
    '(question 3 non tranchée : pas de liste de vendeurs séparée).';

DELETE FROM schema_migrations WHERE version = '040';
