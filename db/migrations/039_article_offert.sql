-- ============================================================================
-- 039 — Chantier point f (2026-09-24), sous-chantier 4 : article offert.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (ADDENDUM_CAHIER_DES_CHARGES.md, point f, réponse
-- à la question 5) : un article offert est DISTINCT d'une remise à 100 %
-- (migration 037, qui la refuse explicitement) — une « sortie commerciale
-- gratuite » identifiée comme telle en base, jamais une vente à prix nul.
-- L'article est déduit du stock même si le montant facturé est zéro.
-- Conservés : article, quantité, valeur normale (pour ne pas fausser la
-- marge dans les rapports C8 — la valeur théorique perdue reste visible même
-- si la recette encaissée est nulle), client si identifié, motif,
-- utilisateur, validation du responsable si nécessaire.
--
-- Décisions complémentaires (validation du plan, 2026-09-24) :
--   * Même schéma déclaration -> validation que la casse (sous-chantier 2,
--     migration 036) : ouverte à qui vend (agent comptabilité, responsable),
--     aucun effet sur le stock tant que non validée ; validation réservée
--     au responsable, qui décrémente réellement.
--   * vente_id NULLABLE : un article offert peut accompagner une vente
--     réelle (« 10 achetés, 1 offert ») ou être une opération autonome
--     (pur geste commercial) — les deux sont légitimes.
--   * Le VENDEUR d'une vente (ventes.vendeur_id, migration 020) référence
--     un compte utilisateur — décision du 2026-09-13, INCHANGÉE par ce
--     cycle (la question 3 de l'addendum point c reste ouverte). Ici, en
--     revanche, l'EMPLOYÉ qui a offert l'article est une exigence NEUVE et
--     plus stricte (2026-09-24) : « un article offert est le geste le plus
--     facile à détourner » — employe_id NOT NULL référence la fiche RH
--     (employes, migration socle), choisi parmi les employés ACTIFS du
--     site, distinct de declarant_id (le compte qui SAISIT la déclaration).
--     Les deux notions (vendeur_id sur ventes, employe_id ici) coexistent
--     sans être unifiées : rien ne les rapproche automatiquement.
--   * valeur_normale n'est JAMAIS fournie par le client de l'API : calculée
--     ICI, dans la fonction SECURITY DEFINER, depuis articles.prix_vente au
--     moment de la déclaration, puis figée — même principe que
--     ventes_lignes.prix_catalogue (migration 037).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Nouvelle catégorie de mouvement de stock.
-- ----------------------------------------------------------------------------
-- Liste de base reprise de la migration 017 (PAS 014, qui ne connaissait pas
-- encore 'annulation_vente') — trouvé par exécution : une première version
-- de ce fichier, basée sur 014, faisait régresser
-- test_annulation_vente_regularise_automatiquement_lecart (chk_mouvements_categorie
-- refusait 'annulation_vente'), corrigé avant tout commit.
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_categorie;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_categorie
  CHECK (categorie IN ('reception_fournisseur', 'vente', 'transfert', 'casse',
                        'retour_client', 'retour_fournisseur', 'annulation_vente',
                        'article_offert'));

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
    (categorie = 'article_offert'        AND type = 'sortie')
  );

-- vente_id : la contrainte posée par la migration 017 refusait vente_id
-- pour toute catégorie hors vente/retour_client/annulation_vente — trouvé
-- par exécution en testant la validation d'une déclaration rattachée à une
-- vente. article_offert rejoint 'vente' (vente_id AUTORISÉ mais pas
-- OBLIGATOIRE, cf. décision « vente_id nullable » ci-dessus), jamais dans
-- le groupe « obligatoire ».
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_vente_id_coherent;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_vente_id_coherent
  CHECK (
    (categorie IN ('retour_client', 'annulation_vente') AND vente_id IS NOT NULL)
    OR (categorie IN ('vente', 'article_offert'))
    OR (categorie NOT IN ('retour_client', 'annulation_vente', 'vente', 'article_offert') AND vente_id IS NULL)
  );

-- ----------------------------------------------------------------------------
-- 2. Article offert — déclaration -> validation (même schéma que la casse).
-- ----------------------------------------------------------------------------
CREATE TABLE declarations_article_offert (
    id                SERIAL PRIMARY KEY,
    article_id        INTEGER NOT NULL REFERENCES articles(id),
    site_id           INTEGER NOT NULL REFERENCES sites(id),
    quantite          NUMERIC(12,3) NOT NULL,
    valeur_normale    NUMERIC(12,2) NOT NULL,
    vente_id          INTEGER REFERENCES ventes(id),
    client_nom        VARCHAR(150),
    employe_id        INTEGER NOT NULL REFERENCES employes(id),
    motif             VARCHAR(200) NOT NULL,
    declarant_id      INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_declaration  TIMESTAMP NOT NULL DEFAULT NOW(),
    statut            VARCHAR(20) NOT NULL DEFAULT 'en_attente',
    valideur_id       INTEGER REFERENCES utilisateurs(id),
    date_validation   TIMESTAMP,
    mouvement_id      INTEGER REFERENCES mouvements_stock(id),
    CONSTRAINT chk_declarations_offert_quantite CHECK (quantite > 0),
    CONSTRAINT chk_declarations_offert_valeur CHECK (valeur_normale >= 0),
    CONSTRAINT chk_declarations_offert_motif CHECK (length(btrim(motif)) > 0),
    CONSTRAINT chk_declarations_offert_statut CHECK (statut IN ('en_attente', 'validee')),
    -- Contrairement au retour client (migration 036), il n'existe pas de cas
    -- « sans mouvement » ici : un article offert validé décrémente TOUJOURS
    -- le stock (il est physiquement remis au client).
    CONSTRAINT chk_declarations_offert_validation_coherente CHECK (
        (statut = 'en_attente' AND valideur_id IS NULL AND date_validation IS NULL AND mouvement_id IS NULL)
        OR
        (statut = 'validee' AND valideur_id IS NOT NULL AND date_validation IS NOT NULL AND mouvement_id IS NOT NULL)
    )
);

COMMENT ON TABLE declarations_article_offert IS
  'Décision 2026-09-22/24 (addendum, point f, question 5) : une sortie '
  'commerciale gratuite, distincte d''une remise à 100 % (jamais une vente '
  'à prix nul). Déclaration ouverte à qui vend (agent comptabilité, '
  'responsable), aucun effet sur le stock tant que non validée. Validation '
  'réservée au responsable, qui décrémente réellement. valeur_normale '
  'figée à la déclaration (articles.prix_vente au moment T), jamais '
  'relue après coup, pour ne pas fausser la marge dans les rapports C8. '
  'employe_id : qui a physiquement offert l''article (fiche RH) — exigence '
  'du 2026-09-24, distincte de declarant_id (qui saisit).';

CREATE INDEX idx_declarations_offert_statut ON declarations_article_offert (statut) WHERE statut = 'en_attente';
CREATE INDEX idx_declarations_offert_article_site ON declarations_article_offert (article_id, site_id) WHERE statut = 'en_attente';

ALTER TABLE declarations_article_offert ENABLE ROW LEVEL SECURITY;
CREATE POLICY p_declarations_offert_site ON declarations_article_offert
  USING (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

GRANT SELECT ON declarations_article_offert TO qf_responsable, qf_agent_comptabilite;

CREATE OR REPLACE FUNCTION declarer_article_offert(
    p_article_id   INTEGER,
    p_site_id      INTEGER,
    p_quantite     NUMERIC(12,3),
    p_motif        VARCHAR,
    p_employe_id   INTEGER,
    p_declarant_id INTEGER,
    p_vente_id     INTEGER DEFAULT NULL,
    p_client_nom   VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_prix_vente   NUMERIC(12,2);
    v_employe_site INTEGER;
    v_employe_actif BOOLEAN;
    v_vente_site   INTEGER;
    v_id           INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour déclarer un article offert.' USING ERRCODE = 'check_violation';
    END IF;

    SELECT prix_vente INTO v_prix_vente FROM articles WHERE id = p_article_id;
    IF v_prix_vente IS NULL THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id USING ERRCODE = 'foreign_key_violation';
    END IF;

    PERFORM 1 FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % sans stock au site %.', p_article_id, p_site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND p_site_id IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent ne peut déclarer un article offert que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT site_id, actif INTO v_employe_site, v_employe_actif
      FROM employes WHERE id = p_employe_id;
    IF v_employe_actif IS NULL THEN
        RAISE EXCEPTION 'Employé % introuvable.', p_employe_id USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF NOT v_employe_actif THEN
        RAISE EXCEPTION 'L''employé % n''est plus actif.', p_employe_id USING ERRCODE = 'check_violation';
    END IF;
    IF v_employe_site IS NOT NULL AND v_employe_site IS DISTINCT FROM p_site_id THEN
        RAISE EXCEPTION 'L''employé % n''appartient pas au site %.', p_employe_id, p_site_id
          USING ERRCODE = 'check_violation';
    END IF;

    IF p_vente_id IS NOT NULL THEN
        SELECT site_id INTO v_vente_site FROM ventes WHERE id = p_vente_id;
        IF v_vente_site IS NULL THEN
            RAISE EXCEPTION 'Vente % introuvable.', p_vente_id USING ERRCODE = 'foreign_key_violation';
        END IF;
        IF v_vente_site IS DISTINCT FROM p_site_id THEN
            RAISE EXCEPTION 'La vente % ne correspond pas au site %.', p_vente_id, p_site_id
              USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    -- Pas de contrôle de stock suffisant ICI, volontairement : le stock peut
    -- bouger entre la déclaration et la validation — le contrôle définitif
    -- se fait dans valider_article_offert() (même principe que la casse).
    INSERT INTO declarations_article_offert
        (article_id, site_id, quantite, valeur_normale, vente_id, client_nom,
         employe_id, motif, declarant_id)
    VALUES
        (p_article_id, p_site_id, p_quantite, v_prix_vente * p_quantite, p_vente_id,
         p_client_nom, p_employe_id, p_motif, p_declarant_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

REVOKE ALL ON FUNCTION declarer_article_offert(INTEGER, INTEGER, NUMERIC, VARCHAR, INTEGER, INTEGER, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION declarer_article_offert(INTEGER, INTEGER, NUMERIC, VARCHAR, INTEGER, INTEGER, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_comptabilite;

CREATE OR REPLACE FUNCTION valider_article_offert(
    p_declaration_id INTEGER,
    p_valideur_id    INTEGER
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_article_id   INTEGER;
    v_site_id      INTEGER;
    v_quantite     NUMERIC(12,3);
    v_motif        VARCHAR(200);
    v_vente_id     INTEGER;
    v_statut       VARCHAR(20);
    stock_actuel   NUMERIC(12,3);
    v_mouvement_id INTEGER;
BEGIN
    SELECT article_id, site_id, quantite, motif, vente_id, statut
      INTO v_article_id, v_site_id, v_quantite, v_motif, v_vente_id, v_statut
      FROM declarations_article_offert WHERE id = p_declaration_id FOR UPDATE;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Déclaration d''article offert % introuvable.', p_declaration_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_statut = 'validee' THEN
        RAISE EXCEPTION 'Déclaration d''article offert % déjà validée.', p_declaration_id
          USING ERRCODE = 'restrict_violation';
    END IF;

    PERFORM 1 FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id FOR UPDATE;
    SELECT quantite_stock INTO stock_actuel
      FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id;
    IF stock_actuel IS NULL OR stock_actuel < v_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour valider cet article offert de % : % disponible(s).',
          v_quantite, COALESCE(stock_actuel, 0)
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE stocks_sites SET quantite_stock = quantite_stock - v_quantite
     WHERE article_id = v_article_id AND site_id = v_site_id;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (v_article_id, v_site_id, 'sortie', 'article_offert', v_quantite, v_motif, p_valideur_id, v_vente_id)
    RETURNING id INTO v_mouvement_id;

    UPDATE declarations_article_offert
       SET statut = 'validee', valideur_id = p_valideur_id, date_validation = NOW(),
           mouvement_id = v_mouvement_id
     WHERE id = p_declaration_id;

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id);
END;
$$;

REVOKE ALL ON FUNCTION valider_article_offert(INTEGER, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION valider_article_offert(INTEGER, INTEGER) TO qf_responsable;

INSERT INTO schema_migrations (version, nom)
VALUES ('039', 'article_offert')
ON CONFLICT (version) DO NOTHING;
