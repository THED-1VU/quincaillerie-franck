-- Contrôles C2-01/D-N1 sur données synthétiques uniquement ; transaction annulée.
\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE n INTEGER; fin TIMESTAMPTZ; i INTEGER;
BEGIN
 IF (SELECT count(*) FROM schema_migrations WHERE version='055')<>1 THEN
  RAISE EXCEPTION 'Migration 055 absente ou dupliquée';
 END IF;
 IF has_table_privilege('qf_agent_comptabilite','approbations_remises','INSERT') OR
    has_function_privilege('qf_agent_comptabilite','tracer_approbation_remise(integer)','EXECUTE') THEN
  RAISE EXCEPTION 'Le caissier peut forger une approbation';
 END IF;
 IF has_column_privilege('qf_agent_comptabilite','articles','prix_achat','SELECT') OR
    has_column_privilege('qf_agent_stock','articles','prix_achat','SELECT') THEN
  RAISE EXCEPTION 'Fuite de prix achat';
 END IF;
 UPDATE utilisateurs SET tentatives_echouees=0 WHERE identifiant='magasin.stock';
 FOR i IN 1..5 LOOP
  PERFORM verifier_connexion('magasin.stock','mot_de_passe_faux',NULL,'controle055');
 END LOOP;
 SELECT tentatives_echouees,verrouille_jusqua INTO n,fin FROM utilisateurs WHERE identifiant='magasin.stock';
 IF n<>5 OR fin IS NULL OR fin<=clock_timestamp()+interval '14 minutes' OR fin>clock_timestamp()+interval '15 minutes' THEN
  RAISE EXCEPTION 'Verrou 5/15 incorrect';
 END IF;
 PERFORM verifier_connexion('magasin.stock','encore_faux',NULL,'controle055');
 IF NOT EXISTS(SELECT 1 FROM utilisateurs WHERE identifiant='magasin.stock' AND tentatives_echouees=5 AND verrouille_jusqua=fin) THEN
  RAISE EXCEPTION 'Le verrou est prolongé ou le compteur incrémenté';
 END IF;
 RAISE NOTICE '055 : présence unique, confidentialité, approbation et verrou 5/15 OK';
END $$;
ROLLBACK;
