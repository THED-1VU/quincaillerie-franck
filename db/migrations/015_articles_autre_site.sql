-- ============================================================================
-- 015 — Chantier C4/C9 (écran stock, cycle 11) : lister les articles de
--        l'AUTRE site, sans prix ni quantité, pour choisir la destination
--        d'un transfert inter-sites.
-- ----------------------------------------------------------------------------
-- Trou d'ergonomie trouvé en concevant l'écran de stock (cycle 11) : un
-- agent stock ne peut lire, via GET /articles, que les articles de SON
-- propre site (RLS, migration 008) — à raison, puisqu'il ne doit voir ni
-- prix ni quantité de l'autre site. Mais transferer_stock() (migration 014)
-- exige de désigner un article de destination sur l'AUTRE site : sans un
-- moyen de le nommer, l'écran devrait faire saisir un identifiant numérique
-- à l'aveugle.
--
-- Cette fonction SECURITY DEFINER ouvre une fenêtre volontairement étroite :
-- id, nom, unité, site — JAMAIS prix_achat, prix_vente, quantite_stock ni
-- seuil_alerte. Elle ne sert qu'à choisir un article dans une liste, jamais
-- à consulter l'état du stock d'un autre site.
--
-- N'INVENTE AUCUNE RÈGLE : ne change rien à ce qui est déjà décidé (points a
-- et f, migration 014) — un pur besoin de lecture pour l'ergonomie de
-- l'écran, sans toucher à l'atomicité ni aux vérifications du transfert
-- lui-même.
-- ============================================================================

CREATE OR REPLACE FUNCTION articles_autre_site()
RETURNS TABLE(id INTEGER, nom VARCHAR, unite VARCHAR, site_id INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF qf_site_courant() IS NULL THEN
        -- Un responsable n'a pas besoin de cette fonction : GET /articles
        -- lui montre déjà les deux sites (aucune RLS ne le restreint).
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

INSERT INTO schema_migrations (version, nom)
VALUES ('015', 'articles_autre_site')
ON CONFLICT (version) DO NOTHING;
