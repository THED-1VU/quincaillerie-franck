-- ============================================================================
-- PRÉ-VOL — à exécuter AVANT d'appliquer les migrations sur une base contenant
-- de vraies données.
-- ----------------------------------------------------------------------------
-- Les migrations 001 et 002 ajoutent des contraintes. Sur une base qui contient
-- déjà des lignes en infraction, l'ajout ÉCHOUE (c'est voulu : mieux vaut un
-- échec franc qu'une contrainte silencieusement absente).
--
-- Ce script ne modifie rien. Il liste les lignes qui bloqueraient, pour qu'on
-- décide quoi en faire AVANT de migrer.
--
-- Usage :
--   psql -d quincaillerie -f db/outils/prevol.sql
--
-- Lecture du résultat : toute ligne avec nb_lignes > 0 doit être traitée.
-- ============================================================================
\pset pager off

SELECT 'articles : stock négatif'                AS controle, count(*) AS nb_lignes FROM articles          WHERE quantite_stock < 0
UNION ALL SELECT 'articles : prix d''achat négatif',        count(*) FROM articles          WHERE prix_achat < 0
UNION ALL SELECT 'articles : prix de vente négatif',        count(*) FROM articles          WHERE prix_vente < 0
UNION ALL SELECT 'articles : seuil d''alerte négatif',      count(*) FROM articles          WHERE seuil_alerte < 0
UNION ALL SELECT 'articles : nom ou unité vide',            count(*) FROM articles          WHERE length(btrim(nom)) = 0 OR length(btrim(unite)) = 0
UNION ALL SELECT 'utilisateurs : rôle et site incohérents', count(*) FROM utilisateurs
          WHERE NOT ((role = 'responsable' AND site_id IS NULL) OR (role <> 'responsable' AND site_id IS NOT NULL))
UNION ALL SELECT 'utilisateurs : tentatives négatives',     count(*) FROM utilisateurs      WHERE tentatives_echouees < 0
UNION ALL SELECT 'mouvements_stock : quantité <= 0',        count(*) FROM mouvements_stock  WHERE quantite <= 0
UNION ALL SELECT 'ventes : montant négatif',                count(*) FROM ventes            WHERE sous_total_ht < 0 OR montant_tva < 0 OR total_ttc < 0
UNION ALL SELECT 'ventes : taux de TVA hors [0,100]',       count(*) FROM ventes            WHERE taux_tva < 0 OR taux_tva > 100
UNION ALL SELECT 'ventes : total <> sous-total + TVA',      count(*) FROM ventes            WHERE total_ttc <> sous_total_ht + montant_tva
UNION ALL SELECT 'ventes : TVA non nulle à taux nul',       count(*) FROM ventes            WHERE taux_tva = 0 AND montant_tva <> 0
UNION ALL SELECT 'ventes : numéro de facture incohérent',   count(*) FROM ventes
          WHERE NOT ((type_document = 'facture' AND numero_facture IS NOT NULL)
                  OR (type_document = 'ticket'  AND numero_facture IS NULL))
UNION ALL SELECT 'ventes : payée sans caisse/date/mode',    count(*) FROM ventes
          WHERE statut = 'payee' AND (date_encaissement IS NULL OR mode_paiement IS NULL OR utilisateur_caisse_id IS NULL)
UNION ALL SELECT 'ventes : annulée non tracée',             count(*) FROM ventes            WHERE statut = 'annulee'
UNION ALL SELECT 'ventes_lignes : quantité <= 0',           count(*) FROM ventes_lignes     WHERE quantite <= 0
UNION ALL SELECT 'ventes_lignes : prix unitaire négatif',   count(*) FROM ventes_lignes     WHERE prix_unitaire < 0
UNION ALL SELECT 'ventes_lignes : article d''un autre site', count(*) FROM ventes_lignes vl
          JOIN ventes v ON v.id = vl.vente_id JOIN articles a ON a.id = vl.article_id
          WHERE a.site_id <> v.site_id
UNION ALL SELECT 'transactions : montant <= 0',             count(*) FROM transactions      WHERE montant <= 0
UNION ALL SELECT 'transactions : plusieurs recettes pour une vente',
          COALESCE((SELECT count(*) FROM (SELECT vente_id FROM transactions
                    WHERE vente_id IS NOT NULL AND type = 'recette'
                    GROUP BY vente_id HAVING count(*) > 1) d), 0)
UNION ALL SELECT 'transactions : site différent de celui de la vente', count(*) FROM transactions t
          JOIN ventes v ON v.id = t.vente_id WHERE t.site_id <> v.site_id
UNION ALL SELECT 'employes : salaire négatif',              count(*) FROM employes          WHERE salaire_mensuel < 0
UNION ALL SELECT 'absences_conges : fin avant début',       count(*) FROM absences_conges   WHERE date_fin < date_debut
UNION ALL SELECT 'avances_salaire : montant <= 0',          count(*) FROM avances_salaire   WHERE montant <= 0
UNION ALL SELECT 'comptages_stock : quantité négative',     count(*) FROM comptages_stock   WHERE quantite_attendue < 0 OR quantite_comptee < 0
UNION ALL SELECT 'comptages_stock : ÉCART DÉCLARÉ FAUX',    count(*) FROM comptages_stock   WHERE ecart IS DISTINCT FROM (quantite_comptee - quantite_attendue)
UNION ALL SELECT 'comptages_stock : doublon article/moment/jour',
          COALESCE((SELECT count(*) FROM (SELECT article_id FROM comptages_stock
                    GROUP BY article_id, moment, date_comptage::date HAVING count(*) > 1) d), 0)
ORDER BY nb_lignes DESC, controle;

\echo ''
\echo 'Toute ligne avec nb_lignes > 0 doit être traitée AVANT la migration.'
\echo 'Cas particulier « ÉCART DÉCLARÉ FAUX » : la migration 003 ne bloque pas,'
\echo 'elle archive ces lignes dans comptages_stock_ecarts_declares puis recalcule.'
\echo 'Cas particulier « annulée non tracée » : renseigner annulee_par_id avant 005.'
