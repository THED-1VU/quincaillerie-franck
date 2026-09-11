-- ============================================================================
-- 000 — Socle de versionnement du schéma
-- ----------------------------------------------------------------------------
-- Crée la table qui trace les migrations appliquées. Toute évolution du schéma
-- passe désormais par un fichier numéroté de db/migrations/ ; plus jamais de
-- modification manuelle de la base en production.
--
-- Cycle 2 — chantier C1. Idempotent.
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version        VARCHAR(10)  PRIMARY KEY,
    nom            VARCHAR(120) NOT NULL,
    applique_le    TIMESTAMP    NOT NULL DEFAULT NOW(),
    applique_par   VARCHAR(100) NOT NULL DEFAULT CURRENT_USER
);

COMMENT ON TABLE schema_migrations IS
  'Migrations de schéma appliquées. Une ligne par fichier db/migrations/NNN_*.sql.';

INSERT INTO schema_migrations (version, nom)
VALUES ('000', 'socle_migrations')
ON CONFLICT (version) DO NOTHING;
