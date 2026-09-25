-- ============================================================================
-- 041 — Point j (reprise de l'existant) : catégorie de mouvement dédiée au
--        chargement du stock initial réel.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (2026-09-19, ADDENDUM_CAHIER_DES_CHARGES.md,
-- point j) : « le chargement initial est un mouvement inventaire_initial
-- daté, tracé, non confondu avec des entrées fournisseur (n'active pas la
-- règle des 20 %) — le seuil initial est [...] fixé à 20 % de la quantité
-- initiale par convention à valider ». Confirmé (validation du plan,
-- 2026-09-25) : la convention des 20 % est retenue — même règle que
-- enregistrer_entree_stock() (migration 002), mais catégorie et fonction
-- distinctes : l'addendum est explicite, « non confondu ».
--
-- Périmètre de ce cycle : import du STOCK seul (articles, stocks_sites,
-- fournisseurs). Le crédit client (15 à 25 clients débiteurs, point b) est
-- volontairement écarté — point b n'est pas construit (aucune table
-- clients), la décision littérale de l'addendum (charger les deux
-- ensemble) est donc reportée à un chantier point b séparé (validation du
-- plan, 2026-09-25).
--
-- Numéro de migration : 041, pas 040 — 040 est déjà pris DEUX FOIS par des
-- sessions concurrentes (`040_plafond_vraisemblance_decide.sql` et
-- `040_vendeur_employe.sql`, chantier B de cette même session) : une
-- collision déjà fusionnée sur main, reconfirmée sans effet fonctionnel
-- (les deux migrations 040 s'appliquent réellement, seule la ligne de
-- `schema_migrations` pour la version '040' ne reflète que la première des
-- deux par ordre alphabétique — un défaut de traçabilité déjà en
-- production, hors périmètre de ce cycle).
-- ============================================================================

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie
  CHECK (categorie IN ('reception_fournisseur', 'vente', 'transfert', 'casse',
                        'retour_client', 'retour_fournisseur', 'annulation_vente',
                        'article_offert', 'inventaire_initial'));

ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie_type_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie_type_coherent
  CHECK (
    (categorie = 'reception_fournisseur' AND type = 'entree') OR
    (categorie = 'vente'                 AND type = 'sortie') OR
    (categorie = 'casse'                 AND type = 'sortie') OR
    (categorie = 'retour_client'         AND type = 'entree') OR
    (categorie = 'retour_fournisseur'    AND type = 'sortie') OR
    (categorie = 'annulation_vente'      AND type = 'entree') OR
    (categorie = 'transfert') OR
    (categorie = 'article_offert'        AND type = 'sortie') OR
    (categorie = 'inventaire_initial'    AND type = 'entree')
  );

-- ----------------------------------------------------------------------------
-- Fonction SECURITY DEFINER dédiée : crée la ligne de stock si absente,
-- recalcule le seuil à 20 % (même formule que enregistrer_entree_stock,
-- migration 002/028), catégorise le mouvement 'inventaire_initial'. Motif
-- porte la zone/catégorie de chargement (texte libre, décision
-- d'implémentation — pas une colonne permanente sur articles, addendum
-- point j n'en demande pas).
--
-- Idempotence (addendum point j : « sans jamais dupliquer ») : VOLONTAIRE-
-- MENT absente ici — la détection « déjà chargé » est la responsabilité de
-- l'outil appelant (db/outils/importer_stock_initial.py), qui interroge
-- stocks_sites AVANT d'appeler cette fonction. Cette fonction reste une
-- primitive simple, réutilisable telle quelle par d'autres outils futurs,
-- sans logique d'import particulière figée dedans.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enregistrer_inventaire_initial(
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
    v_seuil       NUMERIC(12,3);
    v_decimale_ok BOOLEAN;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire (zone/catégorie de chargement).'
          USING ERRCODE = 'check_violation';
    END IF;
    SELECT quantite_decimale_autorisee INTO v_decimale_ok FROM articles WHERE id = p_article_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id USING ERRCODE = 'foreign_key_violation';
    END IF;

    -- Trouvé par exécution (test réel de l'outil d'import) : un article qui
    -- n'autorise pas les quantités décimales (quantite_decimale_autorisee =
    -- false, valeur par défaut) refuse aussi un SEUIL décimal (trigger
    -- verifier_decimale_stocks_sites, migration 034) — et 20 % d'une
    -- quantité entière ordinaire (ex. 13, 17...) est très souvent décimal.
    -- Arrondi à l'entier dans ce cas, comme le fait déjà
    -- enregistrer_entree_stock() implicitement pour les articles anciens
    -- (avant que la même faille latente n'y soit constatée — non corrigée
    -- là, hors périmètre de ce cycle, migrations 002/028/034 déjà
    -- fusionnées ; signalé au propriétaire).
    v_seuil := round(p_quantite * 0.20, CASE WHEN v_decimale_ok THEN 3 ELSE 0 END);

    INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
    VALUES (p_article_id, p_site_id, p_quantite, v_seuil)
    ON CONFLICT (article_id, site_id) DO UPDATE
      SET quantite_stock = stocks_sites.quantite_stock + EXCLUDED.quantite_stock,
          seuil_alerte    = round((stocks_sites.quantite_stock + EXCLUDED.quantite_stock) * 0.20,
                                   CASE WHEN v_decimale_ok THEN 3 ELSE 0 END);

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (p_article_id, p_site_id, 'entree', 'inventaire_initial', p_quantite, p_motif, p_utilisateur_id);

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id);
END;
$$;

REVOKE ALL ON FUNCTION enregistrer_inventaire_initial(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_inventaire_initial(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR)
  TO qf_responsable;

COMMENT ON FUNCTION enregistrer_inventaire_initial(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR) IS
  'Chargement du stock initial réel (addendum point j, décidé 2026-09-19) — '
  'catégorie de mouvement dédiée, JAMAIS confondue avec reception_fournisseur. '
  'Réservée au responsable (import mené par le prestataire, qui agit avec un '
  'compte responsable — db/outils/importer_stock_initial.py). Si un stock '
  'existe déjà pour (article, site), la quantité s''ADDITIONNE (chargement '
  'partiel/successif par zone, addendum point j) — l''idempotence par ligne '
  '(ne pas ré-additionner deux fois la même ligne de fichier) est la '
  'responsabilité de l''outil appelant, pas de cette fonction.';

INSERT INTO schema_migrations (version, nom)
VALUES ('041', 'inventaire_initial')
ON CONFLICT (version) DO NOTHING;
