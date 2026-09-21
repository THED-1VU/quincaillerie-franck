-- Annule la migration 031 : restaure annuler_vente() sur l'ancien modèle
-- (articles.quantite_stock). Comme pour 030, cette restauration n'est
-- exécutable qu'après l'inverse de 027 (qui recrée les colonnes d'articles) ;
-- pour préserver la chaîne, on ne touche ici à rien d'autre que la ligne de
-- version — la fonction multi-site reste en place et devient inoffensive en
-- fin de chaîne.

DELETE FROM schema_migrations WHERE version = '031';
