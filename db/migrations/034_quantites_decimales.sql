-- ============================================================================
-- 034 — Chantier point f (2026-09-22), sous-chantier 1 : quantités décimales
--        par article.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (ADDENDUM_CAHIER_DES_CHARGES.md, point f, réponse
-- à la question 3) : chaque article porte sa propre unité de vente (sac,
-- pièce, barre, mètre, litre, kilogramme, ...) ET son propre indicateur —
-- entier seulement, ou décimal autorisé. Exemples cités : fil électrique au
-- mètre, peinture/liquides en quantité inférieure au contenant, matériaux
-- coupés à la longueur demandée, clous/vis vendus en quantité plutôt qu'au
-- conditionnement complet.
--
-- Conséquence directe : toutes les colonnes de QUANTITÉ (jamais les
-- identifiants ni les prix, déjà NUMERIC) passent d'INTEGER à NUMERIC(12,3)
-- — 3 décimales couvrent largement les exemples cités (12,50 m ; 2,5 L).
-- Un article qui n'autorise pas les décimales (valeur par défaut, la
-- majorité du catalogue — ciment, clous vendus à l'unité entière, etc.)
-- continue de REFUSER toute quantité non entière, par un déclencheur
-- (pas un simple CHECK : la règle dépend d'une AUTRE table, articles).
--
-- Réutilise EXACTEMENT le sens des 6 fonctions de stock de la migration 028
-- (mêmes règles métier, mêmes verrous FOR UPDATE) — seul le type des
-- quantités change.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Indicateur par article.
-- ----------------------------------------------------------------------------
ALTER TABLE articles
  ADD COLUMN quantite_decimale_autorisee BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN articles.quantite_decimale_autorisee IS
  'Décision 2026-09-22 (addendum, point f) : si faux (défaut), toute '
  'quantité de cet article — stock, mouvement, comptage, ligne de vente — '
  'doit être un nombre entier. Si vrai, les décimales sont acceptées '
  '(ex. 12,50 m de câble, 2,5 L de peinture). Paramétrage PAR ARTICLE, '
  'jamais global.';

-- GRANT additif (migration 029) : sans lui, ni le responsable ni l'agent
-- stock ne pourraient écrire cette colonne malgré leur INSERT/UPDATE déjà
-- posé sur `articles` — les privilèges par colonne de ce projet sont une
-- liste blanche, une colonne absente de la liste reste fermée par défaut.
-- Même paire de rôles que pour `unite` (migration 029) : le choix de
-- l'unité et l'autorisation des décimales sont la même décision de fiche.
GRANT INSERT (quantite_decimale_autorisee) ON articles TO qf_responsable;
GRANT UPDATE (quantite_decimale_autorisee) ON articles TO qf_responsable;
GRANT INSERT (quantite_decimale_autorisee) ON articles TO qf_agent_stock;
GRANT UPDATE (quantite_decimale_autorisee) ON articles TO qf_agent_stock;
-- SELECT (qf_responsable a déjà SELECT ON articles table entière, migration
-- 029 — inclut automatiquement cette nouvelle colonne, rien à ajouter pour
-- lui) : qf_agent_stock et qf_agent_comptabilite, dont la liste de colonnes
-- lisibles est fermée, en ont besoin explicitement — chacun des deux écrans
-- (stock, vente) doit savoir si l'article accepte les décimales pour
-- valider la saisie de quantité côté client (`GET /articles`,
-- demonstration.py).
GRANT SELECT (quantite_decimale_autorisee) ON articles TO qf_agent_stock;
GRANT SELECT (quantite_decimale_autorisee) ON articles TO qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- 2. Colonnes de quantité : INTEGER -> NUMERIC(12,3).
-- ----------------------------------------------------------------------------
ALTER TABLE stocks_sites ALTER COLUMN quantite_stock TYPE NUMERIC(12,3);
ALTER TABLE stocks_sites ALTER COLUMN seuil_alerte   TYPE NUMERIC(12,3);

ALTER TABLE mouvements_stock ALTER COLUMN quantite TYPE NUMERIC(12,3);

-- comptages_stock.ecart est une colonne GÉNÉRÉE (quantite_comptee -
-- quantite_attendue) : PostgreSQL refuse d'altérer le type d'une colonne
-- dont dépend une colonne générée ("cannot alter type of a column used
-- by a generated column", trouvé par exécution) — il faut la supprimer
-- puis la recréer avec le nouveau type, une fois ses colonnes sources
-- élargies. L'index partiel qui en dépend (idx_comptages_ecarts, migration
-- 002) est supprimé avec elle, recréé juste après.
DROP INDEX IF EXISTS idx_comptages_ecarts;
ALTER TABLE comptages_stock DROP COLUMN ecart;
ALTER TABLE comptages_stock ALTER COLUMN quantite_attendue TYPE NUMERIC(12,3);
ALTER TABLE comptages_stock ALTER COLUMN quantite_comptee  TYPE NUMERIC(12,3);
ALTER TABLE comptages_stock
  ADD COLUMN ecart NUMERIC(12,3) GENERATED ALWAYS AS (quantite_comptee - quantite_attendue) STORED;
CREATE INDEX idx_comptages_ecarts ON comptages_stock (date_comptage, article_id) WHERE ecart <> 0;

ALTER TABLE ventes_lignes ALTER COLUMN quantite TYPE NUMERIC(12,3);

-- Valeur DÉRIVÉE (calculée par decrementer_stock_vente(), jamais saisie
-- par un client) mais alimentée par une quantité elle-même désormais
-- décimale : sans cet élargissement, l'affectation NUMERIC -> INTEGER
-- l'arrondirait EN SILENCE (aucune erreur) à l'insertion. Trouvé en
-- relisant chaque colonne nommée `%quantite%` du schéma (`information_
-- schema.columns`), pas seulement les 4 tables citées dans l'addendum.
ALTER TABLE ecarts_stock_ventes ALTER COLUMN quantite_manquante TYPE NUMERIC(12,3);

-- `comptages_stock_ecarts_declares` (migration 003) est volontairement
-- IGNORÉE ici : archive figée, une seule écriture au moment de cette
-- migration historique, jamais retouchée depuis (« pièce à conviction ») —
-- l'élargir n'aurait aucun sens et ressemblerait à une falsification.

-- ----------------------------------------------------------------------------
-- 3. Déclencheurs : refuse une quantité non entière si l'article ne
--    l'autorise pas. Un CHECK simple est impossible ici (la règle dépend
--    de la table `articles`, pas de la ligne elle-même) — un déclencheur
--    est la seule façon de l'imposer AU NIVEAU DE LA BASE, pas seulement
--    par discipline applicative (même principe que le reste du projet :
--    la garantie doit survivre à un client qui contourne l'API).
-- ----------------------------------------------------------------------------
-- SECURITY DEFINER nécessaire ici (trouvé par exécution) : qf_agent_stock
-- n'a de GRANT SELECT que sur quelques colonnes d'articles (nom, unité —
-- jamais les prix, ni cette nouvelle colonne), alors que le déclencheur se
-- déclenche pour CE rôle sur un simple INSERT/UPDATE de stocks_sites qu'il
-- est par ailleurs autorisé à provoquer (via une fonction). Sans ceci :
-- "permission denied for table articles" au lieu du refus métier attendu.
CREATE OR REPLACE FUNCTION verifier_decimale_stocks_sites()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_decimale_ok BOOLEAN;
BEGIN
    SELECT quantite_decimale_autorisee INTO v_decimale_ok
      FROM articles WHERE id = NEW.article_id;
    IF NOT COALESCE(v_decimale_ok, FALSE) THEN
        IF NEW.quantite_stock <> trunc(NEW.quantite_stock) THEN
            RAISE EXCEPTION
              'Quantité de stock décimale refusée : l''article % n''autorise que des quantités entières.',
              NEW.article_id
              USING ERRCODE = 'check_violation';
        END IF;
        IF NEW.seuil_alerte <> trunc(NEW.seuil_alerte) THEN
            RAISE EXCEPTION
              'Seuil d''alerte décimal refusé : l''article % n''autorise que des quantités entières.',
              NEW.article_id
              USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_verifier_decimale_stocks_sites ON stocks_sites;
CREATE TRIGGER trg_verifier_decimale_stocks_sites
  BEFORE INSERT OR UPDATE ON stocks_sites
  FOR EACH ROW EXECUTE FUNCTION verifier_decimale_stocks_sites();

CREATE OR REPLACE FUNCTION verifier_decimale_mouvements_stock()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_decimale_ok BOOLEAN;
BEGIN
    SELECT quantite_decimale_autorisee INTO v_decimale_ok
      FROM articles WHERE id = NEW.article_id;
    IF NOT COALESCE(v_decimale_ok, FALSE) AND NEW.quantite <> trunc(NEW.quantite) THEN
        RAISE EXCEPTION
          'Quantité de mouvement décimale refusée : l''article % n''autorise que des quantités entières.',
          NEW.article_id
          USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_verifier_decimale_mouvements_stock ON mouvements_stock;
CREATE TRIGGER trg_verifier_decimale_mouvements_stock
  BEFORE INSERT OR UPDATE ON mouvements_stock
  FOR EACH ROW EXECUTE FUNCTION verifier_decimale_mouvements_stock();

CREATE OR REPLACE FUNCTION verifier_decimale_comptages_stock()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_decimale_ok BOOLEAN;
BEGIN
    SELECT quantite_decimale_autorisee INTO v_decimale_ok
      FROM articles WHERE id = NEW.article_id;
    IF NOT COALESCE(v_decimale_ok, FALSE) AND NEW.quantite_comptee <> trunc(NEW.quantite_comptee) THEN
        RAISE EXCEPTION
          'Quantité comptée décimale refusée : l''article % n''autorise que des quantités entières.',
          NEW.article_id
          USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_verifier_decimale_comptages_stock ON comptages_stock;
-- AFTER figer_quantite_attendue (BEFORE INSERT déjà posé, migration 028) :
-- l'ordre entre deux déclencheurs BEFORE INSERT sur la même table suit
-- l'ordre alphabétique de leur nom chez PostgreSQL ; "trg_figer..." précède
-- "trg_verifier..." (f < v), donc quantite_attendue est déjà figée par
-- stocks_sites (déjà valide) quand ce contrôle s'exécute.
CREATE TRIGGER trg_verifier_decimale_comptages_stock
  BEFORE INSERT OR UPDATE ON comptages_stock
  FOR EACH ROW EXECUTE FUNCTION verifier_decimale_comptages_stock();

CREATE OR REPLACE FUNCTION verifier_decimale_ventes_lignes()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_decimale_ok BOOLEAN;
BEGIN
    SELECT quantite_decimale_autorisee INTO v_decimale_ok
      FROM articles WHERE id = NEW.article_id;
    IF NOT COALESCE(v_decimale_ok, FALSE) AND NEW.quantite <> trunc(NEW.quantite) THEN
        RAISE EXCEPTION
          'Quantité de vente décimale refusée : l''article % n''autorise que des quantités entières.',
          NEW.article_id
          USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_verifier_decimale_ventes_lignes ON ventes_lignes;
CREATE TRIGGER trg_verifier_decimale_ventes_lignes
  BEFORE INSERT OR UPDATE ON ventes_lignes
  FOR EACH ROW EXECUTE FUNCTION verifier_decimale_ventes_lignes();

-- ----------------------------------------------------------------------------
-- 4. Les 6 fonctions de stock (migration 028) : mêmes règles métier, mêmes
--    verrous FOR UPDATE, quantités en NUMERIC(12,3) au lieu d'INTEGER.
-- ----------------------------------------------------------------------------

-- 4.0 La quantité attendue d'un comptage (déclencheur existant, migration
--     028) : NUMERIC au lieu d'INTEGER, logique identique.
CREATE OR REPLACE FUNCTION figer_quantite_attendue()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    stock_courant NUMERIC(12,3);
BEGIN
    SELECT quantite_stock INTO stock_courant
      FROM stocks_sites
     WHERE article_id = NEW.article_id AND site_id = NEW.site_id;

    IF stock_courant IS NULL THEN
        RAISE EXCEPTION 'Comptage impossible : article % sans stock au site %.',
          NEW.article_id, NEW.site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    NEW.quantite_attendue := stock_courant;
    RETURN NEW;
END;
$$;

-- 4.1 Réception fournisseur.
DROP FUNCTION IF EXISTS enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_entree_stock(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       NUMERIC(12,3),
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT 'entrée de stock'
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    pourcentage   NUMERIC;
    plancher      NUMERIC(12,3);
    nouveau_seuil NUMERIC(12,3);
    stock_final   NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité reçue invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    PERFORM 1 FROM sites WHERE id = p_site_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Site % introuvable.', p_site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND p_site_id IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut réceptionner que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    pourcentage := parametre_numerique('seuil_alerte_pourcentage');
    plancher    := parametre_numerique('seuil_alerte_plancher');
    nouveau_seuil := GREATEST(plancher, ROUND(p_quantite * pourcentage / 100.0, 3));

    INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
    VALUES (p_article_id, p_site_id, 0, 0)
    ON CONFLICT (article_id, site_id) DO NOTHING;

    PERFORM 1 FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id FOR UPDATE;

    UPDATE stocks_sites
       SET quantite_stock = quantite_stock + p_quantite,
           seuil_alerte   = nouveau_seuil
     WHERE article_id = p_article_id AND site_id = p_site_id
     RETURNING quantite_stock INTO stock_final;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, p_site_id, 'entree', 'reception_fournisseur', p_quantite, p_motif, p_utilisateur_id);

    RETURN stock_final;
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- 4.2 Vente : décrémente le stock du SITE DE LA VENTE, jamais un autre.
DROP FUNCTION IF EXISTS decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION decrementer_stock_vente(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       NUMERIC(12,3),
    p_utilisateur_id INTEGER,
    p_vente_id       INTEGER,
    p_motif          VARCHAR DEFAULT 'vente'
) RETURNS TABLE(stock_restant NUMERIC(12,3), quantite_manquante NUMERIC(12,3))
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_avant        NUMERIC(12,3);
    quantite_effective NUMERIC(12,3);
    manquant           NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    PERFORM 1 FROM stocks_sites
      WHERE article_id = p_article_id AND site_id = p_site_id
      FOR UPDATE;

    SELECT COALESCE(quantite_stock, 0) INTO stock_avant
      FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id;

    quantite_effective := LEAST(p_quantite, stock_avant);
    manquant           := p_quantite - quantite_effective;

    IF quantite_effective > 0 THEN
        UPDATE stocks_sites
           SET quantite_stock = quantite_stock - quantite_effective
         WHERE article_id = p_article_id AND site_id = p_site_id;

        INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
        VALUES (p_article_id, p_site_id, 'sortie', 'vente', quantite_effective, p_motif, p_utilisateur_id, p_vente_id);
    END IF;

    IF manquant > 0 THEN
        INSERT INTO ecarts_stock_ventes (article_id, site_id, vente_id, quantite_manquante, utilisateur_id)
        VALUES (p_article_id, p_site_id, p_vente_id, manquant, p_utilisateur_id);
    END IF;

    RETURN QUERY SELECT (stock_avant - quantite_effective), manquant;
END;
$$;

REVOKE ALL ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, NUMERIC, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, NUMERIC, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_comptabilite;

-- 4.3 Transfert : UN article, deux sites.
DROP FUNCTION IF EXISTS transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION transferer_stock(
    p_article_id       INTEGER,
    p_site_origine     INTEGER,
    p_site_destination INTEGER,
    p_quantite         NUMERIC(12,3),
    p_utilisateur_id   INTEGER,
    p_motif            VARCHAR
) RETURNS TABLE(stock_origine_restant NUMERIC(12,3), stock_destination_final NUMERIC(12,3))
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_origine NUMERIC(12,3);
    stock_dest    NUMERIC(12,3);
    id_sortie     INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour un transfert.' USING ERRCODE = 'check_violation';
    END IF;
    IF p_site_origine = p_site_destination THEN
        RAISE EXCEPTION 'Transfert refusé : origine et destination sont sur le même site.'
          USING ERRCODE = 'check_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND p_site_origine IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut initier un transfert que depuis son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
    VALUES (p_article_id, p_site_destination, 0, 0)
    ON CONFLICT (article_id, site_id) DO NOTHING;

    PERFORM 1 FROM stocks_sites
      WHERE article_id = p_article_id AND site_id IN (p_site_origine, p_site_destination)
      ORDER BY site_id FOR UPDATE;

    SELECT quantite_stock INTO stock_origine
      FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_origine;
    IF stock_origine IS NULL THEN
        RAISE EXCEPTION 'Article % sans stock au site d''origine %.', p_article_id, p_site_origine
          USING ERRCODE = 'check_violation';
    END IF;
    IF stock_origine < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour transférer % : % disponible(s).',
          p_quantite, stock_origine
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE stocks_sites SET quantite_stock = quantite_stock - p_quantite
     WHERE article_id = p_article_id AND site_id = p_site_origine;
    UPDATE stocks_sites SET quantite_stock = quantite_stock + p_quantite
     WHERE article_id = p_article_id AND site_id = p_site_destination
     RETURNING quantite_stock INTO stock_dest;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, p_site_origine, 'sortie', 'transfert', p_quantite, p_motif, p_utilisateur_id)
    RETURNING id INTO id_sortie;

    INSERT INTO mouvements_stock
        (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, mouvement_origine_id)
    VALUES
        (p_article_id, p_site_destination, 'entree', 'transfert', p_quantite, p_motif, p_utilisateur_id, id_sortie);

    RETURN QUERY
      SELECT s1.quantite_stock, s2.quantite_stock
        FROM stocks_sites s1, stocks_sites s2
       WHERE s1.article_id = p_article_id AND s1.site_id = p_site_origine
         AND s2.article_id = p_article_id AND s2.site_id = p_site_destination;
END;
$$;

REVOKE ALL ON FUNCTION transferer_stock(INTEGER, INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION transferer_stock(INTEGER, INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- 4.4 Casse.
DROP FUNCTION IF EXISTS enregistrer_casse(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_casse(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       NUMERIC(12,3),
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_actuel NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour une casse.' USING ERRCODE = 'check_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND p_site_id IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer une casse que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    PERFORM 1 FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % sans stock au site %.', p_article_id, p_site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    SELECT quantite_stock INTO stock_actuel
      FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id;
    IF stock_actuel < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour déclarer une casse de % : % disponible(s).',
          p_quantite, stock_actuel
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE stocks_sites SET quantite_stock = quantite_stock - p_quantite
     WHERE article_id = p_article_id AND site_id = p_site_id;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, p_site_id, 'sortie', 'casse', p_quantite, p_motif, p_utilisateur_id);

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_casse(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_casse(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) TO qf_responsable;

-- 4.5 Retour client.
DROP FUNCTION IF EXISTS enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_retour_client(
    p_article_id     INTEGER,
    p_vente_id       INTEGER,
    p_quantite       NUMERIC(12,3),
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT NULL
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    site_vente         INTEGER;
    qte_vendue         NUMERIC(12,3);
    qte_deja_retournee NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT site_id INTO site_vente FROM ventes WHERE id = p_vente_id;
    IF site_vente IS NULL THEN
        RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND site_vente IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT COALESCE(SUM(quantite), 0) INTO qte_vendue
      FROM ventes_lignes WHERE vente_id = p_vente_id AND article_id = p_article_id;
    IF qte_vendue = 0 THEN
        RAISE EXCEPTION 'L''article % ne fait pas partie de la vente %.', p_article_id, p_vente_id
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT COALESCE(SUM(quantite), 0) INTO qte_deja_retournee
      FROM mouvements_stock
     WHERE categorie = 'retour_client' AND vente_id = p_vente_id AND article_id = p_article_id;
    IF qte_deja_retournee + p_quantite > qte_vendue THEN
        RAISE EXCEPTION
          'Retour refusé : % déjà rendu(s) + % demandé(s) dépasserait les % vendu(s) pour cet article dans cette vente.',
          qte_deja_retournee, p_quantite, qte_vendue
          USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
    VALUES (p_article_id, site_vente, 0, 0)
    ON CONFLICT (article_id, site_id) DO NOTHING;

    UPDATE stocks_sites SET quantite_stock = quantite_stock + p_quantite
     WHERE article_id = p_article_id AND site_id = site_vente;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (p_article_id, site_vente, 'entree', 'retour_client', p_quantite, p_motif, p_utilisateur_id, p_vente_id);

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = p_article_id AND site_id = site_vente);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- 4.6 Retour fournisseur.
DROP FUNCTION IF EXISTS enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_retour_fournisseur(
    p_mouvement_origine_id INTEGER,
    p_quantite             NUMERIC(12,3),
    p_utilisateur_id       INTEGER,
    p_motif                VARCHAR DEFAULT NULL
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_article_id      INTEGER;
    v_categorie       VARCHAR(30);
    v_type            VARCHAR(20);
    v_quantite_recue  NUMERIC(12,3);
    v_deja_retourne   NUMERIC(12,3);
    v_site            INTEGER;
    stock_actuel      NUMERIC(12,3);
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    SELECT article_id, site_id, categorie, type, quantite
      INTO v_article_id, v_site, v_categorie, v_type, v_quantite_recue
      FROM mouvements_stock WHERE id = p_mouvement_origine_id;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Mouvement d''origine % introuvable.', p_mouvement_origine_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_categorie <> 'reception_fournisseur' OR v_type <> 'entree' THEN
        RAISE EXCEPTION 'Le mouvement % n''est pas une réception fournisseur.', p_mouvement_origine_id
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT COALESCE(SUM(quantite), 0) INTO v_deja_retourne
      FROM mouvements_stock
     WHERE categorie = 'retour_fournisseur' AND mouvement_origine_id = p_mouvement_origine_id;
    IF v_deja_retourne + p_quantite > v_quantite_recue THEN
        RAISE EXCEPTION
          'Retour refusé : % déjà rendu(s) + % demandé(s) dépasserait les % reçu(s) par cette réception.',
          v_deja_retourne, p_quantite, v_quantite_recue
          USING ERRCODE = 'check_violation';
    END IF;

    IF qf_site_courant() IS NOT NULL AND v_site IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    PERFORM 1 FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % sans stock au site %.', v_article_id, v_site
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    SELECT quantite_stock INTO stock_actuel
      FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site;
    IF stock_actuel < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour un retour fournisseur de % : % disponible(s).',
          p_quantite, stock_actuel
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE stocks_sites SET quantite_stock = quantite_stock - p_quantite
     WHERE article_id = v_article_id AND site_id = v_site;

    INSERT INTO mouvements_stock
        (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, mouvement_origine_id)
    VALUES
        (v_article_id, v_site, 'sortie', 'retour_fournisseur', p_quantite, p_motif, p_utilisateur_id, p_mouvement_origine_id);

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_retour_fournisseur(INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_fournisseur(INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- ----------------------------------------------------------------------------
-- 5. candidats_rapprochement() (migration 030) : lit s1.quantite_stock /
--    s2.quantite_stock (désormais NUMERIC) mais déclarait un retour
--    INTEGER — même risque d'arrondi silencieux que ci-dessus, trouvé par
--    la même relecture exhaustive.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS candidats_rapprochement;
DROP FUNCTION IF EXISTS candidats_rapprochement();
CREATE OR REPLACE FUNCTION candidats_rapprochement()
RETURNS TABLE(
    article_id_1      INTEGER,
    article_id_2      INTEGER,
    nom               VARCHAR,
    site_id_1         INTEGER,
    site_id_2         INTEGER,
    quantite_stock_1  NUMERIC(12,3),
    quantite_stock_2  NUMERIC(12,3)
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT a1.id, a2.id, a1.nom, s1.site_id, s2.site_id,
           s1.quantite_stock, s2.quantite_stock
      FROM articles a1
      JOIN articles a2
        ON a2.id > a1.id
       AND btrim(a2.nom) = btrim(a1.nom)
      JOIN stocks_sites s1 ON s1.article_id = a1.id
      JOIN stocks_sites s2 ON s2.article_id = a2.id
     WHERE a1.actif = TRUE
       AND a2.actif = TRUE
       AND s1.site_id <> s2.site_id
       AND NOT EXISTS (
             SELECT 1 FROM rapprochements_articles r
              WHERE r.article_id_1 = a1.id AND r.article_id_2 = a2.id
           )
     ORDER BY a1.nom, a1.id, a2.id;
END;
$$;

CREATE OR REPLACE VIEW candidats_rapprochement AS
SELECT * FROM candidats_rapprochement();

REVOKE ALL ON FUNCTION candidats_rapprochement() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION candidats_rapprochement() TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('034', 'quantites_decimales')
ON CONFLICT (version) DO NOTHING;
