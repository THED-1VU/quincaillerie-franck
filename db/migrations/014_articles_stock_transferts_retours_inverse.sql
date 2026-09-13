-- ============================================================================
-- 014 INVERSE — retire le transfert, la casse, les retours, et les colonnes
-- de traçabilité associées sur mouvements_stock
-- ============================================================================

DROP FUNCTION IF EXISTS transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS enregistrer_casse(INTEGER, INTEGER, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, VARCHAR);

-- Restaure enregistrer_entree_stock() et decrementer_stock_vente() à leur
-- état d'avant ce cycle (INSERT sans "categorie", colonne qui n'existe plus
-- après ce fichier) — sinon leur corps référencerait une colonne absente.
CREATE OR REPLACE FUNCTION enregistrer_entree_stock(
    p_article_id     INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT 'entrée de stock'
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    pourcentage  NUMERIC;
    plancher     INTEGER;
    nouveau_seuil INTEGER;
    stock_final  INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité reçue invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    pourcentage := parametre_numerique('seuil_alerte_pourcentage');
    plancher    := parametre_numerique('seuil_alerte_plancher');

    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    nouveau_seuil := GREATEST(plancher, ROUND(p_quantite * pourcentage / 100.0)::INTEGER);

    UPDATE articles
       SET quantite_stock = quantite_stock + p_quantite,
           seuil_alerte   = nouveau_seuil
     WHERE id = p_article_id
     RETURNING quantite_stock INTO stock_final;

    INSERT INTO mouvements_stock (article_id, type, quantite, motif, utilisateur_id)
    VALUES (p_article_id, 'entree', p_quantite, p_motif, p_utilisateur_id);

    RETURN stock_final;
END;
$$;

CREATE OR REPLACE FUNCTION decrementer_stock_vente(
    p_article_id     INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_vente_id       INTEGER,
    p_motif          VARCHAR DEFAULT 'vente'
) RETURNS TABLE(stock_restant INTEGER, quantite_manquante INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_avant         INTEGER;
    quantite_effective  INTEGER;
    manquant            INTEGER;
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

    SELECT quantite_stock INTO stock_avant FROM articles WHERE id = p_article_id;

    quantite_effective := LEAST(p_quantite, stock_avant);
    manquant           := p_quantite - quantite_effective;

    IF quantite_effective > 0 THEN
        UPDATE articles
           SET quantite_stock = quantite_stock - quantite_effective
         WHERE id = p_article_id;

        INSERT INTO mouvements_stock (article_id, type, quantite, motif, utilisateur_id)
        VALUES (p_article_id, 'sortie', quantite_effective, p_motif, p_utilisateur_id);
    END IF;

    IF manquant > 0 THEN
        INSERT INTO ecarts_stock_ventes (article_id, vente_id, quantite_manquante, utilisateur_id)
        VALUES (p_article_id, p_vente_id, manquant, p_utilisateur_id);
    END IF;

    RETURN QUERY SELECT (stock_avant - quantite_effective), manquant;
END;
$$;

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_origine_id_coherent;
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_vente_id_coherent;
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_motif_obligatoire;
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie_type_coherent;
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS fk_mouvements_origine;
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS fk_mouvements_vente;

ALTER TABLE mouvements_stock DROP COLUMN IF EXISTS mouvement_origine_id;
ALTER TABLE mouvements_stock DROP COLUMN IF EXISTS vente_id;
ALTER TABLE mouvements_stock DROP COLUMN IF EXISTS categorie;

DELETE FROM schema_migrations WHERE version = '014';
