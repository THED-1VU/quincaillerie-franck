-- Annule la migration 016 : restaure enregistrer_retour_client() et
-- enregistrer_retour_fournisseur() à leur corps exact d'avant ce cycle
-- (migration 014), sans les vérifications de cohérence avec le document
-- d'origine.

CREATE OR REPLACE FUNCTION enregistrer_retour_client(
    p_article_id     INTEGER,
    p_vente_id       INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    site_article INTEGER;
    site_vente   INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    SELECT site_id INTO site_article FROM articles WHERE id = p_article_id;

    SELECT site_id INTO site_vente FROM ventes WHERE id = p_vente_id;
    IF site_vente IS NULL THEN
        RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF site_vente IS DISTINCT FROM site_article THEN
        RAISE EXCEPTION 'La vente % n''appartient pas au même site que l''article %.',
          p_vente_id, p_article_id
          USING ERRCODE = 'check_violation';
    END IF;

    IF qf_site_courant() IS NOT NULL AND site_article IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    UPDATE articles SET quantite_stock = quantite_stock + p_quantite WHERE id = p_article_id;

    INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (p_article_id, 'entree', 'retour_client', p_quantite, p_motif, p_utilisateur_id, p_vente_id);

    RETURN (SELECT quantite_stock FROM articles WHERE id = p_article_id);
END;
$$;

CREATE OR REPLACE FUNCTION enregistrer_retour_fournisseur(
    p_mouvement_origine_id INTEGER,
    p_quantite             INTEGER,
    p_utilisateur_id       INTEGER,
    p_motif                VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_article_id INTEGER;
    v_categorie  VARCHAR(30);
    v_type       VARCHAR(20);
    v_site       INTEGER;
    stock_actuel INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    SELECT article_id, categorie, type INTO v_article_id, v_categorie, v_type
      FROM mouvements_stock WHERE id = p_mouvement_origine_id;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Mouvement d''origine % introuvable.', p_mouvement_origine_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_categorie <> 'reception_fournisseur' OR v_type <> 'entree' THEN
        RAISE EXCEPTION 'Le mouvement % n''est pas une réception fournisseur.', p_mouvement_origine_id
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT site_id INTO v_site FROM articles WHERE id = v_article_id;
    IF qf_site_courant() IS NOT NULL AND v_site IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    PERFORM 1 FROM articles WHERE id = v_article_id FOR UPDATE;
    SELECT quantite_stock INTO stock_actuel FROM articles WHERE id = v_article_id;
    IF stock_actuel < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour un retour fournisseur de % : % disponible(s).',
          p_quantite, stock_actuel
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE articles SET quantite_stock = quantite_stock - p_quantite WHERE id = v_article_id;

    INSERT INTO mouvements_stock
        (article_id, type, categorie, quantite, motif, utilisateur_id, mouvement_origine_id)
    VALUES
        (v_article_id, 'sortie', 'retour_fournisseur', p_quantite, p_motif, p_utilisateur_id, p_mouvement_origine_id);

    RETURN (SELECT quantite_stock FROM articles WHERE id = v_article_id);
END;
$$;

DELETE FROM schema_migrations WHERE version = '016';
