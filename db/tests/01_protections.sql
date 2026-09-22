-- ============================================================================
-- TESTS — les protections de la base fonctionnent-elles VRAIMENT ?
-- ----------------------------------------------------------------------------
-- Chaque test tente une écriture aberrante et vérifie que la base la REFUSE.
-- Un test qui « passe » signifie donc : la base a bien dit non.
--
-- Toutes les tentatives sont annulées (sous-transaction) : la base reste dans
-- l'état du jeu d'essai.
--
-- Usage : psql -d quincaillerie_test -f db/tests/01_protections.sql
-- ============================================================================
\set ON_ERROR_STOP on
\pset pager off

DROP TABLE IF EXISTS _tests_resultats;
CREATE TABLE _tests_resultats (
    ordre   SERIAL PRIMARY KEY,
    nom     TEXT NOT NULL,
    attendu TEXT NOT NULL,
    obtenu  TEXT NOT NULL,
    ok      BOOLEAN NOT NULL
);

-- Vérifie qu'une instruction est REFUSÉE par la base.
CREATE OR REPLACE FUNCTION t_refus(p_nom TEXT, p_sql TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE p_sql;
        RAISE EXCEPTION 'SENTINELLE_ACCEPTE';
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM = 'SENTINELLE_ACCEPTE' THEN
            INSERT INTO _tests_resultats (nom, attendu, obtenu, ok)
            VALUES (p_nom, 'refus', 'ACCEPTÉ — protection absente', FALSE);
        ELSE
            INSERT INTO _tests_resultats (nom, attendu, obtenu, ok)
            VALUES (p_nom, 'refus', 'refusé : ' || left(SQLERRM, 110), TRUE);
        END IF;
    END;
END $$;

-- Vérifie qu'une instruction est ACCEPTÉE.
CREATE OR REPLACE FUNCTION t_succes(p_nom TEXT, p_sql TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE p_sql;
        INSERT INTO _tests_resultats (nom, attendu, obtenu, ok)
        VALUES (p_nom, 'succès', 'accepté', TRUE);
    EXCEPTION WHEN OTHERS THEN
        INSERT INTO _tests_resultats (nom, attendu, obtenu, ok)
        VALUES (p_nom, 'succès', 'REFUSÉ : ' || left(SQLERRM, 110), FALSE);
    END;
END $$;

-- Vérifie une valeur attendue.
CREATE OR REPLACE FUNCTION t_valeur(p_nom TEXT, p_sql TEXT, p_attendu TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE v TEXT;
BEGIN
    BEGIN
        EXECUTE p_sql INTO v;
        INSERT INTO _tests_resultats (nom, attendu, obtenu, ok)
        VALUES (p_nom, p_attendu, COALESCE(v, '(null)'), COALESCE(v, '(null)') = p_attendu);
    EXCEPTION WHEN OTHERS THEN
        INSERT INTO _tests_resultats (nom, attendu, obtenu, ok)
        VALUES (p_nom, p_attendu, 'ERREUR : ' || left(SQLERRM, 110), FALSE);
    END;
END $$;

-- ============================================================================
-- 1. Contraintes de domaine (migration 001)
-- ============================================================================
SELECT t_refus('001 · stock négatif',
  $$UPDATE stocks_sites SET quantite_stock = -50 WHERE article_id = 1 AND site_id = 1$$);

SELECT t_refus('001 · prix de vente négatif',
  $$UPDATE articles SET prix_vente = -999 WHERE id = 1$$);

SELECT t_refus('001 · prix d''achat négatif',
  $$UPDATE articles SET prix_achat = -1 WHERE id = 1$$);

SELECT t_refus('001 · seuil d''alerte négatif',
  $$UPDATE stocks_sites SET seuil_alerte = -3 WHERE article_id = 1 AND site_id = 1$$);

SELECT t_refus('001 · mouvement de stock de quantité 0',
  $$INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
    VALUES (1, 1, 'entree', 'reception_fournisseur', 0, 'essai', 2)$$);

SELECT t_refus('001 · taux de TVA à 500 %',
  $$INSERT INTO ventes (site_id, utilisateur_id, sous_total_ht, taux_tva, montant_tva, total_ttc)
    VALUES (1, 4, 100, 500, 500, 600)$$);

SELECT t_refus('001 · total différent de sous-total + TVA',
  $$INSERT INTO ventes (site_id, utilisateur_id, sous_total_ht, taux_tva, montant_tva, total_ttc)
    VALUES (1, 4, 1, 0, 1, 999999)$$);

SELECT t_refus('001 · TVA non nulle alors que le taux est nul',
  $$INSERT INTO ventes (site_id, utilisateur_id, sous_total_ht, taux_tva, montant_tva, total_ttc)
    VALUES (1, 4, 100, 0, 19, 119)$$);

SELECT t_refus('001 · ticket portant un numéro de facture',
  $$INSERT INTO ventes (site_id, utilisateur_id, type_document, numero_facture,
                        sous_total_ht, taux_tva, montant_tva, total_ttc)
    VALUES (1, 4, 'ticket', '2026-0001', 100, 0, 0, 100)$$);

SELECT t_refus('001 · facture sans numéro',
  $$INSERT INTO ventes (site_id, utilisateur_id, type_document,
                        sous_total_ht, taux_tva, montant_tva, total_ttc)
    VALUES (1, 4, 'facture', 100, 0, 0, 100)$$);

SELECT t_refus('001 · vente payée sans caissier ni date d''encaissement',
  $$INSERT INTO ventes (site_id, utilisateur_id, statut,
                        sous_total_ht, taux_tva, montant_tva, total_ttc)
    VALUES (1, 4, 'payee', 100, 0, 0, 100)$$);

SELECT t_refus('001 · agent de stock sans site',
  $$INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id)
    VALUES ('Orphelin', 'agent.orphelin', 'x', 'agent_stock', NULL)$$);

SELECT t_refus('001 · responsable rattaché à un seul site',
  $$INSERT INTO utilisateurs (nom_complet, identifiant, mot_de_passe_hash, role, site_id)
    VALUES ('Resp bis', 'resp.bis', 'x', 'responsable', 1)$$);

SELECT t_refus('001 · congé se terminant avant de commencer',
  $$INSERT INTO absences_conges (employe_id, type, date_debut, date_fin, utilisateur_id)
    VALUES (1, 'conge', '2026-12-31', '2026-01-01', 1)$$);

SELECT t_refus('001 · transaction de montant nul',
  $$INSERT INTO transactions (site_id, utilisateur_id, type, montant, description)
    VALUES (1, 4, 'recette', 0, 'essai')$$);

SELECT t_refus('001 · ligne de vente de quantité négative',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id)
    VALUES (1, 1, -5, 6500, 1)$$);

-- ============================================================================
-- 2. Écart d'inventaire calculé par la base (migration 003) — LE POINT CLÉ
-- ============================================================================
SELECT t_refus('003 · écriture directe de l''écart d''inventaire',
  $$INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment,
                                 quantite_attendue, quantite_comptee, ecart)
    VALUES (1, 1, 2, 'matin', 30, 25, 0)$$);

-- Le client ment sur la quantité attendue (999 au lieu de 30, stock réel).
-- La base doit l'ignorer et calculer l'écart réel : 25 - 30 = -5.
INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment, quantite_attendue, quantite_comptee)
VALUES (1, 1, 2, 'matin', 999, 25);

-- '30.000'/'-5.000', pas '30'/'-5' : quantite_attendue/ecart sont NUMERIC(12,3)
-- depuis la migration 034 (point f, unités décimales) — même valeur,
-- représentation textuelle différente.
SELECT t_valeur('003 · quantité attendue forgée par le client → ignorée',
  $$SELECT quantite_attendue::TEXT FROM comptages_stock WHERE article_id = 1 AND moment = 'matin'$$,
  '30.000');

SELECT t_valeur('003 · écart réellement calculé par la base',
  $$SELECT ecart::TEXT FROM comptages_stock WHERE article_id = 1 AND moment = 'matin'$$,
  '-5.000');

SELECT t_refus('003 · modification d''un comptage déjà enregistré',
  $$UPDATE comptages_stock SET quantite_comptee = 30 WHERE article_id = 1 AND moment = 'matin'$$);

SELECT t_refus('003 · deuxième comptage même article / site / moment / jour',
  $$INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment, quantite_attendue, quantite_comptee)
    VALUES (1, 1, 2, 'matin', 30, 30)$$);

SELECT t_succes('003 · même article, même moment, autre SITE accepté (multi-site)',
  $$INSERT INTO stocks_sites (article_id, site_id, quantite_stock, seuil_alerte) VALUES (1, 2, 0, 0);
    INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment, quantite_attendue, quantite_comptee)
    VALUES (1, 2, 2, 'matin', 0, 0)$$);

SELECT t_succes('003 · comptage du soir accepté (moment différent)',
  $$INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment, quantite_attendue, quantite_comptee)
    VALUES (1, 1, 2, 'soir', 0, 30)$$);

-- ============================================================================
-- 3. Historique non effaçable (migration 004)
-- ============================================================================
INSERT INTO historique_prix_articles
  (article_id, utilisateur_id, ancien_prix_achat, nouveau_prix_achat, ancien_prix_vente, nouveau_prix_vente)
VALUES (2, 1, 2800, 2900, 3500, 3600);

SELECT t_refus('004 · suppression d''un article ayant un historique de prix',
  $$DELETE FROM articles WHERE id = 2$$);

SELECT t_refus('004 · suppression d''une ligne d''historique de prix',
  $$DELETE FROM historique_prix_articles WHERE article_id = 2$$);

-- NB : la ligne est insérée par une instruction SÉPARÉE. Avec une CTE
-- modifiante (WITH m AS (INSERT ...) DELETE ...), le DELETE ne verrait pas la
-- ligne insérée dans la même instruction : il supprimerait 0 ligne et le
-- déclencheur ne se déclencherait jamais — le test passerait à tort.
INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id)
VALUES (1, 1, 'entree', 'reception_fournisseur', 5, 'essai suppression', 2);

SELECT t_refus('004 · suppression d''un mouvement de stock',
  $$DELETE FROM mouvements_stock WHERE motif = 'essai suppression'$$);

SELECT t_refus('004 · suppression d''un comptage d''inventaire',
  $$DELETE FROM comptages_stock WHERE article_id = 1$$);

SELECT t_refus('004 · désactivation d''article sans auteur ni date',
  $$UPDATE articles SET actif = FALSE WHERE id = 3$$);

SELECT t_succes('004 · désactivation d''article tracée (auteur + date)',
  $$UPDATE articles SET actif = FALSE, date_desactivation = NOW(), desactive_par_id = 1
     WHERE id = 3$$);

-- ============================================================================
-- 4. Cohérence entre tables (migration 002)
-- ============================================================================
INSERT INTO ventes (id, site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc,
                    utilisateur_caisse_id, mode_paiement, date_encaissement)
VALUES (900, 1, 4, 'payee', 6500, 0, 0, 6500, 1, 'especes', NOW());

SELECT t_refus('002 · vente du Magasin contenant un article du Comptoir',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id)
    VALUES (900, 3, 1, 800, 1)$$);

SELECT t_succes('002 · ligne de vente du bon site acceptée',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id)
    VALUES (900, 1, 1, 6500, 1)$$);

INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
VALUES (1, 4, 'recette', 6500, 'Vente 900', 900);

SELECT t_refus('002 · deuxième recette pour la même vente (double comptage)',
  $$INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
    VALUES (1, 4, 'recette', 6500, 'Doublon', 900)$$);

SELECT t_refus('002 · transaction rattachée à une vente d''un autre site',
  $$INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
    VALUES (2, 4, 'depense', 100, 'Site incohérent', 900)$$);

-- ============================================================================
-- 5. Cycle de vie d'une vente (migration 005)
-- ============================================================================
SELECT t_refus('005 · annulation sans auteur',
  $$UPDATE ventes SET statut = 'annulee' WHERE id = 900$$);

SELECT t_refus('005 · retour en arrière d''une vente payée',
  $$UPDATE ventes SET statut = 'en_attente' WHERE id = 900$$);

SELECT t_succes('005 · annulation tracée par le responsable',
  $$UPDATE ventes SET statut = 'annulee', annulee_par_id = 1,
                      date_annulation = NOW(), motif_annulation = 'Erreur de saisie'
     WHERE id = 900$$);

SELECT t_refus('005 · seconde annulation de la même vente',
  $$UPDATE ventes SET statut = 'annulee', annulee_par_id = 1, date_annulation = NOW()
     WHERE id = 900$$);

SELECT t_refus('005 · suppression d''une vente',
  $$DELETE FROM ventes WHERE id = 900$$);

SELECT t_refus('005 · suppression d''une ligne de vente déjà annulée',
  $$DELETE FROM ventes_lignes WHERE vente_id = 900$$);

-- La date d'annulation est posée par la base : une antidate est écrasée.
SELECT t_valeur('005 · date d''annulation non antidatable',
  $$SELECT (date_annulation > NOW() - INTERVAL '1 minute')::TEXT FROM ventes WHERE id = 900$$,
  'true');

-- ============================================================================
-- 6. Paramètres applicatifs (migration 006)
-- ============================================================================
-- Le régime fiscal et le taux de TVA (points d) sont désormais TRANCHÉS
-- (cycle 6, migration 011) : ils ne sont plus des exemples valables de
-- paramètre « a_definir ». La durée de session, elle, l'est toujours — voir
-- ADDENDUM_CAHIER_DES_CHARGES.md, point k / dossier de recette §6.
SELECT t_refus('006 · lecture d''un paramètre non tranché (téléphone boutique)',
  $$SELECT parametre_texte('boutique_telephone')$$);

SELECT t_valeur('006 · taux de TVA lisible (régime du réel, décidé cycle 6)',
  $$SELECT parametre_numerique('taux_tva')::TEXT$$, '19.25');

SELECT t_valeur('006 · pourcentage du seuil d''alerte = 20 (cahier des charges)',
  $$SELECT parametre_numerique('seuil_alerte_pourcentage')::TEXT$$, '20');

SELECT t_refus('006 · modification d''un paramètre verrouillé (devise)',
  $$UPDATE parametres SET valeur = 'EUR' WHERE cle = 'devise'$$);

UPDATE parametres SET valeur = '20', utilisateur_id = 1 WHERE cle = 'taux_tva';
SELECT t_valeur('006 · changement de taux de TVA tracé dans l''historique',
  $$SELECT ancienne_valeur || ' -> ' || nouvelle_valeur FROM historique_parametres
     WHERE cle = 'taux_tva' ORDER BY id DESC LIMIT 1$$,
  '19.25 -> 20');
UPDATE parametres SET valeur = '19.25' WHERE cle = 'taux_tva';

-- ============================================================================
-- 7. Régularisation d'un écart de comptage (migration 032, cycle 36)
-- ============================================================================
-- Le comptage « matin » de l'article 1 (section 2) porte un écart réel (-5).
SELECT t_succes('032 · régularisation erreur_de_comptage tracée',
  $$SELECT regulariser_ecart_comptage(
      (SELECT id FROM comptages_stock WHERE article_id = 1 AND moment = 'matin' LIMIT 1),
      'erreur_de_comptage', 1)$$);

SELECT t_refus('032 · re-régularisation du même comptage refusée',
  $$SELECT regulariser_ecart_comptage(
      (SELECT id FROM comptages_stock WHERE article_id = 1 AND moment = 'matin' LIMIT 1),
      'retrouve', 1, 'retrouvé en réserve')$$);

INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment, quantite_comptee)
VALUES (2, 1, 2, 'matin', 1);  -- attendu 40 -> écart -39

SELECT t_refus('032 · vol présumé sans motif refusé',
  $$SELECT regulariser_ecart_comptage(
      (SELECT id FROM comptages_stock WHERE article_id = 2 AND moment = 'matin' LIMIT 1),
      'vol_presume', 1)$$);

SELECT t_refus('032 · type de résolution invalide refusé',
  $$SELECT regulariser_ecart_comptage(
      (SELECT id FROM comptages_stock WHERE article_id = 2 AND moment = 'matin' LIMIT 1),
      'nimporte_quoi', 1)$$);

-- ============================================================================
-- 8. Réinitialisation de mot de passe (migration 033, cycle 38)
-- ============================================================================
SELECT t_refus('033 · mot de passe trop court refusé',
  $$SELECT reinitialiser_mot_de_passe_agent(2, 'court', 1)$$);

SELECT t_refus('033 · réinitialisation d''un compte responsable refusée',
  $$SELECT reinitialiser_mot_de_passe_agent(1, 'UnMotDePasseLong', 1)$$);

SELECT t_succes('033 · réinitialisation d''un agent acceptée',
  $$SELECT reinitialiser_mot_de_passe_agent(2, 'UnMotDePasseLong', 1)$$);

-- ============================================================================
-- 9. Quantités décimales par article (migration 034, point f, addendum,
--    décision 2026-09-22) — refusées par défaut, autorisées si l'article
--    le permet.
-- ============================================================================

-- Article 1 (Ciment) : quantite_decimale_autorisee = FALSE par défaut (jeu
-- d'essai). Une entrée décimale doit être refusée AU NIVEAU DE LA BASE,
-- pas seulement par discipline applicative — même principe que le reste
-- du projet (contourner l'API ne doit rien changer).
SELECT t_refus('034 · entrée de stock décimale sur un article entier-seul',
  $$SELECT enregistrer_entree_stock(1, 1, 12.5, 2, 'essai décimal refusé')$$);

SELECT t_refus('034 · casse décimale sur un article entier-seul',
  $$SELECT enregistrer_casse(1, 1, 2.5, 2, 'essai décimal refusé')$$);

SELECT t_refus('034 · comptage décimal sur un article entier-seul',
  $$INSERT INTO comptages_stock (article_id, utilisateur_id, moment, quantite_comptee, site_id)
    VALUES (1, 2, 'soir', 29.5, 1)$$);

-- Autoriser explicitement les décimales sur l'article 1, le temps du test
-- suivant seulement (restauré juste après, jeu d'essai inchangé pour le
-- reste de la suite).
UPDATE articles SET quantite_decimale_autorisee = TRUE WHERE id = 1;

SELECT t_succes('034 · entrée de stock décimale acceptée si l''article l''autorise',
  $$SELECT enregistrer_entree_stock(1, 1, 12.5, 2, 'essai décimal accepté')$$);

SELECT t_valeur('034 · la quantité décimale est bien celle enregistrée, non arrondie',
  $$SELECT quantite_stock::TEXT FROM stocks_sites WHERE article_id = 1 AND site_id = 1$$,
  '42.500');

UPDATE articles SET quantite_decimale_autorisee = FALSE WHERE id = 1;

-- ============================================================================
-- Résultat
-- ============================================================================
\echo ''
\echo '=============================== RÉSULTATS ==============================='
SELECT ordre,
       CASE WHEN ok THEN '[ok]   ' ELSE '[ÉCHEC]' END AS statut,
       nom,
       obtenu
  FROM _tests_resultats ORDER BY ordre;

\echo ''
SELECT count(*) FILTER (WHERE ok)       AS reussis,
       count(*) FILTER (WHERE NOT ok)   AS echecs,
       count(*)                         AS total
  FROM _tests_resultats;

-- Sortie en erreur si un seul test a échoué : le script d'exécution le voit.
DO $$
DECLARE n INTEGER;
BEGIN
    SELECT count(*) INTO n FROM _tests_resultats WHERE NOT ok;
    IF n > 0 THEN
        RAISE EXCEPTION '% test(s) en échec sur les protections de la base.', n;
    END IF;
END $$;
