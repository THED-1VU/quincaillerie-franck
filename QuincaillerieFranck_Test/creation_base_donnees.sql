-- ============================================================
-- Ets Quincaillerie Franck — Base de données
-- Batouri, région de l'Est, Cameroun
-- Système : PostgreSQL
-- ============================================================

-- ------------------------------------------------------------
-- Table : sites
-- Les deux emplacements physiques (magasin de stock, comptoir)
-- ------------------------------------------------------------
CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO sites (nom) VALUES ('Magasin de stock'), ('Comptoir');

-- ------------------------------------------------------------
-- Table : utilisateurs
-- Chaque personne se connecte avec son propre identifiant.
-- Le role et le site déterminent ce qu'elle voit dans l'application.
-- role : 'responsable', 'agent_stock', 'agent_comptabilite'
-- ------------------------------------------------------------
CREATE TABLE utilisateurs (
    id SERIAL PRIMARY KEY,
    nom_complet VARCHAR(150) NOT NULL,
    identifiant VARCHAR(50) NOT NULL UNIQUE,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('responsable', 'agent_stock', 'agent_comptabilite')),
    site_id INTEGER REFERENCES sites(id),
    -- le responsable n'est rattaché à aucun site unique (accès à tous)
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    tentatives_echouees INTEGER NOT NULL DEFAULT 0,
    -- Invite à changer son mot de passe à la première connexion (voir
    -- ui/login_window.py et ui/dialogue_parametres.py) ; passe à FALSE
    -- dès que la question a été posée, qu'elle soit acceptée ou non.
    doit_changer_mot_de_passe BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Table : fournisseurs
-- ------------------------------------------------------------
CREATE TABLE fournisseurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(150) NOT NULL,
    contact VARCHAR(100),
    telephone VARCHAR(30)
);

-- ------------------------------------------------------------
-- Table : articles
-- Un article appartient toujours à un seul site.
-- Le ciment/fer du magasin n'apparaît jamais au catalogue du comptoir.
-- ------------------------------------------------------------
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(150) NOT NULL,
    categorie VARCHAR(80),
    unite VARCHAR(30) NOT NULL,              -- sac, barre, unité, m3, litre...
    prix_achat NUMERIC(12,2) NOT NULL DEFAULT 0,
    prix_vente NUMERIC(12,2) NOT NULL,
    quantite_stock INTEGER NOT NULL DEFAULT 0,
    seuil_alerte INTEGER NOT NULL DEFAULT 5,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    fournisseur_id INTEGER REFERENCES fournisseurs(id),
    date_creation TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_articles_site ON articles(site_id);

-- ------------------------------------------------------------
-- Table : mouvements_stock
-- Historique des entrées et sorties de stock (pas de transfert entre sites)
-- ------------------------------------------------------------
CREATE TABLE mouvements_stock (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    type VARCHAR(20) NOT NULL CHECK (type IN ('entree', 'sortie')),
    quantite INTEGER NOT NULL,
    motif VARCHAR(200),
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_mouvement TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mouvements_article ON mouvements_stock(article_id);
CREATE INDEX idx_mouvements_date ON mouvements_stock(date_mouvement);

-- ------------------------------------------------------------
-- Table : historique_prix_articles
-- Traçabilité des changements de prix (achat/vente) sur un article
-- existant : qui a changé quoi, quand, de quel montant à quel montant.
-- Sans cela, un prix modifié en douce ouvre la porte au vol — voir
-- modules/articles.py (modifier_article) et ui/formulaire_article.py
-- (qui réserve la modification des prix au responsable).
-- ------------------------------------------------------------
CREATE TABLE historique_prix_articles (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    ancien_prix_achat NUMERIC(12,2) NOT NULL,
    nouveau_prix_achat NUMERIC(12,2) NOT NULL,
    ancien_prix_vente NUMERIC(12,2) NOT NULL,
    nouveau_prix_vente NUMERIC(12,2) NOT NULL,
    date_modification TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Table : historique_modifications_articles
-- Même principe que ci-dessus, mais pour les autres champs qu'un
-- agent stock peut modifier (nom, unité, seuil d'alerte) : sans trace,
-- impossible de savoir qui a changé un seuil ou renommé un article,
-- et quand. Une ligne par champ modifié à chaque enregistrement.
-- ------------------------------------------------------------
CREATE TABLE historique_modifications_articles (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    champ VARCHAR(30) NOT NULL,
    ancienne_valeur VARCHAR(200),
    nouvelle_valeur VARCHAR(200),
    date_modification TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_historique_modif_article ON historique_modifications_articles(article_id);

CREATE INDEX idx_historique_prix_article ON historique_prix_articles(article_id);

-- ------------------------------------------------------------
-- Table : ventes
-- Une vente peut être imprimée en ticket rapide ou en facture détaillée.
-- numero_facture n'est rempli que pour les factures détaillées.
--
-- Circuit réel de la boutique : la comptabilité enregistre la commande
-- du client (statut 'en_attente', le stock est retiré immédiatement) ;
-- le client va ensuite payer à la caisse, tenue par le responsable, qui
-- encaisse (statut passe à 'payee' — c'est seulement à ce moment que la
-- vente compte dans les recettes). Une commande non payée peut être
-- annulée (statut 'annulee'), ce qui restitue le stock.
-- ------------------------------------------------------------
CREATE TABLE ventes (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    type_document VARCHAR(20) NOT NULL DEFAULT 'ticket' CHECK (type_document IN ('ticket', 'facture')),
    numero_facture VARCHAR(30) UNIQUE,        -- ex : 2026-0842, rempli si type_document = 'facture'
    statut VARCHAR(20) NOT NULL DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'payee', 'annulee')),
    utilisateur_caisse_id INTEGER REFERENCES utilisateurs(id),  -- qui a encaissé (rempli à l'encaissement)
    mode_paiement VARCHAR(30) CHECK (
        mode_paiement IN ('especes', 'orange_money', 'mtn_momo', 'credit_client', 'autre')
    ),  -- rempli à l'encaissement, voir modules/paiement.py
    sous_total_ht NUMERIC(12,2) NOT NULL,
    taux_tva NUMERIC(5,2) NOT NULL DEFAULT 0,
    montant_tva NUMERIC(12,2) NOT NULL,
    total_ttc NUMERIC(12,2) NOT NULL,
    date_vente TIMESTAMP NOT NULL DEFAULT NOW(),
    date_encaissement TIMESTAMP
);

CREATE INDEX idx_ventes_site ON ventes(site_id);
CREATE INDEX idx_ventes_date ON ventes(date_vente);
CREATE INDEX idx_ventes_statut ON ventes(statut);

-- ------------------------------------------------------------
-- Table : ventes_lignes
-- Détail des articles vendus dans chaque vente
-- ------------------------------------------------------------
CREATE TABLE ventes_lignes (
    id SERIAL PRIMARY KEY,
    vente_id INTEGER NOT NULL REFERENCES ventes(id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    quantite INTEGER NOT NULL,
    prix_unitaire NUMERIC(12,2) NOT NULL
);

CREATE INDEX idx_ventes_lignes_vente ON ventes_lignes(vente_id);

-- ------------------------------------------------------------
-- Table : transactions
-- Recettes et dépenses comptables (les ventes y créent une ligne automatiquement)
-- ------------------------------------------------------------
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    type VARCHAR(20) NOT NULL CHECK (type IN ('recette', 'depense')),
    montant NUMERIC(12,2) NOT NULL,
    description VARCHAR(200),
    vente_id INTEGER REFERENCES ventes(id),   -- rempli si la transaction vient d'une vente
    employe_id INTEGER,                       -- rempli si la dépense est un salaire (voir employes ci-dessous)
    date_transaction TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_site ON transactions(site_id);
CREATE INDEX idx_transactions_date ON transactions(date_transaction);

-- ------------------------------------------------------------
-- Volet RH — réservé au responsable (voir modules/rh.py) :
-- fiche employé, absences/congés, avances sur salaire. Le paiement du
-- salaire lui-même reste une dépense normale (table transactions),
-- simplement rattachée à l'employé via transactions.employe_id, pour
-- que la comptabilité ait une vraie traçabilité au lieu d'un texte libre.
-- ------------------------------------------------------------
CREATE TABLE employes (
    id SERIAL PRIMARY KEY,
    nom_complet VARCHAR(150) NOT NULL,
    poste VARCHAR(100),
    telephone VARCHAR(30),
    type_contrat VARCHAR(20) NOT NULL DEFAULT 'permanent'
        CHECK (type_contrat IN ('permanent', 'temporaire')),
    salaire_mensuel NUMERIC(12,2) NOT NULL DEFAULT 0,
    site_id INTEGER REFERENCES sites(id),
    date_embauche DATE,
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE transactions
    ADD CONSTRAINT fk_transactions_employe FOREIGN KEY (employe_id) REFERENCES employes(id);

CREATE TABLE absences_conges (
    id SERIAL PRIMARY KEY,
    employe_id INTEGER NOT NULL REFERENCES employes(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL CHECK (type IN ('absence', 'conge')),
    date_debut DATE NOT NULL,
    date_fin DATE NOT NULL,
    motif VARCHAR(200),
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_creation TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_absences_conges_employe ON absences_conges(employe_id);

CREATE TABLE avances_salaire (
    id SERIAL PRIMARY KEY,
    employe_id INTEGER NOT NULL REFERENCES employes(id) ON DELETE CASCADE,
    montant NUMERIC(12,2) NOT NULL,
    motif VARCHAR(200),
    remboursee BOOLEAN NOT NULL DEFAULT FALSE,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    date_avance TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_avances_salaire_employe ON avances_salaire(employe_id);

-- ------------------------------------------------------------
-- Table : comptages_stock
-- Inventaire physique (matin/soir), article par article, fait par
-- l'agent stock — jamais par la comptabilité, qui n'a pas à voir les
-- quantités en stock. quantite_attendue est une copie figée de
-- articles.quantite_stock au moment du comptage (pas une valeur
-- recalculée après coup) : ça permet de savoir exactement ce qui était
-- attendu ce jour-là, même si le stock a bougé depuis. ecart < 0 =
-- marchandise manquante (voir modules/inventaire.py).
-- ------------------------------------------------------------
CREATE TABLE comptages_stock (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id),
    moment VARCHAR(10) NOT NULL CHECK (moment IN ('matin', 'soir')),
    quantite_attendue INTEGER NOT NULL,
    quantite_comptee INTEGER NOT NULL,
    ecart INTEGER NOT NULL,
    date_comptage TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_comptages_stock_article ON comptages_stock(article_id);
CREATE INDEX idx_comptages_stock_date ON comptages_stock(date_comptage);

-- ============================================================
-- Fin du script
-- ============================================================
