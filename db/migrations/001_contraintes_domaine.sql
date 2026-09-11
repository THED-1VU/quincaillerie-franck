-- ============================================================================
-- 001 — Contraintes de domaine
-- ----------------------------------------------------------------------------
-- Le schéma d'origine accepte des valeurs aberrantes : stock négatif, prix
-- négatif, quantité vendue négative, TVA à 500 %, congé qui finit avant de
-- commencer, agent sans site. Prouvé par exécution au diagnostic du cycle 2.
-- Cette migration fait défendre ces règles PAR LA BASE, donc quel que soit le
-- programme client.
--
-- Ce qui n'est PAS décidé ici (règle métier non tranchée — voir
-- ADDENDUM_CAHIER_DES_CHARGES.md) :
--   * la méthode d'arrondi de la TVA et le taux applicable (point d) : on
--     vérifie seulement l'arithmétique total = sous-total + TVA, jamais le
--     calcul de la TVA elle-même ;
--   * le plafond de vraisemblance d'une quantité vendue (point e).
--
-- Cycle 2 — chantier C1. Idempotent.
-- Pré-requis : db/outils/prevol.sql ne doit signaler aucune ligne en infraction.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- utilisateurs
-- ----------------------------------------------------------------------------
ALTER TABLE utilisateurs DROP CONSTRAINT IF EXISTS chk_utilisateurs_identifiant_non_vide;
ALTER TABLE utilisateurs ADD  CONSTRAINT chk_utilisateurs_identifiant_non_vide
  CHECK (length(btrim(identifiant)) > 0);

ALTER TABLE utilisateurs DROP CONSTRAINT IF EXISTS chk_utilisateurs_tentatives_positives;
ALTER TABLE utilisateurs ADD  CONSTRAINT chk_utilisateurs_tentatives_positives
  CHECK (tentatives_echouees >= 0);

-- Le responsable couvre les deux sites (site_id NULL) ; un agent est toujours
-- rattaché à un site. Sans cette règle, un agent « orphelin » passe au travers
-- de tout cloisonnement par site.
ALTER TABLE utilisateurs DROP CONSTRAINT IF EXISTS chk_utilisateurs_role_site;
ALTER TABLE utilisateurs ADD  CONSTRAINT chk_utilisateurs_role_site
  CHECK (
    (role =  'responsable' AND site_id IS NULL)
    OR
    (role <> 'responsable' AND site_id IS NOT NULL)
  );

-- ----------------------------------------------------------------------------
-- articles
-- ----------------------------------------------------------------------------
ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_quantite_positive;
ALTER TABLE articles ADD  CONSTRAINT chk_articles_quantite_positive
  CHECK (quantite_stock >= 0);

ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_prix_achat_positif;
ALTER TABLE articles ADD  CONSTRAINT chk_articles_prix_achat_positif
  CHECK (prix_achat >= 0);

ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_prix_vente_positif;
ALTER TABLE articles ADD  CONSTRAINT chk_articles_prix_vente_positif
  CHECK (prix_vente >= 0);

ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_seuil_positif;
ALTER TABLE articles ADD  CONSTRAINT chk_articles_seuil_positif
  CHECK (seuil_alerte >= 0);

ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_nom_non_vide;
ALTER TABLE articles ADD  CONSTRAINT chk_articles_nom_non_vide
  CHECK (length(btrim(nom)) > 0);

ALTER TABLE articles DROP CONSTRAINT IF EXISTS chk_articles_unite_non_vide;
ALTER TABLE articles ADD  CONSTRAINT chk_articles_unite_non_vide
  CHECK (length(btrim(unite)) > 0);

-- ----------------------------------------------------------------------------
-- mouvements_stock — la colonne « type » porte le sens ; la quantité est une
-- magnitude, toujours strictement positive.
-- ----------------------------------------------------------------------------
ALTER TABLE mouvements_stock DROP CONSTRAINT IF EXISTS chk_mouvements_quantite_positive;
ALTER TABLE mouvements_stock ADD  CONSTRAINT chk_mouvements_quantite_positive
  CHECK (quantite > 0);

-- ----------------------------------------------------------------------------
-- ventes
-- ----------------------------------------------------------------------------
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_montants_positifs;
ALTER TABLE ventes ADD  CONSTRAINT chk_ventes_montants_positifs
  CHECK (sous_total_ht >= 0 AND montant_tva >= 0 AND total_ttc >= 0);

ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_taux_tva_borne;
ALTER TABLE ventes ADD  CONSTRAINT chk_ventes_taux_tva_borne
  CHECK (taux_tva >= 0 AND taux_tva <= 100);

-- Arithmétique pure : le total est la somme de ses deux composantes. Ne
-- présuppose aucun taux ni aucune méthode d'arrondi (addendum, point d).
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_coherence_totaux;
ALTER TABLE ventes ADD  CONSTRAINT chk_ventes_coherence_totaux
  CHECK (total_ttc = sous_total_ht + montant_tva);

-- Taux nul ⇒ montant de TVA nul. Également de l'arithmétique, pas une règle
-- fiscale : permet d'exploiter l'application sans aucune TVA.
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_tva_nulle_si_taux_nul;
ALTER TABLE ventes ADD  CONSTRAINT chk_ventes_tva_nulle_si_taux_nul
  CHECK (taux_tva > 0 OR montant_tva = 0);

-- Le numéro de facture n'existe que pour une facture détaillée (commentaire du
-- schéma d'origine, repris au cahier des charges §3.3).
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_numero_facture_coherent;
ALTER TABLE ventes ADD  CONSTRAINT chk_ventes_numero_facture_coherent
  CHECK (
    (type_document = 'facture' AND numero_facture IS NOT NULL)
    OR
    (type_document = 'ticket'  AND numero_facture IS NULL)
  );

-- Une vente encaissée porte toujours qui a encaissé, quand, et comment.
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_payee_complete;
ALTER TABLE ventes ADD  CONSTRAINT chk_ventes_payee_complete
  CHECK (
    statut <> 'payee'
    OR (date_encaissement IS NOT NULL
        AND mode_paiement IS NOT NULL
        AND utilisateur_caisse_id IS NOT NULL)
  );

-- ----------------------------------------------------------------------------
-- ventes_lignes
-- ----------------------------------------------------------------------------
ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS chk_ventes_lignes_quantite_positive;
ALTER TABLE ventes_lignes ADD  CONSTRAINT chk_ventes_lignes_quantite_positive
  CHECK (quantite > 0);

ALTER TABLE ventes_lignes DROP CONSTRAINT IF EXISTS chk_ventes_lignes_prix_positif;
ALTER TABLE ventes_lignes ADD  CONSTRAINT chk_ventes_lignes_prix_positif
  CHECK (prix_unitaire >= 0);

-- ----------------------------------------------------------------------------
-- transactions
-- ----------------------------------------------------------------------------
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS chk_transactions_montant_positif;
ALTER TABLE transactions ADD  CONSTRAINT chk_transactions_montant_positif
  CHECK (montant > 0);

-- ----------------------------------------------------------------------------
-- employes / RH
-- ----------------------------------------------------------------------------
ALTER TABLE employes DROP CONSTRAINT IF EXISTS chk_employes_salaire_positif;
ALTER TABLE employes ADD  CONSTRAINT chk_employes_salaire_positif
  CHECK (salaire_mensuel >= 0);

ALTER TABLE absences_conges DROP CONSTRAINT IF EXISTS chk_absences_periode_coherente;
ALTER TABLE absences_conges ADD  CONSTRAINT chk_absences_periode_coherente
  CHECK (date_fin >= date_debut);

ALTER TABLE avances_salaire DROP CONSTRAINT IF EXISTS chk_avances_montant_positif;
ALTER TABLE avances_salaire ADD  CONSTRAINT chk_avances_montant_positif
  CHECK (montant > 0);

-- ----------------------------------------------------------------------------
-- comptages_stock
-- ----------------------------------------------------------------------------
ALTER TABLE comptages_stock DROP CONSTRAINT IF EXISTS chk_comptages_quantites_positives;
ALTER TABLE comptages_stock ADD  CONSTRAINT chk_comptages_quantites_positives
  CHECK (quantite_attendue >= 0 AND quantite_comptee >= 0);

INSERT INTO schema_migrations (version, nom)
VALUES ('001', 'contraintes_domaine')
ON CONFLICT (version) DO NOTHING;
