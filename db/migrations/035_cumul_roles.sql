-- ============================================================================
-- 035 — Chantier C3 (cycle 41) : cumul de rôles sur un même compte.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (2026-09-22, addendum point h, question 4) :
-- un compte peut porter PLUSIEURS rôles (petit effectif). Le modèle reste
-- mono-colonne pour le rôle PRINCIPAL (utilisateurs.role — utilisé pour le
-- site, la redirection d'écran et le jeton), et cette table porte la liste
-- complète des rôles effectifs.
--
-- Question 3 du point h (détail des prix ou total seul pour le caissier) :
-- documentée comme EN ATTENTE dans l'addendum — le terrain vente est réservé
-- au point f en cours ; aucune implémentation ici.
-- ============================================================================

CREATE TABLE utilisateurs_roles (
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    role           VARCHAR(30) NOT NULL
                   CHECK (role IN ('responsable', 'agent_stock', 'agent_comptabilite')),
    PRIMARY KEY (utilisateur_id, role)
);

COMMENT ON TABLE utilisateurs_roles IS
  'Rôles cumulés d''un compte (addendum point h, question 4, décidée le '
  '2026-09-22). utilisateurs.role reste le rôle PRINCIPAL (site, écran '
  'd''accueil, jeton) ; cette table porte tous les rôles effectifs.';

-- Reprise de l'existant : chaque compte porte au moins son rôle principal.
INSERT INTO utilisateurs_roles (utilisateur_id, role)
SELECT id, role FROM utilisateurs
ON CONFLICT (utilisateur_id, role) DO NOTHING;

-- Lecture des rôles par le serveur (connexion) et par le responsable (liste
-- des comptes) — fenêtre minimale, sans exposer la table à qf_app.
CREATE OR REPLACE FUNCTION roles_utilisateur(p_utilisateur_id INTEGER)
RETURNS TABLE (role VARCHAR)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
        SELECT ur.role
          FROM utilisateurs_roles ur
         WHERE ur.utilisateur_id = p_utilisateur_id
         ORDER BY CASE ur.role
                    WHEN 'responsable' THEN 1
                    WHEN 'agent_comptabilite' THEN 2
                    ELSE 3
                  END;
END;
$$;

REVOKE ALL ON FUNCTION roles_utilisateur(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION roles_utilisateur(INTEGER) TO qf_app;
GRANT EXECUTE ON FUNCTION roles_utilisateur(INTEGER) TO qf_responsable;

-- Le responsable gère les rôles des comptes qu'il crée : lecture et
-- insertion seulement (aucune mise à jour directe — la route applicative
-- est le seul point d'écriture, et seule la création ajoute des rôles).
GRANT SELECT ON utilisateurs_roles TO qf_responsable;
GRANT INSERT ON utilisateurs_roles TO qf_responsable;

INSERT INTO schema_migrations (version, nom)
VALUES ('035', 'cumul_roles')
ON CONFLICT (version) DO NOTHING;
