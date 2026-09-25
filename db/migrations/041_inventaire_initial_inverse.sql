-- ============================================================================
-- 041 (inverse) — retire la catégorie inventaire_initial et sa fonction.
-- ----------------------------------------------------------------------------
-- ATTENTION : si des mouvements inventaire_initial réels existent déjà,
-- cette migration inverse REFUSE de continuer plutôt que de les effacer
-- silencieusement — même principe que les migrations 034/036/039/040.
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM mouvements_stock WHERE categorie = 'inventaire_initial') THEN
        RAISE EXCEPTION
          'Migration inverse 041 refusée : des mouvements inventaire_initial '
          'réels existent. Aucun retrait possible (historique non '
          'destructible) — annuler manuellement le chargement concerné '
          'd''abord si c''est vraiment voulu.'
          USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

DROP FUNCTION IF EXISTS enregistrer_inventaire_initial(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR);

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie_type_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie_type_coherent
  CHECK (
    (categorie = 'reception_fournisseur' AND type = 'entree') OR
    (categorie = 'vente'                 AND type = 'sortie') OR
    (categorie = 'casse'                 AND type = 'sortie') OR
    (categorie = 'retour_client'         AND type = 'entree') OR
    (categorie = 'retour_fournisseur'    AND type = 'sortie') OR
    (categorie = 'annulation_vente'      AND type = 'entree') OR
    (categorie = 'transfert') OR
    (categorie = 'article_offert'        AND type = 'sortie')
  );

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie
  CHECK (categorie IN ('reception_fournisseur', 'vente', 'transfert', 'casse',
                        'retour_client', 'retour_fournisseur', 'annulation_vente',
                        'article_offert'));

DELETE FROM schema_migrations WHERE version = '041';
