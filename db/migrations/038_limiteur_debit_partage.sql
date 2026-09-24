-- ============================================================================
-- 038 — Chantier C11 (cycle 44) : limiteur de débit PARTAGÉ entre processus.
-- ----------------------------------------------------------------------------
-- Jusqu'ici le limiteur de tentatives de connexion (securite.LimiteurDebit)
-- était EN MÉMOIRE, donc PAR PROCESSUS : deux workers uvicorn = deux
-- compteurs, un attaquant répartit ses essais et contourne. Décision du
-- propriétaire (2026-09-24) : seuil 10 tentatives/minute INCHANGÉ, mais
-- partagé via la base — une seule source de vérité, comme le verrouillage
-- de compte (tentatives_max_connexion, migration 008/009).
-- ============================================================================

CREATE TABLE limitations_debit (
    cle           VARCHAR(150) PRIMARY KEY,
    fenetre_debut TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    compteur      INTEGER     NOT NULL DEFAULT 0
);

COMMENT ON TABLE limitations_debit IS
  'Compteurs du limiteur de débit PARTAGÉ entre processus (cycle 44). '
  'Fenêtre glissante de 60 s par défaut, seuil porté par config.ini '
  '(tentatives_max_par_minute).';

-- Fenêtre glissante atomique : upsert puis verrou de ligne, réinitialisation
-- si la fenêtre est expirée, refus si le seuil est atteint, sinon incrément.
CREATE OR REPLACE FUNCTION tentative_autorisee(
    p_cle               VARCHAR,
    p_max               INTEGER,
    p_fenetre_secondes  INTEGER
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_debut    TIMESTAMPTZ;
    v_compteur INTEGER;
BEGIN
    INSERT INTO limitations_debit (cle, fenetre_debut, compteur)
    VALUES (p_cle, NOW(), 0)
    ON CONFLICT (cle) DO NOTHING;

    SELECT fenetre_debut, compteur INTO v_debut, v_compteur
      FROM limitations_debit WHERE cle = p_cle FOR UPDATE;

    IF v_debut + make_interval(secs => p_fenetre_secondes) <= NOW() THEN
        UPDATE limitations_debit SET fenetre_debut = NOW(), compteur = 1
         WHERE cle = p_cle;
        RETURN TRUE;
    END IF;

    IF v_compteur >= p_max THEN
        RETURN FALSE;
    END IF;

    UPDATE limitations_debit SET compteur = compteur + 1 WHERE cle = p_cle;
    RETURN TRUE;
END;
$$;

-- Une connexion réussie efface le compteur (même règle que le limiteur en
-- mémoire : tâtonner avant de trouver n'a pas à brider après coup).
CREATE OR REPLACE FUNCTION reinitialiser_limitation(p_cle VARCHAR)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    DELETE FROM limitations_debit WHERE cle = p_cle;
END;
$$;

REVOKE ALL ON FUNCTION tentative_autorisee(VARCHAR, INTEGER, INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION reinitialiser_limitation(VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION tentative_autorisee(VARCHAR, INTEGER, INTEGER) TO qf_app;
GRANT EXECUTE ON FUNCTION reinitialiser_limitation(VARCHAR) TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('038', 'limiteur_debit_partage')
ON CONFLICT (version) DO NOTHING;
