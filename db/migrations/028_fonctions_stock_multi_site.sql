-- ============================================================================
-- 028 — Chantier 13b (cycle 35) : fonctions de stock sur le modèle multi-site.
-- ----------------------------------------------------------------------------
-- Toutes les fonctions SECURITY DEFINER du stock sont réécrites pour cibler
-- `stocks_sites (article_id, site_id)` au lieu des anciennes colonnes
-- d'`articles`. Le site devient un paramètre EXPLICITE là où l'opération le
-- désigne (réception, casse), est dérivé du document d'origine là où il est
-- sans ambiguïté (retour client -> vente, retour fournisseur -> réception),
-- et le transfert devient : UN article, un site d'origine, un site de
-- destination — avec création automatique de la ligne de destination si elle
-- n'existe pas (inversion du refus historique, décision du 2026-09-19).
--
-- `articles_autre_site()` (migration 015) n'a plus d'objet : le catalogue est
-- désormais commun aux deux sites, le transfert ne désigne plus un article de
-- destination. Elle est supprimée.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. La quantité attendue d'un comptage se lit dans stocks_sites, par
--    (article, site).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION figer_quantite_attendue()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    stock_courant INTEGER;
BEGIN
    SELECT quantite_stock INTO stock_courant
      FROM stocks_sites
     WHERE article_id = NEW.article_id AND site_id = NEW.site_id;

    IF stock_courant IS NULL THEN
        RAISE EXCEPTION 'Comptage impossible : article % sans stock au site %.',
          NEW.article_id, NEW.site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    -- La valeur éventuellement envoyée par le client est ignorée, sciemment.
    NEW.quantite_attendue := stock_courant;
    RETURN NEW;
END;
$$;

-- ----------------------------------------------------------------------------
-- 1. Réception fournisseur : crée la ligne de stock du site si elle n'existe
--    pas encore (première réception ouvre le stock — décision 2026-09-19).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_entree_stock(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT 'entrée de stock'
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    pourcentage   NUMERIC;
    plancher      INTEGER;
    nouveau_seuil INTEGER;
    stock_final   INTEGER;
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
    nouveau_seuil := GREATEST(plancher, ROUND(p_quantite * pourcentage / 100.0)::INTEGER);

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

REVOKE ALL ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- ----------------------------------------------------------------------------
-- 2. Vente : décrémente le stock du SITE DE LA VENTE, jamais un autre.
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS decrementer_stock_vente(INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION decrementer_stock_vente(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_vente_id       INTEGER,
    p_motif          VARCHAR DEFAULT 'vente'
) RETURNS TABLE(stock_restant INTEGER, quantite_manquante INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_avant        INTEGER;
    quantite_effective INTEGER;
    manquant           INTEGER;
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

    -- Verrou de ligne : sérialise les ventes concurrentes du même
    -- (article, site). Sans lui, deux sessions liraient le même stock et la
    -- seconde échouerait à l'UPDATE (quantité négative) au lieu de consigner
    -- un écart — prouvé par la suite de concurrence (03_concurrence.sh).
    PERFORM 1 FROM stocks_sites
      WHERE article_id = p_article_id AND site_id = p_site_id
      FOR UPDATE;

    SELECT COALESCE(quantite_stock, 0) INTO stock_avant
      FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id;

    -- Jamais de blocage (addendum point e) : on prend tout ce qui est
    -- disponible, jamais plus. Le reste est un écart, pas un refus.
    quantite_effective := LEAST(p_quantite, stock_avant);
    manquant           := p_quantite - quantite_effective;

    IF quantite_effective > 0 THEN
        UPDATE stocks_sites
           SET quantite_stock = quantite_stock - quantite_effective
         WHERE article_id = p_article_id AND site_id = p_site_id;

        INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
        VALUES (p_article_id, p_site_id, 'sortie', 'vente', quantite_effective, p_motif, p_utilisateur_id);
    END IF;

    IF manquant > 0 THEN
        INSERT INTO ecarts_stock_ventes (article_id, site_id, vente_id, quantite_manquante, utilisateur_id)
        VALUES (p_article_id, p_site_id, p_vente_id, manquant, p_utilisateur_id);
    END IF;

    RETURN QUERY SELECT (stock_avant - quantite_effective), manquant;
END;
$$;

REVOKE ALL ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_comptabilite;

-- ----------------------------------------------------------------------------
-- 3. Transfert : UN article, deux sites. La ligne de destination est créée
--    automatiquement si absente (inversion du refus historique).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION transferer_stock(
    p_article_id       INTEGER,
    p_site_origine     INTEGER,
    p_site_destination INTEGER,
    p_quantite         INTEGER,
    p_utilisateur_id   INTEGER,
    p_motif            VARCHAR
) RETURNS TABLE(stock_origine_restant INTEGER, stock_destination_final INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_origine INTEGER;
    stock_dest    INTEGER;
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

    -- Verrou des deux lignes, dans un ordre stable : évite un interblocage
    -- si deux transferts opposés se croisent au même instant.
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

REVOKE ALL ON FUNCTION transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- ----------------------------------------------------------------------------
-- 4. Casse : cible explicite (article, site).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS enregistrer_casse(INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_casse(
    p_article_id     INTEGER,
    p_site_id        INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    stock_actuel INTEGER;
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

REVOKE ALL ON FUNCTION enregistrer_casse(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_casse(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) TO qf_responsable;

-- ----------------------------------------------------------------------------
-- 5. Retour client : le site est celui de la vente d'origine (sans
--    ambiguïté) ; cohérence article/quantité conservée (migration 016).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_retour_client(
    p_article_id     INTEGER,
    p_vente_id       INTEGER,
    p_quantite       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    site_vente         INTEGER;
    qte_vendue         INTEGER;
    qte_deja_retournee INTEGER;
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
    -- Pas de recalcul du seuil : un retour n'est pas une réception fournisseur.

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (p_article_id, site_vente, 'entree', 'retour_client', p_quantite, p_motif, p_utilisateur_id, p_vente_id);

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = p_article_id AND site_id = site_vente);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- ----------------------------------------------------------------------------
-- 6. Retour fournisseur : article et site dérivés du mouvement d'origine.
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_retour_fournisseur(
    p_mouvement_origine_id INTEGER,
    p_quantite             INTEGER,
    p_utilisateur_id       INTEGER,
    p_motif                VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_article_id      INTEGER;
    v_categorie       VARCHAR(30);
    v_type            VARCHAR(20);
    v_quantite_recue  INTEGER;
    v_deja_retourne   INTEGER;
    v_site            INTEGER;
    stock_actuel      INTEGER;
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

REVOKE ALL ON FUNCTION enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- ----------------------------------------------------------------------------
-- 7. articles_autre_site() n'a plus d'objet (catalogue commun aux deux sites).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS articles_autre_site();

INSERT INTO schema_migrations (version, nom)
VALUES ('028', 'fonctions_stock_multi_site')
ON CONFLICT (version) DO NOTHING;
