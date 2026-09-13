-- ============================================================================
-- 017 — Chantier C5 : annulation d'une vente, régularisation d'un écart de
--        vente à découvert.
-- ----------------------------------------------------------------------------
-- Les deux manquaient depuis les cycles 2 et 6 : la mécanique de
-- transition de statut d'une vente (« annulée », tracée, irréversible)
-- existe depuis la migration 005, mais rien ne restituait le stock ni ne
-- contre-passait la recette — exactement ce que le CDC §3.3 décrit déjà
-- (« Annulation d'une vente — responsable uniquement : restitue le stock
-- et retire la recette associée »), aucune règle nouvelle inventée ici.
-- ecarts_stock_ventes.regularise existe depuis le cycle 6 (migration 011)
-- sans qu'aucune fonction ne l'ait jamais fait passer à TRUE.
--
-- FAILLE TROUVÉE PAR EXÉCUTION EN ÉCRIVANT CE CYCLE, avant tout code
-- applicatif : decrementer_stock_vente() (cycle 6) reçoit bien
-- p_vente_id en paramètre, mais ne l'écrivait JAMAIS dans
-- mouvements_stock.vente_id — seul le motif texte (« vente #123 »)
-- portait ce lien, jamais une vraie clé étrangère. Sans ça,
-- annuler_vente() ci-dessous n'aurait rien trouvé à restituer pour
-- AUCUNE vente réelle. Corrigé en 1 bis : la fonction est mise à jour
-- (CREATE OR REPLACE, même comportement sinon) pour renseigner
-- vente_id. Choix assumé : la colonne reste NULLABLE pour la catégorie
-- « vente » plutôt que rendue obligatoire — les mouvements déjà créés
-- avant ce cycle n'ont pas ce lien et il n'existe aucun moyen fiable de
-- le reconstruire après coup (le motif texte n'est pas structuré de
-- façon garantie) ; les ventes enregistrées à partir de ce cycle l'auront
-- toujours.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Nouvelle catégorie de mouvement : le stock restitué par une
--    annulation n'est ni une réception, ni un retour client (le motif
--    n'est pas le même : ici, la vente elle-même n'a jamais dû avoir
--    lieu), donc une catégorie à part, distincte des six déjà posées.
-- ----------------------------------------------------------------------------
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie
  CHECK (categorie IN ('reception_fournisseur', 'vente', 'transfert', 'casse',
                        'retour_client', 'retour_fournisseur', 'annulation_vente'));

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie_type_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie_type_coherent
  CHECK (
    (categorie = 'reception_fournisseur' AND type = 'entree') OR
    (categorie = 'vente'                 AND type = 'sortie') OR
    (categorie = 'casse'                 AND type = 'sortie') OR
    (categorie = 'retour_client'         AND type = 'entree') OR
    (categorie = 'retour_fournisseur'    AND type = 'sortie') OR
    (categorie = 'annulation_vente'      AND type = 'entree') OR
    (categorie = 'transfert')
  );

-- Motif obligatoire, comme pour un transfert ou une casse : une annulation
-- n'est pas anodine, la même prudence s'applique.
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_motif_obligatoire;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_motif_obligatoire
  CHECK (
    categorie NOT IN ('transfert', 'casse', 'annulation_vente')
    OR (motif IS NOT NULL AND length(btrim(motif)) > 0)
  );

-- vente_id : obligatoire pour retour_client et annulation_vente (inchangé
-- pour le premier) ; désormais AUTORISÉ (mais pas rendu obligatoire, voir
-- l'en-tête de ce fichier) pour la catégorie vente elle-même.
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_vente_id_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_vente_id_coherent
  CHECK (
    (categorie IN ('retour_client', 'annulation_vente') AND vente_id IS NOT NULL)
    OR (categorie = 'vente')
    OR (categorie NOT IN ('retour_client', 'annulation_vente', 'vente') AND vente_id IS NULL)
  );

-- ----------------------------------------------------------------------------
-- 1 bis. Correction de decrementer_stock_vente() (cycle 6) : renseigne
--        enfin vente_id sur le mouvement de sortie qu'elle crée — sans
--        quoi aucune vente réelle ne pourrait jamais être retrouvée pour
--        être annulée. Comportement inchangé par ailleurs.
-- ----------------------------------------------------------------------------
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

        INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
        VALUES (p_article_id, 'sortie', 'vente', quantite_effective, p_motif, p_utilisateur_id, p_vente_id);
    END IF;

    IF manquant > 0 THEN
        INSERT INTO ecarts_stock_ventes (article_id, vente_id, quantite_manquante, utilisateur_id)
        VALUES (p_article_id, p_vente_id, manquant, p_utilisateur_id);
    END IF;

    RETURN QUERY SELECT (stock_avant - quantite_effective), manquant;
END;
$$;

-- ----------------------------------------------------------------------------
-- 2. Traçabilité d'une régularisation d'écart de vente à découvert : qui,
--    quand — la colonne « regularise » existait seule depuis le cycle 6.
-- ----------------------------------------------------------------------------
ALTER TABLE ecarts_stock_ventes ADD COLUMN IF NOT EXISTS regularise_par_id INTEGER;
ALTER TABLE ecarts_stock_ventes ADD COLUMN IF NOT EXISTS date_regularisation TIMESTAMP;

ALTER TABLE ecarts_stock_ventes DROP CONSTRAINT IF EXISTS fk_ecarts_stock_ventes_regularise_par;
ALTER TABLE ecarts_stock_ventes ADD  CONSTRAINT fk_ecarts_stock_ventes_regularise_par
  FOREIGN KEY (regularise_par_id) REFERENCES utilisateurs(id);

ALTER TABLE ecarts_stock_ventes DROP CONSTRAINT IF EXISTS chk_ecarts_stock_ventes_regularisation_tracee;
ALTER TABLE ecarts_stock_ventes ADD  CONSTRAINT chk_ecarts_stock_ventes_regularisation_tracee
  CHECK (
    (regularise = FALSE AND regularise_par_id IS NULL AND date_regularisation IS NULL)
    OR
    (regularise = TRUE AND regularise_par_id IS NOT NULL AND date_regularisation IS NOT NULL)
  );

-- ----------------------------------------------------------------------------
-- 3. annuler_vente() : restitue EXACTEMENT le stock réellement décrémenté
--    (pas la quantité vendue — une vente acceptée à découvert, point e,
--    n'avait pas tout décrémenté), contre-passe la recette, régularise
--    d'office tout écart de vente à découvert devenu sans objet.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION annuler_vente(
    p_vente_id       INTEGER,
    p_utilisateur_id INTEGER,
    p_motif          VARCHAR
) RETURNS TABLE(montant_ttc NUMERIC, articles_restitues INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_statut    VARCHAR(20);
    v_site      INTEGER;
    v_total_ttc NUMERIC(12,2);
    r           RECORD;
    v_compte    INTEGER := 0;
BEGIN
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour annuler une vente.' USING ERRCODE = 'check_violation';
    END IF;

    SELECT ventes.statut, ventes.site_id, ventes.total_ttc INTO v_statut, v_site, v_total_ttc
      FROM ventes WHERE id = p_vente_id FOR UPDATE;
    IF v_statut IS NULL THEN
        RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_statut = 'annulee' THEN
        RAISE EXCEPTION 'Vente % déjà annulée.', p_vente_id
          USING ERRCODE = 'restrict_violation';
    END IF;

    FOR r IN
        SELECT article_id, SUM(quantite) AS quantite
          FROM mouvements_stock
         WHERE categorie = 'vente' AND vente_id = p_vente_id
         GROUP BY article_id
    LOOP
        UPDATE articles SET quantite_stock = quantite_stock + r.quantite WHERE id = r.article_id;
        INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
        VALUES (r.article_id, 'entree', 'annulation_vente', r.quantite, p_motif, p_utilisateur_id, p_vente_id);
        v_compte := v_compte + 1;
    END LOOP;

    UPDATE ventes
       SET statut = 'annulee', annulee_par_id = p_utilisateur_id, motif_annulation = p_motif
     WHERE id = p_vente_id;
    -- date_annulation posée par le trigger existant (migration 005),
    -- jamais par ce code : elle ne doit pas être antidatable.

    INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
    VALUES (v_site, p_utilisateur_id, 'depense', v_total_ttc,
            'Annulation de la vente #' || p_vente_id, p_vente_id);

    -- Un écart de vente à découvert devient sans objet si la vente est
    -- annulée : régularisé d'office, tracé comme tel.
    UPDATE ecarts_stock_ventes
       SET regularise = TRUE, regularise_par_id = p_utilisateur_id, date_regularisation = NOW()
     WHERE vente_id = p_vente_id AND regularise = FALSE;

    RETURN QUERY SELECT v_total_ttc, v_compte;
END;
$$;

REVOKE ALL ON FUNCTION annuler_vente(INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION annuler_vente(INTEGER, INTEGER, VARCHAR) TO qf_responsable;

-- ----------------------------------------------------------------------------
-- 4. regulariser_ecart_vente() : marque un écart de vente à découvert
--    comme traité — jamais l'inverse (comme un remboursement d'avance),
--    et jamais accessible en dehors de cette fonction (aucun GRANT UPDATE
--    direct sur ecarts_stock_ventes pour qf_responsable).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION regulariser_ecart_vente(
    p_ecart_id       INTEGER,
    p_utilisateur_id INTEGER
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_deja BOOLEAN;
BEGIN
    SELECT regularise INTO v_deja FROM ecarts_stock_ventes WHERE id = p_ecart_id FOR UPDATE;
    IF v_deja IS NULL THEN
        RAISE EXCEPTION 'Écart % introuvable.', p_ecart_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_deja THEN
        RAISE EXCEPTION 'Écart % déjà régularisé.', p_ecart_id USING ERRCODE = 'restrict_violation';
    END IF;

    UPDATE ecarts_stock_ventes
       SET regularise = TRUE, regularise_par_id = p_utilisateur_id, date_regularisation = NOW()
     WHERE id = p_ecart_id;
END;
$$;

REVOKE ALL ON FUNCTION regulariser_ecart_vente(INTEGER, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION regulariser_ecart_vente(INTEGER, INTEGER) TO qf_responsable;

INSERT INTO schema_migrations (version, nom)
VALUES ('017', 'annulation_vente_regularisation_ecart')
ON CONFLICT (version) DO NOTHING;
