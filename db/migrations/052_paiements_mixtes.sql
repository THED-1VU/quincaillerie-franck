-- ============================================================================
-- 052 — Décision D2 (propriétaire, 2026-10-23, cycle 75) : paiements mixtes
--        espèces + Mobile Money sur UNE MÊME vente, traçables par mode.
-- ----------------------------------------------------------------------------
-- Ce qui existait : ventes.mode_paiement = UN seul mode par vente ; l'attendu
-- de caisse (019) sommait total_ttc par ce mode. Une vente réglée moitié
-- espèces, moitié Orange Money était donc impossible à enregistrer sans
-- fausser un des deux modes.
--
-- Choix de structure (figé APRÈS analyse du schéma, comme exigé par l'ordre
-- du cycle 75) :
--   * table ventes_paiements : UNE ligne par (vente, mode) — les composantes
--     séparées, jamais une estimation ; un seul mode par vente reprend
--     exactement l'ancien comportement (une composante = le total) ;
--   * ventes.mode_paiement reste rempli et dit la vérité : le mode unique,
--     ou 'mixte' (ajouté au CHECK) quand plusieurs composantes ;
--   * l'invariant « somme des composantes = total encaissé » est porté PAR
--     LA BASE (trigger de contrainte différé : vérifié à COMMIT, quel que
--     soit le chemin d'écriture, application ou SQL direct) — jamais cru
--     sur parole côté client ;
--   * calculer_attendu_caisse() (019) est réécrite pour sommer les
--     COMPOSANTES : la part espèces alimente la caisse espèces, la part
--     Mobile Money son mode — pour une vente ancienne (backfill : une
--     composante = total), l'attendu est numériquement identique ;
--   * le crédit client garde son chemin DÉDIÉ (045/047) : une vente à
--     crédit n'a AUCUNE composante de paiement (aucun argent entré), les
--     règlements passent par reglements_creances — les créances restent
--     cohérentes, aucun double comptage ;
--   * la recette du journal (transactions) reste UNE par vente, du TOTAL
--     (cahier des charges §3.3) : le journal est sans mode par conception
--     (l'attendu de caisse n'y touche pas, 019), donc aucun double comptage
--     espèces/Mobile Money ;
--   * annulation (017/031) : inchangée — contre-passe le TOTAL par UNE
--     dépense, et la vente annulée sort de l'attendu (statut) ; les
--     composantes restent en base, trace de ce qui avait réellement été
--     réglé, par mode.
--
-- Idempotent (ON CONFLICT / IF EXISTS). Inverse fournie.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Composantes de paiement : une ligne par (vente, mode). Immuables en
-- pratique : pas de DELETE accordé aux rôles applicatifs (annulation et
-- corrections passent par les mécanismes existants, jamais par un effacement).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ventes_paiements (
    id            SERIAL PRIMARY KEY,
    vente_id      INTEGER NOT NULL REFERENCES ventes(id) ON DELETE RESTRICT,
    mode_paiement VARCHAR(20) NOT NULL
                  CHECK (mode_paiement IN ('especes', 'orange_money', 'mtn_momo', 'autre')),
    montant       NUMERIC(12,2) NOT NULL CHECK (montant > 0),
    -- Une seule composante par mode et par vente : « moitié Orange Money,
    -- moitié Orange Money » n'a pas de sens métier et cacherait une erreur
    -- de saisie.
    CONSTRAINT uq_ventes_paiements_mode UNIQUE (vente_id, mode_paiement)
);

CREATE INDEX IF NOT EXISTS idx_ventes_paiements_vente ON ventes_paiements(vente_id);

COMMENT ON TABLE ventes_paiements IS
  'Composantes de paiement par mode (décision D2, 2026-10-23) : une vente '
  'peut être réglée espèces ET Mobile Money. La somme des composantes égale '
  'le total encaissé (trigger de contrainte différé trg_somme_paiements_'
  'vente). Une vente à crédit n''a aucune composante (045) ; une vente à un '
  'seul mode en a exactement une, du total (backfill inclus).';

-- ----------------------------------------------------------------------------
-- Backfill : chaque vente passée encaissée (ou annulée, pour l'historique)
-- reprend UNE composante = son total, dans son mode d'origine — l'attendu
-- de caisse recalculé est numériquement identique à l'ancien. Le crédit
-- client n'a jamais été une recette de caisse (019) : aucune composante.
-- Un montant nul (notamment un brouillon historique) n'est pas un paiement.
-- ----------------------------------------------------------------------------
INSERT INTO ventes_paiements (vente_id, mode_paiement, montant)
SELECT id, mode_paiement, total_ttc
  FROM ventes
 WHERE mode_paiement IN ('especes', 'orange_money', 'mtn_momo', 'autre')
   AND total_ttc > 0
   AND statut IN ('payee', 'annulee')
ON CONFLICT (vente_id, mode_paiement) DO NOTHING;

-- ----------------------------------------------------------------------------
-- ventes.mode_paiement : 'mixte' rejoint la liste quand plusieurs modes ont
-- réellement servi. L'ancienne contrainte anonyme (création_base_donnees.sql)
-- est remplacée par une contrainte NOMMÉE, remplaçable proprement.
-- ----------------------------------------------------------------------------
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS ventes_mode_paiement_check;
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS ventes_mode_paiement;
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_mode_paiement;
ALTER TABLE ventes ADD CONSTRAINT chk_ventes_mode_paiement
  CHECK (mode_paiement IN
    ('especes', 'orange_money', 'mtn_momo', 'autre', 'credit_client', 'mixte'));

-- ----------------------------------------------------------------------------
-- Invariant porté par la base : somme des composantes = total encaissé.
-- Trigger de contrainte DIFFÉRÉ (vérifié à COMMIT) : une vente et ses
-- composantes s'insèrent dans la même transaction, dans n'importe quel
-- ordre ; SQL direct qui tricherait est rejeté aussi (postgres compris).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION verifier_somme_paiements_vente()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_vente_id INTEGER := COALESCE(NEW.vente_id, OLD.vente_id);
    v_total    NUMERIC(12,2);
    v_somme    NUMERIC(12,2);
BEGIN
    SELECT total_ttc INTO v_total FROM ventes WHERE id = v_vente_id;
    IF v_total IS NULL THEN
        RAISE EXCEPTION
          'Vente % introuvable : impossible de vérifier la somme de ses '
          'composantes de paiement.', v_vente_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    SELECT COALESCE(SUM(montant), 0) INTO v_somme
      FROM ventes_paiements WHERE vente_id = v_vente_id;
    IF v_somme <> v_total THEN
        RAISE EXCEPTION
          'Vente % : la somme des composantes de paiement (%) ne correspond '
          'pas au total encaissé (%).', v_vente_id, v_somme, v_total
          USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION verifier_somme_paiements_vente() IS
  'Invariant D2 : la somme des composantes de paiement d''une vente égale '
  'son total encaissé. Trigger de contrainte différé (vérifié à COMMIT), '
  'donc valable pour toute voie d''écriture, application comme SQL direct.';

DROP TRIGGER IF EXISTS trg_somme_paiements_vente ON ventes_paiements;
CREATE CONSTRAINT TRIGGER trg_somme_paiements_vente
  AFTER INSERT OR UPDATE OR DELETE ON ventes_paiements
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION verifier_somme_paiements_vente();

-- ----------------------------------------------------------------------------
-- calculer_attendu_caisse() — SOURCE UNIQUE de l'attendu par mode (019),
-- réécrite pour sommer les composantes. Une vente à un seul mode (et toute
-- vente d'avant 052 via le backfill) donne exactement l'ancien résultat ;
-- une vente mixte répartit sa part espèces dans la caisse espèces et sa
-- part Mobile Money dans le mode correspondant. credit_client reste absent
-- des quatre totaux (aucune composante).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calculer_attendu_caisse(p_site_id INTEGER, p_date DATE)
RETURNS TABLE(especes NUMERIC, orange_money NUMERIC, mtn_momo NUMERIC, autre NUMERIC)
LANGUAGE sql
STABLE
AS $$
    SELECT
        COALESCE(SUM(vp.montant) FILTER (WHERE vp.mode_paiement = 'especes'), 0),
        COALESCE(SUM(vp.montant) FILTER (WHERE vp.mode_paiement = 'orange_money'), 0),
        COALESCE(SUM(vp.montant) FILTER (WHERE vp.mode_paiement = 'mtn_momo'), 0),
        COALESCE(SUM(vp.montant) FILTER (WHERE vp.mode_paiement = 'autre'), 0)
      FROM ventes v
      JOIN ventes_paiements vp ON vp.vente_id = v.id
     WHERE v.site_id = p_site_id AND v.statut = 'payee'
       AND v.date_encaissement::date = p_date;
$$;

COMMENT ON FUNCTION calculer_attendu_caisse(INTEGER, DATE) IS
  'Total attendu par mode de paiement (ventes payee du site et du jour), '
  'sommé depuis les composantes ventes_paiements (décision D2, 2026-10-23) '
  '— la part espèces d''une vente mixte alimente la caisse espèces, la '
  'part Mobile Money son mode. credit_client volontairement absent des 4 '
  'totaux (addendum point b). Utilisée par cloturer_caisse() ET par GET '
  '/caisse/attendu.';

-- ----------------------------------------------------------------------------
-- Cloisonnement : mêmes rôles que ventes (008) — responsable et agent
-- comptabilité lisent et créent ; personne n'efface ni ne modifie une
-- composante (pas de GRANT UPDATE/DELETE : l'annulation contrapasse par
-- une dépense et sort la vente de l'attendu, elle ne réécrit pas l'histoire).
-- ----------------------------------------------------------------------------
GRANT USAGE, SELECT ON SEQUENCE ventes_paiements_id_seq
  TO qf_responsable, qf_agent_comptabilite;
GRANT SELECT, INSERT ON ventes_paiements TO qf_responsable, qf_agent_comptabilite;
REVOKE ALL ON ventes_paiements FROM PUBLIC, qf_agent_stock;

ALTER TABLE ventes_paiements ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_ventes_paiements_site ON ventes_paiements;
CREATE POLICY p_ventes_paiements_site ON ventes_paiements
  USING      (current_user = 'qf_responsable' OR EXISTS (
                SELECT 1 FROM ventes v
                 WHERE v.id = ventes_paiements.vente_id
                   AND v.site_id = qf_site_courant()))
  WITH CHECK (current_user = 'qf_responsable' OR EXISTS (
                SELECT 1 FROM ventes v
                 WHERE v.id = ventes_paiements.vente_id
                   AND v.site_id = qf_site_courant()));

INSERT INTO schema_migrations (version, nom)
VALUES ('052', 'paiements_mixtes')
ON CONFLICT (version) DO NOTHING;
