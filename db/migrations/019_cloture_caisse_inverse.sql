-- Annule la migration 019.

DROP TRIGGER  IF EXISTS trg_journal_non_supprimable  ON clotures_caisse;
DROP TRIGGER  IF EXISTS trg_cloture_caisse_figee     ON clotures_caisse;
DROP FUNCTION IF EXISTS cloturer_caisse(INTEGER, DATE, NUMERIC, INTEGER, NUMERIC, NUMERIC, NUMERIC, VARCHAR, INTEGER);
DROP FUNCTION IF EXISTS calculer_attendu_caisse(INTEGER, DATE);
DROP FUNCTION IF EXISTS interdire_modification_cloture_caisse();
DROP TABLE    IF EXISTS clotures_caisse;

DELETE FROM parametres WHERE cle = 'seuil_ecart_caisse_tolere';

DELETE FROM schema_migrations WHERE version = '019';
