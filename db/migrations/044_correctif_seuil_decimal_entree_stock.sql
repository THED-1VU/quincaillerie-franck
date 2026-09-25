-- ============================================================================
-- 044 — Correctif : le seuil d'alerte recalculé par enregistrer_entree_stock()
--        pouvait être décimal (20 % d'une quantité entière ordinaire, ex.
--        13 -> 2,6) et se faire refuser par la base pour un article
--        n'autorisant pas les quantités décimales (trigger
--        verifier_decimale_stocks_sites, migration 034).
-- ----------------------------------------------------------------------------
-- Trouvé par exécution en construisant l'outil d'import du stock initial
-- (point j, migration 041) : le même calcul, corrigé là pour
-- enregistrer_inventaire_initial(), existe ICI aussi, dans la fonction de
-- réception fournisseur — le chemin le PLUS quotidien de la boutique.
-- Signalé au propriétaire, qui a demandé la correction immédiate (plus
-- grave qu'un chargement initial ponctuel : une réception ordinaire tombant
-- devant un client).
--
-- Seule enregistrer_entree_stock() est concernée. Vérifié par exécution sur
-- TOUTES les fonctions actuellement en vigueur en base qui touchent à la
-- fois seuil_alerte et un arrondi : transferer_stock() ne recalcule JAMAIS
-- le seuil de la ligne de destination (un défaut différent, laissé de côté
-- — décision du propriétaire, 2026-09-25) ; regulariser_ecart_comptage() ne
-- touche jamais stocks_sites (traçabilité pure, db/README.md).
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
    v_decimale_ok BOOLEAN;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité reçue invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT quantite_decimale_autorisee INTO v_decimale_ok FROM articles WHERE id = p_article_id;
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
    -- Arrondi à l'entier (pas 3 décimales) quand l'article n'autorise pas
    -- les quantités décimales : sinon un pourcentage non rond (13 x 20 % =
    -- 2,6) fait refuser la réception par le trigger de cohérence décimale,
    -- alors même que la quantité reçue, elle, était bien un entier valide.
    nouveau_seuil := GREATEST(
        plancher,
        ROUND(p_quantite * pourcentage / 100.0, CASE WHEN v_decimale_ok THEN 3 ELSE 0 END)
    );

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

INSERT INTO schema_migrations (version, nom)
VALUES ('044', 'correctif_seuil_decimal_entree_stock')
ON CONFLICT (version) DO NOTHING;
