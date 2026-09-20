-- ============================================================================
-- 023 — Chantier C0-C (cycle 31) : création du tout premier compte
--        responsable sur une installation neuve.
-- ----------------------------------------------------------------------------
-- Problème de l'œuf et de la poule : la gestion des comptes se fait par le
-- responsable depuis l'application (CDC §3.8, décision du 2026-09-20), mais
-- sur une installation neuve AUCUN responsable n'existe encore pour se
-- connecter. Cette migration fournit l'unique point de création du premier
-- compte : une fonction SECURITY DEFINER, exécutable par le seul rôle
-- applicatif qf_app, appelée par l'outil console
-- db/outils/creer_compte_responsable.ps1.
--
-- Garanties :
--   * refuse si un compte responsable existe déjà (quel que soit son état) ;
--   * identifiant non vide et non déjà utilisé ;
--   * mot de passe d'au moins 8 caractères ;
--   * hache le mot de passe ELLE-MÊME (pgcrypto, bcrypt $2a$ 12 tours — même
--     format que server/app/securite.py) : le mot de passe en clair n'est
--     jamais écrit en base, le hachage n'est jamais restitué ;
--   * trace l'action dans journal_comptes (action 'creation').
--
-- Idempotent (CREATE OR REPLACE).
-- ============================================================================

CREATE OR REPLACE FUNCTION creer_premier_responsable(
    p_nom_complet  VARCHAR,
    p_identifiant  VARCHAR,
    p_mot_de_passe TEXT
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Les contrôles d'entrée d'abord, pour qu'un utilisateur reçoive le
    -- message le plus précis possible ; le garde-fou « responsable existe
    -- déjà » vient en dernier, une fois que les valeurs fournies sont saines.
    IF btrim(p_nom_complet) = '' THEN
        RAISE EXCEPTION 'Le nom complet est obligatoire.';
    END IF;

    IF btrim(p_identifiant) = '' THEN
        RAISE EXCEPTION 'L''identifiant est obligatoire.';
    END IF;

    IF EXISTS (SELECT 1 FROM utilisateurs WHERE identifiant = btrim(p_identifiant)) THEN
        RAISE EXCEPTION 'Cet identifiant est déjà utilisé.';
    END IF;

    -- Longueur minimale volontairement conservatrice (8 caractères) : c'est
    -- une protection technique, pas une règle métier du propriétaire — le
    -- seuil peut être durci plus tard sans changer l'outil qui appelle.
    IF length(p_mot_de_passe) < 8 THEN
        RAISE EXCEPTION 'Le mot de passe doit comporter au moins 8 caractères.';
    END IF;

    IF EXISTS (SELECT 1 FROM utilisateurs WHERE role = 'responsable') THEN
        RAISE EXCEPTION 'Un compte responsable existe déjà : cet outil ne crée que le tout premier.';
    END IF;

    INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash,
                              role, site_id, actif, doit_changer_mot_de_passe)
    VALUES (btrim(p_nom_complet), btrim(p_identifiant),
            crypt(p_mot_de_passe, gen_salt('bf', 12)),
            'responsable', NULL, TRUE, TRUE)
    RETURNING id INTO v_id;

    INSERT INTO journal_comptes (utilisateur_cible_id, action, utilisateur_auteur_id)
    VALUES (v_id, 'creation', v_id);

    RETURN v_id;
END;
$$;

COMMENT ON FUNCTION creer_premier_responsable(VARCHAR, VARCHAR, TEXT) IS
  'Crée le tout premier compte responsable d''une installation neuve. '
  'Refuse si un responsable existe déjà. Hache le mot de passe en interne '
  '(bcrypt $2a$, 12 tours) et ne le restitue jamais. Réservé à qf_app, '
  'appelé par db/outils/creer_compte_responsable.ps1.';

REVOKE ALL ON FUNCTION creer_premier_responsable(VARCHAR, VARCHAR, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION creer_premier_responsable(VARCHAR, VARCHAR, TEXT)
  TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('023', 'premier_compte_responsable')
ON CONFLICT (version) DO NOTHING;
