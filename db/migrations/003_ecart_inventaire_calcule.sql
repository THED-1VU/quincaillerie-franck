-- ============================================================================
-- 003 — L'écart d'inventaire devient un CALCUL DE LA BASE
-- ----------------------------------------------------------------------------
-- C'EST LA MIGRATION LA PLUS IMPORTANTE DU CYCLE : l'écart d'inventaire est la
-- mesure qui détecte la disparition de marchandise. Dans le schéma d'origine,
-- il est ÉCRIT par le programme client. Diagnostic du cycle 2, prouvé par
-- exécution : on a inséré « attendu 10, compté 3, écart 0 » — accepté. Un vol
-- de 7 sacs devenait invisible.
--
-- Deux failles, deux verrous :
--
--   1. « ecart » écrit librement          → colonne GÉNÉRÉE par la base
--                                           (quantite_comptee - quantite_attendue).
--                                           Toute tentative d'écriture est REFUSÉE.
--
--   2. « quantite_attendue » fournie par  → renseignée par la base elle-même,
--      le client (il suffisait d'envoyer     par déclencheur, à partir de
--      attendue = comptée pour un écart      articles.quantite_stock au moment
--      nul)                                  du comptage. La valeur envoyée par
--                                            le client est ignorée.
--
-- Il ne reste donc qu'UNE seule valeur d'origine humaine : « quantite_comptee »,
-- ce que l'agent a réellement compté. C'est exactement l'intention du comptage
-- à l'aveugle du cahier des charges §3.6.
--
-- En complément : un comptage est un FAIT, il n'est plus modifiable après coup,
-- et il ne peut y en avoir qu'un par article, par moment et par jour.
--
-- Cycle 2 — chantier C1.
-- NOTE : la colonne « ecart » est recréée, elle passe donc en dernière position
-- dans la table. Sa valeur est recalculée pour toutes les lignes existantes.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Conservation des écarts MENSONGERS déjà présents, avant recalcul.
-- Si une base en production contient des lignes où l'écart déclaré ne
-- correspond pas au calcul, on ne les efface pas : on les archive. C'est une
-- pièce à conviction, pas un détail technique.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comptages_stock_ecarts_declares (
    id                 SERIAL PRIMARY KEY,
    comptage_id        INTEGER   NOT NULL,
    ecart_declare      INTEGER   NOT NULL,
    ecart_recalcule    INTEGER   NOT NULL,
    quantite_attendue  INTEGER   NOT NULL,
    quantite_comptee   INTEGER   NOT NULL,
    archive_le         TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE comptages_stock_ecarts_declares IS
  'Écarts d''inventaire qui avaient été DÉCLARÉS par le programme client et qui '
  'ne correspondaient pas au calcul, relevés lors de la migration 003. '
  'Conservés comme pièce à conviction.';

INSERT INTO comptages_stock_ecarts_declares
    (comptage_id, ecart_declare, ecart_recalcule, quantite_attendue, quantite_comptee)
SELECT id, ecart, (quantite_comptee - quantite_attendue), quantite_attendue, quantite_comptee
  FROM comptages_stock
 WHERE ecart IS DISTINCT FROM (quantite_comptee - quantite_attendue);

-- ----------------------------------------------------------------------------
-- 1. « ecart » : colonne générée, non inscriptible
-- ----------------------------------------------------------------------------
ALTER TABLE comptages_stock DROP COLUMN IF EXISTS ecart;
ALTER TABLE comptages_stock
  ADD COLUMN ecart INTEGER
  GENERATED ALWAYS AS (quantite_comptee - quantite_attendue) STORED;

COMMENT ON COLUMN comptages_stock.ecart IS
  'CALCULÉ PAR LA BASE : quantite_comptee - quantite_attendue. Négatif = '
  'marchandise manquante. Aucun programme client ne peut écrire cette valeur.';

-- ----------------------------------------------------------------------------
-- 2. « quantite_attendue » : figée par la base au moment du comptage
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION figer_quantite_attendue()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    stock_courant INTEGER;
BEGIN
    SELECT quantite_stock INTO stock_courant
      FROM articles WHERE id = NEW.article_id;

    IF stock_courant IS NULL THEN
        RAISE EXCEPTION 'Comptage impossible : article % introuvable.', NEW.article_id
          USING ERRCODE = 'foreign_key_violation';
    END IF;

    -- La valeur éventuellement envoyée par le client est ignorée, sciemment.
    NEW.quantite_attendue := stock_courant;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION figer_quantite_attendue() IS
  'Renseigne comptages_stock.quantite_attendue à partir du stock réel au moment '
  'du comptage. Ignore toute valeur fournie par le client : sans cela, il '
  'suffisait d''envoyer attendue = comptée pour masquer un écart.';

DROP TRIGGER IF EXISTS trg_figer_quantite_attendue ON comptages_stock;
CREATE TRIGGER trg_figer_quantite_attendue
  BEFORE INSERT ON comptages_stock
  FOR EACH ROW EXECUTE FUNCTION figer_quantite_attendue();

-- ----------------------------------------------------------------------------
-- 3. Un comptage est un fait : non modifiable après enregistrement
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION interdire_modification_comptage()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.quantite_comptee  IS DISTINCT FROM OLD.quantite_comptee
    OR NEW.quantite_attendue IS DISTINCT FROM OLD.quantite_attendue
    OR NEW.article_id        IS DISTINCT FROM OLD.article_id
    OR NEW.moment            IS DISTINCT FROM OLD.moment
    OR NEW.date_comptage     IS DISTINCT FROM OLD.date_comptage THEN
        RAISE EXCEPTION
          'Un comptage d''inventaire ne se modifie pas. Enregistrez un nouveau comptage.'
          USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_interdire_modification_comptage ON comptages_stock;
CREATE TRIGGER trg_interdire_modification_comptage
  BEFORE UPDATE ON comptages_stock
  FOR EACH ROW EXECUTE FUNCTION interdire_modification_comptage();

-- ----------------------------------------------------------------------------
-- 4. Un seul comptage par article, par moment et par jour
--    (sinon : compter, voir l'écart, recompter « mieux », garder le bon)
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS uq_comptage_article_moment_jour;
CREATE UNIQUE INDEX uq_comptage_article_moment_jour
  ON comptages_stock (article_id, moment, (date_comptage::date));

COMMENT ON INDEX uq_comptage_article_moment_jour IS
  'Un seul comptage par article, par moment (matin/soir) et par jour : empêche '
  'de recompter jusqu''à obtenir un écart nul.';

INSERT INTO schema_migrations (version, nom)
VALUES ('003', 'ecart_inventaire_calcule')
ON CONFLICT (version) DO NOTHING;
