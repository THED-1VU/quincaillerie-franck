-- ============================================================================
-- 047 (inverse) — retire montant_retourne et restaure encours_client(),
-- vieillissement_creances() et valider_retour_client() dans leur état
-- précédent (migration 045). REFUSE si un retour a déjà réduit une
-- créance réelle (historique non destructible).
--
-- Corps capturés par introspection sur la base juste avant la migration
-- 047, pas retapés de mémoire.
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM creances WHERE montant_retourne > 0) THEN
        RAISE EXCEPTION
          'Migration inverse 047 refusée : au moins un retour a déjà réduit '
          'une créance réelle (montant_retourne > 0). Aucun retrait possible '
          '(historique non destructible).'
          USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION valider_retour_client(
    p_declaration_id INTEGER,
    p_valideur_id INTEGER,
    p_confirmation_remboursement BOOLEAN DEFAULT FALSE
) RETURNS NUMERIC
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_article_id      INTEGER;
    v_vente_id        INTEGER;
    v_site_id         INTEGER;
    v_quantite        NUMERIC(12,3);
    v_issue           VARCHAR(30);
    v_etat            VARCHAR(20);
    v_motif           VARCHAR(200);
    v_statut          VARCHAR(20);
    v_mouvement_id    INTEGER;
    v_prix_moyen      NUMERIC(12,2);
    v_montant         NUMERIC(12,2);
    stock_final       NUMERIC(12,3);
BEGIN
    SELECT article_id, vente_id, site_id, quantite, issue, etat_marchandise, motif, statut
      INTO v_article_id, v_vente_id, v_site_id, v_quantite, v_issue, v_etat, v_motif, v_statut
      FROM declarations_retour_client WHERE id = p_declaration_id FOR UPDATE;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Déclaration de retour % introuvable.', p_declaration_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_statut = 'validee' THEN
        RAISE EXCEPTION 'Déclaration de retour % déjà validée.', p_declaration_id
          USING ERRCODE = 'restrict_violation';
    END IF;

    IF v_issue = 'remboursement_especes' AND NOT p_confirmation_remboursement THEN
        RAISE EXCEPTION 'Confirmation explicite requise pour valider un remboursement espèces.'
          USING ERRCODE = 'check_violation';
    END IF;

    IF v_etat = 'revendable' THEN
        INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
        VALUES (v_article_id, v_site_id, 0, 0)
        ON CONFLICT (article_id, site_id) DO NOTHING;

        UPDATE stocks_sites SET quantite_stock = quantite_stock + v_quantite
         WHERE article_id = v_article_id AND site_id = v_site_id;

        INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
        VALUES (v_article_id, v_site_id, 'entree', 'retour_client', v_quantite, v_motif, p_valideur_id, v_vente_id)
        RETURNING id INTO v_mouvement_id;
    ELSE
        v_mouvement_id := NULL;
    END IF;

    IF v_issue = 'remboursement_especes' THEN
        SELECT COALESCE(SUM(quantite * prix_unitaire) / NULLIF(SUM(quantite), 0), 0)
          INTO v_prix_moyen
          FROM ventes_lignes WHERE vente_id = v_vente_id AND article_id = v_article_id;
        v_montant := v_quantite * v_prix_moyen;

        INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
        VALUES (v_site_id, p_valideur_id, 'depense', v_montant,
                'Remboursement espèces — retour vente #' || v_vente_id, v_vente_id);
    END IF;

    UPDATE declarations_retour_client
       SET statut = 'validee', valideur_id = p_valideur_id, date_validation = NOW(),
           mouvement_id = v_mouvement_id
     WHERE id = p_declaration_id;

    SELECT quantite_stock INTO stock_final
      FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id;
    RETURN COALESCE(stock_final, 0);
END;
$$;

CREATE OR REPLACE FUNCTION encours_client(p_client_id INTEGER)
RETURNS NUMERIC(12,2)
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE((SELECT SUM(montant) FROM creances WHERE client_id = p_client_id AND NOT annulee), 0)
         - COALESCE((SELECT SUM(montant) FROM reglements_creances WHERE client_id = p_client_id), 0);
$$;

CREATE OR REPLACE FUNCTION vieillissement_creances()
RETURNS TABLE(tranche VARCHAR, montant NUMERIC)
LANGUAGE sql
STABLE
AS $$
    WITH cumul AS (
        SELECT c.id, c.client_id, c.montant, c.date_creance,
               COALESCE(
                 SUM(c.montant) OVER (PARTITION BY c.client_id
                                       ORDER BY c.date_creance, c.id
                                       ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
                 0
               ) AS cumul_avant
          FROM creances c
         WHERE NOT c.annulee
    ),
    regle AS (
        SELECT client_id, SUM(montant) AS total_regle
          FROM reglements_creances
         GROUP BY client_id
    ),
    restant AS (
        SELECT cu.date_creance,
               GREATEST(0, cu.montant - GREATEST(0, COALESCE(r.total_regle, 0) - cu.cumul_avant)) AS montant_restant
          FROM cumul cu
          LEFT JOIN regle r ON r.client_id = cu.client_id
    )
    SELECT
      CASE
        WHEN CURRENT_DATE - date_creance::date <= 30 THEN '0-30'
        WHEN CURRENT_DATE - date_creance::date <= 60 THEN '31-60'
        WHEN CURRENT_DATE - date_creance::date <= 90 THEN '61-90'
        ELSE '91+'
      END AS tranche,
      SUM(montant_restant) AS montant
      FROM restant
     WHERE montant_restant > 0
     GROUP BY 1;
$$;

DROP FUNCTION IF EXISTS detail_paiement_vente(INTEGER);

ALTER TABLE creances DROP CONSTRAINT IF EXISTS chk_creances_montant_retourne;
ALTER TABLE creances DROP COLUMN IF EXISTS montant_retourne;

DELETE FROM schema_migrations WHERE version = '047';
