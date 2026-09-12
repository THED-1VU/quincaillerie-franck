-- ============================================================================
-- 010 — Corrige un oubli de la migration 008 : qf_app ne pouvait RIEN voir
-- ----------------------------------------------------------------------------
-- Trouvé par exécution réelle au cycle 3, en câblant le tout premier appel du
-- serveur applicatif : verifier_connexion() répondait
--     ERROR: function verifier_connexion(...) does not exist
-- pour le rôle qf_app — alors que la fonction existe bel et bien et que
-- qf_app avait reçu EXECUTE dessus (migration 009). En la rejouant sous
-- « postgres », l'appel réussissait ; sous « qf_app », non.
--
-- Cause : la migration 008 accorde USAGE ON SCHEMA public à qf_responsable,
-- qf_agent_stock et qf_agent_comptabilite — mais PAS à qf_app. Comme qf_app
-- est NOINHERIT (voulu : il ne doit tenir aucun droit de ces trois rôles),
-- il n'a jamais hérité de ce USAGE. Sans USAGE sur le schéma, PostgreSQL ne
-- se contente pas de refuser l'exécution : il rend l'objet INVISIBLE au
-- moment de résoudre le nom de la fonction, d'où le message « n'existe
-- pas » au lieu de « permission refusée » — comportement normal de
-- PostgreSQL (il évite de révéler le contenu d'un schéma auquel on n'a pas
-- accès), mais trompeur si on ne le sait pas.
--
-- Migration 008 volontairement NON modifiée : elle est déjà fusionnée et
-- appliquée (cycle 2) ; on corrige en avant, jamais en réécrivant l'histoire.
--
-- Cycle 3 — chantiers C2/C11. Idempotent.
-- ============================================================================

GRANT USAGE ON SCHEMA public TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('010', 'correction_usage_qf_app')
ON CONFLICT (version) DO NOTHING;
