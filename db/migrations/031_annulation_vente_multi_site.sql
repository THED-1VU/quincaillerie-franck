-- ============================================================================
-- 031 — Chantier 13b (cycle 35) : adapter annuler_vente() au modèle
--        multi-site.
-- ----------------------------------------------------------------------------
-- La migration 028 a réécrit toutes les fonctions de stock SAUF
-- annuler_vente() (migration 017), qui restituait encore sur
-- articles.quantite_stock et insérait des mouvements sans site_id — prouvé
-- cassé par la suite pytest (test_ventes : 0 article restitué). Réécrite
-- ici : la restitution se fait sur stocks_sites (article, site), le
-- mouvement d'annulation porte son site_id.
-- ============================================================================

CREATE OR REPLACE FUNCTION annuler_vente(
    p_vente_id       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR
) RETURNS TABLE(montant_ttc NUMERIC, articles_restitues INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_statut    VARCHAR(20);
    v_site      INTEGER;
    v_total_ttc NUMERIC(12,2);
    r           RECORD;
    v_compte    INTEGER := 0;
BEGIN
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour annuler une vente.' USING ERRCODE = 'check_violation';
    END IF;

    SELECT ventes.statut, ventes.site_id, ventes.total_ttc INTO v_statut, v_site, v_total_ttc
      FROM ventes WHERE id = p_vente_id FOR UPDATE;
    IF v_statut IS NULL THEN
        RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_statut = 'annulee' THEN
        RAISE EXCEPTION 'Vente % déjà annulée.', p_vente_id
          USING ERRCODE = 'restrict_violation';
    END IF;

    FOR r IN
        SELECT article_id, site_id, SUM(quantite) AS quantite
          FROM mouvements_stock
         WHERE categorie = 'vente' AND vente_id = p_vente_id
         GROUP BY article_id, site_id
    LOOP
        INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
        VALUES (r.article_id, r.site_id, 0, 0)
        ON CONFLICT (article_id, site_id) DO NOTHING;

        UPDATE stocks_sites SET quantite_stock = quantite_stock + r.quantite
         WHERE article_id = r.article_id AND site_id = r.site_id;

        INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
        VALUES (r.article_id, r.site_id, 'entree', 'annulation_vente', r.quantite, p_motif, p_utilisateur_id, p_vente_id);
        v_compte := v_compte + 1;
    END LOOP;

    UPDATE ventes
       SET statut = 'annulee', annulee_par_id = p_utilisateur_id, motif_annulation = p_motif
     WHERE id = p_vente_id;

    INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
    VALUES (v_site, p_utilisateur_id, 'depense', v_total_ttc,
            'Annulation de la vente #' || p_vente_id, p_vente_id);

    UPDATE ecarts_stock_ventes
       SET regularise = TRUE, regularise_par_id = p_utilisateur_id, date_regularisation = NOW()
     WHERE vente_id = p_vente_id AND regularise = FALSE;

    RETURN QUERY SELECT v_total_ttc, v_compte;
END;
$$;

REVOKE ALL ON FUNCTION annuler_vente(INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION annuler_vente(INTEGER, INTEGER, VARCHAR) TO qf_responsable;

INSERT INTO schema_migrations (version, nom)
VALUES ('031', 'annulation_vente_multi_site')
ON CONFLICT (version) DO NOTHING;
