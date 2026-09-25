-- ============================================================================
-- 045 (inverse) — retire le crédit client. REFUSE si des créances ou des
-- règlements réels existent déjà (historique non destructible, même
-- principe que partout ailleurs dans ce projet).
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM creances) THEN
        RAISE EXCEPTION
          'Migration inverse 045 refusée : des créances réelles existent. '
          'Aucun retrait possible (historique non destructible).'
          USING ERRCODE = 'check_violation';
    END IF;
    IF EXISTS (SELECT 1 FROM reglements_creances) THEN
        RAISE EXCEPTION
          'Migration inverse 045 refusée : des règlements réels existent. '
          'Aucun retrait possible (historique non destructible).'
          USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

DROP FUNCTION IF EXISTS enregistrer_creance_initiale(INTEGER, NUMERIC, INTEGER, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS enregistrer_reglement_creance(INTEGER, NUMERIC, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS vieillissement_creances();
DROP FUNCTION IF EXISTS encours_client(INTEGER);

-- Restaure annuler_vente() dans son état précédent (migration 017) — corps
-- capturé par introspection sur la base juste avant la migration 045, pas
-- retapé de mémoire. La créance déjà refusée par le REFUS ci-dessus (des
-- créances réelles existeraient) garantit qu'aucune vente à crédit annulée
-- ne peut exister à ce stade — restaurer le comportement d'origine
-- (dépense systématique) est donc sûr.
CREATE OR REPLACE FUNCTION annuler_vente(
    p_vente_id INTEGER,
    p_utilisateur_id INTEGER,
    p_motif VARCHAR
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

DROP TABLE IF EXISTS reglements_creances;
DROP TABLE IF EXISTS creances;
DROP TABLE IF EXISTS clients;

DELETE FROM parametres WHERE cle = 'credit_client_actif';

DELETE FROM schema_migrations WHERE version = '045';
