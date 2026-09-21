-- ============================================================================
-- 030 — Chantier 13b (cycle 35) : adapter le rapprochement d'homonymes
--        (cycle 13a) au modèle multi-site.
-- ----------------------------------------------------------------------------
-- Depuis la migration 027, `articles` n'a plus ni `site_id` ni
-- `quantite_stock` : les fonctions du cycle 13a (migration 025) qui lisaient
-- ces colonnes sont cassées. On les réécrit sur le nouveau modèle :
--   * une paire candidate = deux FICHES de même nom strict (après btrim),
--     chacune ayant une ligne de stock sur un site DIFFÉRENT ;
--   * la quantité affichée est celle de la ligne de stock du site concerné.
-- La table `rapprochements_articles` et la vue miroir restent inchangées.
-- ============================================================================

DROP VIEW IF EXISTS candidats_rapprochement;

DROP FUNCTION IF EXISTS candidats_rapprochement();
CREATE OR REPLACE FUNCTION candidats_rapprochement()
RETURNS TABLE(
    article_id_1      INTEGER,
    article_id_2      INTEGER,
    nom               VARCHAR,
    site_id_1         INTEGER,
    site_id_2         INTEGER,
    quantite_stock_1  INTEGER,
    quantite_stock_2  INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT a1.id, a2.id, a1.nom, s1.site_id, s2.site_id,
           s1.quantite_stock, s2.quantite_stock
      FROM articles a1
      JOIN articles a2
        ON a2.id > a1.id
       AND btrim(a2.nom) = btrim(a1.nom)
      JOIN stocks_sites s1 ON s1.article_id = a1.id
      JOIN stocks_sites s2 ON s2.article_id = a2.id
     WHERE a1.actif = TRUE
       AND a2.actif = TRUE
       AND s1.site_id <> s2.site_id
       AND NOT EXISTS (
             SELECT 1 FROM rapprochements_articles r
              WHERE r.article_id_1 = a1.id AND r.article_id_2 = a2.id
           )
     ORDER BY a1.nom, a1.id, a2.id;
END;
$$;

DROP FUNCTION IF EXISTS enregistrer_rapprochement(INTEGER, INTEGER, VARCHAR, VARCHAR);
CREATE OR REPLACE FUNCTION enregistrer_rapprochement(
    p_article_id_1 INTEGER,
    p_article_id_2 INTEGER,
    p_decision     VARCHAR,
    p_decide_par   VARCHAR
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_nom        VARCHAR;
    v_site_1     INTEGER;
    v_site_2     INTEGER;
    v_rapprochement_id INTEGER;
BEGIN
    IF p_article_id_1 >= p_article_id_2 THEN
        RAISE EXCEPTION 'Les identifiants doivent être ordonnés.'
          USING ERRCODE = 'check_violation';
    END IF;
    IF p_decision NOT IN ('fusionner', 'distincts') THEN
        RAISE EXCEPTION 'Décision invalide : %. (fusionner ou distincts)', p_decision
          USING ERRCODE = 'check_violation';
    END IF;

    SELECT a1.nom, s1.site_id, s2.site_id
      INTO v_nom, v_site_1, v_site_2
      FROM articles a1
      JOIN articles a2
        ON a2.id = p_article_id_2
       AND btrim(a2.nom) = btrim(a1.nom)
      JOIN stocks_sites s1 ON s1.article_id = a1.id
      JOIN stocks_sites s2 ON s2.article_id = a2.id
     WHERE a1.id = p_article_id_1;

    IF v_nom IS NULL THEN
        RAISE EXCEPTION
          'Les articles % et % ne forment pas une paire homonyme candidate.',
          p_article_id_1, p_article_id_2
          USING ERRCODE = 'check_violation';
    END IF;
    IF v_site_1 = v_site_2 THEN
        RAISE EXCEPTION 'Les deux fiches doivent avoir un stock sur des sites différents.'
          USING ERRCODE = 'check_violation';
    END IF;

    PERFORM 1 FROM rapprochements_articles
      WHERE article_id_1 = p_article_id_1 AND article_id_2 = p_article_id_2;
    IF FOUND THEN
        RAISE EXCEPTION 'Une décision est déjà enregistrée pour cette paire.'
          USING ERRCODE = 'unique_violation';
    END IF;

    INSERT INTO rapprochements_articles
        (article_id_1, article_id_2, decision, decide_par, date_decision)
    VALUES (p_article_id_1, p_article_id_2, p_decision, p_decide_par, NOW())
    RETURNING id INTO v_rapprochement_id;

    RETURN v_rapprochement_id;
END;
$$;

CREATE OR REPLACE VIEW candidats_rapprochement AS
SELECT * FROM candidats_rapprochement();

REVOKE ALL ON FUNCTION candidats_rapprochement() FROM PUBLIC;
REVOKE ALL ON FUNCTION enregistrer_rapprochement(INTEGER, INTEGER, VARCHAR, VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION candidats_rapprochement() TO qf_app;
GRANT EXECUTE ON FUNCTION enregistrer_rapprochement(INTEGER, INTEGER, VARCHAR, VARCHAR) TO qf_app;

INSERT INTO schema_migrations (version, nom)
VALUES ('030', 'rapprochement_multi_site')
ON CONFLICT (version) DO NOTHING;
