-- Annule la migration 048 : la vue du rapport disparaît et le paramètre
-- du seuil est supprimé (il n'existait pas avant ce cycle — jamais de
-- valeur sentinelle laissée derrière : la décision reste consignée dans
-- ADDENDUM_CAHIER_DES_CHARGES.md, pas dans la base).

DROP VIEW IF EXISTS ecarts_prix_vendeurs;

DELETE FROM parametres WHERE cle = 'seuil_ecart_prix_vendeur';

DELETE FROM schema_migrations WHERE version = '048';
