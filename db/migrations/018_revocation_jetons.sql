-- ============================================================================
-- 018 — Chantier C11 : révocation de session avant expiration naturelle.
-- ----------------------------------------------------------------------------
-- Limite documentée depuis le cycle 3 (server/app/securite.py) : un jeton
-- signé HMAC, sans état côté serveur, ne peut pas être invalidé avant sa
-- propre expiration — pas de « déconnexion forcée » instantanée. PostgreSQL,
-- déjà le magasin partagé du projet, sert ici de registre de révocation :
-- résout la limite ET la rend partagée entre plusieurs processus applicatifs
-- (l'autre limite documentée du même paragraphe), sans dépendance nouvelle
-- (Redis, etc.).
--
-- Le jeton lui-même reste inchangé dans sa nature (signé, à durée limitée) :
-- seul un identifiant aléatoire (jti) s'ajoute à sa charge utile, pour que
-- « déconnexion » puisse désigner UN jeton précis, jamais tous les jetons
-- d'un utilisateur (portée volontairement étroite : ce cycle ne traite pas
-- la révocation de masse — ex. changement de mot de passe pour tous les
-- postes d'un même compte — qui resterait à faire séparément si demandé).
-- ============================================================================

CREATE TABLE jetons_revoques (
    jti            VARCHAR(32) PRIMARY KEY,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    revoque_le     TIMESTAMP NOT NULL DEFAULT NOW(),
    -- Copie de l'expiration DU JETON LUI-MÊME (pas une politique de
    -- rétention) : passé ce moment, le jeton serait de toute façon refusé
    -- par sa propre signature (securite.py) — la ligne devient inutile,
    -- purgeable. Aucune tâche de purge automatique ce cycle (volumétrie
    -- d'une boutique : quelques déconnexions par jour, jamais un problème
    -- avant longtemps) ; à ajouter si le volume le justifie un jour.
    expire_a       TIMESTAMP NOT NULL
);

COMMENT ON TABLE jetons_revoques IS
    'Jetons de session explicitement révoqués (déconnexion) avant leur '
    'expiration naturelle — cycle 21, chantier C11. Une ligne devient sans '
    'effet une fois expire_a dépassé (le jeton est de toute façon refusé '
    'par sa signature), mais n''est pas purgée automatiquement.';

CREATE INDEX idx_jetons_revoques_expire_a ON jetons_revoques(expire_a);

-- ----------------------------------------------------------------------------
-- revoquer_jeton() : appelée par la route de déconnexion, SOUS qf_app
-- directement (comme verifier_connexion) — la révocation n'est pas une
-- donnée cloisonnée par site, aucune bascule de rôle utilisateur requise.
-- ON CONFLICT DO NOTHING : redemander la déconnexion du même jeton (par
-- exemple un double clic) n'est pas une erreur.
-- ----------------------------------------------------------------------------
-- p_expire_a_epoch : secondes Unix (comme le champ "exp" du jeton lui-même,
-- securite.py) plutôt qu'un TIMESTAMP — évite toute question de fuseau
-- horaire côté appelant Python (le serveur ne calcule qu'un entier, jamais
-- une date) ; to_timestamp() la restitue dans le fuseau de LA CONNEXION
-- (Africa/Douala, database.py), comme toute autre donnée horodatée du projet.
CREATE OR REPLACE FUNCTION revoquer_jeton(
    p_jti               VARCHAR,
    p_utilisateur_id    INTEGER,
    p_expire_a_epoch    BIGINT
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_jti IS NULL OR length(btrim(p_jti)) = 0 THEN
        RAISE EXCEPTION 'Identifiant de jeton invalide.' USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO jetons_revoques (jti, utilisateur_id, expire_a)
    VALUES (p_jti, p_utilisateur_id, to_timestamp(p_expire_a_epoch))
    ON CONFLICT (jti) DO NOTHING;
END;
$$;

REVOKE ALL ON FUNCTION revoquer_jeton(VARCHAR, INTEGER, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION revoquer_jeton(VARCHAR, INTEGER, BIGINT) TO qf_app;

-- ----------------------------------------------------------------------------
-- jeton_est_revoque() : appelée à CHAQUE requête authentifiée (deps.py),
-- avant toute bascule de rôle — SOUS qf_app, comme la révocation elle-même.
-- STABLE (jamais VOLATILE) : une seule lecture, aucune écriture, permet à
-- PostgreSQL de réutiliser le résultat dans une même transaction si besoin.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION jeton_est_revoque(p_jti VARCHAR)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$ SELECT EXISTS(SELECT 1 FROM jetons_revoques WHERE jti = p_jti) $$;

REVOKE ALL ON FUNCTION jeton_est_revoque(VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION jeton_est_revoque(VARCHAR) TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('018', 'revocation_jetons')
ON CONFLICT (version) DO NOTHING;
