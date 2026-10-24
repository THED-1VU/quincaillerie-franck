-- Retour au comportement 053 ; historique métier non effacé silencieusement.
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM approbations_remises) THEN
  RAISE EXCEPTION 'Inverse 055 refusée : conserver les approbations avant retour arrière.';
 END IF;
END $$;
DROP FUNCTION tracer_approbation_remise(INTEGER);
DROP TABLE approbations_remises;
DROP TRIGGER trg_effacer_verrou_compte ON utilisateurs;
DROP FUNCTION effacer_verrou_compte();
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
BEGIN
    SELECT id, u2.nom_complet, u2.role, u2.site_id, u2.actif,
           u2.tentatives_echouees, u2.mot_de_passe_hash, u2.doit_changer_mot_de_passe
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

    seuil := parametre_numerique('tentatives_max_connexion');

    IF u.tentatives_echouees >= seuil THEN
        -- Verrouillé : on ne vérifie même pas le mot de passe fourni, pour ne
        -- rien laisser deviner et ne pas incrémenter indéfiniment.
        INSERT INTO journal_connexions (identifiant_saisi, utilisateur_id, succes, motif_echec, adresse_ip, poste)
        VALUES (p_identifiant, u.id, FALSE, 'compte_verrouille', p_adresse_ip, p_poste);
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR,
                            NULL::INTEGER, NULL::BOOLEAN, 'compte_verrouille'::VARCHAR;
        RETURN;
    END IF;

    IF octet_length(p_mot_de_passe) <= 72 AND u.mot_de_passe_hash = crypt(p_mot_de_passe, u.mot_de_passe_hash) THEN
        UPDATE utilisateurs SET tentatives_echouees = 0 WHERE id = u.id;
        INSERT INTO journal_connexions (identifiant_saisi, utilisateur_id, succes, adresse_ip, poste)
        VALUES (p_identifiant, u.id, TRUE, p_adresse_ip, p_poste);
        RETURN QUERY SELECT TRUE, u.id, u.nom_complet, u.role, u.site_id,
                            u.doit_changer_mot_de_passe, NULL::VARCHAR;
        RETURN;
    ELSE
        nouvelles_tentatives := u.tentatives_echouees + 1;
        UPDATE utilisateurs SET tentatives_echouees = nouvelles_tentatives WHERE id = u.id;
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
ALTER TABLE utilisateurs DROP COLUMN verrouille_jusqua;
UPDATE parametres SET valeur='5',a_decider=TRUE,
 reference_decision='retour inverse 055 : confirmation de politique à réexaminer'
 WHERE cle='tentatives_max_connexion';
DELETE FROM schema_migrations WHERE version='055';
