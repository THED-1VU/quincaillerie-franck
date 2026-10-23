DROP TRIGGER IF EXISTS trg_paiements_depuis_vente ON ventes;
DROP TRIGGER IF EXISTS trg_somme_paiements_vente ON ventes_paiements;
DROP TRIGGER IF EXISTS trg_verrou_vente_paiement ON ventes_paiements;
DROP FUNCTION IF EXISTS controler_paiements_complets();
DROP FUNCTION IF EXISTS verifier_integrite_paiements(INTEGER);
DROP FUNCTION IF EXISTS verrouiller_vente_paiement();
REVOKE UPDATE(id) ON ventes FROM qf_responsable,qf_agent_comptabilite;
GRANT UPDATE ON ventes,ventes_lignes,transactions,mouvements_stock TO qf_responsable;
GRANT UPDATE ON ventes,ventes_lignes TO qf_agent_comptabilite;
CREATE CONSTRAINT TRIGGER trg_somme_paiements_vente
AFTER INSERT OR UPDATE OR DELETE ON ventes_paiements DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION verifier_somme_paiements_vente();
DELETE FROM schema_migrations WHERE version='054';
