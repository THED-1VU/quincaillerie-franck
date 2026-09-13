-- Annule la migration 017.

DROP FUNCTION IF EXISTS annuler_vente(INTEGER, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS regulariser_ecart_vente(INTEGER, INTEGER);

ALTER TABLE ecarts_stock_ventes DROP CONSTRAINT IF EXISTS chk_ecarts_stock_ventes_regularisation_tracee;
ALTER TABLE ecarts_stock_ventes DROP CONSTRAINT IF EXISTS fk_ecarts_stock_ventes_regularise_par;
ALTER TABLE ecarts_stock_ventes DROP COLUMN IF EXISTS date_regularisation;
ALTER TABLE ecarts_stock_ventes DROP COLUMN IF EXISTS regularise_par_id;

-- Restaure decrementer_stock_vente() à son corps exact d'avant ce cycle
-- (cycle 6) : vente_id n'était pas écrit dans mouvements_stock.
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

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_vente_id_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_vente_id_coherent
  CHECK (
    (categorie = 'retour_client' AND vente_id IS NOT NULL)
    OR (categorie <> 'retour_client' AND vente_id IS NULL)
  );

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_motif_obligatoire;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_motif_obligatoire
  CHECK (
    categorie NOT IN ('transfert', 'casse')
    OR (motif IS NOT NULL AND length(btrim(motif)) > 0)
  );

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie_type_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie_type_coherent
  CHECK (
    (categorie = 'reception_fournisseur' AND type = 'entree') OR
    (categorie = 'vente'                 AND type = 'sortie') OR
    (categorie = 'casse'                 AND type = 'sortie') OR
    (categorie = 'retour_client'         AND type = 'entree') OR
    (categorie = 'retour_fournisseur'    AND type = 'sortie') OR
    (categorie = 'transfert')
  );

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie
  CHECK (categorie IN ('reception_fournisseur', 'vente', 'transfert', 'casse',
                        'retour_client', 'retour_fournisseur'));

DELETE FROM schema_migrations WHERE version = '017';
