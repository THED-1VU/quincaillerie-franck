-- ============================================================================
-- 047 — Correctif : un retour client sur une vente à crédit pouvait donner
-- lieu à un remboursement en espèces, inventant une dépense pour de
-- l'argent jamais réellement encaissé (voir incident consigné dans
-- RAPPORT AVANCEMENT/loop-state.md — le même défaut qu'annuler_vente(),
-- corrigé migration 045, trouvé une deuxième fois en le cherchant
-- délibérément).
-- ----------------------------------------------------------------------------
-- Règle du propriétaire (2026-09-26) : un retour réduit D'ABORD la créance
-- restante. Si la valeur du retour dépasse ce qui reste dû, la créance
-- tombe à zéro et SEUL l'excédent devient un remboursement en espèces —
-- puisque le client a réellement versé cet argent-là. Un maçon qui a acheté
-- à crédit, versé un acompte, puis rapporte un article défectueux, doit
-- pouvoir se faire rembourser l'excédent sans que le retour soit refusé.
--
-- Mécanique : montant_retourne (append-only sur creances, jamais une
-- modification de montant lui-même) réduit le montant EFFECTIF de la
-- créance (montant - montant_retourne) partout où encours_client() et
-- vieillissement_creances() utilisaient montant. Le "restant dû" de LA
-- créance de cette vente est recalculé avec la même formule FIFO que
-- vieillissement_creances() (cumul des créances plus anciennes du même
-- client, réglées en premier) :
--   réduction_dette = MIN(valeur_retour, restant_dû)
--   excédent_especes = valeur_retour - réduction_dette   (jamais négatif)
-- Une créance intégralement impayée absorbe tout le retour (réduction =
-- valeur_retour, excédent = 0) ; une créance intégralement réglée laisse
-- tout partir en espèces (réduction = 0, excédent = valeur_retour) — les
-- deux extrêmes de la même formule, pas des cas séparés.
-- ============================================================================

ALTER TABLE creances ADD COLUMN montant_retourne NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE creances ADD CONSTRAINT chk_creances_montant_retourne
  CHECK (montant_retourne >= 0 AND montant_retourne <= montant);

COMMENT ON COLUMN creances.montant_retourne IS
  'Réduction cumulée par retour client (migration 047) — append-only, comme '
  'annulee : jamais une modification de montant lui-même. Le montant EFFECTIF '
  'd''une créance est toujours (montant - montant_retourne).';

-- ----------------------------------------------------------------------------
-- encours_client() — le montant effectif remplace montant partout.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION encours_client(p_client_id INTEGER)
RETURNS NUMERIC(12,2)
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE((SELECT SUM(montant - montant_retourne) FROM creances
                       WHERE client_id = p_client_id AND NOT annulee), 0)
         - COALESCE((SELECT SUM(montant) FROM reglements_creances WHERE client_id = p_client_id), 0);
$$;

-- ----------------------------------------------------------------------------
-- vieillissement_creances() — idem : montant effectif partout, y compris
-- dans le cumul FIFO (une créance déjà réduite par un retour compte pour
-- moins dans le cumul des créances plus anciennes vues par les suivantes).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION vieillissement_creances()
RETURNS TABLE(tranche VARCHAR, montant NUMERIC)
LANGUAGE sql
STABLE
AS $$
    WITH cumul AS (
        SELECT c.id, c.client_id, (c.montant - c.montant_retourne) AS montant_effectif, c.date_creance,
               COALESCE(
                 SUM(c.montant - c.montant_retourne) OVER (PARTITION BY c.client_id
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
               GREATEST(0, cu.montant_effectif - GREATEST(0, COALESCE(r.total_regle, 0) - cu.cumul_avant)) AS montant_restant
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

-- ----------------------------------------------------------------------------
-- valider_retour_client() — un remboursement espèces sur une vente à crédit
-- réduit d'abord la créance ; seul l'excédent (au-delà de ce qui reste dû)
-- devient une dépense réelle. Comportement inchangé pour toute vente qui
-- n'est pas à crédit.
-- ----------------------------------------------------------------------------
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
    v_article_id        INTEGER;
    v_vente_id          INTEGER;
    v_site_id           INTEGER;
    v_quantite          NUMERIC(12,3);
    v_issue             VARCHAR(30);
    v_etat              VARCHAR(20);
    v_motif             VARCHAR(200);
    v_statut            VARCHAR(20);
    v_mouvement_id      INTEGER;
    v_prix_moyen        NUMERIC(12,2);
    v_montant           NUMERIC(12,2);
    stock_final         NUMERIC(12,3);
    v_mode_paiement     VARCHAR(30);
    v_creance_id        INTEGER;
    v_client_id         INTEGER;
    v_creance_montant   NUMERIC(12,2);
    v_creance_retourne  NUMERIC(12,2);
    v_creance_date      TIMESTAMP;
    v_cumul_avant       NUMERIC(12,2);
    v_total_regle       NUMERIC(12,2);
    v_restant_du        NUMERIC(12,2);
    v_reduction_dette   NUMERIC(12,2);
    v_excedent_especes  NUMERIC(12,2);
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

        SELECT mode_paiement INTO v_mode_paiement FROM ventes WHERE id = v_vente_id;

        IF v_mode_paiement = 'credit_client' THEN
            SELECT id, client_id, montant, montant_retourne, date_creance
              INTO v_creance_id, v_client_id, v_creance_montant, v_creance_retourne, v_creance_date
              FROM creances WHERE vente_id = v_vente_id AND NOT annulee;

            IF v_creance_id IS NULL THEN
                -- Créance introuvable ou déjà annulée (vente à crédit
                -- annulée avant la validation de ce retour, cas non
                -- attendu) : traité comme intégralement réglé, tout part
                -- en espèces — jamais de blocage silencieux.
                v_reduction_dette := 0;
                v_excedent_especes := v_montant;
            ELSE
                SELECT COALESCE(SUM(montant - montant_retourne), 0) INTO v_cumul_avant
                  FROM creances
                 WHERE client_id = v_client_id AND NOT annulee
                   AND (date_creance, id) < (v_creance_date, v_creance_id);
                SELECT COALESCE(SUM(montant), 0) INTO v_total_regle
                  FROM reglements_creances WHERE client_id = v_client_id;

                v_restant_du := GREATEST(
                    0,
                    (v_creance_montant - v_creance_retourne) - GREATEST(0, v_total_regle - v_cumul_avant)
                );

                -- Le retour réduit D'ABORD la créance restante ; seul
                -- l'excédent (au-delà de ce qui reste dû) est un
                -- remboursement en espèces réel — décision du propriétaire,
                -- 2026-09-26 : un acompte partiel ne doit jamais bloquer un
                -- retour, la banalité du cas (acompte puis retour) l'exige.
                v_reduction_dette := LEAST(v_montant, v_restant_du);
                v_excedent_especes := v_montant - v_reduction_dette;

                IF v_reduction_dette > 0 THEN
                    UPDATE creances SET montant_retourne = montant_retourne + v_reduction_dette
                     WHERE id = v_creance_id;
                END IF;
            END IF;
        ELSE
            v_reduction_dette := 0;
            v_excedent_especes := v_montant;
        END IF;

        IF v_excedent_especes > 0 THEN
            INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
            VALUES (v_site_id, p_valideur_id, 'depense', v_excedent_especes,
                    'Remboursement espèces — retour vente #' || v_vente_id, v_vente_id);
        END IF;
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

COMMENT ON FUNCTION valider_retour_client(INTEGER, INTEGER, BOOLEAN) IS
  'Un remboursement espèces sur une vente à crédit réduit d''abord la '
  'créance restante (montant_retourne) ; seul l''excédent devient une '
  'dépense réelle (migration 047, trouvé en cherchant délibérément le même '
  'défaut qu''annuler_vente, migration 045).';

-- ----------------------------------------------------------------------------
-- detail_paiement_vente() — pour que GET /stock/retours-client/declarations
-- (server/app/routes/stock.py) montre le mode de paiement de la vente
-- d'origine AVANT que le responsable valide. Cette route reste partagée
-- avec qf_agent_stock (même principe que la liste des casses, migration
-- 036 : un agent stock voit le statut de ses propres déclarations) — un
-- GRANT direct, même column-level, sur ventes/clients/creances aurait
-- élargi ce que "lire les ventes" (db/tests/02_habilitations.sql) protège :
-- SELECT count(*) FROM ventes ne demande AUCUN privilège sur une colonne
-- précise, seulement une existence de droit sur la table — un simple
-- GRANT SELECT (mode_paiement) l'aurait donc rouvert. SECURITY DEFINER,
-- fenêtre minimale, évite ce trou complètement : agent_stock n'obtient
-- toujours aucun accès direct à ventes/clients/creances.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION detail_paiement_vente(p_vente_id INTEGER)
RETURNS TABLE(mode_paiement VARCHAR, client_nom VARCHAR)
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
    SELECT v.mode_paiement, c.nom
      FROM ventes v
      LEFT JOIN creances cr ON cr.vente_id = v.id AND NOT cr.annulee
      LEFT JOIN clients c ON c.id = cr.client_id
     WHERE v.id = p_vente_id;
$$;

COMMENT ON FUNCTION detail_paiement_vente(INTEGER) IS
  'Mode de paiement d''une vente (et le nom du client, pour une vente à '
  'crédit) — pour l''écran de validation des retours (migration 047). '
  'SECURITY DEFINER pour ne jamais élargir ce que qf_agent_stock peut lire '
  'directement sur ventes/clients/creances.';

REVOKE ALL ON FUNCTION detail_paiement_vente(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION detail_paiement_vente(INTEGER)
  TO qf_responsable, qf_agent_stock;

INSERT INTO schema_migrations (version, nom)
VALUES ('047', 'retour_client_credit')
ON CONFLICT (version) DO NOTHING;
