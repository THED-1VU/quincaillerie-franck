-- ============================================================================
-- 036 (inverse) — retire le flux déclaration/validation, restaure les
--                  fonctions directes à un seul temps (état de la
--                  migration 034).
-- ----------------------------------------------------------------------------
-- ATTENTION : si des déclarations réelles existent déjà (validées ou en
-- attente), cette migration inverse REFUSE de continuer plutôt que de les
-- effacer silencieusement — même principe que la migration 034 (inverse).
-- ============================================================================

DO $$
DECLARE
    v_message TEXT := '';
BEGIN
    IF EXISTS (SELECT 1 FROM declarations_casse) THEN
        v_message := v_message || 'declarations_casse ';
    END IF;
    IF EXISTS (SELECT 1 FROM declarations_retour_client) THEN
        v_message := v_message || 'declarations_retour_client ';
    END IF;
    IF v_message <> '' THEN
        RAISE EXCEPTION
          'Migration inverse 036 refusée : des déclarations réelles existent dans : %. '
          'Les traiter (valider ou archiver) manuellement d''abord si c''est vraiment voulu.', v_message
          USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

-- ----------------------------------------------------------------------------
-- Restaure enregistrer_retour_client() (état de la migration 034).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS valider_retour_client(INTEGER, INTEGER, BOOLEAN);
DROP FUNCTION IF EXISTS declarer_retour_client(INTEGER, INTEGER, NUMERIC, VARCHAR, VARCHAR, INTEGER, VARCHAR);

CREATE OR REPLACE FUNCTION enregistrer_retour_client(
    p_article_id     INTEGER,
    p_vente_id       INTEGER,
    p_quantite       NUMERIC(12,3),
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT NULL
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    site_vente         INTEGER;
    qte_vendue         NUMERIC(12,3);
    qte_deja_retournee NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT site_id INTO site_vente FROM ventes WHERE id = p_vente_id;
    IF site_vente IS NULL THEN
        RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND site_vente IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

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

    INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
    VALUES (p_article_id, site_vente, 0, 0)
    ON CONFLICT (article_id, site_id) DO NOTHING;

    UPDATE stocks_sites SET quantite_stock = quantite_stock + p_quantite
     WHERE article_id = p_article_id AND site_id = site_vente;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (p_article_id, site_vente, 'entree', 'retour_client', p_quantite, p_motif, p_utilisateur_id, p_vente_id);

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = p_article_id AND site_id = site_vente);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

DROP TABLE IF EXISTS declarations_retour_client;

-- ----------------------------------------------------------------------------
-- Restaure enregistrer_casse() (état de la migration 034).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS valider_casse(INTEGER, INTEGER);
DROP FUNCTION IF EXISTS declarer_casse(INTEGER, INTEGER, NUMERIC, VARCHAR, INTEGER, VARCHAR);

CREATE OR REPLACE FUNCTION enregistrer_casse(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       NUMERIC(12,3),
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_actuel NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour une casse.' USING ERRCODE = 'check_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND p_site_id IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer une casse que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    PERFORM 1 FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % sans stock au site %.', p_article_id, p_site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    SELECT quantite_stock INTO stock_actuel
      FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id;
    IF stock_actuel < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour déclarer une casse de % : % disponible(s).',
          p_quantite, stock_actuel
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE stocks_sites SET quantite_stock = quantite_stock - p_quantite
     WHERE article_id = p_article_id AND site_id = p_site_id;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, p_site_id, 'sortie', 'casse', p_quantite, p_motif, p_utilisateur_id);

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_casse(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_casse(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) TO qf_responsable;

DROP TABLE IF EXISTS declarations_casse;

DELETE FROM schema_migrations WHERE version = '036';
