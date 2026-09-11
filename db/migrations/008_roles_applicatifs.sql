-- ============================================================================
-- 008 — Comptes PostgreSQL applicatifs et privilèges
-- ----------------------------------------------------------------------------
-- Diagnostic du cycle 2, prouvé par exécution : un seul rôle existe, « postgres »,
-- SUPERUTILISATEUR — et c'est celui que config.example.ini donne à l'application.
-- Tout client qui obtient ce mot de passe lit et écrit tout. Le cahier des
-- charges §4.2 exige pourtant une séparation des droits « appliquée à la fois
-- dans l'interface ET dans les requêtes à la base ».
--
-- Quatre rôles, aucun superutilisateur, aucun droit de modifier le schéma :
--
--   qf_app                  rôle de CONNEXION du serveur web. NOINHERIT : il ne
--                           possède par lui-même aucun droit sur les données. Il
--                           doit basculer explicitement (SET ROLE) vers le rôle
--                           correspondant à l'utilisateur connecté.
--   qf_responsable          les deux sites, toutes les données métier.
--   qf_agent_stock          un site. Ne peut PAS LIRE les colonnes de prix.
--   qf_agent_comptabilite   un site. Ne peut PAS LIRE les quantités en stock.
--
-- Le cloisonnement par colonne est fait par GRANT au niveau colonne : la
-- requête « SELECT prix_vente FROM articles » est refusée par PostgreSQL à
-- l'agent stock. Masquer l'information dans l'interface ne suffit pas.
--
-- Le cloisonnement par SITE est fait par Row Level Security, à partir de la
-- variable de session « qf.site_id » que le serveur positionne pour la durée
-- de la requête. Ce socle sera exploité et testé plus largement au cycle 3
-- (chantier C3).
--
-- Cycle 2 — chantier C1. Idempotent.
-- Le MOT DE PASSE de qf_app n'est PAS dans ce dépôt : voir
-- db/outils/definir_mot_de_passe_app.sql.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Pré-requis : l'agent stock crée des articles SANS saisir de prix. Le prix de
-- vente doit donc avoir une valeur par défaut, que seul le responsable fixera
-- ensuite (cahier des charges §2 et §3.2).
-- ----------------------------------------------------------------------------
ALTER TABLE articles ALTER COLUMN prix_vente SET DEFAULT 0;

-- ----------------------------------------------------------------------------
-- Création des rôles
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_responsable') THEN
        CREATE ROLE qf_responsable NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_agent_stock') THEN
        CREATE ROLE qf_agent_stock NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_agent_comptabilite') THEN
        CREATE ROLE qf_agent_comptabilite NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_app') THEN
        CREATE ROLE qf_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$$;

GRANT qf_responsable, qf_agent_stock, qf_agent_comptabilite TO qf_app;

COMMENT ON ROLE qf_app IS
  'Rôle de connexion du serveur web. NOINHERIT : aucun droit propre. Le serveur '
  'exécute SET ROLE vers qf_responsable / qf_agent_stock / qf_agent_comptabilite '
  'selon l''utilisateur authentifié, puis RESET ROLE.';

-- ----------------------------------------------------------------------------
-- Table rase : personne n'a de droit par défaut
-- ----------------------------------------------------------------------------
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM qf_responsable, qf_agent_stock, qf_agent_comptabilite;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM qf_responsable, qf_agent_stock, qf_agent_comptabilite;

GRANT USAGE ON SCHEMA public TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;
-- USAGE seulement : aucun des rôles ne peut créer ni supprimer d'objet.

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- RÉFÉRENTIEL commun (lecture seule pour tous les rôles)
-- ----------------------------------------------------------------------------
GRANT SELECT ON sites       TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;
GRANT SELECT ON parametres  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;
GRANT SELECT ON parametres_a_decider TO qf_responsable;

-- Jamais le hachage du mot de passe, pour PERSONNE — pas même le responsable.
-- La vérification du mot de passe à la connexion se fera par une fonction
-- dédiée, exécutée avec les droits de son propriétaire (chantier C2, cycle 3) :
-- aucun rôle applicatif n'a jamais besoin de LIRE un hachage.
GRANT SELECT (id, nom_complet, identifiant, role, site_id, actif,
              doit_changer_mot_de_passe, tentatives_echouees, date_creation)
  ON utilisateurs TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- RESPONSABLE — les deux sites, toutes les données métier.
-- Pas de DDL, pas de gestion de rôles : ce n'est pas un superutilisateur.
-- Deux restrictions s'appliquent AUSSI à lui :
--   * il n'a jamais accès en lecture au hachage d'un mot de passe (il peut en
--     écrire un, à la création d'un compte ou à une réinitialisation) ;
--   * il ne peut pas modifier le seuil d'alerte à la main — le cahier des
--     charges §4.2 est explicite : « le seuil d'alerte ne peut être modifié par
--     personne directement, afin qu'il ne puisse pas servir à dissimuler un vol
--     de marchandise ». Il est recalculé par enregistrer_entree_stock().
-- ----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON
    fournisseurs, employes, ventes, ventes_lignes, transactions,
    absences_conges, avances_salaire, mouvements_stock
  TO qf_responsable;

GRANT SELECT ON articles TO qf_responsable;
GRANT INSERT (nom, categorie, unite, prix_achat, prix_vente, quantite_stock,
              site_id, fournisseur_id)
  ON articles TO qf_responsable;
GRANT UPDATE (nom, categorie, unite, prix_achat, prix_vente, quantite_stock,
              fournisseur_id, actif, date_desactivation, desactive_par_id)
  ON articles TO qf_responsable;

GRANT INSERT (nom_complet, identifiant, mot_de_passe_hash, role, site_id,
              actif, doit_changer_mot_de_passe)
  ON utilisateurs TO qf_responsable;
GRANT UPDATE (nom_complet, identifiant, mot_de_passe_hash, role, site_id,
              actif, tentatives_echouees, doit_changer_mot_de_passe)
  ON utilisateurs TO qf_responsable;

GRANT SELECT, INSERT ON
    historique_prix_articles, historique_modifications_articles,
    comptages_stock, journal_connexions, journal_comptes
  TO qf_responsable;

GRANT UPDATE (valeur, utilisateur_id) ON parametres TO qf_responsable;
GRANT SELECT ON comptages_stock_ecarts_declares, historique_parametres TO qf_responsable;
GRANT SELECT ON schema_migrations TO qf_responsable;

-- ----------------------------------------------------------------------------
-- AGENT STOCK — un site. Ne voit AUCUN prix, AUCUN montant en FCFA.
-- Les colonnes prix_achat et prix_vente sont volontairement absentes des GRANT :
-- « SELECT prix_vente FROM articles » est refusé par PostgreSQL lui-même.
-- ----------------------------------------------------------------------------
GRANT SELECT (id, nom, categorie, unite, quantite_stock, seuil_alerte,
              site_id, fournisseur_id, date_creation, actif,
              date_desactivation, desactive_par_id)
  ON articles TO qf_agent_stock;

-- Création d'article sans prix (prix_vente prend son DEFAULT à 0).
GRANT INSERT (nom, categorie, unite, quantite_stock, site_id, fournisseur_id)
  ON articles TO qf_agent_stock;

-- Modification : nom, catégorie, unité, quantité. NI le prix, NI le seuil
-- d'alerte — ce dernier ne doit être modifiable par personne directement,
-- sinon il sert à dissimuler une disparition de marchandise (CDC §4.2).
GRANT UPDATE (nom, categorie, unite, quantite_stock)
  ON articles TO qf_agent_stock;

GRANT SELECT, INSERT ON mouvements_stock TO qf_agent_stock;
GRANT SELECT, INSERT ON comptages_stock  TO qf_agent_stock;
GRANT SELECT, INSERT ON historique_modifications_articles TO qf_agent_stock;
GRANT SELECT (id, nom, contact, telephone) ON fournisseurs TO qf_agent_stock;

-- Aucun droit sur : ventes, ventes_lignes, transactions, employes,
-- absences_conges, avances_salaire, historique_prix_articles.

-- ----------------------------------------------------------------------------
-- AGENT COMPTABILITÉ — un site. Ne voit JAMAIS les quantités en stock.
-- quantite_stock et seuil_alerte (qui en dérive) sont absents des GRANT.
-- ----------------------------------------------------------------------------
GRANT SELECT (id, nom, categorie, unite, prix_vente, site_id,
              fournisseur_id, date_creation, actif)
  ON articles TO qf_agent_comptabilite;

GRANT SELECT, INSERT, UPDATE ON ventes, ventes_lignes TO qf_agent_comptabilite;
GRANT SELECT, INSERT          ON transactions         TO qf_agent_comptabilite;
GRANT SELECT (id, nom, contact, telephone) ON fournisseurs TO qf_agent_comptabilite;

-- Rattacher une dépense de salaire à un employé, sans voir son salaire.
GRANT SELECT (id, nom_complet, poste, site_id, actif) ON employes TO qf_agent_comptabilite;

-- Aucun droit sur : comptages_stock, mouvements_stock,
-- historique_prix_articles, absences_conges, avances_salaire.

-- ----------------------------------------------------------------------------
-- Pont de privilège : décrément de stock lors d'une vente
-- ----------------------------------------------------------------------------
-- La comptabilité doit faire baisser le stock en enregistrant une vente, alors
-- qu'elle n'a aucun droit d'écriture sur articles.quantite_stock (et ne doit
-- même pas pouvoir le lire). Elle passe donc par cette fonction, exécutée avec
-- les droits de son propriétaire.
--
-- La fonction garantit UNIQUEMENT ce qui est déjà tranché :
--   * le décrément est ATOMIQUE et sérialisé (verrou de ligne) : deux ventes
--     simultanées du même article ne peuvent pas lire le même stock et
--     l'écrire toutes les deux ;
--   * le stock ne devient JAMAIS négatif (contrainte de la migration 001).
--
-- Elle ne tranche PAS ce qui ne l'est pas : que doit faire l'application quand
-- le stock est insuffisant alors que le client a déjà payé (refus, ou saisie
-- autorisée avec écart à régulariser) reste la question du point e de
-- ADDENDUM_CAHIER_DES_CHARGES.md. La fonction se contente de signaler la
-- situation avec le stock réellement disponible ; la décision appartient à la
-- couche métier, au cycle où elle aura été tranchée.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION decrementer_stock_vente(
    p_article_id     INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT 'vente'
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_restant INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    -- Verrou de ligne : sérialise les ventes concurrentes du même article.
    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT quantite_stock INTO stock_restant FROM articles WHERE id = p_article_id;

    IF stock_restant < p_quantite THEN
        RAISE EXCEPTION
          'Stock insuffisant pour l''article % : % demandé(s), % disponible(s).',
          p_article_id, p_quantite, stock_restant
          USING ERRCODE = 'check_violation',
                HINT = 'Traitement à trancher — addendum, point e.';
    END IF;

    UPDATE articles
       SET quantite_stock = quantite_stock - p_quantite
     WHERE id = p_article_id
     RETURNING quantite_stock INTO stock_restant;

    INSERT INTO mouvements_stock (article_id, type, quantite, motif, utilisateur_id)
    VALUES (p_article_id, 'sortie', p_quantite, p_motif, p_utilisateur_id);

    RETURN stock_restant;
END;
$$;

REVOKE ALL ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- Entrée de stock : le SEUIL D'ALERTE est recalculé par la base
-- ----------------------------------------------------------------------------
-- Cahier des charges §3.2 et §4.2 : le seuil d'alerte n'est jamais saisi. Il
-- vaut 20 % de la quantité REÇUE et n'est recalculé QUE lors d'une entrée de
-- stock — jamais lors d'une sortie ni d'une simple modification de fiche, pour
-- empêcher qu'il serve à masquer une disparition de marchandise. Personne ne
-- doit pouvoir le modifier directement.
--
-- Ce n'est donc plus un droit d'écriture accordé à quelqu'un, mais le RÉSULTAT
-- de cette fonction, seule voie d'entrée de stock. Le pourcentage et le
-- plancher viennent de la table « parametres », jamais d'une constante du code.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enregistrer_entree_stock(
    p_article_id     INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT 'entrée de stock'
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    pourcentage  NUMERIC;
    plancher     INTEGER;
    nouveau_seuil INTEGER;
    stock_final  INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité reçue invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    pourcentage := parametre_numerique('seuil_alerte_pourcentage');
    plancher    := parametre_numerique('seuil_alerte_plancher');

    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    nouveau_seuil := GREATEST(plancher, ROUND(p_quantite * pourcentage / 100.0)::INTEGER);

    UPDATE articles
       SET quantite_stock = quantite_stock + p_quantite,
           seuil_alerte   = nouveau_seuil
     WHERE id = p_article_id
     RETURNING quantite_stock INTO stock_final;

    INSERT INTO mouvements_stock (article_id, type, quantite, motif, utilisateur_id)
    VALUES (p_article_id, 'entree', p_quantite, p_motif, p_utilisateur_id);

    RETURN stock_final;
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

GRANT EXECUTE ON FUNCTION parametre_texte(VARCHAR), parametre_numerique(VARCHAR)
  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- Cloisonnement par SITE (socle ; exploité au cycle 3 / chantier C3)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION qf_site_courant()
RETURNS INTEGER
LANGUAGE sql
STABLE
AS $$ SELECT NULLIF(current_setting('qf.site_id', TRUE), '')::INTEGER $$;

COMMENT ON FUNCTION qf_site_courant() IS
  'Site de l''utilisateur connecté, positionné par le serveur web pour la durée '
  'de la requête : SET LOCAL qf.site_id = ''2''. NULL pour le responsable.';

GRANT EXECUTE ON FUNCTION qf_site_courant()
  TO qf_responsable, qf_agent_stock, qf_agent_comptabilite;

ALTER TABLE articles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE ventes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE mouvements_stock  ENABLE ROW LEVEL SECURITY;
ALTER TABLE comptages_stock   ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_articles_site ON articles;
CREATE POLICY p_articles_site ON articles
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

DROP POLICY IF EXISTS p_ventes_site ON ventes;
CREATE POLICY p_ventes_site ON ventes
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

DROP POLICY IF EXISTS p_transactions_site ON transactions;
CREATE POLICY p_transactions_site ON transactions
  USING      (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

-- Mouvements et comptages n'ont pas de colonne site : on passe par l'article.
DROP POLICY IF EXISTS p_mouvements_site ON mouvements_stock;
CREATE POLICY p_mouvements_site ON mouvements_stock
  USING (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = mouvements_stock.article_id
                       AND a.site_id = qf_site_courant()))
  WITH CHECK (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = mouvements_stock.article_id
                       AND a.site_id = qf_site_courant()));

DROP POLICY IF EXISTS p_comptages_site ON comptages_stock;
CREATE POLICY p_comptages_site ON comptages_stock
  USING (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = comptages_stock.article_id
                       AND a.site_id = qf_site_courant()))
  WITH CHECK (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = comptages_stock.article_id
                       AND a.site_id = qf_site_courant()));

INSERT INTO schema_migrations (version, nom)
VALUES ('008', 'roles_applicatifs')
ON CONFLICT (version) DO NOTHING;
