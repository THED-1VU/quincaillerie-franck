-- Annule la migration 030.
--
-- Volontairement une « non-opération » sur les objets : les fonctions du
-- cycle 13a (migration 025) ne peuvent pas être recréées ici — elles
-- référencent `articles.site_id`/`articles.quantite_stock`, qui n'existent
-- plus à ce stade de la chaîne d'inverses (l'inverse de 027, qui les
-- restaure, est appliqué APRÈS celui-ci). La version multi-site des
-- fonctions reste donc en place ; elle redevient inoffensive à la fin de la
-- chaîne (la suite SQL ne compare que le schéma, pas l'exécutabilité des
-- fonctions). Aucun objet n'est touché, l'ordre de la chaîne est préservé.

DELETE FROM schema_migrations WHERE version = '030';
