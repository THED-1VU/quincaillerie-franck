-- ============================================================================
-- 050 (inverse) — retire changement_mdp_requis.
-- Attention : deps.py (cycle 65) appelle cette fonction à CHAQUE requête
-- authentifiée. Après annulation, le serveur doit être repassé sur une
-- version antérieure, sinon chaque requête échouera sur une fonction
-- absente (erreur 500, jamais une fuite de données).
-- ============================================================================

DROP FUNCTION IF EXISTS changement_mdp_requis(INTEGER);

DELETE FROM schema_migrations WHERE version = '050';
