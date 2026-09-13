-- ============================================================================
-- 016 — Correction des constats n°1 et n°2 du contrôle de boucle après le
--        cycle 9 (n°1 déjà corrigé au cycle 11, application seulement) :
--        un retour client ou fournisseur ne doit jamais dépasser, en
--        article et en quantité, ce que le document d'origine porte
--        réellement.
-- ----------------------------------------------------------------------------
-- CONSTAT (trouvé par exécution, contrôle de boucle après le cycle 9) :
-- enregistrer_retour_client() et enregistrer_retour_fournisseur()
-- (migration 014) ne vérifiaient que le SITE et la NATURE du mouvement
-- référencé — jamais que l'article retourné ait réellement fait partie du
-- document d'origine, ni que la quantité rendue (cumulée sur plusieurs
-- retours) ne dépasse ce qui a réellement été vendu ou reçu. Le
-- « rattachement » n'était qu'une clé étrangère de traçabilité, pas une
-- garantie de cohérence.
--
-- CORRECTIF :
--   * enregistrer_retour_client() : refuse si l'article ne fait pas partie
--     de la vente référencée (ventes_lignes) ; refuse si la quantité déjà
--     retournée pour ce COUPLE (vente, article) plus la quantité demandée
--     dépasserait la quantité réellement vendue dans cette vente précise
--     (pas une limite globale sur l'article — un même article vendu dans
--     une autre vente n'entre pas dans le calcul, cohérent avec « rattaché
--     à la vente d'origine »).
--   * enregistrer_retour_fournisseur() : refuse si la quantité déjà
--     retournée pour CETTE réception précise plus la quantité demandée
--     dépasserait la quantité réellement reçue par ce mouvement.
--
-- N'INVENTE AUCUNE RÈGLE NOUVELLE : applique strictement ce que
-- l'addendum (point f, cycle 9) décrivait déjà — « retour client : entrée
-- rattachée à la vente d'origine » n'a jamais voulu dire « sans rapport
-- avec ce qui a été vendu ».
-- ============================================================================

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
    site_article        INTEGER;
    site_vente          INTEGER;
    qte_vendue          INTEGER;
    qte_deja_retournee  INTEGER;
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

    -- Trouvé par exécution, comme pour transferer_stock() et
    -- enregistrer_entree_stock() ci-dessus : la cohérence vente/article ne
    -- suffit pas, il faut aussi que l'AGENT APPELANT soit bien de ce site
    -- (un agent du Comptoir ne doit pas pouvoir manipuler le stock du
    -- Magasin même via une vente/article tous deux du Magasin).
    IF qf_site_courant() IS NOT NULL AND site_article IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Cohérence article/quantité avec le document d'origine (migration
    -- 016) : l'article doit avoir été réellement vendu dans CETTE vente,
    -- et la quantité rendue (cumulée) ne doit jamais dépasser ce qui a
    -- réellement été vendu pour ce couple (vente, article).
    SELECT COALESCE(SUM(quantite), 0) INTO qte_vendue
      FROM ventes_lignes WHERE vente_id = p_vente_id AND article_id = p_article_id;
    IF qte_vendue = 0 THEN
        RAISE EXCEPTION 'L''article % ne fait pas partie de la vente %.', p_article_id, p_vente_id
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT COALESCE(SUM(quantite), 0) INTO qte_deja_retournee
      FROM mouvements_stock
     WHERE categorie = 'retour_client' AND vente_id = p_vente_id AND article_id = p_article_id;
    IF qte_deja_retournee + p_quantite > qte_vendue THEN
        RAISE EXCEPTION
          'Retour refusé : % déjà rendu(s) + % demandé(s) dépasserait les % vendu(s) pour cet article dans cette vente.',
          qte_deja_retournee, p_quantite, qte_vendue
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE articles SET quantite_stock = quantite_stock + p_quantite WHERE id = p_article_id;
    -- Pas de recalcul du seuil : un retour n'est pas une réception fournisseur.

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
    v_article_id      INTEGER;
    v_categorie       VARCHAR(30);
    v_type            VARCHAR(20);
    v_quantite_recue  INTEGER;
    v_deja_retourne   INTEGER;
    v_site            INTEGER;
    stock_actuel      INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    SELECT article_id, categorie, type, quantite
      INTO v_article_id, v_categorie, v_type, v_quantite_recue
      FROM mouvements_stock WHERE id = p_mouvement_origine_id;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Mouvement d''origine % introuvable.', p_mouvement_origine_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_categorie <> 'reception_fournisseur' OR v_type <> 'entree' THEN
        RAISE EXCEPTION 'Le mouvement % n''est pas une réception fournisseur.', p_mouvement_origine_id
          USING ERRCODE = 'check_violation';
    END IF;

    -- Cohérence quantité avec le document d'origine (migration 016) : la
    -- quantité rendue (cumulée sur tous les retours déjà faits contre
    -- CETTE réception précise) ne doit jamais dépasser ce qui a réellement
    -- été reçu par ce mouvement.
    SELECT COALESCE(SUM(quantite), 0) INTO v_deja_retourne
      FROM mouvements_stock
     WHERE categorie = 'retour_fournisseur' AND mouvement_origine_id = p_mouvement_origine_id;
    IF v_deja_retourne + p_quantite > v_quantite_recue THEN
        RAISE EXCEPTION
          'Retour refusé : % déjà rendu(s) + % demandé(s) dépasserait les % reçu(s) par cette réception.',
          v_deja_retourne, p_quantite, v_quantite_recue
          USING ERRCODE = 'check_violation';
    END IF;

    -- Même garde que pour les autres fonctions ci-dessus : un agent stock ne
    -- retourne au fournisseur que depuis son propre site.
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

INSERT INTO schema_migrations (version, nom)
VALUES ('016', 'retours_coherence_document_origine')
ON CONFLICT (version) DO NOTHING;
