-- ============================================================================
-- 046 — C1 : normalisation des noms d'articles pour le rapprochement à
--        l'import du stock initial (candidat 16, décidé 2026-09-26).
-- ----------------------------------------------------------------------------
-- Décision du propriétaire : un humain saisit 800 à 1 200 lignes Excel ; la
-- comparaison exacte (btrim + casse) laissait « Fer a beton », « Fer à
-- béton  12 » et « Fer à béton-12 » créer des fiches distinctes pour le même
-- article réel. La normalisation est INSENSIBLE à :
--   * la casse (minuscules) ;
--   * les accents (translate : àâä->a, éèêë->e, îï->i, ôö->o, ùûü->u, ç->c,
--     œ->o) ;
--   * les espaces multiples (réduits à un seul) ;
--   * les tirets, tirets bas et apostrophes (remplacés par une espace puis
--     réduits — « béton-12 » == « béton 12 » == « béton  12 »).
-- La fonction ne tranche JAMAIS entre plusieurs fiches : elle sert uniquement
-- de clé de rapprochement. L'outil d'import présente les paires douteuses
-- (plusieurs fiches normalisées identiques) au responsable au lieu de choisir.
-- ============================================================================

CREATE OR REPLACE FUNCTION normaliser_nom_article(p_nom VARCHAR)
RETURNS VARCHAR
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $fn$
  SELECT btrim(
    regexp_replace(
      regexp_replace(
        translate(
          lower(COALESCE(p_nom, '')),
          'àâäéèêëîïôöùûüçœ',
          'aaaeeeeiioouuuco'
        ),
        '[-_''’]+', ' ', 'g'
      ),
      '[[:space:]]+', ' ', 'g'
    )
  );
$fn$;

REVOKE ALL ON FUNCTION normaliser_nom_article(VARCHAR) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION normaliser_nom_article(VARCHAR)
  TO qf_app, qf_responsable, qf_agent_stock, qf_agent_comptabilite;

COMMENT ON FUNCTION normaliser_nom_article(VARCHAR) IS
  'Candidat 16 (C1, décidé 2026-09-26) : clé de rapprochement des noms '
  'd''articles à l''import du stock initial — insensible à la casse, aux '
  'accents, aux espaces multiples et aux tirets. Ne tranche jamais entre '
  'plusieurs fiches : l''outil appelant présente les paires douteuses au '
  'responsable.';

INSERT INTO schema_migrations (version, nom)
VALUES ('046', 'normalisation_noms_articles')
ON CONFLICT (version) DO NOTHING;
