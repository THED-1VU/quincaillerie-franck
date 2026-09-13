-- ============================================================================
-- 013 — Fuseau horaire de la base : Africa/Douala, explicite, jamais hérité
--        du système d'exploitation (cycle de correction après le cycle 7)
-- ----------------------------------------------------------------------------
-- Trouvé par exécution lors du contrôle de boucle après le cycle 7 :
--   SHOW TimeZone;  ->  Europe/Paris
-- alors que le poste serveur sera physiquement à Batouri, Cameroun
-- (Africa/Douala, UTC+1, jamais d'heure d'été). CURRENT_DATE et NOW() sont
-- utilisés pour :
--   * l'unicité d'un comptage « un par article, par moment, par JOUR »
--     (migration 003) ;
--   * les écrans « écarts DU JOUR » (chantier C7) et « ventes DU JOUR »
--     (chantier C5, GET /ventes/synthese-jour).
-- Un décalage de fuseau déplace silencieusement la frontière du jour
-- calendaire vue par la base par rapport à l'heure réelle de la boutique.
--
-- Fixé ici au niveau de LA BASE (pg_db_role_setting), pas du serveur
-- PostgreSQL ni du système d'exploitation : ce réglage suit la base quel
-- que soit le fuseau du système sur lequel PostgreSQL tourne, et quel que
-- soit son nom (dev : quincaillerie_test ; production : à définir) —
-- d'où le bloc dynamique plutôt qu'un nom de base écrit en dur.
--
-- Défense en profondeur, cycle de correction (voir server/app/database.py) :
-- le serveur applicatif fixe ÉGALEMENT le fuseau à chaque connexion
-- (SET LOCAL TIME ZONE), pour ne dépendre ni de ce réglage de base ni d'une
-- variable d'environnement oubliée sur le poste.
--
-- Cycle de correction (après cycle 7). Idempotent.
-- ============================================================================

DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I SET timezone TO %L', current_database(), 'Africa/Douala');
END
$$;

-- Prend effet pour les NOUVELLES connexions ; celle-ci (la session de la
-- migration elle-même) doit aussi l'adopter pour que la vérification qui
-- suit soit probante immédiatement.
SET timezone TO 'Africa/Douala';

-- Vérification immédiate, par exécution, pas par confiance dans l'ALTER.
DO $$
DECLARE
    fuseau_courant TEXT;
BEGIN
    SELECT current_setting('TimeZone') INTO fuseau_courant;
    IF fuseau_courant <> 'Africa/Douala' THEN
        RAISE EXCEPTION
          'Le fuseau horaire de la session courante est % après SET, pas Africa/Douala.',
          fuseau_courant;
    END IF;
END
$$;

INSERT INTO schema_migrations (version, nom)
VALUES ('013', 'fuseau_horaire_boutique')
ON CONFLICT (version) DO NOTHING;
