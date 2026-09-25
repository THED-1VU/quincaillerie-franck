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

-- Depuis la migration 036 (retours enrichis), enregistrer_casse() n'existe
-- plus : la déclaration (declarer_casse) n'écrit jamais dans stocks_sites/
-- mouvements_stock, donc le déclencheur décimal ne s'y applique pas — SEULE
-- la validation (valider_casse) doit être refusée.
SELECT t_succes('034 · déclaration de casse décimale acceptée (aucun effet sur le stock)',
  $$SELECT declarer_casse(1, 1, 2.5, 'essai décimal refusé', 2)$$);
SELECT t_refus('034 · validation de cette casse décimale refusée sur un article entier-seul',
  $$SELECT valider_casse(
      (SELECT id FROM declarations_casse WHERE article_id = 1 AND quantite = 2.5 LIMIT 1), 1)$$);

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
-- Restaure aussi le STOCK ET LE SEUIL (pas seulement l'indicateur) : la
-- réception décimale ci-dessus a aussi recalculé seuil_alerte à 2,5
-- (20 % de 12,5) — le laisser fractionnaire avec l'indicateur remis à
-- FALSE aurait refusé la PROCHAINE écriture sur cette ligne, quelle
-- qu'elle soit (le déclencheur vérifie TOUTE la ligne, pas seulement la
-- colonne visée) — trouvé par exécution en écrivant la section 10.
UPDATE stocks_sites SET quantite_stock = 30, seuil_alerte = 6
 WHERE article_id = 1 AND site_id = 1;

-- ============================================================================
-- 10. Retours enrichis : casse et retour client en deux temps (migration
--     036, point f, décision 2026-09-22).
-- ============================================================================

-- --- Casse : déclaration (aucun effet) -> validation (décrémente) --------
SELECT t_refus('036 · déclaration de casse sans motif refusée',
  $$SELECT declarer_casse(1, 1, 1, '', 2)$$);

SELECT t_succes('036 · déclaration de casse acceptée (constat, sans effet sur le stock)',
  $$SELECT declarer_casse(1, 1, 2, 'test protections', 2)$$);

SELECT t_valeur('036 · déclaration de casse : aucun effet sur le stock tant que non validée',
  $$SELECT quantite_stock::TEXT FROM stocks_sites WHERE article_id = 1 AND site_id = 1$$,
  '30.000');

SELECT t_succes('036 · validation de casse décrémente réellement le stock',
  $$SELECT valider_casse((SELECT id FROM declarations_casse WHERE motif = 'test protections' LIMIT 1), 1)$$);

SELECT t_valeur('036 · stock réellement décrémenté après validation',
  $$SELECT quantite_stock::TEXT FROM stocks_sites WHERE article_id = 1 AND site_id = 1$$,
  '28.000');

SELECT t_refus('036 · re-validation d''une casse déjà validée refusée',
  $$SELECT valider_casse((SELECT id FROM declarations_casse WHERE motif = 'test protections' LIMIT 1), 1)$$);

-- --- Retour client : déclaration -> validation, issue, état de la --------
-- --- marchandise (réutilise la vente 900 de la section 4, 1 unité de     --
-- --- l'article 1 vendue au Magasin) ---------------------------------------
SELECT t_succes('036 · déclaration de retour client acceptée (aucun effet tant que non validée)',
  $$SELECT declarer_retour_client(1, 900, 1, 'remboursement_especes', 'revendable', 2, 'test protections')$$);

SELECT t_valeur('036 · déclaration de retour client : aucun effet sur le stock tant que non validée',
  $$SELECT quantite_stock::TEXT FROM stocks_sites WHERE article_id = 1 AND site_id = 1$$,
  '28.000');

SELECT t_refus('036 · validation d''un remboursement espèces SANS confirmation refusée',
  $$SELECT valider_retour_client(
      (SELECT id FROM declarations_retour_client WHERE motif = 'test protections' LIMIT 1), 1, FALSE)$$);

SELECT t_succes('036 · validation d''un remboursement espèces AVEC confirmation acceptée',
  $$SELECT valider_retour_client(
      (SELECT id FROM declarations_retour_client WHERE motif = 'test protections' LIMIT 1), 1, TRUE)$$);

SELECT t_valeur('036 · stock réellement réintégré après validation (revendable)',
  $$SELECT quantite_stock::TEXT FROM stocks_sites WHERE article_id = 1 AND site_id = 1$$,
  '29.000');

SELECT t_valeur('036 · remboursement espèces trace une dépense du bon montant',
  $$SELECT montant::TEXT FROM transactions WHERE vente_id = 900 AND type = 'depense'$$,
  '6500.00');

-- Le retour ci-dessus a épuisé le 1 unité vendue dans la vente 900 : tout
-- nouveau retour sur cette vente doit être refusé (dépassement du vendu).
SELECT t_refus('036 · retour au-delà de la quantité vendue refusé',
  $$SELECT declarer_retour_client(1, 900, 1, 'echange', 'revendable', 2, 'en trop')$$);

-- ============================================================================
-- 11. Remises (migration 037, point f, décision 2026-09-22/23) — cohérence
--     catalogue/remise/prix payé vérifiée par la base, remise à 100 %
--     refusée (réservée au sous-chantier 4, article offert), tolérance
--     legacy (prix_catalogue NULL) préservée.
--     (réutilise la vente 900 de la section 4, article 1 : catalogue 6 500.)
-- ============================================================================

-- Remise cohérente (6500 - 500 = 6000) acceptée.
SELECT t_succes('037 · ligne de vente avec remise cohérente acceptée',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id, prix_catalogue, remise_montant)
    VALUES (900, 1, 1, 6000, 1, 6500, 500)$$);

-- Remise incohérente (le montant déclaré ne correspond pas à
-- catalogue - payé) refusée : la base ne fait pas confiance à une
-- remise_montant fournie sans vérifier son calcul.
SELECT t_refus('037 · ligne de vente avec remise incohérente refusée',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id, prix_catalogue, remise_montant)
    VALUES (900, 1, 1, 6000, 1, 6500, 999)$$);

-- Remise à 100 % (prix payé nul) refusée ICI : décision 2026-09-23, c'est
-- le mécanisme dédié à l'article offert (sous-chantier 4) qui la couvre.
SELECT t_refus('037 · ligne de vente à prix payé nul (remise 100 %) refusée',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id, prix_catalogue, remise_montant)
    VALUES (900, 1, 1, 0, 1, 6500, 6500)$$);

-- Prix négocié AU-DESSUS du catalogue (upsell) : remise_montant doit être 0,
-- jamais une valeur négative forcée par l'équation — GREATEST(...,0),
-- pas une égalité stricte.
SELECT t_succes('037 · prix payé au-dessus du catalogue (upsell) accepté sans remise',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id, prix_catalogue, remise_montant)
    VALUES (900, 1, 1, 7000, 1, 6500, 0)$$);

-- remise_montant négatif refusé quel que soit le catalogue.
SELECT t_refus('037 · remise_montant négatif refusé',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id, prix_catalogue, remise_montant)
    VALUES (900, 1, 1, 6500, 1, 6500, -1)$$);

-- Ligne sans prix_catalogue (legacy, antérieure au cycle 42, ou écrite hors
-- de la route applicative) : NULL toléré, aucune cohérence exigée avec
-- remise_montant — jamais rétro-inventé.
SELECT t_succes('037 · ligne sans prix_catalogue (legacy) tolérée',
  $$INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id)
    VALUES (900, 1, 1, 6500, 1)$$);

-- Remise globale (vente entière) : positive acceptée, négative refusée.
SELECT t_succes('037 · remise globale positive sur la vente acceptée',
  $$UPDATE ventes SET remise_globale_montant = 1000 WHERE id = 900$$);

SELECT t_refus('037 · remise globale négative refusée',
  $$UPDATE ventes SET remise_globale_montant = -1 WHERE id = 900$$);

UPDATE ventes SET remise_globale_montant = 0 WHERE id = 900;

-- ============================================================================
-- 10. Cumul de rôles (migration 035, chantier C3, décision 2026-09-22)
-- ============================================================================
SELECT t_succes('035 · la reprise initialise un rôle au minimum',
  $$SELECT count(*) FROM utilisateurs_roles WHERE utilisateur_id = 1$$);

SELECT t_refus('035 · rôle inconnu refusé par la table de cumul',
  $$INSERT INTO utilisateurs_roles (utilisateur_id, role) VALUES (1, 'caissier')$$);

SELECT t_refus('035 · cumul pour un utilisateur inexistant refusé',
  $$INSERT INTO utilisateurs_roles (utilisateur_id, role) VALUES (999999, 'agent_stock')$$);

SELECT t_succes('035 · roles_utilisateur() restitue les rôles d''un compte',
  $$SELECT roles_utilisateur(2)$$);

-- ============================================================================
-- 11. Limiteur de débit PARTAGÉ (migration 038, chantier C11, cycle 44)
-- ============================================================================
SELECT t_succes('038 · première tentative autorisée',
  $$SELECT tentative_autorisee('test_038', 3, 60)$$);

SELECT t_succes('038 · deuxième tentative autorisée',
  $$SELECT tentative_autorisee('test_038', 3, 60)$$);

SELECT t_succes('038 · troisième tentative autorisée (seuil 3)',
  $$SELECT tentative_autorisee('test_038', 3, 60)$$);

SELECT t_valeur('038 · quatrième tentative refusée (compteur partagé)',
  $$SELECT tentative_autorisee('test_038', 3, 60)::TEXT$$,
  'false');

SELECT t_succes('038 · réinitialisation du compteur',
  $$SELECT reinitialiser_limitation('test_038')$$);

SELECT t_succes('038 · de nouveau autorisée après réinitialisation',
  $$SELECT tentative_autorisee('test_038', 3, 60)$$);

-- ============================================================================
-- 12. Article offert (migration 039, point f, décision 2026-09-22/24) —
--     déclaration -> validation (même schéma que la casse), employé
--     obligatoire (fiche RH, actif, même site), vente_id optionnel.
-- ============================================================================

-- Baseline capturée ICI (pas de valeur codée en dur) : les sections
-- précédentes (remises, cumul de rôles, limiteur de débit) ne touchent pas
-- stocks_sites, mais dépendre d'une valeur absolue aurait été fragile.
SELECT quantite_stock AS stock_avant_offert
  FROM stocks_sites WHERE article_id = 1 AND site_id = 1 \gset

-- Employé inactif refusé.
UPDATE employes SET actif = FALSE WHERE id = 1;
SELECT t_refus('039 · déclaration avec un employé inactif refusée',
  $$SELECT declarer_article_offert(1, 1, 1, 'test employé inactif', 1, 2)$$);
UPDATE employes SET actif = TRUE WHERE id = 1;

-- Employé d'un autre site refusé (article 3, stocké uniquement au
-- Comptoir/site 2 ; l'employé 1 du jeu d'essai est au Magasin/site 1).
SELECT t_refus('039 · déclaration avec un employé d''un autre site refusée',
  $$SELECT declarer_article_offert(3, 2, 1, 'test mauvais site', 1, 2)$$);

-- Quantité nulle ou négative refusée.
SELECT t_refus('039 · déclaration de quantité nulle refusée',
  $$SELECT declarer_article_offert(1, 1, 0, 'quantité nulle', 1, 2)$$);

-- Déclaration valide : AUCUN effet sur le stock tant que non validée.
SELECT t_succes('039 · déclaration acceptée (constat, sans effet sur le stock)',
  $$SELECT declarer_article_offert(1, 1, 2, 'test protections', 1, 2)$$);

SELECT t_valeur('039 · déclaration : aucun effet sur le stock tant que non validée',
  $$SELECT quantite_stock::TEXT FROM stocks_sites WHERE article_id = 1 AND site_id = 1$$,
  :'stock_avant_offert');

-- valeur_normale figée depuis articles.prix_vente (6500) × quantité (2).
SELECT t_valeur('039 · valeur_normale figée depuis le prix catalogue',
  $$SELECT valeur_normale::TEXT FROM declarations_article_offert WHERE motif = 'test protections' LIMIT 1$$,
  '13000.00');

-- Validation : décrémente réellement le stock.
SELECT t_succes('039 · validation décrémente réellement le stock',
  $$SELECT valider_article_offert((SELECT id FROM declarations_article_offert WHERE motif = 'test protections' LIMIT 1), 1)$$);

SELECT t_valeur('039 · mouvement de stock catégorisé article_offert',
  $$SELECT categorie FROM mouvements_stock
     WHERE id = (SELECT mouvement_id FROM declarations_article_offert WHERE motif = 'test protections' LIMIT 1)$$,
  'article_offert');

-- Re-validation d'une déclaration déjà validée refusée.
SELECT t_refus('039 · re-validation d''une déclaration déjà validée refusée',
  $$SELECT valider_article_offert((SELECT id FROM declarations_article_offert WHERE motif = 'test protections' LIMIT 1), 1)$$);

-- Rattachement optionnel à une vente réelle (vente 900, site 1) : accepté,
-- et le mouvement de stock résultant porte bien vente_id — contrainte
-- chk_mouvements_vente_id_coherent élargie par cette migration (trouvé par
-- exécution : la version initiale de 039, basée sur la migration 014,
-- refusait vente_id pour la catégorie article_offert).
SELECT t_succes('039 · déclaration rattachée à une vente réelle acceptée',
  $$SELECT declarer_article_offert(1, 1, 1, 'rattaché à une vente', 1, 2, 900)$$);

SELECT t_succes('039 · validation d''une déclaration rattachée à une vente acceptée',
  $$SELECT valider_article_offert((SELECT id FROM declarations_article_offert WHERE motif = 'rattaché à une vente' LIMIT 1), 1)$$);

SELECT t_valeur('039 · le mouvement de stock porte bien vente_id',
  $$SELECT vente_id::TEXT FROM mouvements_stock
     WHERE id = (SELECT mouvement_id FROM declarations_article_offert WHERE motif = 'rattaché à une vente' LIMIT 1)$$,
  '900');

-- Non-régression (migration 017, chantier C5) : catégorie 'annulation_vente'
-- toujours acceptée — une première version de cette migration avait
-- réécrit chk_mouvements_categorie depuis la migration 014 (qui ne
-- connaissait pas encore 'annulation_vente'), faisant régresser
-- test_annulation_vente_regularise_automatiquement_lecart ; corrigé avant
-- tout commit, reconfirmé ici au niveau SQL directement.
SELECT t_succes('039 · non-régression : catégorie annulation_vente toujours acceptée',
  $$INSERT INTO mouvements_stock (article_id, site_id, type, categorie, quantite, motif, utilisateur_id, vente_id)
    VALUES (1, 1, 'entree', 'annulation_vente', 1, 'test non-régression 039', 2, 900)$$);

-- Stock final attendu : baseline - 2 (déclaration validée) - 1 (rattachée à
-- la vente, validée) = baseline - 3. L'INSERT direct ci-dessus (non-
-- régression annulation_vente) ne touche PAS stocks_sites — seules les
-- fonctions SECURITY DEFINER (valider_article_offert...) le font, jamais
-- une écriture brute dans mouvements_stock.
SELECT t_valeur('039 · stock final cohérent avec les mouvements ci-dessus',
  $$SELECT quantite_stock::TEXT FROM stocks_sites WHERE article_id = 1 AND site_id = 1$$,
  (SELECT (:'stock_avant_offert'::NUMERIC - 3)::TEXT));

-- ============================================================================
-- 13. Vendeur = fiche employé, pas un compte utilisateur (migration 040,
--     addendum point c, question 3 tranchée le 2026-09-19, livrée le
--     2026-09-25). La règle « même site ou actif » est vérifiée côté
--     Python (server/app/routes/ventes.py, pas de fonction SECURITY
--     DEFINER pour l'enregistrement d'une vente) — seule la contrainte de
--     clé étrangère elle-même relève de ce niveau SQL direct.
-- ============================================================================

-- vendeur_id doit référencer un employé RÉEL — un identifiant inexistant
-- est refusé par la seule contrainte de clé étrangère, sans avoir besoin
-- de l'API.
SELECT t_refus('040 · vente avec un vendeur (employé) inexistant refusée',
  $$UPDATE ventes SET vendeur_id = 999999 WHERE id = 900$$);

-- Démontre le changement de sémantique lui-même : un ancien identifiant de
-- COMPTE utilisateur (ex. 4, agent comptabilité du jeu d'essai) n'est plus
-- un vendeur valide, puisque employes n'a que les id 1 et 2.
SELECT t_refus('040 · un identifiant de compte utilisateur nest plus un vendeur valide',
  $$UPDATE ventes SET vendeur_id = 4 WHERE id = 900$$);

-- Un employé réel (id 1, jeu d'essai) est accepté par la contrainte —
-- aucune vérification de site ici, elle est côté Python.
SELECT t_succes('040 · vente avec un vendeur (employé) réel acceptée',
  $$UPDATE ventes SET vendeur_id = 1 WHERE id = 900$$);

UPDATE ventes SET vendeur_id = NULL WHERE id = 900;

-- ============================================================================
-- 13. Plafond de vraisemblance DÉCIDÉ (migration 040, chantier C7,
--     décision 2026-09-25 : 10 000)
-- ============================================================================
SELECT t_valeur('040 · plafond fixé à 10 000',
  $$SELECT valeur FROM parametres WHERE cle = 'plafond_vraisemblance_comptage'$$,
  '10000');

SELECT t_valeur('040 · plafond actif (a_decider = false)',
  $$SELECT a_decider::TEXT FROM parametres WHERE cle = 'plafond_vraisemblance_comptage'$$,
  'false');

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
