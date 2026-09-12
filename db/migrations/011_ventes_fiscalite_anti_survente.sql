-- ============================================================================
-- 011 — Chantier C5 (ventes) : décisions du propriétaire (addendum points b,
--        d, e) appliquées ; jamais devinées.
-- ----------------------------------------------------------------------------
-- Le propriétaire a tranché, cycle 6 (voir ADDENDUM_CAHIER_DES_CHARGES.md,
-- section « Décisions prises ») :
--   * point d (fiscalité)  : régime du réel, TVA 19,25 %, prix négociés
--     compris TTC, arrondi arithmétique standard sur le TOTAL de TVA de la
--     vente (jamais ligne à ligne).
--   * point e (anti-survente) : une vente déjà encaissée n'est JAMAIS
--     bloquée pour cause de stock insuffisant. Le stock est ramené à 0
--     (jamais négatif), et l'écart est consigné dans un journal dédié,
--     réservé au responsable — jamais visible de l'agent stock, qui compte
--     à l'aveugle (chantier C7).
--   * point b (crédit client) : PAS activé ce cycle — reste hors du CHECK
--     applicatif de la route (le mode 'credit_client' existe dans le schéma
--     d'origine mais la route serveur le refuse explicitement). Aucune table
--     Client, aucune créance : à l'arrêt tant que le reste du point b n'est
--     pas tranché.
--   * point c (numéro facturier + vendeur) : PAS traité ce cycle — objectif
--     anti-vol (priorité n°3 du propriétaire) volontairement incomplet.
--     Aucune colonne ajoutée à `ventes`. Voir loop-state.md, reste à faire.
--
-- Cycle 6 — chantier C5. Idempotent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Fiscalité (point d) : ne remplace QUE les paramètres concernés, jamais une
-- valeur au hasard. Le trigger trg_tracer_parametre (migration 006) journalise
-- automatiquement le changement dans historique_parametres et lève a_decider.
-- ----------------------------------------------------------------------------
UPDATE parametres SET
    valeur = 'reel',
    utilisateur_id = (SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1)
  WHERE cle = 'regime_fiscal';

UPDATE parametres SET
    valeur = '19.25',
    utilisateur_id = (SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1)
  WHERE cle = 'taux_tva';

UPDATE parametres SET
    valeur = 'oui',
    utilisateur_id = (SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1)
  WHERE cle = 'prix_saisis_ttc';

UPDATE parametres SET
    valeur = 'arithmetique',
    utilisateur_id = (SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1)
  WHERE cle = 'arrondi_montants';

-- ----------------------------------------------------------------------------
-- Journal des écarts de stock issus d'une vente à découvert (point e).
-- Distinct de mouvements_stock : ce n'est pas un mouvement réel (rien n'est
-- physiquement entré ni sorti pour la partie manquante), c'est un ÉCART À
-- EXPLIQUER, remonté au seul responsable — jamais à l'agent stock, qui
-- compte à l'aveugle (chantier C7 : le lien avec le prochain comptage reste
-- à construire, cette table est le socle qu'il consommera).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ecarts_stock_ventes (
    id                  SERIAL PRIMARY KEY,
    article_id          INTEGER NOT NULL REFERENCES articles(id),
    vente_id            INTEGER NOT NULL REFERENCES ventes(id),
    quantite_manquante  INTEGER NOT NULL CHECK (quantite_manquante > 0),
    utilisateur_id      INTEGER NOT NULL REFERENCES utilisateurs(id),
    regularise          BOOLEAN NOT NULL DEFAULT FALSE,
    date_ecart          TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE ecarts_stock_ventes IS
  'Écart entre quantité vendue et stock réellement disponible au moment de la '
  'vente (addendum point e) : jamais un blocage, toujours une trace. Réservé '
  'à la consultation du responsable — jamais de l''agent stock (comptage à '
  'l''aveugle, chantier C7). regularise reste FALSE tant qu''aucune route de '
  'régularisation n''existe (reste à faire).';

CREATE INDEX IF NOT EXISTS idx_ecarts_stock_ventes_article ON ecarts_stock_ventes(article_id);
CREATE INDEX IF NOT EXISTS idx_ecarts_stock_ventes_vente   ON ecarts_stock_ventes(vente_id);

ALTER TABLE ecarts_stock_ventes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_ecarts_stock_ventes_site ON ecarts_stock_ventes;
CREATE POLICY p_ecarts_stock_ventes_site ON ecarts_stock_ventes
  USING (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = ecarts_stock_ventes.article_id
                       AND a.site_id = qf_site_courant()))
  WITH CHECK (current_user = 'qf_responsable'
         OR EXISTS (SELECT 1 FROM articles a
                     WHERE a.id = ecarts_stock_ventes.article_id
                       AND a.site_id = qf_site_courant()));

-- Lecture réservée au responsable : ni l'agent stock (comptage à l'aveugle),
-- ni le comptable (n'a pas à voir les écarts de stock des autres lignes).
GRANT SELECT ON ecarts_stock_ventes TO qf_responsable;

-- ----------------------------------------------------------------------------
-- decrementer_stock_vente (migration 008) devient anti-survente (point e) :
-- ne lève plus jamais d'exception pour stock insuffisant, décrémente jusqu'à
-- 0, et consigne l'écart. Signature élargie (p_vente_id) pour rattacher
-- l'écart à la vente qui l'a produit — remplacée intégralement (DROP puis
-- CREATE, pas OR REPLACE) car le nombre de paramètres ET le type de retour
-- changent, ce que CREATE OR REPLACE FUNCTION n'autorise pas silencieusement.
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS decrementer_stock_vente(INTEGER, INTEGER, INTEGER, VARCHAR);

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

    -- Verrou de ligne : sérialise les ventes concurrentes du même article.
    PERFORM 1 FROM articles WHERE id = p_article_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Article % introuvable.', p_article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    SELECT quantite_stock INTO stock_avant FROM articles WHERE id = p_article_id;

    -- Jamais de blocage (addendum point e) : on prend tout ce qui est
    -- disponible, jamais plus. Le reste est un écart, pas un refus.
    quantite_effective := LEAST(p_quantite, stock_avant);
    manquant           := p_quantite - quantite_effective;

    IF quantite_effective > 0 THEN
        UPDATE articles
           SET quantite_stock = quantite_stock - quantite_effective
         WHERE id = p_article_id;

        INSERT INTO mouvements_stock (article_id, type, quantite, motif, utilisateur_id)
        VALUES (p_article_id, 'sortie', quantite_effective, p_motif, p_utilisateur_id);
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

INSERT INTO schema_migrations (version, nom)
VALUES ('011', 'ventes_fiscalite_anti_survente')
ON CONFLICT (version) DO NOTHING;
