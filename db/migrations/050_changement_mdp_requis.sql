-- ============================================================================
-- 050 — Chantier C8 (cycle 65) : obligation de changer le mot de passe
--        provisoire, vérifiable par le seul rôle applicatif qf_app.
-- ----------------------------------------------------------------------------
-- L'obligation est documentée (server/README.md, chantier C2 : « obligation
-- de changer le mot de passe à la première connexion ») et le drapeau
-- utilisateurs.doit_changer_mot_de_passe est émis dans le jeton — mais rien
-- ne l'appliquait : un compte nouvellement créé (ou réinitialisé par le
-- responsable) pouvait travailler indéfiniment avec son mot de passe
-- provisoire. Défaut trouvé par exécution au cycle 65 (matrice des rôles).
--
-- Comme pour compte_est_actif (024), qf_app n'a aucun SELECT direct sur
-- utilisateurs (008) : cette fonction SECURITY DEFINER est la fenêtre
-- étroite qui manque. Elle renvoie uniquement un booléen, relu EN BASE à
-- chaque requête authentifiée — pas la valeur figée du jeton : après un
-- changement réussi, la même session redevient utilisable immédiatement,
-- et une réinitialisation par le responsable coupe un jeton encore valide.
-- ============================================================================

CREATE OR REPLACE FUNCTION changement_mdp_requis(p_utilisateur_id INTEGER)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT COALESCE(
        (SELECT doit_changer_mot_de_passe FROM utilisateurs WHERE id = p_utilisateur_id),
        FALSE
    )
$$;

COMMENT ON FUNCTION changement_mdp_requis(INTEGER) IS
  'Renvoie TRUE si le compte doit encore changer son mot de passe provisoire. '
  'Fenêtre étroite réservée à qf_app (appelée à chaque requête authentifiée, '
  'avant toute bascule de rôle) pour appliquer l''obligation documentée de '
  'changement à la première connexion, sans jamais exposer d''autre colonne '
  'de utilisateurs.';

REVOKE ALL ON FUNCTION changement_mdp_requis(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION changement_mdp_requis(INTEGER) TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('050', 'changement_mdp_requis')
ON CONFLICT (version) DO NOTHING;
