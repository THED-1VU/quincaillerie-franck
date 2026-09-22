-- ============================================================================
-- 033 — Chantier C2 (cycle 38) : durée de session définitive + réinitialisation
--        du mot de passe d'un agent par le responsable.
-- ----------------------------------------------------------------------------
-- Décisions du propriétaire (2026-09-22) :
--   * durée de session : 8 heures (480 minutes) — formalise la valeur déjà
--     utilisée par config.ini ; la base cesse d'être « a_definir » ;
--   * réinitialisation : le responsable SAISIT le nouveau mot de passe
--     (>= 8 caractères), jamais affiché ensuite ; l'agent devra le changer à
--     sa première connexion (doit_changer_mot_de_passe forcé).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Durée de session : décidée, tracée par le déclencheur des paramètres.
-- ----------------------------------------------------------------------------
UPDATE parametres SET
    valeur = '480',
    a_decider = FALSE,
    utilisateur_id = (SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1),
    reference_decision = 'décision propriétaire 2026-09-22 (8 heures)'
  WHERE cle = 'duree_session_minutes';

-- Le serveur lit désormais ce paramètre à chaque connexion. Plutôt que
-- d'exposer la table `parametres` à qf_app (rôle de connexion du serveur),
-- une fonction SECURITY DEFINER dédiée ouvre une fenêtre minimale : la
-- durée décidée, ou NULL si elle ne l'est pas encore.
CREATE OR REPLACE FUNCTION duree_session_minutes_decidee()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_valeur  TEXT;
    v_decider BOOLEAN;
BEGIN
    SELECT valeur, a_decider INTO v_valeur, v_decider
      FROM parametres WHERE cle = 'duree_session_minutes';
    IF v_valeur IS NULL OR v_valeur = 'a_definir' OR v_decider THEN
        RETURN NULL;
    END IF;
    RETURN v_valeur::INTEGER;
END;
$$;

REVOKE ALL ON FUNCTION duree_session_minutes_decidee() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION duree_session_minutes_decidee() TO qf_app;

-- ----------------------------------------------------------------------------
-- 2. Réinitialisation du mot de passe d'un agent par le responsable.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION reinitialiser_mot_de_passe_agent(
    p_compte_id            INTEGER,
    p_nouveau_mot_de_passe VARCHAR,
    p_responsable_id       INTEGER
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_role VARCHAR(30);
BEGIN
    IF p_nouveau_mot_de_passe IS NULL OR length(p_nouveau_mot_de_passe) < 8 THEN
        RAISE EXCEPTION 'Le mot de passe doit faire au moins 8 caractères.'
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT role INTO v_role FROM utilisateurs WHERE id = p_compte_id;
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'Compte % introuvable.', p_compte_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_role = 'responsable' THEN
        RAISE EXCEPTION 'La réinitialisation par le responsable ne vise que les comptes agents.'
          USING ERRCODE = 'check_violation';
    END IF;

    -- Le mot de passe n'est JAMAIS lu ni restitué : seule sa forme hachée
    -- est écrite (bcrypt $2a$, 12 tours — cohérent avec la migration 023).
    UPDATE utilisateurs
       SET mot_de_passe_hash = crypt(p_nouveau_mot_de_passe, gen_salt('bf', 12)),
           doit_changer_mot_de_passe = TRUE,
           tentatives_echouees = 0
     WHERE id = p_compte_id;

    INSERT INTO journal_comptes
        (utilisateur_cible_id, action, ancienne_valeur, nouvelle_valeur,
         utilisateur_auteur_id, date_action)
    VALUES
        (p_compte_id, 'reinitialisation_mot_de_passe', NULL, NULL,
         p_responsable_id, NOW());
END;
$$;

REVOKE ALL ON FUNCTION reinitialiser_mot_de_passe_agent(INTEGER, VARCHAR, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION reinitialiser_mot_de_passe_agent(INTEGER, VARCHAR, INTEGER)
  TO qf_responsable;

INSERT INTO schema_migrations (version, nom)
VALUES ('033', 'session_reset_mot_de_passe')
ON CONFLICT (version) DO NOTHING;
