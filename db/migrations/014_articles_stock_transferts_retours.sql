-- ============================================================================
-- 014 — Chantier C4 (articles et stock) : transfert inter-sites, casse,
--        retours client/fournisseur
-- ----------------------------------------------------------------------------
-- Décisions du propriétaire (cycle 9), addendum points a et f :
--
--   a) Transfert inter-sites : opération UNIQUE et ATOMIQUE produisant une
--      sortie du site d'origine et une entrée au site de destination, même
--      horodatage, même auteur, motif obligatoire. Ne recalcule PAS le seuil
--      d'alerte (ce n'est pas une réception fournisseur). Déclenché par le
--      responsable, ou par l'agent stock DU SITE D'ORIGINE.
--   f) Casse/avarie : sortie à motif obligatoire, réservée au responsable
--      (« validée par le responsable » = c'est lui qui l'enregistre — aucun
--      flux d'approbation en deux temps n'a été décrit, on ne l'invente pas).
--      Retour client : entrée rattachée à la vente d'origine.
--      Retour fournisseur : sortie rattachée à la réception d'origine.
--      Les trois : tracées, horodatées, attribuées — jamais confondues avec
--      une correction de quantité (aucune route ne permet d'écrire
--      articles.quantite_stock directement, seulement via ces fonctions).
--
-- CE QUI N'EST PAS TRANCHÉ ET N'EST DONC PAS TRAITÉ ICI :
--   * remises (adressées séparément dans l'addendum, point f, non demandées
--     par le propriétaire cette fois) ;
--   * unités/conversions et quantités décimales (idem, point f) ;
--   * chargement du stock initial / volumétrie (point j) — POST /articles
--     ne permet donc PAS de saisir une quantité initiale : un article naît
--     toujours à quantite_stock = 0 (défaut du schéma), toute quantité
--     réelle passe par une réception (enregistrer_entree_stock, cycle 2).
--   * "même identifiant catalogue sur les deux sites" (point a, question 4,
--     non retranchée par la décision de ce cycle) : un transfert vise DEUX
--     articles déjà existants, un par site — aucune création automatique
--     d'une fiche miroir. Si l'article n'existe pas encore au site de
--     destination, le transfert est refusé plutôt que d'inventer une fiche.
--   * seuil d'alerte sur un retour client/fournisseur : ni l'un ni l'autre
--     n'est une réception fournisseur, donc ni l'un ni l'autre ne recalcule
--     le seuil — extension directe du principe déjà posé au cycle 2
--     (migration 008 : « recalculé UNIQUEMENT lors d'une entrée de stock »
--     au sens réception, comme le confirme la décision de ce cycle pour le
--     transfert), pas une règle nouvelle.
--
-- Cycle 9 — chantier C4. Idempotent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. mouvements_stock gagne une catégorie (le "pourquoi"), en plus du type
--    (le "sens" : entrée/sortie, inchangé). Colonnes de traçabilité pour les
--    retours, nullables selon la catégorie.
-- ----------------------------------------------------------------------------
ALTER TABLE mouvements_stock ADD COLUMN IF NOT EXISTS categorie VARCHAR(30);
ALTER TABLE mouvements_stock ADD COLUMN IF NOT EXISTS vente_id INTEGER;
ALTER TABLE mouvements_stock ADD COLUMN IF NOT EXISTS mouvement_origine_id INTEGER;

-- Réamorçage des lignes déjà présentes (cycles précédents) : toute entrée
-- venait d'enregistrer_entree_stock() (réception), toute sortie de
-- decrementer_stock_vente() (vente) — les deux seules fonctions qui
-- écrivaient dans cette table avant ce cycle.
UPDATE mouvements_stock SET categorie = 'reception_fournisseur' WHERE type = 'entree' AND categorie IS NULL;
UPDATE mouvements_stock SET categorie = 'vente'                 WHERE type = 'sortie' AND categorie IS NULL;

ALTER TABLE mouvements_stock ALTER COLUMN categorie SET NOT NULL;

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie
  CHECK (categorie IN ('reception_fournisseur', 'vente', 'transfert', 'casse',
                        'retour_client', 'retour_fournisseur'));

-- Cohérence catégorie / type : une réception est toujours une entrée, une
-- vente/casse/retour fournisseur toujours une sortie, un retour client
-- toujours une entrée ; un transfert peut être l'une ou l'autre selon la
-- moitié (sortie côté origine, entrée côté destination).
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

-- Motif obligatoire pour un transfert ou une casse (décision explicite du
-- propriétaire). Resté optionnel pour les retours et la réception : rien
-- ne l'exige pour ceux-là dans la décision de ce cycle.
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_motif_obligatoire;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_motif_obligatoire
  CHECK (
    categorie NOT IN ('transfert', 'casse')
    OR (motif IS NOT NULL AND length(btrim(motif)) > 0)
  );

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS fk_mouvements_vente;
ALTER TABLE mouvements_stock ADD  CONSTRAINT fk_mouvements_vente
  FOREIGN KEY (vente_id) REFERENCES ventes(id) ON DELETE RESTRICT;

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS fk_mouvements_origine;
ALTER TABLE mouvements_stock ADD  CONSTRAINT fk_mouvements_origine
  FOREIGN KEY (mouvement_origine_id) REFERENCES mouvements_stock(id) ON DELETE RESTRICT;

-- vente_id : seulement pour un retour client. mouvement_origine_id :
-- seulement pour un retour fournisseur ou la moitié "destination" d'un
-- transfert (contrôlé par les fonctions ci-dessous, pas figé ici puisque
-- l'autre moitié du transfert n'en a légitimement pas).
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_vente_id_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_vente_id_coherent
  CHECK (
    (categorie = 'retour_client' AND vente_id IS NOT NULL)
    OR (categorie <> 'retour_client' AND vente_id IS NULL)
  );

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_origine_id_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_origine_id_coherent
  CHECK (
    mouvement_origine_id IS NULL
    OR categorie IN ('retour_fournisseur', 'transfert')
  );

COMMENT ON COLUMN mouvements_stock.categorie IS
  'Le POURQUOI du mouvement, en plus du type (le sens). Ajoutée au cycle 9 '
  '(chantier C4) pour distinguer transfert/casse/retours d''une réception ou '
  'd''une vente, sans changer le sens de la colonne "type" déjà en usage.';
COMMENT ON COLUMN mouvements_stock.mouvement_origine_id IS
  'Auto-référence : le mouvement dont celui-ci découle. Pour un retour '
  'fournisseur, la réception qu''il annule partiellement. Pour la moitié '
  '"entrée" d''un transfert, sa moitié "sortie" (même transfert, même '
  'horodatage, même auteur).';

-- ----------------------------------------------------------------------------
-- 1 bis. `categorie` étant NOT NULL, les DEUX fonctions déjà existantes qui
--        écrivent dans mouvements_stock doivent la renseigner — TROUVÉ PAR
--        EXÉCUTION (pas en relisant le code) : sans ce correctif,
--        enregistrer_entree_stock() et decrementer_stock_vente() échouent
--        immédiatement (violation de la contrainte NOT NULL), cassant à la
--        fois la réception de stock (cycle 2) ET l'enregistrement d'une
--        vente (cycle 6).
--
--        AUTRE FAILLE TROUVÉE PAR EXÉCUTION, EN EXPOSANT enregistrer_entree_
--        stock() PAR UNE ROUTE POUR LA PREMIÈRE FOIS CE CYCLE : la fonction
--        (écrite au cycle 2, jamais appelée que par des tests SQL directs
--        jusqu'ici) ne vérifiait AUCUN site — un agent stock du Magasin
--        pouvait réceptionner du stock sur un article du Comptoir. Jamais
--        exploitable avant qu'une route existe ; corrigé en l'exposant,
--        comme pour transferer_stock() ci-dessous (même piège : à
--        l'intérieur d'une fonction SECURITY DEFINER, current_user devient
--        le PROPRIÉTAIRE de la fonction, pas l'appelant — qf_site_courant()
--        reste la seule source fiable).
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

-- ----------------------------------------------------------------------------
-- 2. Transfert inter-sites : une seule fonction, deux écritures atomiques.
--    Jamais de recalcul de seuil (décision explicite). Un agent stock ne
--    peut initier que depuis SON site (vérifié explicitement : cette
--    fonction SECURITY DEFINER contourne la RLS, donc la contrainte de site
--    ne peut venir que d'ici, pas de la base).
-- ----------------------------------------------------------------------------
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

    -- Verrou des deux lignes, dans un ordre stable (id croissant) : évite un
    -- interblocage si deux transferts opposés se croisent au même instant.
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

    -- Un agent stock ne déclenche un transfert que depuis SON site (décision
    -- du propriétaire). Le responsable, qui couvre les deux sites, n'a pas
    -- cette restriction : sa session ne porte AUCUN site (qf_site_courant()
    -- vaut NULL pour lui, jamais positionné par connexion_pour()).
    --
    -- PIÈGE ÉVITÉ : `current_user` À L'INTÉRIEUR d'une fonction SECURITY
    -- DEFINER vaut le PROPRIÉTAIRE de la fonction (ici postgres), PAS
    -- l'appelant — vérifié par exécution (une première version comparait
    -- current_user = 'qf_agent_stock', qui ne se déclenchait JAMAIS, laissant
    -- n'importe quel agent transférer depuis n'importe quel site). C'est
    -- différent d'une politique RLS ordinaire, où current_user reflète bien
    -- le rôle réellement actif. qf_site_courant() reste fiable ici : c'est
    -- une variable de session (set_config), pas une identité de rôle.
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
    -- Le seuil d'alerte n'est touché NI côté origine (une sortie ne le
    -- recalcule jamais), NI côté destination (ce n'est pas une réception
    -- fournisseur — décision explicite du propriétaire).

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

-- ----------------------------------------------------------------------------
-- 3. Casse / avarie : réservée au responsable (décision de ce cycle).
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 4. Retour client : entrée rattachée à la vente d'origine, même site.
-- ----------------------------------------------------------------------------
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
    site_article INTEGER;
    site_vente   INTEGER;
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

    -- Trouvé par exécution, comme pour transferer_stock() et
    -- enregistrer_entree_stock() ci-dessus : la cohérence vente/article ne
    -- suffit pas, il faut aussi que l'AGENT APPELANT soit bien de ce site
    -- (un agent du Comptoir ne doit pas pouvoir manipuler le stock du
    -- Magasin même via une vente/article tous deux du Magasin).
    IF qf_site_courant() IS NOT NULL AND site_article IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut enregistrer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    UPDATE articles SET quantite_stock = quantite_stock + p_quantite WHERE id = p_article_id;
    -- Pas de recalcul du seuil : un retour n'est pas une réception fournisseur.

    INSERT INTO mouvements_stock (article_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (p_article_id, 'entree', 'retour_client', p_quantite, p_motif, p_utilisateur_id, p_vente_id);

    RETURN (SELECT quantite_stock FROM articles WHERE id = p_article_id);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_retour_client(INTEGER, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

-- ----------------------------------------------------------------------------
-- 5. Retour fournisseur : sortie rattachée à la réception d'origine, même
--    article (on ne rend pas un article différent de celui reçu).
-- ----------------------------------------------------------------------------
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
    v_article_id INTEGER;
    v_categorie  VARCHAR(30);
    v_type       VARCHAR(20);
    v_site       INTEGER;
    stock_actuel INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;

    SELECT article_id, categorie, type INTO v_article_id, v_categorie, v_type
      FROM mouvements_stock WHERE id = p_mouvement_origine_id;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Mouvement d''origine % introuvable.', p_mouvement_origine_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_categorie <> 'reception_fournisseur' OR v_type <> 'entree' THEN
        RAISE EXCEPTION 'Le mouvement % n''est pas une réception fournisseur.', p_mouvement_origine_id
          USING ERRCODE = 'check_violation';
    END IF;

    -- Même garde que pour les autres fonctions ci-dessus : un agent stock ne
    -- retourne au fournisseur que depuis son propre site.
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

INSERT INTO schema_migrations (version, nom)
VALUES ('014', 'articles_stock_transferts_retours')
ON CONFLICT (version) DO NOTHING;
