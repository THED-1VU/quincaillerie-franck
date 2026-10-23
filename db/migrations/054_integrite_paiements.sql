-- 054 — Les deux côtés de la relation vérifient l'invariant au COMMIT.
-- Verrou matériel de la vente parente : les écritures concurrentes de
-- composantes ne peuvent pas valider deux instantanés incompatibles.
-- Les parcours d'annulation/retour passent par les fonctions SECURITY DEFINER.
-- Aucun endpoint métier ne réécrit ces documents ou journaux directement.
REVOKE UPDATE ON ventes,ventes_lignes,transactions,mouvements_stock FROM qf_responsable;
REVOKE UPDATE ON ventes,ventes_lignes FROM qf_agent_comptabilite;
-- Droit minimal pour le verrou matériel ; aucune colonne métier modifiable.
GRANT UPDATE(id) ON ventes TO qf_responsable,qf_agent_comptabilite;
CREATE FUNCTION verrouiller_vente_paiement()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_id INTEGER;
BEGIN
    FOR v_id IN SELECT DISTINCT unnest(CASE TG_OP
        WHEN 'INSERT' THEN ARRAY[NEW.vente_id]
        WHEN 'DELETE' THEN ARRAY[OLD.vente_id]
        ELSE ARRAY[OLD.vente_id,NEW.vente_id] END) ORDER BY 1
    LOOP
        -- Une écriture, même sans changement de valeur, assure aussi le refus
        -- des instantanés périmés en REPEATABLE READ / SERIALIZABLE.
        UPDATE ventes SET id=id WHERE id=v_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Vente % introuvable ou inaccessible.',v_id
              USING ERRCODE='foreign_key_violation';
        END IF;
    END LOOP;
    RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER trg_verrou_vente_paiement BEFORE INSERT OR UPDATE OR DELETE
ON ventes_paiements FOR EACH ROW EXECUTE FUNCTION verrouiller_vente_paiement();

CREATE FUNCTION verifier_integrite_paiements(p_id INTEGER)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE v ventes%ROWTYPE; v_somme NUMERIC; v_nombre INTEGER; v_mode TEXT;
BEGIN
    SELECT * INTO v FROM ventes WHERE id=p_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Vente % introuvable ou inaccessible.',p_id
          USING ERRCODE='foreign_key_violation';
    END IF;
    SELECT COALESCE(sum(montant),0),count(*),min(mode_paiement)
      INTO v_somme,v_nombre,v_mode FROM ventes_paiements WHERE vente_id=p_id;
    IF v.mode_paiement='credit_client' THEN
        IF v_nombre<>0 THEN
            RAISE EXCEPTION 'Vente à crédit % : aucune composante autorisée.',p_id
              USING ERRCODE='check_violation';
        END IF;
        RETURN;
    END IF;
    -- Un brouillon sans paiement reste un brouillon ; pas une recette.
    IF v.statut='en_attente' AND v_nombre=0 THEN RETURN; END IF;
    IF v_somme<>v.total_ttc OR
       (v.mode_paiement='mixte' AND v_nombre<2) OR
       (v.mode_paiement<>'mixte' AND
          NOT ((v.total_ttc=0 AND v_nombre=0) OR (v_nombre=1 AND v_mode=v.mode_paiement))) THEN
        RAISE EXCEPTION 'Vente % : composantes, somme ou modes incohérents.',p_id
          USING ERRCODE='check_violation';
    END IF;
END $$;

CREATE FUNCTION controler_paiements_complets()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME='ventes' THEN
        PERFORM verifier_integrite_paiements(NEW.id);
    ELSE
        IF TG_OP<>'INSERT' THEN PERFORM verifier_integrite_paiements(OLD.vente_id); END IF;
        IF TG_OP<>'DELETE' THEN PERFORM verifier_integrite_paiements(NEW.vente_id); END IF;
    END IF;
    RETURN NULL;
END $$;
DROP TRIGGER trg_somme_paiements_vente ON ventes_paiements;
CREATE CONSTRAINT TRIGGER trg_somme_paiements_vente
AFTER INSERT OR UPDATE OR DELETE ON ventes_paiements DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION controler_paiements_complets();
CREATE CONSTRAINT TRIGGER trg_paiements_depuis_vente
AFTER INSERT OR UPDATE ON ventes DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION controler_paiements_complets();

-- Le validateur doit être utilisable depuis les déclencheurs des deux rôles.
REVOKE ALL ON FUNCTION verrouiller_vente_paiement(), verifier_integrite_paiements(INTEGER),
    controler_paiements_complets() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION verifier_integrite_paiements(INTEGER)
    TO qf_responsable,qf_agent_comptabilite;
SELECT verifier_integrite_paiements(id) FROM ventes;
INSERT INTO schema_migrations(version,nom) VALUES ('054','integrite_paiements');
