-- ============================================================================
-- 012 — Comptage à l'aveugle : restreindre par COLONNE, pas seulement par
--        convention applicative (chantier C7)
-- ----------------------------------------------------------------------------
-- Diagnostic du cycle 7, prouvé par exécution AVANT d'écrire une route :
--   SET ROLE qf_agent_stock; SELECT ecart, quantite_attendue FROM comptages_stock;
--   -> ACCEPTÉ (0 ligne, table vide, mais la requête n'est PAS refusée).
--
-- La migration 008 accordait un SELECT SANS restriction de colonne sur
-- comptages_stock à qf_agent_stock. La quantité attendue et l'écart étaient
-- donc lisibles en SQL direct, même si aucune route applicative ne les
-- exposait — exactement le même type de faille que celle déjà corrigée pour
-- articles.prix_vente (invisible pour qf_agent_stock depuis le cycle 2).
-- Comme pour les prix, la vraie protection doit être dans la base, pas dans
-- une route qui choisit « par convention » de ne pas lire ces colonnes.
--
-- Cycle 7 — chantier C7. Idempotent.
-- ============================================================================

REVOKE SELECT ON comptages_stock FROM qf_agent_stock;

-- Colonnes visibles pour l'agent stock : tout, SAUF quantite_attendue et
-- ecart — exactement ce qu'un comptage à l'aveugle doit lui cacher, y
-- compris après coup (le fait de voir un écart passé ne l'aide pas à
-- tricher sur CE comptage-là, déjà figé, mais reste hors du principe énoncé
-- au cycle 5 : « la quantité attendue n'est jamais envoyée »).
GRANT SELECT (id, article_id, utilisateur_id, moment, quantite_comptee, date_comptage)
  ON comptages_stock TO qf_agent_stock;

-- L'INSERT restait déjà sûr sans restriction de colonne :
--   * "ecart" est une colonne GENERATED ALWAYS (migration 003) — PostgreSQL
--     refuse par construction toute tentative d'y écrire une valeur ;
--   * "quantite_attendue" est écrasée par le déclencheur
--     figer_quantite_attendue() (migration 003), quelle que soit la valeur
--     envoyée par le client.
-- Rien à changer sur INSERT.

INSERT INTO schema_migrations (version, nom)
VALUES ('012', 'comptage_aveugle_colonnes')
ON CONFLICT (version) DO NOTHING;
