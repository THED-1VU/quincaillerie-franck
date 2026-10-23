-- 053 — Sessions enregistrées, révocation durable et permissions courantes.
-- Les jetons précédents non enregistrés imposent une reconnexion.
CREATE TABLE sessions_serveur (
    jti VARCHAR(32) PRIMARY KEY CHECK (jti ~ '^[0-9a-f]{32}$'),
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    expire_a TIMESTAMPTZ NOT NULL,
    cree_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_sessions_serveur_utilisateur ON sessions_serveur(utilisateur_id);
CREATE TABLE journal_securite (
    id BIGSERIAL PRIMARY KEY,
    utilisateur_cible_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    utilisateur_auteur_id INTEGER REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    compte_sql TEXT NOT NULL DEFAULT session_user,
    role_sql TEXT NOT NULL DEFAULT current_setting('role'),
    action TEXT NOT NULL,
    date_action TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
REVOKE ALL ON journal_securite FROM PUBLIC,qf_app,qf_responsable,qf_agent_stock,qf_agent_comptabilite;
GRANT SELECT ON journal_securite TO qf_responsable;
CREATE TRIGGER trg_journal_securite_immuable BEFORE UPDATE OR DELETE ON journal_securite
FOR EACH ROW EXECUTE FUNCTION interdire_suppression_journal();
REVOKE ALL ON sessions_serveur FROM PUBLIC, qf_app, qf_responsable,
    qf_agent_stock, qf_agent_comptabilite;

CREATE FUNCTION enregistrer_session(p_jti VARCHAR, p_utilisateur_id INTEGER, p_expire BIGINT)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
    IF p_expire <= extract(epoch FROM clock_timestamp()) OR
       p_expire > extract(epoch FROM clock_timestamp()) + 28800 THEN
        RAISE EXCEPTION 'Durée de session invalide (maximum 480 minutes).'
          USING ERRCODE = 'check_violation';
    END IF;
    INSERT INTO sessions_serveur(jti, utilisateur_id, expire_a)
    VALUES (p_jti, p_utilisateur_id, to_timestamp(p_expire));
END $$;

CREATE FUNCTION contexte_session(p_jti VARCHAR, p_utilisateur_id INTEGER)
RETURNS TABLE(role VARCHAR, site_id INTEGER, roles VARCHAR[], enregistree BOOLEAN)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
    SELECT u.role, u.site_id,
           COALESCE((SELECT array_agg(ur.role ORDER BY ur.role) FROM utilisateurs_roles ur
                     WHERE ur.utilisateur_id=u.id), ARRAY[u.role]),
           EXISTS(SELECT 1 FROM sessions_serveur s WHERE s.jti=p_jti
                  AND s.utilisateur_id=u.id AND s.expire_a > clock_timestamp())
      FROM utilisateurs u WHERE u.id=p_utilisateur_id;
$$;

CREATE FUNCTION invalider_sessions_compte()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_exception TEXT;
BEGIN
    -- Seul le libre-service peut préserver le jeton qui effectue le changement.
    -- Une désactivation, réinitialisation ou modification de périmètre ne le peut pas.
    IF NEW.mot_de_passe_hash IS DISTINCT FROM OLD.mot_de_passe_hash AND
       NEW.actif = OLD.actif AND NEW.role = OLD.role AND
       NEW.site_id IS NOT DISTINCT FROM OLD.site_id AND
       NOT NEW.doit_changer_mot_de_passe THEN
        v_exception := current_setting('qf.session_courante', true);
    END IF;
    IF NEW.mot_de_passe_hash IS DISTINCT FROM OLD.mot_de_passe_hash OR
       NEW.actif IS DISTINCT FROM OLD.actif OR NEW.role IS DISTINCT FROM OLD.role OR
       NEW.site_id IS DISTINCT FROM OLD.site_id THEN
        INSERT INTO journal_securite(utilisateur_cible_id,utilisateur_auteur_id,action)
        VALUES (NEW.id,qf_utilisateur_courant(),'invalidation_sessions_compte');
        INSERT INTO jetons_revoques(jti, utilisateur_id, expire_a)
        SELECT s.jti, s.utilisateur_id, s.expire_a
          FROM sessions_serveur s WHERE s.utilisateur_id=NEW.id
           AND s.jti IS DISTINCT FROM v_exception
        ON CONFLICT (jti) DO NOTHING;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_invalider_sessions_compte
AFTER UPDATE OF mot_de_passe_hash, actif, role, site_id ON utilisateurs
FOR EACH ROW EXECUTE FUNCTION invalider_sessions_compte();

CREATE FUNCTION tracer_roles_compte()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
    INSERT INTO journal_securite(utilisateur_cible_id,utilisateur_auteur_id,action)
    VALUES (COALESCE(NEW.utilisateur_id,OLD.utilisateur_id),qf_utilisateur_courant(),
            TG_OP || '_role_' || COALESCE(NEW.role,OLD.role));
    RETURN NULL;
END $$;
CREATE TRIGGER trg_tracer_roles_compte AFTER INSERT OR UPDATE OR DELETE ON utilisateurs_roles
FOR EACH ROW EXECUTE FUNCTION tracer_roles_compte();

REVOKE ALL ON FUNCTION enregistrer_session(VARCHAR,INTEGER,BIGINT),
    contexte_session(VARCHAR,INTEGER), invalider_sessions_compte(),tracer_roles_compte() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_session(VARCHAR,INTEGER,BIGINT),
    contexte_session(VARCHAR,INTEGER) TO qf_app;
CREATE FUNCTION journaliser_limitation_connexion(p_identifiant VARCHAR,p_ip VARCHAR)
RETURNS VOID LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
    INSERT INTO journal_connexions(identifiant_saisi,utilisateur_id,succes,motif_echec,adresse_ip,poste)
    VALUES (p_identifiant,(SELECT id FROM utilisateurs WHERE identifiant=p_identifiant),
            FALSE,'autre',p_ip,'api_limitation_debit');
$$;
REVOKE ALL ON FUNCTION journaliser_limitation_connexion(VARCHAR,VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION journaliser_limitation_connexion(VARCHAR,VARCHAR) TO qf_app;
INSERT INTO schema_migrations(version,nom) VALUES ('053','sessions_serveur');

-- S?rialiser les ?checs simultan?s : aucun incr?ment perdu.
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
    IF octet_length(p_nouveau_mot_de_passe) > 72 THEN
        RAISE EXCEPTION 'Mot de passe trop long : maximum 72 octets UTF-8.' USING ERRCODE='check_violation';
    END IF;
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
    IF octet_length(p_mot_de_passe) > 72 THEN
        RAISE EXCEPTION 'Mot de passe trop long : maximum 72 octets UTF-8.' USING ERRCODE='check_violation';
    END IF;
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
