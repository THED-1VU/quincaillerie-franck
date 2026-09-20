-- ============================================================================
-- 025 — Chantier 13a (cycle 34) : rapprochement des fiches articles homonymes.
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (2026-09-20) : avant la migration article/stock
-- multi-site (cycle 13b), les fiches articles portant le MÊME nom sur des
-- sites DIFFÉRENTS doivent être rapprochées par un HUMAIN, une par une —
-- jamais fusionnées automatiquement.
--
-- Cette migration fournit :
--   1. la table ``rapprochements_articles`` : les décisions humaines
--      (``fusionner`` ou ``distincts``), une par paire, définitives ;
--   2. la fonction ``candidats_rapprochement()`` (SECURITY DEFINER, seule
--      fenêtre du rôle applicatif ``qf_app`` sur les articles pour ce
--      besoin — ``qf_app`` n'a volontairement aucun SELECT direct sur
--      ``articles``, migration 008) : les paires homonymes (même ``nom``
--      après ``btrim``, sites différents) non encore tranchées ;
--   3. la vue ``candidats_rapprochement``, simple miroir de la fonction,
--      pour l'inspection administrative (psql) et pour la migration 13b ;
--   4. la fonction ``enregistrer_rapprochement()`` (SECURITY DEFINER) qui
--      valide puis consigne une décision.
--
-- Le critère de suggestion est le nom STRICTEMENT identique (après
-- suppression des espaces de bord), décision du propriétaire : pas de
-- normalisation de casse ni d'accents — une suggestion, pas une fusion.
--
-- NOTE CYCLE 13b : quand ``articles`` perdra ``site_id``, ``quantite_stock``
-- et ``seuil_alerte``, cette migration sera remplacée par sa version
-- multi-site ; les décisions déjà enregistrées dans
-- ``rapprochements_articles``, elles, seront CONSOMMÉES telles quelles par
-- la migration de données du cycle 13b (elles ne dépendent que des ``id``).
-- ============================================================================

CREATE TABLE rapprochements_articles (
    id            SERIAL PRIMARY KEY,
    article_id_1  INTEGER NOT NULL REFERENCES articles(id),
    article_id_2  INTEGER NOT NULL REFERENCES articles(id),
    decision      VARCHAR(20) NOT NULL CHECK (decision IN ('fusionner', 'distincts')),
    decide_par    VARCHAR(150) NOT NULL,
    date_decision TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_rapprochement_paire UNIQUE (article_id_1, article_id_2),
    CONSTRAINT chk_rapprochement_ordre CHECK (article_id_1 < article_id_2)
);

COMMENT ON TABLE rapprochements_articles IS
  'Décisions humaines, une par paire d''articles homonymes, préalables à la '
  'fusion de la migration multi-site (cycle 13b). Jamais une fusion '
  'automatique : chaque ligne a été validée une par une par le propriétaire.';

-- ---------------------------------------------------------------------------
-- Fonction SECURITY DEFINER : liste des paires homonymes non tranchées.
-- Exécutée par qf_app (outil console) avec les droits du propriétaire de la
-- fonction (postgres), qui contourne la RLS par construction : la liste doit
-- montrer les DEUX sites, c'est le but même du rapprochement.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION candidats_rapprochement()
RETURNS TABLE (
    article_id_1     INTEGER,
    article_id_2     INTEGER,
    nom              VARCHAR,
    site_id_1        INTEGER,
    site_id_2        INTEGER,
    quantite_stock_1 INTEGER,
    quantite_stock_2 INTEGER
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT a.id, b.id, btrim(a.nom),
           a.site_id, b.site_id,
           a.quantite_stock, b.quantite_stock
      FROM articles a
      JOIN articles b
        ON btrim(a.nom) = btrim(b.nom)
       AND a.id < b.id
       AND a.site_id <> b.site_id
     WHERE NOT EXISTS (
           SELECT 1 FROM rapprochements_articles r
            WHERE (r.article_id_1 = a.id AND r.article_id_2 = b.id)
               OR (r.article_id_1 = b.id AND r.article_id_2 = a.id)
           )
$$;

COMMENT ON FUNCTION candidats_rapprochement() IS
  'Paires d''articles de même nom (btrim strict), sur des sites différents, '
  'sans décision enregistrée. SECURITY DEFINER : qf_app n''a aucun SELECT '
  'direct sur articles (migration 008) — cette fonction est sa fenêtre '
  'étroite, réservée au rapprochement humain du cycle 13a.';

CREATE OR REPLACE VIEW candidats_rapprochement AS
    SELECT * FROM candidats_rapprochement();

COMMENT ON VIEW candidats_rapprochement IS
  'Miroir de candidats_rapprochement() pour l''inspection administrative.';

-- ---------------------------------------------------------------------------
-- Fonction SECURITY DEFINER : consigne une décision humaine.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enregistrer_rapprochement(
    p_article_id_1 INTEGER,
    p_article_id_2 INTEGER,
    p_decision     VARCHAR,
    p_decide_par   VARCHAR
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    IF p_article_id_1 IS NULL OR p_article_id_2 IS NULL
       OR p_article_id_1 >= p_article_id_2 THEN
        RAISE EXCEPTION 'Paire invalide : les identifiants doivent être renseignés et ordonnés (id1 < id2).'
            USING ERRCODE = 'check_violation';
    END IF;
    IF p_decision NOT IN ('fusionner', 'distincts') THEN
        RAISE EXCEPTION 'Décision invalide : attendu fusionner ou distincts.'
            USING ERRCODE = 'check_violation';
    END IF;
    IF p_decide_par IS NULL OR btrim(p_decide_par) = '' THEN
        RAISE EXCEPTION 'Le nom de la personne qui décide est obligatoire.'
            USING ERRCODE = 'check_violation';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM articles a
          JOIN articles b
            ON btrim(a.nom) = btrim(b.nom)
           AND a.id < b.id
           AND a.site_id <> b.site_id
         WHERE a.id = p_article_id_1 AND b.id = p_article_id_2
    ) THEN
        RAISE EXCEPTION 'Ces deux articles ne forment pas une paire homonyme candidate.'
            USING ERRCODE = 'check_violation';
    END IF;

    IF EXISTS (
        SELECT 1 FROM rapprochements_articles
         WHERE article_id_1 = p_article_id_1 AND article_id_2 = p_article_id_2
    ) THEN
        RAISE EXCEPTION 'Une décision est déjà enregistrée pour cette paire.'
            USING ERRCODE = 'unique_violation';
    END IF;

    INSERT INTO rapprochements_articles (article_id_1, article_id_2, decision, decide_par)
    VALUES (p_article_id_1, p_article_id_2, p_decision, btrim(p_decide_par))
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

COMMENT ON FUNCTION enregistrer_rapprochement(INTEGER, INTEGER, VARCHAR, VARCHAR) IS
  'Consigne la décision humaine (fusionner/distincts) pour une paire '
  'd''articles homonymes candidate. Définitif : une paire ne se tranche '
  'qu''une fois.';

REVOKE ALL ON FUNCTION candidats_rapprochement() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION candidats_rapprochement() TO qf_app;
REVOKE ALL ON FUNCTION enregistrer_rapprochement(INTEGER, INTEGER, VARCHAR, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION enregistrer_rapprochement(INTEGER, INTEGER, VARCHAR, VARCHAR) TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('025', 'rapprochements_articles')
ON CONFLICT (version) DO NOTHING;
