-- ============================================================================
-- 024 — Chantier C2 (cycle 32) : compte actif, lisible par le seul rôle
--        applicatif qf_app.
-- ----------------------------------------------------------------------------
-- Règle décidée par le propriétaire le 2026-09-20 : quand un compte est
-- désactivé, sa session en cours est coupée immédiatement (la requête
-- suivante est refusée). server/app/deps.py doit donc vérifier
-- utilisateurs.actif à CHAQUE requête authentifiée, avant toute bascule de
-- rôle — mais qf_app n'a volontairement aucun SELECT direct sur utilisateurs
-- (migration 008 : seuls les trois rôles métier lisent des colonnes précises,
-- jamais le hachage). Cette fonction SECURITY DEFINER est la fenêtre étroite
-- qui lui manque : elle ne renvoie qu'un booléen, jamais aucune autre donnée.
-- ============================================================================

CREATE OR REPLACE FUNCTION compte_est_actif(p_utilisateur_id INTEGER)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT COALESCE((SELECT actif FROM utilisateurs WHERE id = p_utilisateur_id), FALSE)
$$;

COMMENT ON FUNCTION compte_est_actif(INTEGER) IS
  'Renvoie TRUE si le compte existe et est actif, FALSE sinon. Fenêtre '
  'étroite réservée à qf_app pour couper immédiatement la session d''un '
  'compte désactivé (décision du 2026-09-20), sans jamais exposer d''autre '
  'colonne de utilisateurs.';

REVOKE ALL ON FUNCTION compte_est_actif(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION compte_est_actif(INTEGER) TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('024', 'compte_est_actif')
ON CONFLICT (version) DO NOTHING;
