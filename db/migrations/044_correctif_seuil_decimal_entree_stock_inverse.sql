-- ============================================================================
-- 044 (inverse) — restaure enregistrer_entree_stock() dans son état
-- précédent (seuil TOUJOURS arrondi à 3 décimales, y compris pour un
-- article n'autorisant pas les quantités décimales).
--
-- Corps capturé par introspection sur la base juste avant la migration 044
-- (\sf enregistrer_entree_stock), pas retapé de mémoire.
-- ============================================================================

CREATE OR REPLACE FUNCTION enregistrer_entree_stock(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       NUMERIC(12,3),
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT 'entrée de stock'
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    pourcentage   NUMERIC;
    plancher      NUMERIC(12,3);
    nouveau_seuil NUMERIC(12,3);
    stock_final   NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité reçue invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    PERFORM 1 FROM sites WHERE id = p_site_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Site % introuvable.', p_site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND p_site_id IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut réceptionner que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    pourcentage := parametre_numerique('seuil_alerte_pourcentage');
    plancher    := parametre_numerique('seuil_alerte_plancher');
    nouveau_seuil := GREATEST(plancher, ROUND(p_quantite * pourcentage / 100.0, 3));

    INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
    VALUES (p_article_id, p_site_id, 0, 0)
    ON CONFLICT (article_id, site_id) DO NOTHING;

    PERFORM 1 FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id FOR UPDATE;

    UPDATE stocks_sites
       SET quantite_stock = quantite_stock + p_quantite,
           seuil_alerte   = nouveau_seuil
     WHERE article_id = p_article_id AND site_id = p_site_id
     RETURNING quantite_stock INTO stock_final;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, p_site_id, 'entree', 'reception_fournisseur', p_quantite, p_motif, p_utilisateur_id);

    RETURN stock_final;
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_agent_stock, qf_responsable;

DELETE FROM schema_migrations WHERE version = '044';
