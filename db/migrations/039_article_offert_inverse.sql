-- ============================================================================
-- 039 (inverse) — retire l'article offert (déclaration/validation,
--                  catégorie de mouvement, table).
-- ----------------------------------------------------------------------------
-- ATTENTION : si des déclarations réelles existent déjà (validées ou en
-- attente), cette migration inverse REFUSE de continuer plutôt que de les
-- effacer silencieusement — même principe que les migrations 034/036.
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM declarations_article_offert) THEN
        RAISE EXCEPTION
          'Migration inverse 039 refusée : des déclarations d''article offert '
          'réelles existent. Les traiter (valider ou archiver) manuellement '
          'd''abord si c''est vraiment voulu.'
          USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

DROP FUNCTION IF EXISTS valider_article_offert(INTEGER, INTEGER);
DROP FUNCTION IF EXISTS declarer_article_offert(INTEGER, INTEGER, NUMERIC, VARCHAR, INTEGER, INTEGER, INTEGER, VARCHAR);

DROP TABLE IF EXISTS declarations_article_offert;

-- Restaure la contrainte de la migration 017 (avant l'élargissement à
-- article_offert ci-dessus).
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_vente_id_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_vente_id_coherent
  CHECK (
    (categorie IN ('retour_client', 'annulation_vente') AND vente_id IS NOT NULL)
    OR (categorie = 'vente')
    OR (categorie NOT IN ('retour_client', 'annulation_vente', 'vente') AND vente_id IS NULL)
  );

-- Restaure exactement l'état de la migration 017 (PAS 014) : c'est la
-- dernière à avoir posé ces deux contraintes avant 039.
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie_type_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie_type_coherent
  CHECK (
    (categorie = 'reception_fournisseur' AND type = 'entree') OR
    (categorie = 'vente'                 AND type = 'sortie') OR
    (categorie = 'casse'                 AND type = 'sortie') OR
    (categorie = 'retour_client'         AND type = 'entree') OR
    (categorie = 'retour_fournisseur'    AND type = 'sortie') OR
    (categorie = 'annulation_vente'      AND type = 'entree') OR
    (categorie = 'transfert')
  );

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie
  CHECK (categorie IN ('reception_fournisseur', 'vente', 'transfert', 'casse',
                        'retour_client', 'retour_fournisseur', 'annulation_vente'));

DELETE FROM schema_migrations WHERE version = '039';
