-- ============================================================================
-- 036 — Chantier point f (2026-09-22/23), sous-chantier 2 : retours clients
--        enrichis + casse en deux temps (déclaration -> validation).
-- ----------------------------------------------------------------------------
-- Décisions du propriétaire (ADDENDUM_CAHIER_DES_CHARGES.md, point f,
-- réponses aux questions 1 et 2) :
--
--   1. Casse/avaries : la DÉCLARATION (constat) est ouverte à n'importe quel
--      utilisateur qui la constate ; la VALIDATION de la sortie de stock
--      reste réservée au responsable seul. Ceci INVERSE la décision du
--      cycle 9 (voir 014_articles_stock_transferts_retours.sql, en-tête :
--      « aucun flux d'approbation en deux temps n'a été décrit, on ne
--      l'invente pas ») — un flux EST maintenant décrit, on l'applique.
--   2. Retour client : validation du responsable OBLIGATOIRE avant tout
--      retour (aucun agent stock ne réintègre seul) ; état de la
--      marchandise vérifié avant réintégration (pas de réintégration
--      automatique) ; trois issues (échange / avoir client / remboursement
--      espèces — ce dernier exige une confirmation explicite supplémentaire
--      du responsable) ; tracé dans l'historique du stock ET de la vente
--      (déjà le cas via mouvements_stock.vente_id, migration 014/028).
--
-- Décisions complémentaires du propriétaire (2026-09-23, validation du
-- plan) :
--   * Marchandise invendable reprise en retour : catégorie `casse`
--     EXISTANTE (motif préfixé « retour invendable — ... »), PAS de
--     nouvelle catégorie. Note d'implémentation, pas une décision
--     métier : ceci ne peut PAS se traduire par un mouvement
--     mouvements_stock réel (voir plus bas, valider_retour_client) — un tel
--     mouvement décrémenterait stocks_sites, or l'article n'a JAMAIS été
--     réintégré. La perte est tracée dans declarations_retour_client
--     (etat_marchandise = 'invendable'), sans mouvement de stock fantôme.
--   * Route d'historique de vente : HORS périmètre (rattaché à C8 si utile
--     un jour) — la traçabilité en base (mouvements_stock.vente_id) suffit.
--   * Un responsable peut valider sa propre déclaration de casse (2 appels,
--     même personne) — pas de séparation stricte déclarant/validateur.
--
-- Numérotation : 035 était pris (au moment d'écrire) par un autre chantier
-- en cours en parallèle (C3, cumul de rôles) — vu directement comme fichier
-- non committé dans le dépôt principal, jamais poussé. Reconfirmé sur
-- origin/main juste avant fusion (voir le message du cycle).
--
-- Retour fournisseur : non concerné par ces décisions, INCHANGÉ.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Casse — déclaration -> validation.
-- ----------------------------------------------------------------------------
CREATE TABLE declarations_casse (
    id                SERIAL PRIMARY KEY,
    article_id        INTEGER NOT NULL REFERENCES articles(id),
    site_id           INTEGER NOT NULL REFERENCES sites(id),
    quantite          NUMERIC(12,3) NOT NULL,
    motif             VARCHAR(200) NOT NULL,
    observation       VARCHAR(500),
    declarant_id      INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_declaration  TIMESTAMP NOT NULL DEFAULT NOW(),
    statut            VARCHAR(20) NOT NULL DEFAULT 'en_attente',
    valideur_id       INTEGER REFERENCES utilisateurs(id),
    date_validation   TIMESTAMP,
    mouvement_id      INTEGER REFERENCES mouvements_stock(id),
    CONSTRAINT chk_declarations_casse_quantite CHECK (quantite > 0),
    CONSTRAINT chk_declarations_casse_motif CHECK (length(btrim(motif)) > 0),
    CONSTRAINT chk_declarations_casse_statut CHECK (statut IN ('en_attente', 'validee')),
    CONSTRAINT chk_declarations_casse_validation_coherente CHECK (
        (statut = 'en_attente' AND valideur_id IS NULL AND date_validation IS NULL AND mouvement_id IS NULL)
        OR
        (statut = 'validee' AND valideur_id IS NOT NULL AND date_validation IS NOT NULL AND mouvement_id IS NOT NULL)
    )
);

COMMENT ON TABLE declarations_casse IS
  'Décision 2026-09-22 (addendum, point f) : la déclaration d''une casse est '
  'ouverte à tout utilisateur qui la constate ; seule la VALIDATION (qui '
  'décrémente réellement stocks_sites) est réservée au responsable. Une '
  'ligne en_attente n''a AUCUN effet sur le stock.';

CREATE INDEX idx_declarations_casse_statut ON declarations_casse (statut) WHERE statut = 'en_attente';

ALTER TABLE declarations_casse ENABLE ROW LEVEL SECURITY;
CREATE POLICY p_declarations_casse_site ON declarations_casse
  USING (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

GRANT SELECT ON declarations_casse TO qf_responsable, qf_agent_stock;

CREATE OR REPLACE FUNCTION declarer_casse(
    p_article_id   INTEGER,
    p_site_id      INTEGER,
    p_quantite     NUMERIC(12,3),
    p_motif        VARCHAR,
    p_declarant_id INTEGER,
    p_observation  VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_motif IS NULL OR length(btrim(p_motif)) = 0 THEN
        RAISE EXCEPTION 'Motif obligatoire pour déclarer une casse.' USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM stocks_sites WHERE article_id = p_article_id AND site_id = p_site_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % sans stock au site %.', p_article_id, p_site_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF qf_site_courant() IS NOT NULL AND p_site_id IS DISTINCT FROM qf_site_courant() THEN
        RAISE EXCEPTION 'Un agent stock ne peut déclarer une casse que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Pas de contrôle de stock suffisant ICI, volontairement : le stock
    -- peut bouger entre la déclaration et la validation (autre vente,
    -- autre mouvement) — le contrôle définitif se fait dans valider_casse().
    INSERT INTO declarations_casse (article_id, site_id, quantite, motif, observation, declarant_id)
    VALUES (p_article_id, p_site_id, p_quantite, p_motif, p_observation, p_declarant_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

REVOKE ALL ON FUNCTION declarer_casse(INTEGER, INTEGER, NUMERIC, VARCHAR, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION declarer_casse(INTEGER, INTEGER, NUMERIC, VARCHAR, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

CREATE OR REPLACE FUNCTION valider_casse(
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
    v_statut       VARCHAR(20);
    stock_actuel   NUMERIC(12,3);
    v_mouvement_id INTEGER;
BEGIN
    SELECT article_id, site_id, quantite, motif, statut
      INTO v_article_id, v_site_id, v_quantite, v_motif, v_statut
      FROM declarations_casse WHERE id = p_declaration_id FOR UPDATE;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Déclaration de casse % introuvable.', p_declaration_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_statut = 'validee' THEN
        RAISE EXCEPTION 'Déclaration de casse % déjà validée.', p_declaration_id
          USING ERRCODE = 'restrict_violation';
    END IF;

    PERFORM 1 FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id FOR UPDATE;
    SELECT quantite_stock INTO stock_actuel
      FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id;
    IF stock_actuel IS NULL OR stock_actuel < v_quantite THEN
        RAISE EXCEPTION 'Stock insuffisant pour valider cette casse de % : % disponible(s).',
          v_quantite, COALESCE(stock_actuel, 0)
          USING ERRCODE = 'check_violation';
    END IF;

    UPDATE stocks_sites SET quantite_stock = quantite_stock - v_quantite
     WHERE article_id = v_article_id AND site_id = v_site_id;

    INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (v_article_id, v_site_id, 'sortie', 'casse', v_quantite, v_motif, p_valideur_id)
    RETURNING id INTO v_mouvement_id;

    UPDATE declarations_casse
       SET statut = 'validee', valideur_id = p_valideur_id, date_validation = NOW(),
           mouvement_id = v_mouvement_id
     WHERE id = p_declaration_id;

    RETURN (SELECT quantite_stock FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id);
END;
$$;

REVOKE ALL ON FUNCTION valider_casse(INTEGER, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION valider_casse(INTEGER, INTEGER) TO qf_responsable;

-- L'ancienne voie directe (un seul temps) n'existe plus : une seule voie
-- d'écriture, comme partout ailleurs dans ce projet.
DROP FUNCTION IF EXISTS enregistrer_casse(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR);

-- ----------------------------------------------------------------------------
-- 2. Retour client — déclaration -> validation, avec issue et état de la
--    marchandise.
-- ----------------------------------------------------------------------------
CREATE TABLE declarations_retour_client (
    id                SERIAL PRIMARY KEY,
    article_id        INTEGER NOT NULL REFERENCES articles(id),
    vente_id          INTEGER NOT NULL REFERENCES ventes(id),
    site_id           INTEGER NOT NULL REFERENCES sites(id),
    quantite          NUMERIC(12,3) NOT NULL,
    issue             VARCHAR(30) NOT NULL,
    etat_marchandise  VARCHAR(20) NOT NULL,
    motif             VARCHAR(200),
    declarant_id      INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_declaration  TIMESTAMP NOT NULL DEFAULT NOW(),
    statut            VARCHAR(20) NOT NULL DEFAULT 'en_attente',
    valideur_id       INTEGER REFERENCES utilisateurs(id),
    date_validation   TIMESTAMP,
    mouvement_id      INTEGER REFERENCES mouvements_stock(id),
    CONSTRAINT chk_declarations_retour_quantite CHECK (quantite > 0),
    CONSTRAINT chk_declarations_retour_issue
      CHECK (issue IN ('echange', 'avoir_client', 'remboursement_especes')),
    CONSTRAINT chk_declarations_retour_etat
      CHECK (etat_marchandise IN ('revendable', 'invendable')),
    CONSTRAINT chk_declarations_retour_statut CHECK (statut IN ('en_attente', 'validee')),
    -- Une marchandise INVENDABLE validée n'a JAMAIS de mouvement de stock
    -- (rien n'a jamais été réintégré) ; une marchandise REVENDABLE validée
    -- en a TOUJOURS un (la réintégration elle-même). Imposé au niveau base,
    -- pas seulement par discipline applicative.
    CONSTRAINT chk_declarations_retour_validation_coherente CHECK (
        (statut = 'en_attente' AND valideur_id IS NULL AND date_validation IS NULL AND mouvement_id IS NULL)
        OR
        (statut = 'validee' AND valideur_id IS NOT NULL AND date_validation IS NOT NULL AND (
            (etat_marchandise = 'revendable' AND mouvement_id IS NOT NULL)
            OR
            (etat_marchandise = 'invendable' AND mouvement_id IS NULL)
        ))
    )
);

COMMENT ON TABLE declarations_retour_client IS
  'Décision 2026-09-22 (addendum, point f) : validation du responsable '
  'obligatoire avant tout retour client. etat_marchandise=invendable ne '
  'génère JAMAIS de mouvement de stock (rien n''a été réintégré) — la '
  'perte est tracée ICI, pas dans mouvements_stock (pas de mouvement '
  'fantôme). issue=remboursement_especes exige une confirmation explicite '
  'supplémentaire à la validation (voir valider_retour_client) et crée une '
  'dépense dans transactions.';

CREATE INDEX idx_declarations_retour_statut ON declarations_retour_client (statut) WHERE statut = 'en_attente';
CREATE INDEX idx_declarations_retour_vente ON declarations_retour_client (vente_id, article_id);

ALTER TABLE declarations_retour_client ENABLE ROW LEVEL SECURITY;
CREATE POLICY p_declarations_retour_site ON declarations_retour_client
  USING (current_user = 'qf_responsable' OR site_id = qf_site_courant())
  WITH CHECK (current_user = 'qf_responsable' OR site_id = qf_site_courant());

GRANT SELECT ON declarations_retour_client TO qf_responsable, qf_agent_stock;

CREATE OR REPLACE FUNCTION declarer_retour_client(
    p_article_id       INTEGER,
    p_vente_id         INTEGER,
    p_quantite         NUMERIC(12,3),
    p_issue            VARCHAR,
    p_etat_marchandise VARCHAR,
    p_declarant_id     INTEGER,
    p_motif            VARCHAR DEFAULT NULL
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    site_vente         INTEGER;
    qte_vendue         NUMERIC(12,3);
    qte_deja_retournee NUMERIC(12,3);
    qte_deja_declaree  NUMERIC(12,3);
    v_id               INTEGER;
BEGIN
    IF p_quantite IS NULL OR p_quantite <= 0 THEN
        RAISE EXCEPTION 'Quantité invalide : %.', p_quantite USING ERRCODE = 'check_violation';
    END IF;
    IF p_issue NOT IN ('echange', 'avoir_client', 'remboursement_especes') THEN
        RAISE EXCEPTION 'Issue de retour invalide : %.', p_issue USING ERRCODE = 'check_violation';
    END IF;
    IF p_etat_marchandise NOT IN ('revendable', 'invendable') THEN
        RAISE EXCEPTION 'État de la marchandise invalide : %.', p_etat_marchandise
          USING ERRCODE = 'check_violation';
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
        RAISE EXCEPTION 'Un agent stock ne peut déclarer un retour que pour son propre site.'
          USING ERRCODE = 'insufficient_privilege';
    END IF;

    SELECT COALESCE(SUM(quantite), 0) INTO qte_vendue
      FROM ventes_lignes WHERE vente_id = p_vente_id AND article_id = p_article_id;
    IF qte_vendue = 0 THEN
        RAISE EXCEPTION 'L''article % ne fait pas partie de la vente %.', p_article_id, p_vente_id
          USING ERRCODE = 'check_violation';
    END IF;

    -- Source unique : declarations_retour_client, PAS mouvements_stock —
    -- trouvé par exécution qu'un retour VALIDÉ mais invendable n'a jamais
    -- de ligne mouvements_stock (aucune réintégration), donc le compter
    -- depuis mouvements_stock seul aurait laissé passer un dépassement du
    -- vendu (ex. 3 échangés + 2 remboursés + 1 invendable = 6 réellement
    -- rendus, mais mouvements_stock n'en voit que 5).
    SELECT COALESCE(SUM(quantite), 0) INTO qte_deja_retournee
      FROM declarations_retour_client
     WHERE article_id = p_article_id AND vente_id = p_vente_id AND statut = 'validee';

    -- Les déclarations encore EN ATTENTE comptent aussi : sans ça, deux
    -- déclarations simultanées non encore validées pourraient ensemble
    -- dépasser le vendu.
    SELECT COALESCE(SUM(quantite), 0) INTO qte_deja_declaree
      FROM declarations_retour_client
     WHERE article_id = p_article_id AND vente_id = p_vente_id AND statut = 'en_attente';

    IF qte_deja_retournee + qte_deja_declaree + p_quantite > qte_vendue THEN
        RAISE EXCEPTION
          'Retour refusé : % déjà rendu(s)/en attente + % demandé(s) dépasserait les % vendu(s) pour cet article dans cette vente.',
          qte_deja_retournee + qte_deja_declaree, p_quantite, qte_vendue
          USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO declarations_retour_client
        (article_id, vente_id, site_id, quantite, issue, etat_marchandise, motif, declarant_id)
    VALUES (p_article_id, p_vente_id, site_vente, p_quantite, p_issue, p_etat_marchandise, p_motif, p_declarant_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

REVOKE ALL ON FUNCTION declarer_retour_client(INTEGER, INTEGER, NUMERIC, VARCHAR, VARCHAR, INTEGER, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION declarer_retour_client(INTEGER, INTEGER, NUMERIC, VARCHAR, VARCHAR, INTEGER, VARCHAR)
  TO qf_responsable, qf_agent_stock;

CREATE OR REPLACE FUNCTION valider_retour_client(
    p_declaration_id             INTEGER,
    p_valideur_id                INTEGER,
    p_confirmation_remboursement BOOLEAN DEFAULT FALSE
) RETURNS NUMERIC(12,3)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_article_id      INTEGER;
    v_vente_id        INTEGER;
    v_site_id         INTEGER;
    v_quantite        NUMERIC(12,3);
    v_issue           VARCHAR(30);
    v_etat            VARCHAR(20);
    v_motif           VARCHAR(200);
    v_statut          VARCHAR(20);
    v_mouvement_id    INTEGER;
    v_prix_moyen      NUMERIC(12,2);
    v_montant         NUMERIC(12,2);
    stock_final       NUMERIC(12,3);
BEGIN
    SELECT article_id, vente_id, site_id, quantite, issue, etat_marchandise, motif, statut
      INTO v_article_id, v_vente_id, v_site_id, v_quantite, v_issue, v_etat, v_motif, v_statut
      FROM declarations_retour_client WHERE id = p_declaration_id FOR UPDATE;
    IF v_article_id IS NULL THEN
        RAISE EXCEPTION 'Déclaration de retour % introuvable.', p_declaration_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_statut = 'validee' THEN
        RAISE EXCEPTION 'Déclaration de retour % déjà validée.', p_declaration_id
          USING ERRCODE = 'restrict_violation';
    END IF;

    IF v_issue = 'remboursement_especes' AND NOT p_confirmation_remboursement THEN
        RAISE EXCEPTION 'Confirmation explicite requise pour valider un remboursement espèces.'
          USING ERRCODE = 'check_violation';
    END IF;

    IF v_etat = 'revendable' THEN
        INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte)
        VALUES (v_article_id, v_site_id, 0, 0)
        ON CONFLICT (article_id, site_id) DO NOTHING;

        UPDATE stocks_sites SET quantite_stock = quantite_stock + v_quantite
         WHERE article_id = v_article_id AND site_id = v_site_id;

        INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
        VALUES (v_article_id, v_site_id, 'entree', 'retour_client', v_quantite, v_motif, p_valideur_id, v_vente_id)
        RETURNING id INTO v_mouvement_id;
    ELSE
        -- Invendable : AUCUN mouvement de stock (voir commentaire de la
        -- table) — la perte est tracée par cette ligne elle-même, motif
        -- déjà préfixé "retour invendable" côté route (server/app), pas ici
        -- (aucune écriture mouvements_stock à préfixer dans cette branche).
        v_mouvement_id := NULL;
    END IF;

    IF v_issue = 'remboursement_especes' THEN
        SELECT COALESCE(SUM(quantite * prix_unitaire) / NULLIF(SUM(quantite), 0), 0)
          INTO v_prix_moyen
          FROM ventes_lignes WHERE vente_id = v_vente_id AND article_id = v_article_id;
        v_montant := v_quantite * v_prix_moyen;

        INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
        VALUES (v_site_id, p_valideur_id, 'depense', v_montant,
                'Remboursement espèces — retour vente #' || v_vente_id, v_vente_id);
    END IF;

    UPDATE declarations_retour_client
       SET statut = 'validee', valideur_id = p_valideur_id, date_validation = NOW(),
           mouvement_id = v_mouvement_id
     WHERE id = p_declaration_id;

    SELECT quantite_stock INTO stock_final
      FROM stocks_sites WHERE article_id = v_article_id AND site_id = v_site_id;
    RETURN COALESCE(stock_final, 0);
END;
$$;

REVOKE ALL ON FUNCTION valider_retour_client(INTEGER, INTEGER, BOOLEAN) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION valider_retour_client(INTEGER, INTEGER, BOOLEAN) TO qf_responsable;

-- Ancienne voie directe (un seul temps, agent stock inclus) retirée.
DROP FUNCTION IF EXISTS enregistrer_retour_client(INTEGER, INTEGER, NUMERIC, INTEGER, VARCHAR);

INSERT INTO schema_migrations (version, nom)
VALUES ('036', 'retours_enrichis')
ON CONFLICT (version) DO NOTHING;
