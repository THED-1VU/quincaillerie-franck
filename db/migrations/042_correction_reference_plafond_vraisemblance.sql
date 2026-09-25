-- ============================================================================
-- 042 — Correction de référence (2026-09-25) : le plafond 10 000 posé au
-- cycle 51 est une VALEUR PAR DÉFAUT posée par l'équipe de développement,
-- EN ATTENTE DE CONFIRMATION du propriétaire — pas une décision du
-- propriétaire. La valeur n'est PAS modifiée ; seule la référence est
-- corrigée.
-- ============================================================================

UPDATE parametres
   SET reference_decision = 'Défaut équipe de développement (2026-09-25), à confirmer par le propriétaire'
 WHERE cle = 'plafond_vraisemblance_comptage';

INSERT INTO schema_migrations (version, nom)
VALUES ('042', 'correction_reference_plafond_vraisemblance')
ON CONFLICT (version) DO NOTHING;
