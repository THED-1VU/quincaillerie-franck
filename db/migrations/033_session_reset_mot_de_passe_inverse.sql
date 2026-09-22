-- Annule la migration 033.

DROP FUNCTION IF EXISTS reinitialiser_mot_de_passe_agent(INTEGER, VARCHAR, INTEGER);
DROP FUNCTION IF EXISTS duree_session_minutes_decidee();

REVOKE EXECUTE ON FUNCTION parametre_numerique(VARCHAR) FROM qf_app;
REVOKE EXECUTE ON FUNCTION parametre_texte(VARCHAR) FROM qf_app;

UPDATE parametres SET
    valeur = 'a_definir',
    a_decider = TRUE,
    utilisateur_id = (SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1),
    reference_decision = 'dossier de recette §6, session inactive'
  WHERE cle = 'duree_session_minutes';

DELETE FROM schema_migrations WHERE version = '033';
