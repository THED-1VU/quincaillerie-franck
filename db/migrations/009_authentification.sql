-- ============================================================================
-- 009 — Authentification côté base : vérifier un mot de passe sans jamais
--        le rendre lisible à personne, y compris au serveur applicatif.
-- ----------------------------------------------------------------------------
-- Depuis la migration 008, AUCUN rôle applicatif ne peut lire
-- utilisateurs.mot_de_passe_hash. C'est volontaire, mais il faut bien que
-- quelque chose vérifie un mot de passe à la connexion. Ce quelque chose est
-- une fonction SECURITY DEFINER : elle seule voit le hachage, en interne,
-- et ne le restitue jamais dans son résultat — seulement un verdict et le
-- profil de l'utilisateur.
--
-- PIÈGE RENCONTRÉ ET VÉRIFIÉ PAR EXÉCUTION (cycle 3, phase 1) :
-- pgcrypto ne valide PAS un hachage bcrypt généré au format « $2b$ » (celui
-- que produit la bibliothèque Python `bcrypt` par défaut) : crypt() renvoie
-- alors un résultat FAUX même pour le bon mot de passe. pgcrypto ne connaît
-- que le format « $2a$ ». Il ne s'agit pas d'un bug de cette base : c'est une
-- limitation connue de pgcrypto. La solution retenue, VÉRIFIÉE PAR EXÉCUTION
-- (les deux sens : bon mot de passe -> vrai, mauvais mot de passe -> faux) :
-- le serveur applicatif doit générer tout hachage avec
--     bcrypt.gensalt(rounds=12, prefix=b"2a")
-- jamais avec le préfixe par défaut. Voir server/app/securite.py.
--
-- Cycle 3 — chantiers C2 (authentification) et C11 (sécurité applicative).
-- Idempotent.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ----------------------------------------------------------------------------
-- Utilisateur courant (pour le libre-service : changer SON PROPRE mot de
-- passe). Positionné par le serveur, dans la même transaction que
-- qf.site_id : SET LOCAL qf.utilisateur_id = '12';
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION qf_utilisateur_courant()
RETURNS INTEGER
LANGUAGE sql
STABLE
AS $$ SELECT NULLIF(current_setting('qf.utilisateur_id', TRUE), '')::INTEGER $$;

COMMENT ON FUNCTION qf_utilisateur_courant() IS
  'Identifiant de l''utilisateur authentifié pour la requête en cours. '
  'Sert au libre-service (changer son propre mot de passe), jamais à '
  'accorder un droit sur les données d''un tiers.';

GRANT EXECUTE ON FUNCTION qf_utilisateur_courant()
  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- verifier_connexion : le seul endroit de tout le système qui lit
-- mot_de_passe_hash. Ne le renvoie JAMAIS. Journalise systématiquement,
-- succès comme échec (journal_connexions, créé à la migration 005).
--
-- Règles reprises du cahier des charges §3.1 et de l'addendum :
--   - compte désactivé -> refus, motif distinct (l'utilisateur doit savoir
--     qu'il doit voir le responsable, pas rester à essayer des mots de passe) ;
--   - compte verrouillé (tentatives_echouees >= seuil) -> refus SANS même
--     vérifier le mot de passe fourni, pour ne pas laisser deviner s'il était
--     bon (et ne pas incrémenter indéfiniment) ;
--   - identifiant inconnu ou mot de passe incorrect -> même statut public
--     « refusé », pour ne pas révéler quels identifiants existent ; mais le
--     journal, lui, distingue les deux motifs (utile au responsable) ;
--   - bon mot de passe -> tentatives_echouees remis à 0, profil renvoyé.
--
-- Le seuil de verrouillage vient de parametres.tentatives_max_connexion
-- (valeur proposée : 5, à confirmer par le propriétaire — voir addendum).
-- ----------------------------------------------------------------------------
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

COMMENT ON FUNCTION verifier_connexion(VARCHAR, TEXT, VARCHAR, VARCHAR) IS
  'Seule fonction habilitée à lire mot_de_passe_hash. Ne le renvoie jamais. '
  'Journalise systématiquement dans journal_connexions. Le préfixe du '
  'hachage DOIT être $2a$ (pas $2b$) : voir server/app/securite.py.';

REVOKE ALL ON FUNCTION verifier_connexion(VARCHAR, TEXT, VARCHAR, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION verifier_connexion(VARCHAR, TEXT, VARCHAR, VARCHAR) TO qf_app;

-- ----------------------------------------------------------------------------
-- changer_mon_mot_de_passe : libre-service (cahier des charges §3.1 —
-- « Écran Paramètres permettant à tout utilisateur de modifier son propre
-- identifiant/mot de passe à tout moment »). Un agent n'a AUCUN droit
-- d'écriture sur la table utilisateurs (migration 008) : cette fonction lui
-- ouvre une porte étroite, limitée à SA PROPRE ligne, jamais à celle d'un
-- tiers — qf_utilisateur_courant() vient de la session, pas d'un paramètre
-- que l'appelant pourrait manipuler.
--
-- La fonction vérifie ELLE-MÊME le mot de passe actuel (au lieu de faire
-- rappeler verifier_connexion par le serveur) : un changement de mot de
-- passe n'est pas une connexion, il n'a pas à polluer journal_connexions.
-- Renvoie FALSE si le mot de passe actuel est incorrect (pas d'exception :
-- ce n'est pas une erreur de programmation, c'est un cas d'usage normal).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION changer_mon_mot_de_passe(
    p_mot_de_passe_actuel TEXT,
    p_nouveau_hash TEXT
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    moi INTEGER;
    hash_actuel TEXT;
BEGIN
    moi := qf_utilisateur_courant();
    IF moi IS NULL THEN
        RAISE EXCEPTION 'Aucune session active.' USING ERRCODE = 'invalid_authorization_specification';
    END IF;

    SELECT mot_de_passe_hash INTO hash_actuel FROM utilisateurs WHERE id = moi;
    IF hash_actuel IS NULL OR hash_actuel <> crypt(p_mot_de_passe_actuel, hash_actuel) THEN
        RETURN FALSE;
    END IF;

    -- Contrôle de forme minimal : on attend un hachage bcrypt au format $2a$,
    -- jamais un mot de passe en clair par erreur d'intégration côté serveur.
    IF p_nouveau_hash !~ '^\$2a\$\d{2}\$' THEN
        RAISE EXCEPTION 'Format de hachage invalide (préfixe $2a$ attendu).'
          USING ERRCODE = 'invalid_parameter_value';
    END IF;

    UPDATE utilisateurs
       SET mot_de_passe_hash = p_nouveau_hash,
           doit_changer_mot_de_passe = FALSE
     WHERE id = moi;

    INSERT INTO journal_comptes (utilisateur_cible_id, action, utilisateur_auteur_id)
    VALUES (moi, 'reinitialisation_mot_de_passe', moi);

    RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION changer_mon_mot_de_passe(TEXT, TEXT) IS
  'Libre-service : change le mot de passe du SEUL utilisateur de la session '
  'en cours (qf_utilisateur_courant()), après avoir vérifié elle-même le mot '
  'de passe actuel. Aucun paramètre ne permet de viser un autre compte.';

REVOKE ALL ON FUNCTION changer_mon_mot_de_passe(TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION changer_mon_mot_de_passe(TEXT, TEXT)
  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

INSERT INTO schema_migrations (version, nom)
VALUES ('009', 'authentification')
ON CONFLICT (version) DO NOTHING;
