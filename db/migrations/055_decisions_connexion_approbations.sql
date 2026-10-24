-- 055 réservée dans loop-state.md et publiée avant création (PR #107).
-- Décisions propriétaire du 24/10/2026 : C2-01 et trace D-N1.
ALTER TABLE utilisateurs ADD COLUMN verrouille_jusqua TIMESTAMPTZ;
-- Un compte déjà verrouillé reçoit une échéance bornée lors de l'upgrade.
UPDATE utilisateurs SET verrouille_jusqua=clock_timestamp()+interval '15 minutes'
 WHERE tentatives_echouees>=5;
GRANT SELECT(verrouille_jusqua),UPDATE(verrouille_jusqua) ON utilisateurs TO qf_responsable;
UPDATE parametres SET valeur='5',a_decider=FALSE,
 reference_decision='C2-01 propriétaire 2026-10-24 : 5 échecs consécutifs, verrou 15 minutes'
 WHERE cle='tentatives_max_connexion';

CREATE FUNCTION effacer_verrou_compte() RETURNS trigger LANGUAGE plpgsql
SET search_path=public,pg_temp AS $$
BEGIN
 IF NEW.tentatives_echouees=0 THEN NEW.verrouille_jusqua:=NULL; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER trg_effacer_verrou_compte BEFORE UPDATE OF tentatives_echouees ON utilisateurs
 FOR EACH ROW EXECUTE FUNCTION effacer_verrou_compte();
REVOKE ALL ON FUNCTION effacer_verrou_compte() FROM PUBLIC;

CREATE OR REPLACE FUNCTION verifier_connexion(
    p_identifiant  VARCHAR,
    p_mot_de_passe TEXT,
    p_adresse_ip   VARCHAR DEFAULT NULL,
    p_poste        VARCHAR DEFAULT NULL
) RETURNS TABLE (
    ok                          BOOLEAN,
    utilisateur_id              INTEGER,
    nom_complet                 VARCHAR,
    role                        VARCHAR,
    site_id                     INTEGER,
    doit_changer_mot_de_passe   BOOLEAN,
    motif                       VARCHAR
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    u RECORD;
    seuil INTEGER;
    nouvelles_tentatives INTEGER;
    maintenant TIMESTAMPTZ;
BEGIN
    SELECT id, u2.nom_complet, u2.role, u2.site_id, u2.actif,
           u2.tentatives_echouees, u2.verrouille_jusqua, u2.mot_de_passe_hash, u2.doit_changer_mot_de_passe
      INTO u
      FROM utilisateurs u2
     WHERE u2.identifiant = p_identifiant FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO journal_connexions (identifiant_saisi, succes, motif_echec, adresse_ip, poste)
        VALUES (p_identifiant, FALSE, 'identifiant_inconnu', p_adresse_ip, p_poste);
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR,
                            NULL::INTEGER, NULL::BOOLEAN, 'identifiant_ou_mot_de_passe_incorrect'::VARCHAR;
        RETURN;
    END IF;

    IF NOT u.actif THEN
        INSERT INTO journal_connexions (identifiant_saisi, utilisateur_id, succes, motif_echec, adresse_ip, poste)
        VALUES (p_identifiant, u.id, FALSE, 'compte_desactive', p_adresse_ip, p_poste);
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR,
                            NULL::INTEGER, NULL::BOOLEAN, 'compte_desactive'::VARCHAR;
        RETURN;
    END IF;

    -- C2-01, 24/10/2026. Le temps est lu APRES le verrou de ligne.
    -- Une requête en attente ne prolonge pas le verrou ni son compteur.
    maintenant := clock_timestamp();
    seuil := 5;
    IF u.verrouille_jusqua IS NOT NULL AND u.verrouille_jusqua > maintenant THEN
        INSERT INTO journal_connexions (identifiant_saisi, utilisateur_id, succes, motif_echec, adresse_ip, poste)
        VALUES (p_identifiant,u.id,FALSE,'compte_verrouille',p_adresse_ip,p_poste);
        RETURN QUERY SELECT FALSE,NULL::INTEGER,NULL::VARCHAR,NULL::VARCHAR,
                            NULL::INTEGER,NULL::BOOLEAN,'compte_verrouille'::VARCHAR;
        RETURN;
    END IF;
    IF u.verrouille_jusqua IS NOT NULL THEN
        UPDATE utilisateurs SET tentatives_echouees=0,verrouille_jusqua=NULL WHERE id=u.id;
        u.tentatives_echouees := 0;
    END IF;

    IF octet_length(p_mot_de_passe) <= 72 AND u.mot_de_passe_hash = crypt(p_mot_de_passe, u.mot_de_passe_hash) THEN
        UPDATE utilisateurs SET tentatives_echouees = 0, verrouille_jusqua=NULL WHERE id = u.id;
        INSERT INTO journal_connexions (identifiant_saisi, utilisateur_id, succes, adresse_ip, poste)
        VALUES (p_identifiant, u.id, TRUE, p_adresse_ip, p_poste);
        RETURN QUERY SELECT TRUE, u.id, u.nom_complet, u.role, u.site_id,
                            u.doit_changer_mot_de_passe, NULL::VARCHAR;
        RETURN;
    ELSE
        nouvelles_tentatives := u.tentatives_echouees + 1;
        UPDATE utilisateurs SET tentatives_echouees=nouvelles_tentatives,
            verrouille_jusqua=CASE WHEN nouvelles_tentatives>=seuil THEN clock_timestamp()+interval '15 minutes' ELSE NULL END WHERE id=u.id;
        INSERT INTO journal_connexions (identifiant_saisi, utilisateur_id, succes, motif_echec, adresse_ip, poste)
        VALUES (p_identifiant, u.id, FALSE, 'mot_de_passe_incorrect', p_adresse_ip, p_poste);

        IF nouvelles_tentatives >= seuil THEN
            RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR,
                                NULL::INTEGER, NULL::BOOLEAN, 'compte_verrouille'::VARCHAR;
        ELSE
            RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR,
                                NULL::INTEGER, NULL::BOOLEAN, 'identifiant_ou_mot_de_passe_incorrect'::VARCHAR;
        END IF;
        RETURN;
    END IF;
END;
$$;

CREATE TABLE approbations_remises (
 vente_id INTEGER PRIMARY KEY REFERENCES ventes(id) ON DELETE RESTRICT,
 responsable_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
 total_catalogue NUMERIC NOT NULL CHECK(total_catalogue>0),
 total_ttc NUMERIC NOT NULL CHECK(total_ttc>0),
 remise_totale NUMERIC NOT NULL CHECK(remise_totale>total_catalogue*0.10),
 date_approbation TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 reference_decision TEXT NOT NULL DEFAULT 'D-N1 propriétaire 2026-10-24'
);
REVOKE ALL ON approbations_remises FROM PUBLIC,qf_app,qf_agent_stock,qf_agent_comptabilite,qf_responsable;
GRANT SELECT ON approbations_remises TO qf_responsable;
CREATE TRIGGER trg_approbation_immuable BEFORE UPDATE OR DELETE ON approbations_remises
 FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();

CREATE FUNCTION tracer_approbation_remise(p_vente INTEGER) RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE auteur INTEGER; catalogue NUMERIC; remise NUMERIC; final NUMERIC;
BEGIN
 auteur:=qf_utilisateur_courant();
 IF current_setting('role')<>'qf_responsable' OR NOT EXISTS
    (SELECT 1 FROM utilisateurs u WHERE u.id=auteur AND u.actif AND
      (u.role='responsable' OR EXISTS(SELECT 1 FROM utilisateurs_roles r WHERE r.utilisateur_id=u.id AND r.role='responsable'))) THEN
    RAISE EXCEPTION 'Approbation réservée au responsable authentifié.' USING ERRCODE='insufficient_privilege';
 END IF;
 SELECT SUM(l.prix_catalogue*l.quantite),SUM(l.remise_montant*l.quantite)+v.remise_globale_montant,v.total_ttc
 INTO catalogue,remise,final FROM ventes v JOIN ventes_lignes l ON l.vente_id=v.id
 WHERE v.id=p_vente AND v.utilisateur_id=auteur GROUP BY v.id;
 IF catalogue IS NULL OR remise<=catalogue*0.10 THEN
    RAISE EXCEPTION 'Vente sans approbation exceptionnelle à tracer.' USING ERRCODE='check_violation';
 END IF;
 INSERT INTO approbations_remises(vente_id,responsable_id,total_catalogue,total_ttc,remise_totale)
 VALUES(p_vente,auteur,catalogue,final,remise);
END $$;
REVOKE ALL ON FUNCTION tracer_approbation_remise(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION tracer_approbation_remise(INTEGER) TO qf_responsable;

INSERT INTO schema_migrations(version,nom) VALUES('055','decisions_connexion_approbations');
