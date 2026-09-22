-- ============================================================================
-- 032 — Chantier C7 (cycle 36) : régularisation d'un écart de comptage et
--        plafond de vraisemblance.
-- ----------------------------------------------------------------------------
-- Décisions du propriétaire (2026-09-22) :
--   * 4 types de résolution : erreur_de_comptage, retrouve, vol_presume,
--     casse_deja_enregistree — motif OBLIGATOIRE sauf pour
--     erreur_de_comptage ;
--   * la régularisation TRACE UNIQUEMENT la décision : elle ne modifie
--     JAMAIS le stock — toute correction physique passe par les fonctions
--     C4 existantes (réception, casse, transfert) ;
--   * plafond de vraisemblance du comptage : paramètre créé à `a_definir` —
--     AUCUN comptage n'est refusé tant que le propriétaire ne fixe pas de
--     valeur. La mécanique de refus est prête (route), pas activée.
-- ============================================================================

CREATE TABLE regularisations_ecarts_comptage (
    id                  SERIAL PRIMARY KEY,
    comptage_id         INTEGER NOT NULL UNIQUE REFERENCES comptages_stock(id),
    type_resolution     VARCHAR(30) NOT NULL,
    motif               VARCHAR(200),
    decide_par_id       INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_regularisation TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_regularisation_type
      CHECK (type_resolution IN ('erreur_de_comptage', 'retrouve',
                                 'vol_presume', 'casse_deja_enregistree')),
    CONSTRAINT chk_regularisation_motif
      CHECK (type_resolution = 'erreur_de_comptage'
             OR (motif IS NOT NULL AND length(btrim(motif)) > 0))
);

COMMENT ON TABLE regularisations_ecarts_comptage IS
  'Décision du responsable sur un écart de comptage constaté. Traçabilité '
  'PURE : aucune ligne de cette table ne modifie le stock — la correction '
  'physique passe par les fonctions du chantier C4 (décision 2026-09-22).';

ALTER TABLE regularisations_ecarts_comptage ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_regularisations_comptage_site ON regularisations_ecarts_comptage;
CREATE POLICY p_regularisations_comptage_site ON regularisations_ecarts_comptage
  USING (current_user = 'qf_responsable')
  WITH CHECK (current_user = 'qf_responsable');

GRANT SELECT ON regularisations_ecarts_comptage TO qf_responsable;

-- ----------------------------------------------------------------------------
-- Fonction SECURITY DEFINER : seule voie d'écriture, réservée au responsable.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION regulariser_ecart_comptage(
    p_comptage_id     INTEGER,
    p_type_resolution VARCHAR,
    p_decide_par_id   INTEGER,
    p_motif           VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_ecart      INTEGER;
    v_id         INTEGER;
BEGIN
    IF p_type_resolution NOT IN ('erreur_de_comptage', 'retrouve',
                                 'vol_presume', 'casse_deja_enregistree') THEN
        RAISE EXCEPTION 'Type de résolution invalide : %.', p_type_resolution
          USING ERRCODE = 'check_violation';
    END IF;
    IF p_type_resolution <> 'erreur_de_comptage'
       AND (p_motif IS NULL OR length(btrim(p_motif)) = 0) THEN
        RAISE EXCEPTION 'Motif obligatoire pour cette résolution.'
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT ecart INTO v_ecart FROM comptages_stock WHERE id = p_comptage_id;
    IF v_ecart IS NULL THEN
        RAISE EXCEPTION 'Comptage % introuvable.', p_comptage_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_ecart = 0 THEN
        RAISE EXCEPTION 'Le comptage % ne porte aucun écart : rien à régulariser.',
          p_comptage_id
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM regularisations_ecarts_comptage
      WHERE comptage_id = p_comptage_id;
    IF FOUND THEN
        RAISE EXCEPTION 'Une résolution est déjà enregistrée pour ce comptage.'
          USING ERRCODE = 'unique_violation';
    END IF;

    INSERT INTO regularisations_ecarts_comptage
        (comptage_id, type_resolution, motif, decide_par_id, date_regularisation)
    VALUES (p_comptage_id, p_type_resolution, p_motif, p_decide_par_id, NOW())
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

REVOKE ALL ON FUNCTION regulariser_ecart_comptage(INTEGER, VARCHAR, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION regulariser_ecart_comptage(INTEGER, VARCHAR, INTEGER, VARCHAR)
  TO qf_responsable;

-- ----------------------------------------------------------------------------
-- Plafond de vraisemblance : mécanique prête, NON activée (a_definir).
-- ----------------------------------------------------------------------------
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
VALUES ('plafond_vraisemblance_comptage', 'a_definir', 'entier',
        'Quantité comptée maximale acceptée sur une ligne de comptage. Tant que '
        'cette valeur n''est pas fixée par le propriétaire, AUCUN comptage n''est '
        'refusé pour vraisemblance.',
        TRUE, TRUE, 'décision propriétaire 2026-09-22 — à fixer')
ON CONFLICT (cle) DO NOTHING;

INSERT INTO schema_migrations (version, nom)
VALUES ('032', 'regularisation_ecart_comptage')
ON CONFLICT (version) DO NOTHING;
