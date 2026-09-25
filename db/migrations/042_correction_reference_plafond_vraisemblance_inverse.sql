-- Annule la migration 042 : rétablit la référence posée au cycle 51.

UPDATE parametres
   SET reference_decision = 'Décision 2026-09-25 (cycle 51)'
 WHERE cle = 'plafond_vraisemblance_comptage';

DELETE FROM schema_migrations WHERE version = '042';
