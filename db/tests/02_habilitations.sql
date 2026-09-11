-- ============================================================================
-- TESTS — les comptes applicatifs restreints sont-ils VRAIMENT restreints ?
-- ----------------------------------------------------------------------------
-- Le cahier des charges §4.2 exige une séparation des droits appliquée « à la
-- fois dans l'interface ET dans les requêtes à la base ». On vérifie ici le
-- second point, le seul qui résiste à un client modifié : PostgreSQL lui-même
-- doit refuser la lecture des colonnes interdites.
--
--   agent stock         ne doit lire AUCUN prix ;
--   agent comptabilité  ne doit lire AUCUNE quantité en stock ;
--   ni l'un ni l'autre   ne doit lire un hachage de mot de passe ;
--   aucun rôle           ne doit être superutilisateur ni pouvoir faire du DDL.
--
-- Usage : psql -d quincaillerie_test -f db/tests/02_habilitations.sql
-- ============================================================================
\set ON_ERROR_STOP on
\pset pager off

DROP TABLE IF EXISTS _tests_droits;
CREATE TABLE _tests_droits (
    ordre  SERIAL PRIMARY KEY,
    role   TEXT NOT NULL,
    nom    TEXT NOT NULL,
    obtenu TEXT NOT NULL,
    ok     BOOLEAN NOT NULL
);
GRANT INSERT ON _tests_droits TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;
GRANT USAGE, SELECT ON SEQUENCE _tests_droits_ordre_seq
  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

CREATE OR REPLACE FUNCTION d_refus(p_nom TEXT, p_sql TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE p_sql;
        RAISE EXCEPTION 'SENTINELLE_ACCEPTE';
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM = 'SENTINELLE_ACCEPTE' THEN
            INSERT INTO _tests_droits (role, nom, obtenu, ok)
            VALUES (current_user, p_nom, 'ACCEPTÉ — droit non restreint', FALSE);
        ELSE
            INSERT INTO _tests_droits (role, nom, obtenu, ok)
            VALUES (current_user, p_nom, 'refusé : ' || left(SQLERRM, 90), TRUE);
        END IF;
    END;
END $$;

CREATE OR REPLACE FUNCTION d_succes(p_nom TEXT, p_sql TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE p_sql;
        INSERT INTO _tests_droits (role, nom, obtenu, ok) VALUES (current_user, p_nom, 'accepté', TRUE);
    EXCEPTION WHEN OTHERS THEN
        INSERT INTO _tests_droits (role, nom, obtenu, ok)
        VALUES (current_user, p_nom, 'REFUSÉ à tort : ' || left(SQLERRM, 90), FALSE);
    END;
END $$;

-- Vérifie une valeur. (Ne JAMAIS écrire un test avec « 1/0 » dans un CASE :
-- PostgreSQL replie les constantes au moment de la planification et lève une
-- division par zéro même dans la branche non prise — le test échoue à tort.)
CREATE OR REPLACE FUNCTION d_valeur(p_nom TEXT, p_sql TEXT, p_attendu TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE v TEXT;
BEGIN
    BEGIN
        EXECUTE p_sql INTO v;
        INSERT INTO _tests_droits (role, nom, obtenu, ok)
        VALUES (current_user, p_nom, COALESCE(v, '(null)') || ' (attendu ' || p_attendu || ')',
                COALESCE(v, '(null)') = p_attendu);
    EXCEPTION WHEN OTHERS THEN
        INSERT INTO _tests_droits (role, nom, obtenu, ok)
        VALUES (current_user, p_nom, 'ERREUR : ' || left(SQLERRM, 90), FALSE);
    END;
END $$;

GRANT EXECUTE ON FUNCTION d_refus(TEXT, TEXT), d_succes(TEXT, TEXT), d_valeur(TEXT, TEXT, TEXT)
  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

-- ============================================================================
-- AGENT STOCK — un site, aucun prix, aucun montant en FCFA
-- ============================================================================
SET ROLE qf_agent_stock;
SET qf.site_id = '1';   -- Magasin de stock. (Le serveur web, lui, utilise SET LOCAL
                      -- dans une transaction ; ici on est hors transaction.)

SELECT d_refus('lire le prix de vente d''un article',
  $$SELECT prix_vente FROM articles LIMIT 1$$);
SELECT d_refus('lire le prix d''achat d''un article',
  $$SELECT prix_achat FROM articles LIMIT 1$$);
SELECT d_refus('lire toutes les colonnes d''articles (SELECT *)',
  $$SELECT * FROM articles LIMIT 1$$);
SELECT d_refus('modifier un prix de vente',
  $$UPDATE articles SET prix_vente = 1 WHERE id = 1$$);
SELECT d_refus('modifier le seuil d''alerte',
  $$UPDATE articles SET seuil_alerte = 0 WHERE id = 1$$);
SELECT d_refus('lire les ventes',
  $$SELECT count(*) FROM ventes$$);
SELECT d_refus('lire les transactions comptables',
  $$SELECT count(*) FROM transactions$$);
SELECT d_refus('lire les salaires des employés',
  $$SELECT salaire_mensuel FROM employes LIMIT 1$$);
SELECT d_refus('lire un hachage de mot de passe',
  $$SELECT mot_de_passe_hash FROM utilisateurs LIMIT 1$$);
SELECT d_refus('lire l''historique des prix',
  $$SELECT count(*) FROM historique_prix_articles$$);
SELECT d_refus('créer une table (DDL)',
  $$CREATE TABLE essai_ddl (x INTEGER)$$);

SELECT d_succes('lire nom, unité et quantité en stock',
  $$SELECT nom, unite, quantite_stock FROM articles LIMIT 1$$);
SELECT d_succes('mettre à jour la quantité en stock',
  $$UPDATE articles SET quantite_stock = quantite_stock WHERE id = 1$$);
SELECT d_succes('enregistrer un comptage d''inventaire',
  $$INSERT INTO comptages_stock (article_id, utilisateur_id, moment, quantite_attendue, quantite_comptee)
    VALUES (2, 2, 'soir', 0, 40)$$);

-- Le seuil d'alerte n'est pas saisi : il est recalculé par la base à l'entrée
-- de stock (20 % de la quantité reçue). 50 reçus → seuil 10.
SELECT d_succes('enregistrer une entrée de stock par la fonction dédiée',
  $$SELECT enregistrer_entree_stock(1, 50, 2, 'Livraison essai')$$);
SELECT d_valeur('seuil d''alerte recalculé par la base (20 % de 50)',
  $$SELECT seuil_alerte::TEXT FROM articles WHERE id = 1$$, '10');

-- Cloisonnement par site : l'article 3 appartient au Comptoir, il ne doit pas
-- être visible pour un agent du Magasin.
SELECT d_valeur('aucun article d''un autre site visible',
  $$SELECT count(*)::TEXT FROM articles WHERE site_id <> 1$$, '0');
SELECT d_valeur('les articles de son propre site restent visibles',
  $$SELECT (count(*) > 0)::TEXT FROM articles$$, 'true');

RESET ROLE;

-- ============================================================================
-- AGENT COMPTABILITÉ — un site, aucune quantité en stock
-- ============================================================================
SET ROLE qf_agent_comptabilite;
SET qf.site_id = '1';

SELECT d_refus('lire la quantité en stock',
  $$SELECT quantite_stock FROM articles LIMIT 1$$);
SELECT d_refus('lire le seuil d''alerte (il révèle le volume reçu)',
  $$SELECT seuil_alerte FROM articles LIMIT 1$$);
SELECT d_refus('lire toutes les colonnes d''articles (SELECT *)',
  $$SELECT * FROM articles LIMIT 1$$);
SELECT d_refus('lire le prix d''achat (la marge)',
  $$SELECT prix_achat FROM articles LIMIT 1$$);
SELECT d_refus('lire les comptages d''inventaire',
  $$SELECT count(*) FROM comptages_stock$$);
SELECT d_refus('lire les mouvements de stock',
  $$SELECT count(*) FROM mouvements_stock$$);
SELECT d_refus('écrire directement dans le stock',
  $$UPDATE articles SET quantite_stock = 0 WHERE id = 1$$);
SELECT d_refus('lire les salaires des employés',
  $$SELECT salaire_mensuel FROM employes LIMIT 1$$);
SELECT d_refus('lire les avances sur salaire',
  $$SELECT count(*) FROM avances_salaire$$);

SELECT d_succes('lire nom et prix de vente d''un article',
  $$SELECT nom, prix_vente FROM articles LIMIT 1$$);
SELECT d_succes('enregistrer une recette',
  $$INSERT INTO transactions (site_id, utilisateur_id, type, montant, description)
    VALUES (1, 4, 'recette', 1000, 'Essai habilitation')$$);
SELECT d_succes('rattacher une dépense à un employé (sans voir son salaire)',
  $$INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, employe_id)
    VALUES (1, 4, 'depense', 60000, 'Salaire', 1)$$);
-- Le décrément de stock passe par la fonction de pont, jamais par un UPDATE.
SELECT d_succes('décrémenter le stock via la fonction de pont',
  $$SELECT decrementer_stock_vente(1, 1, 4, 'vente essai')$$);

RESET ROLE;

-- ============================================================================
-- RESPONSABLE — les deux sites, mais pas superutilisateur
-- ============================================================================
SET ROLE qf_responsable;

SELECT d_succes('lire les prix',   $$SELECT prix_vente FROM articles LIMIT 1$$);
SELECT d_succes('lire les stocks', $$SELECT quantite_stock FROM articles LIMIT 1$$);
SELECT d_valeur('voir les DEUX sites (vue consolidée)',
  $$SELECT count(DISTINCT site_id)::TEXT FROM articles$$, '2');
SELECT d_succes('fixer un prix de vente',
  $$UPDATE articles SET prix_vente = 6600 WHERE id = 1$$);
SELECT d_succes('lire les paramètres à décider',
  $$SELECT count(*) FROM parametres_a_decider$$);
SELECT d_succes('créer un compte utilisateur (en écrivant le hachage)',
  $$INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id)
    VALUES ('Nouvel agent', 'nouvel.agent', 'hash_factice', 'agent_stock', 2)$$);

SELECT d_refus('lire un hachage de mot de passe',
  $$SELECT mot_de_passe_hash FROM utilisateurs LIMIT 1$$);
SELECT d_refus('modifier le seuil d''alerte à la main',
  $$UPDATE articles SET seuil_alerte = 0 WHERE id = 1$$);
SELECT d_refus('déplacer un article d''un site à l''autre (transfert non tranché)',
  $$UPDATE articles SET site_id = 2 WHERE id = 1$$);
SELECT d_refus('créer une table (DDL)',
  $$CREATE TABLE essai_ddl (x INTEGER)$$);
SELECT d_refus('supprimer une table',
  $$DROP TABLE comptages_stock$$);
SELECT d_refus('créer un rôle',
  $$CREATE ROLE intrus LOGIN$$);

RESET ROLE;

-- ============================================================================
-- Aucun rôle applicatif n'est superutilisateur
-- ============================================================================
INSERT INTO _tests_droits (role, nom, obtenu, ok)
SELECT rolname, 'n''est pas superutilisateur',
       CASE WHEN rolsuper THEN 'SUPERUTILISATEUR' ELSE 'non superutilisateur' END,
       NOT rolsuper
  FROM pg_roles WHERE rolname LIKE 'qf\_%';

INSERT INTO _tests_droits (role, nom, obtenu, ok)
SELECT rolname, 'ne peut pas créer de base ni de rôle',
       format('createdb=%s createrole=%s', rolcreatedb, rolcreaterole),
       NOT rolcreatedb AND NOT rolcreaterole
  FROM pg_roles WHERE rolname LIKE 'qf\_%';

-- qf_app est NOINHERIT : sans SET ROLE, il n'a aucun droit propre.
INSERT INTO _tests_droits (role, nom, obtenu, ok)
SELECT 'qf_app', 'NOINHERIT (doit basculer par SET ROLE)',
       CASE WHEN rolinherit THEN 'hérite automatiquement' ELSE 'n''hérite pas' END,
       NOT rolinherit
  FROM pg_roles WHERE rolname = 'qf_app';

-- ============================================================================
-- Résultat
-- ============================================================================
\echo ''
\echo '========================= RÉSULTATS — HABILITATIONS ========================='
SELECT ordre,
       CASE WHEN ok THEN '[ok]   ' ELSE '[ÉCHEC]' END AS statut,
       role, nom, obtenu
  FROM _tests_droits ORDER BY ordre;

\echo ''
SELECT count(*) FILTER (WHERE ok) AS reussis,
       count(*) FILTER (WHERE NOT ok) AS echecs,
       count(*) AS total
  FROM _tests_droits;

DO $$
DECLARE n INTEGER;
BEGIN
    SELECT count(*) INTO n FROM _tests_droits WHERE NOT ok;
    IF n > 0 THEN
        RAISE EXCEPTION '% test(s) d''habilitation en échec.', n;
    END IF;
END $$;
