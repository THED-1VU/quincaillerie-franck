-- Annule la migration 028 : restaure les fonctions dans leur version
-- antérieure (une fiche = un article ET un site, quantités sur `articles`).

CREATE OR REPLACE FUNCTION figer_quantite_attendue()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    stock_courant INTEGER;
BEGIN
    SELECT quantite_stock INTO stock_courant
      FROM articles WHERE id = NEW.article_id;

    IF stock_courant IS NULL THEN
        RAISE EXCEPTION 'Comptage impossible : article % introuvable.', NEW.article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    NEW.quantite_attendue := stock_courant;
    RETURN NEW;
END;
$$;

DROP FUNCTION IF EXISTS enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
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
    pourcentage   NUMERIC;
    plancher      INTEGER;
    nouveau_seuil INTEGER;
    stock_final   INTEGER;
    site_article  INTEGER;
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

    SELECT site_id INTO site_article FROM articles WHERE id = p_article_id;
    IF qf_site_courant() IS NOT NULL AND site_article IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut réceptionner que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    nouveau_seuil := GREATEST(plancher, ROUND(p_quantite * pourcentage / 100.0)::INTEGER);

    UPDATE articles
       SET quantite_stock = quantite_stock + p_quantite,
           seuil_alerte   = nouveau_seuil
     WHERE id = p_article_id
     RETURNING quantite_stock INTO stock_final;

    INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, 'entree', 'reception_fournisseur', p_quantite, p_motif, p_utilisateur_id);

    RETURN stock_final;
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_entree_stock(INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

DROP FUNCTION IF EXISTS decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION decrementer_stock_vente(
    p_article_id     INTEGER,
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
    stock_avant         INTEGER;
    quantite_effective  INTEGER;
    manquant            INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT quantite_stock INTO stock_avant FROM articles WHERE id = p_article_id;

    quantite_effective := LEAST(p_quantite, stock_avant);
    manquant           := p_quantite - quantite_effective;

    IF quantite_effective > 0 THEN
        UPDATE articles
           SET quantite_stock = quantite_stock - quantite_effective
         WHERE id = p_article_id;

        INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id)
        VALUES (p_article_id, 'sortie', 'vente', quantite_effective, p_motif, p_utilisateur_id);
    END IF;

    IF manquant > 0 THEN
        INSERT INTO ecarts_stock_ventes (article_id, vente_id, quantite_manquante, utilisateur_id)
        VALUES (p_article_id, p_vente_id, manquant, p_utilisateur_id);
    END IF;

    RETURN QUERY SELECT (stock_avant - quantite_effective), manquant;
END;
$$;

REVOKE ALL ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION decrementer_stock_vente(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_comptabilite;

DROP FUNCTION IF EXISTS transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION transferer_stock(
    p_article_id_origine     INTEGER,
    p_article_id_destination INTEGER,
    p_quantite               INTEGER,
    p_utilisateur_id         INTEGER,
    p_motif                  VARCHAR
) RETURNS TABLE(stock_origine_restant INTEGER, stock_destination_final INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    site_origine     INTEGER;
    site_destination INTEGER;
    stock_origine    INTEGER;
    id_sortie        INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour un transfert.' USING ERRCODE = 'check_violation';
    END IF;
    IF p_article_id_origine = p_article_id_destination THEN
        RAISE EXCEPTION 'L''article d''origine et de destination doivent être différents.'
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id IN (p_article_id_origine, p_article_id_destination)
      ORDER BY id FOR UPDATE;

    SELECT site_id, quantite_stock INTO site_origine, stock_origine
      FROM articles WHERE id = p_article_id_origine;
    IF site_origine IS NULL THEN
        RAISE EXCEPTION 'Article d''origine % introuvable.', p_article_id_origine
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT site_id INTO site_destination FROM articles WHERE id = p_article_id_destination;
    IF site_destination IS NULL THEN
        RAISE EXCEPTION 'Article de destination % introuvable.', p_article_id_destination
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    IF site_origine = site_destination THEN
        RAISE EXCEPTION 'Transfert refusé : origine et destination sont sur le même site.'
          USING ERRCODE = 'check_violation';
    END IF;

    IF qf_site_courant() IS NOT NULL AND site_origine IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut initier un transfert que depuis son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF stock_origine < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour transférer % : % disponible(s).',
          p_quantite, stock_origine
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE articles SET quantite_stock = quantite_stock - p_quantite WHERE id = p_article_id_origine;
    UPDATE articles SET quantite_stock = quantite_stock + p_quantite WHERE id = p_article_id_destination;

    INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id_origine, 'sortie', 'transfert', p_quantite, p_motif, p_utilisateur_id)
    RETURNING id INTO id_sortie;

    INSERT INTO mouvements_stock
        (article_id, type, categorie, quantite, motif, utilisateur_id, mouvement_origine_id)
    VALUES
        (p_article_id_destination, 'entree', 'transfert', p_quantite, p_motif, p_utilisateur_id, id_sortie);

    RETURN QUERY
      SELECT a1.quantite_stock, a2.quantite_stock
        FROM articles a1, articles a2
       WHERE a1.id = p_article_id_origine AND a2.id = p_article_id_destination;
END;
$$;

REVOKE ALL ON FUNCTION transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION transferer_stock(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

DROP FUNCTION IF EXISTS enregistrer_casse(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_casse(
    p_article_id     INTEGER,
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

    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT quantite_stock INTO stock_actuel FROM articles WHERE id = p_article_id;
    IF stock_actuel < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour déclarer une casse de % : % disponible(s).',
          p_quantite, stock_actuel
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE articles SET quantite_stock = quantite_stock - p_quantite WHERE id = p_article_id;

    INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, 'sortie', 'casse', p_quantite, p_motif, p_utilisateur_id);

    RETURN (SELECT quantite_stock FROM articles WHERE id = p_article_id);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_casse(INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_casse(INTEGER, INTEGER, INTEGER, VARCHAR) TO qf_responsable;

DROP FUNCTION IF EXISTS enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
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
    site_article        INTEGER;
    site_vente          INTEGER;
    qte_vendue          INTEGER;
    qte_deja_retournee  INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    SELECT site_id INTO site_article FROM articles WHERE id = p_article_id;

    SELECT site_id INTO site_vente FROM ventes WHERE id = p_vente_id;
    IF site_vente IS NULL THEN
        RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF site_vente IS DISTINCT FROM site_article THEN
        RAISE EXCEPTION 'La vente % n''appartient pas au même site que l''article %.',
          p_vente_id, p_article_id
          USING ERRCODE = 'check_violation';
    END IF;

    IF qf_site_courant() IS NOT NULL AND site_article IS DISTINCT FROM qf_site_courant() THEN
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

    UPDATE articles SET quantite_stock = quantite_stock + p_quantite WHERE id = p_article_id;

    INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (p_article_id, 'entree', 'retour_client', p_quantite, p_motif, p_utilisateur_id, p_vente_id);

    RETURN (SELECT quantite_stock FROM articles WHERE id = p_article_id);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

DROP FUNCTION IF EXISTS enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR);
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

    SELECT article_id, categorie, type, quantite
      INTO v_article_id, v_categorie, v_type, v_quantite_recue
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

    SELECT site_id INTO v_site FROM articles WHERE id = v_article_id;
    IF qf_site_courant() IS NOT NULL AND v_site IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    PERFORM 1 FROM articles WHERE id = v_article_id FOR UPDATE;
    SELECT quantite_stock INTO stock_actuel FROM articles WHERE id = v_article_id;
    IF stock_actuel < p_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour un retour fournisseur de % : % disponible(s).',
          p_quantite, stock_actuel
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE articles SET quantite_stock = quantite_stock - p_quantite WHERE id = v_article_id;

    INSERT INTO mouvements_stock
        (article_id, type, categorie, quantite, motif, utilisateur_id, mouvement_origine_id)
    VALUES
        (v_article_id, 'sortie', 'retour_fournisseur', p_quantite, p_motif, p_utilisateur_id, p_mouvement_origine_id);

    RETURN (SELECT quantite_stock FROM articles WHERE id = v_article_id);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_fournisseur(INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

CREATE OR REPLACE FUNCTION articles_autre_site()
RETURNS TABLE(id INTEGER, nom VARCHAR, unite VARCHAR, site_id INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF qf_site_courant() IS NULL THEN
        RAISE EXCEPTION 'Cette fonction est réservée à un compte rattaché à un site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    RETURN QUERY
    SELECT a.id, a.nom, a.unite, a.site_id
      FROM articles a
     WHERE a.actif = TRUE
       AND a.site_id <> qf_site_courant()
     ORDER BY a.nom;
END;
$$;

REVOKE ALL ON FUNCTION articles_autre_site() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION articles_autre_site() TO qf_agent_stock;

DELETE FROM schema_migrations WHERE version = '028';
