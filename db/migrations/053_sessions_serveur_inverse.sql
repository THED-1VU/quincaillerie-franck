DROP TRIGGER IF EXISTS trg_invalider_sessions_compte ON utilisateurs;
DROP TRIGGER IF EXISTS trg_tracer_roles_compte ON utilisateurs_roles;
DROP FUNCTION IF EXISTS tracer_roles_compte();
DROP TABLE IF EXISTS journal_securite;
DROP FUNCTION IF EXISTS invalider_sessions_compte();
DROP FUNCTION IF EXISTS contexte_session(VARCHAR,INTEGER);
DROP FUNCTION IF EXISTS enregistrer_session(VARCHAR,INTEGER,BIGINT);
DROP FUNCTION IF EXISTS journaliser_limitation_connexion(VARCHAR,VARCHAR);
DROP TABLE IF EXISTS sessions_serveur;
DELETE FROM schema_migrations WHERE version='053';

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
     WHERE u2.identifiant = p_identifiant;

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

    IF u.mot_de_passe_hash = crypt(p_mot_de_passe, u.mot_de_passe_hash) THEN
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


CREATE OR REPLACE FUNCTION reinitialiser_mot_de_passe_agent(
    p_compte_id            INTEGER,
    p_nouveau_mot_de_passe VARCHAR,
    p_responsable_id       INTEGER
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_role VARCHAR(30);
BEGIN
    IF p_nouveau_mot_de_passe IS NULL OR length(p_nouveau_mot_de_passe) < 8 THEN
        RAISE EXCEPTION 'Le mot de passe doit faire au moins 8 caractères.'
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT role INTO v_role FROM utilisateurs WHERE id = p_compte_id;
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'Compte % introuvable.', p_compte_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_role = 'responsable' THEN
        RAISE EXCEPTION 'La réinitialisation par le responsable ne vise que les comptes agents.'
          USING ERRCODE = 'check_violation';
    END IF;

    -- Le mot de passe n'est JAMAIS lu ni restitué : seule sa forme hachée
    -- est écrite (bcrypt $2a$, 12 tours — cohérent avec la migration 023).
    UPDATE utilisateurs
       SET mot_de_passe_hash = crypt(p_nouveau_mot_de_passe, gen_salt('bf', 12)),
           doit_changer_mot_de_passe = TRUE,
           tentatives_echouees = 0
     WHERE id = p_compte_id;

    INSERT INTO journal_comptes
        (utilisateur_cible_id, action, ancienne_valeur, nouvelle_valeur,
         utilisateur_auteur_id, date_action)
    VALUES
        (p_compte_id, 'reinitialisation_mot_de_passe', NULL, NULL,
         p_responsable_id, NOW());
END;
$$;

CREATE OR REPLACE FUNCTION creer_premier_responsable(
    p_nom_complet  VARCHAR,
    p_identifiant  VARCHAR,
    p_mot_de_passe TEXT
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Les contrôles d'entrée d'abord, pour qu'un utilisateur reçoive le
    -- message le plus précis possible ; le garde-fou « responsable existe
    -- déjà » vient en dernier, une fois que les valeurs fournies sont saines.
    IF btrim(p_nom_complet) = '' THEN
        RAISE EXCEPTION 'Le nom complet est obligatoire.';
    END IF;

    IF btrim(p_identifiant) = '' THEN
        RAISE EXCEPTION 'L''identifiant est obligatoire.';
    END IF;

    IF EXISTS (SELECT 1 FROM utilisateurs WHERE identifiant = btrim(p_identifiant)) THEN
        RAISE EXCEPTION 'Cet identifiant est déjà utilisé.';
    END IF;

    -- Longueur minimale volontairement conservatrice (8 caractères) : c'est
    -- une protection technique, pas une règle métier du propriétaire — le
    -- seuil peut être durci plus tard sans changer l'outil qui appelle.
    IF length(p_mot_de_passe) < 8 THEN
        RAISE EXCEPTION 'Le mot de passe doit comporter au moins 8 caractères.';
    END IF;

    IF EXISTS (SELECT 1 FROM utilisateurs WHERE role = 'responsable') THEN
        RAISE EXCEPTION 'Un compte responsable existe déjà : cet outil ne crée que le tout premier.';
    END IF;

    INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash,
                              role, site_id, actif, doit_changer_mot_de_passe)
    VALUES (btrim(p_nom_complet), btrim(p_identifiant),
            crypt(p_mot_de_passe, gen_salt('bf', 12)),
            'responsable', NULL, TRUE, TRUE)
    RETURNING id INTO v_id;

    INSERT INTO journal_comptes (utilisateur_cible_id, action, utilisateur_auteur_id)
    VALUES (v_id, 'creation', v_id);

    RETURN v_id;
END;
$$;
