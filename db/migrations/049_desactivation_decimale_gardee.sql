-- ============================================================================
-- 049 — Garde-fou : refus de désactiver les quantités décimales d'un article
--        tant qu'un stock ou un seuil décimal existe déjà.
-- ----------------------------------------------------------------------------
-- Cycle 60 (C4, case décimale sur la fiche article) : le paramètre
-- articles.quantite_decimale_autorisee devient modifiable depuis l'écran
-- (il était déjà accepté par POST/PUT /articles depuis le cycle 39).
--
-- Risque trouvé en préparant ce câblage, prouvé par exécution : décocher la
-- case d'un article qui a déjà un stock décimal (ex. 2,5 kg) le rend
-- INFIRMEMENT mouvementable — le déclencheur verifier_decimale_stocks_sites
-- (migration 034) refuse toute mise à jour de stocks_sites qui laisserait une
-- quantité ou un seuil décimal, y compris une réception ENTIÈRE (2,5 + 1 =
-- 3,5). L'article resterait bloqué, sans que rien ne l'indique à l'écran.
--
-- La règle est donc technique, pas métier : on n'interdit PAS de repasser un
-- article aux quantités entières (utile pour corriger un paramétrage posé par
-- erreur), on l'interdit seulement quand des valeurs décimales RÉELLES
-- existent déjà. Corriger d'abord le stock (comptage entier) et le seuil
-- (réception à seuil entier), puis décocher.
--
-- Même principe que 034 : la garantie vit dans la base, pas seulement dans
-- l'écran — un client qui contourne PUT /articles est refusé de la même
-- façon. SECURITY DEFINER : qf_agent_stock ne voit que son site via la RLS
-- (migration 029), alors que le contrôle doit porter sur les deux sites.
-- ============================================================================

CREATE OR REPLACE FUNCTION refuser_desactivation_decimale()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF OLD.quantite_decimale_autorisee AND NOT NEW.quantite_decimale_autorisee THEN
        IF EXISTS (
            SELECT 1
              FROM stocks_sites
             WHERE article_id = NEW.id
               AND (quantite_stock <> trunc(quantite_stock)
                    OR seuil_alerte <> trunc(seuil_alerte))
        ) THEN
            RAISE EXCEPTION
              'Désactivation refusée : l''article % a déjà un stock ou un seuil décimal. Corrigez ces valeurs en entiers avant de repasser aux quantités entières.',
              NEW.id
              USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_refuser_desactivation_decimale ON articles;
CREATE TRIGGER trg_refuser_desactivation_decimale
  BEFORE UPDATE OF quantite_decimale_autorisee ON articles
  FOR EACH ROW EXECUTE FUNCTION refuser_desactivation_decimale();

INSERT INTO schema_migrations (version, nom)
VALUES ('049', 'desactivation_decimale_gardee')
ON CONFLICT (version) DO NOTHING;
