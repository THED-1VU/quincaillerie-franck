-- ============================================================================
-- 052 (inverse) — Retire les paiements mixtes (décision D2).
-- ----------------------------------------------------------------------------
-- L'attendu de caisse revient à la définition 019 (sommé sur
-- ventes.mode_paiement) ; la contrainte 'mixte' est retirée — elle ne peut
-- s'appliquer que si AUCUNE vente n'est 'mixte'.
-- ============================================================================

DROP POLICY IF EXISTS p_ventes_paiements_site ON ventes_paiements;
REVOKE ALL ON ventes_paiements FROM qf_responsable, qf_agent_comptabilite;
DROP TRIGGER IF EXISTS trg_somme_paiements_vente ON ventes_paiements;
DROP FUNCTION IF EXISTS verifier_somme_paiements_vente();
DROP TABLE IF EXISTS ventes_paiements;

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_mode_paiement;
ALTER TABLE ventes ADD CONSTRAINT ventes_mode_paiement_check
  CHECK (mode_paiement IN
    ('especes', 'orange_money', 'mtn_momo', 'autre', 'credit_client'));

CREATE OR REPLACE FUNCTION calculer_attendu_caisse(p_site_id INTEGER, p_date DATE)
RETURNS TABLE(especes NUMERIC, orange_money NUMERIC, mtn_momo NUMERIC, autre NUMERIC)
LANGUAGE sql
STABLE
AS $$
    SELECT
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'especes'), 0),
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'orange_money'), 0),
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'mtn_momo'), 0),
        COALESCE(SUM(total_ttc) FILTER (WHERE mode_paiement = 'autre'), 0)
      FROM ventes
     WHERE site_id = p_site_id AND statut = 'payee' AND date_encaissement::date = p_date;
$$;

DELETE FROM schema_migrations WHERE version = '052';
