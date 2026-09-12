-- ============================================================================
-- 011 INVERSE — retour à l'état « à décider » (avant les décisions du
-- cycle 6 sur les points b, d, e de l'addendum)
-- ============================================================================

-- decrementer_stock_vente : retour à la version bloquante de la migration 008.
DROP FUNCTION IF EXISTS decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);

CREATE OR REPLACE FUNCTION decrementer_stock_vente(
    p_article_id     INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT 'vente'
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_restant INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT quantite_stock INTO stock_restant FROM articles WHERE id = p_article_id;

    IF stock_restant < p_quantite THEN
        RAISE EXCEPTION
          'Stock insuffisant pour l''article % : % demandé(s), % disponible(s).',
          p_article_id, p_quantite, stock_restant
          USING ERRCODE = 'check_violation',
                HINT = 'Traitement à trancher — addendum, point e.';
    END IF;

    UPDATE articles
       SET quantite_stock = quantite_stock - p_quantite
     WHERE id = p_article_id
     RETURNING quantite_stock INTO stock_restant;

    INSERT INTO mouvements_stock (article_id, type, quantite, motif, utilisateur_id)
    VALUES (p_article_id, 'sortie', p_quantite, p_motif, p_utilisateur_id);

    RETURN stock_restant;
END;
$$;

REVOKE ALL ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_comptabilite;

DROP TABLE IF EXISTS ecarts_stock_ventes;

UPDATE parametres SET valeur = 'a_definir', a_decider = TRUE WHERE cle = 'regime_fiscal';
UPDATE parametres SET valeur = '0',          a_decider = TRUE WHERE cle = 'taux_tva';
UPDATE parametres SET valeur = 'a_definir', a_decider = TRUE WHERE cle = 'prix_saisis_ttc';
UPDATE parametres SET valeur = 'a_definir', a_decider = TRUE WHERE cle = 'arrondi_montants';

DELETE FROM schema_migrations WHERE version = '011';
